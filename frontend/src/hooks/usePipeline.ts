import { useCallback, useEffect, useRef, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type StepStatus = 'pending' | 'active' | 'done';
export type PipelineStatus = 'idle' | 'running' | 'paused' | 'done' | 'error' | 'blocked';

export interface StepInfo {
  label: string;
  status: StepStatus;
}

const STEP_LABELS = [
  'Extract form',
  'Generate strategy',
  'Generate responses',
  'Shuffle responses',
  'Submit responses',
];

function makeSteps(): StepInfo[] {
  return STEP_LABELS.map((label) => ({ label, status: 'pending' as StepStatus }));
}

async function buildHeaders(getToken: () => Promise<string>): Promise<Record<string, string>> {
  const token = await getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export function usePipeline(getToken: () => Promise<string>) {
  const [status, setStatus] = useState<PipelineStatus>('idle');
  const [steps, setSteps] = useState<StepInfo[]>(makeSteps());
  const [log, setLog] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0); // steps completed so far
  const [submitProgress, setSubmitProgress] = useState<{
    current: number;
    total: number;
    batch?: number;
    totalBatches?: number;
  } | null>(null);
  const [resultId, setResultId] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);

  const appendLog = useCallback((msg: string) => {
    setLog((prev) => [...prev, msg]);
  }, []);

  const stopStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  /** Mark a step as active in the step list */
  const activateStep = useCallback((stepIdx: number) => {
    setSteps((prev) =>
      prev.map((s, i) => ({
        ...s,
        status: i === stepIdx ? 'active' : i < stepIdx ? 'done' : 'pending',
      })),
    );
  }, []);

  /** Mark a step as done in the step list */
  const completeStep = useCallback((stepIdx: number) => {
    setSteps((prev) =>
      prev.map((s, i) => ({
        ...s,
        status: i <= stepIdx ? 'done' : 'pending',
      })),
    );
  }, []);

  /** Open an SSE stream for a job and resolve events */
  const openStream = useCallback(
    (jobId: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        stopStream();

        const controller = new AbortController();
        esRef.current = { close: () => controller.abort() } as unknown as EventSource;

        buildHeaders(getToken)
          .then((hdrs) =>
            fetch(`${API_URL}/stream/${jobId}`, {
              headers: hdrs,
              signal: controller.signal,
            })
          )
          .then(async (res) => {
            if (!res.ok || !res.body) throw new Error(`Stream error: ${res.status}`);
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              const parts = buffer.split('\n\n');
              buffer = parts.pop() ?? '';

              for (const part of parts) {
                const line = part.trim();
                if (!line.startsWith('data:')) continue;
                const raw = line.slice(5).trim();
                let event: Record<string, unknown>;
                try {
                  event = JSON.parse(raw);
                } catch {
                  continue;
                }

                if (event.type === 'step') {
                  const stepIdx = (event.step as number) - 1;
                  if (event.status === 'start') {
                    activateStep(stepIdx);
                  } else if (event.status === 'done') {
                    completeStep(stepIdx);
                  }
                  if (event.message) appendLog(event.message as string);
                } else if (event.type === 'message') {
                  appendLog(event.text as string);
                } else if (event.type === 'submit_progress') {
                  setSubmitProgress({
                    current: event.current as number,
                    total: event.total as number,
                    batch: event.batch as number | undefined,
                    totalBatches: event.total_batches as number | undefined,
                  });
                } else if (event.type === 'result') {
                  setResults((prev) => ({ ...prev, [event.key as string]: event.data }));
                } else if (event.type === 'step_complete') {
                  // step-by-step mode: step finished, wait for user
                  resolve();
                } else if (event.type === 'done') {
                  appendLog(`Pipeline complete — ${event.total} responses submitted.`);
                  setSubmitProgress(null);
                  setStatus('done');
                  setSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
                  if (event.result_id) setResultId(event.result_id as string);
                  if (event.session_id) setSessionId(event.session_id as string);
                  resolve();
                } else if (event.type === 'error') {
                  appendLog(`Error: ${event.message}`);
                  setError(event.message as string);
                  setStatus('error');
                  reject(new Error(event.message as string));
                }
              }
            }
          })
          .catch((err: Error) => {
            if (err.name !== 'AbortError') {
              setError(err.message);
              setStatus('error');
              reject(err);
            }
          });
      });
    },
    [activateStep, appendLog, completeStep, getToken, stopStream],
  );

  // ─── Public actions ─────────────────────────────────────────────────────────

  const startFullPipeline = useCallback(
    async (formUrl: string, totalResponses: number) => {
      setStatus('running');
      setSteps(makeSteps());
      setLog([]);
      setResults({});
      setError(null);

      const res = await fetch(`${API_URL}/run`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({ form_url: formUrl, total_responses: totalResponses }),
      });
      if (res.status === 402) {
        setStatus('blocked');
        return;
      }
      if (!res.ok) throw new Error(`Failed to start: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      await openStream(job_id);
    },
    [appendLog, getToken, openStream],
  );

  const createSession = useCallback(
    async (formUrl: string, totalResponses: number) => {
      setStatus('running');
      setSteps(makeSteps());
      setLog([]);
      setResults({});
      setError(null);
      setCurrentStep(0);

      const res = await fetch(`${API_URL}/session`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({ form_url: formUrl, total_responses: totalResponses }),
      });
      if (res.status === 402) {
        setStatus('blocked');
        return;
      }
      if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
      const { session_id } = (await res.json()) as { session_id: string };
      setSessionId(session_id);

      // Immediately run step 1 using session_id directly (state update is async)
      const advRes = await fetch(`${API_URL}/session/${session_id}/advance`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
      });
      if (!advRes.ok) throw new Error(`Failed to advance: ${advRes.status}`);
      const { job_id, step } = (await advRes.json()) as { job_id: string; step: number };

      await openStream(job_id);

      setCurrentStep(step);
      if (step < 5) {
        setStatus('paused');
      }
    },
    [appendLog, getToken, openStream],
  );

  const advanceSession = useCallback(async () => {
    if (!sessionId) return;
    setStatus('running');

    const res = await fetch(`${API_URL}/session/${sessionId}/advance`, {
      method: 'POST',
      headers: await buildHeaders(getToken),
    });
    if (!res.ok) throw new Error(`Failed to advance: ${res.status}`);
    const { job_id, step } = (await res.json()) as { job_id: string; step: number };

    await openStream(job_id);

    // After stream resolves the step is done
    setCurrentStep(step);
    if (step < 5) {
      setStatus('paused');
    }
  }, [appendLog, getToken, openStream, sessionId]);

  const reset = useCallback(() => {
    stopStream();
    setStatus('idle');
    setSteps(makeSteps());
    setLog([]);
    setResults({});
    setError(null);
    setSessionId(null);
    setCurrentStep(0);
    setSubmitProgress(null);
    setResultId(null);
  }, [stopStream]);

  const resubmit = useCallback(
    async (totalResponses: number) => {
      setStatus('running');
      setLog([]);
      setError(null);
      setSubmitProgress(null);
      // Reset only submit step to pending so stepper shows re-submission
      setSteps((prev) =>
        prev.map((s, i) => (i === 4 ? { ...s, status: 'pending' } : s)),
      );

      let res: Response;
      // Prefer session resubmit if we have a live session, else fall back to result_id
      if (sessionId) {
        res = await fetch(`${API_URL}/session/${sessionId}/resubmit`, {
          method: 'POST',
          headers: await buildHeaders(getToken),
          body: JSON.stringify({ total_responses: totalResponses }),
        });
      } else if (resultId) {
        res = await fetch(`${API_URL}/resubmit`, {
          method: 'POST',
          headers: await buildHeaders(getToken),
          body: JSON.stringify({ result_id: resultId, total_responses: totalResponses }),
        });
      } else {
        setError('No completed pipeline result to resubmit.');
        setStatus('error');
        return;
      }

      if (!res.ok) throw new Error(`Resubmit failed: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      await openStream(job_id);
    },
    [getToken, openStream, resultId, sessionId],
  );

  const resubmitFromHistory = useCallback(
    async (pipelineId: string, totalResponses: number) => {
      setStatus('running');
      setSteps(makeSteps());
      setLog([]);
      setResults({});
      setError(null);
      setSubmitProgress(null);
      setResultId(null);
      setSessionId(null);

      const res = await fetch(`${API_URL}/history/${pipelineId}/resubmit`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({ total_responses: totalResponses }),
      });
      if (!res.ok) throw new Error(`History resubmit failed: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      await openStream(job_id);
    },
    [getToken, openStream],
  );

  return {
    status,
    steps,
    log,
    results,
    error,
    sessionId,
    currentStep,
    submitProgress,
    resultId,
    startFullPipeline,
    createSession,
    advanceSession,
    resubmit,
    resubmitFromHistory,
    reset,
  };
}
