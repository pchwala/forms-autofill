import { useCallback, useEffect, useRef, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type StepStatus = 'pending' | 'active' | 'done';
export type PipelineStatus =
  | 'idle'
  | 'running'    // preview phase: extracting + generating strategy
  | 'preview'    // strategy ready, awaiting persona selection / payment
  | 'submitting' // paid phase: generating + submitting responses
  | 'done'
  | 'error'
  | 'blocked';   // no credits — paywall

export interface StepInfo {
  label: string;
  status: StepStatus;
}

/** Aggregate distribution for one preview question. */
export interface PreviewDistribution {
  id: string;
  label: string;
  type: string;
  options: { option: string; percent: number }[];
  skipped_percent: number;
}

export interface PreviewPersona {
  code: string;
  name: string;
  description: string;
  count_percent: number;
}

export interface PreviewQuestion {
  id: string;
  label: string;
  type: string;
  options: string[];
  per_persona: Record<string, Record<string, number> | null>;
}

export interface PreviewData {
  personas: PreviewPersona[];
  questions: PreviewQuestion[];
  distributions: PreviewDistribution[];
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
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [submitProgress, setSubmitProgress] = useState<{
    current: number;
    total: number;
    batch?: number;
    totalBatches?: number;
  } | null>(null);

  const esRef = useRef<{ close: () => void } | null>(null);

  const appendLog = useCallback((msg: string) => {
    setLog((prev) => [...prev, msg]);
  }, []);

  const stopStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => () => stopStream(), [stopStream]);

  const activateStep = useCallback((stepIdx: number) => {
    setSteps((prev) =>
      prev.map((s, i) => ({
        ...s,
        status: i === stepIdx ? 'active' : i < stepIdx ? 'done' : s.status,
      })),
    );
  }, []);

  const completeStep = useCallback((stepIdx: number) => {
    setSteps((prev) =>
      prev.map((s, i) => (i <= stepIdx ? { ...s, status: 'done' } : s)),
    );
  }, []);

  /** Open an SSE stream for a job. Resolves with the final 'done' event payload. */
  const openStream = useCallback(
    (jobId: string): Promise<Record<string, unknown>> => {
      return new Promise((resolve, reject) => {
        stopStream();
        const controller = new AbortController();
        esRef.current = { close: () => controller.abort() };

        buildHeaders(getToken)
          .then((hdrs) =>
            fetch(`${API_URL}/stream/${jobId}`, { headers: hdrs, signal: controller.signal }),
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
                let event: Record<string, unknown>;
                try {
                  event = JSON.parse(line.slice(5).trim());
                } catch {
                  continue;
                }

                if (event.type === 'step') {
                  const stepIdx = (event.step as number) - 1;
                  if (event.status === 'start') activateStep(stepIdx);
                  else if (event.status === 'done') completeStep(stepIdx);
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
                  if (event.key === 'preview') setPreview(event.data as PreviewData);
                  setResults((prev) => ({ ...prev, [event.key as string]: event.data }));
                } else if (event.type === 'done') {
                  resolve(event);
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

  /** Free phase: run extract + strategy, then surface the preview. */
  const startPreview = useCallback(
    async (formUrl: string, totalResponses: number, desirePrompt: string) => {
      setStatus('running');
      setSteps(makeSteps());
      setLog([]);
      setResults({});
      setPreview(null);
      setPipelineId(null);
      setSubmitProgress(null);
      setError(null);

      const res = await fetch(`${API_URL}/preview`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({
          form_url: formUrl,
          total_responses: totalResponses,
          desire_prompt: desirePrompt.trim() || null,
        }),
      });
      if (!res.ok) throw new Error(`Failed to start preview: ${res.status}`);
      const { job_id, pipeline_id } = (await res.json()) as {
        job_id: string;
        pipeline_id: string;
      };
      setPipelineId(pipeline_id);
      await openStream(job_id);
      setStatus('preview');
    },
    [getToken, openStream],
  );

  /** Paid phase: generate + submit responses for the selected personas. */
  const submitResponses = useCallback(
    async (selectedCodes: string[], totalResponses: number): Promise<boolean> => {
      if (!pipelineId) return false;
      setStatus('submitting');
      setError(null);
      setSubmitProgress(null);
      // Reset the generate/shuffle/submit steps so the stepper shows them re-running.
      setSteps((prev) =>
        prev.map((s, i) => (i >= 2 ? { ...s, status: 'pending' } : { ...s, status: 'done' })),
      );

      const res = await fetch(`${API_URL}/pipelines/${pipelineId}/submit`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({
          selected_persona_codes: selectedCodes,
          total_responses: totalResponses,
        }),
      });
      if (res.status === 402) {
        setStatus('blocked');
        return false;
      }
      if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      const doneEvent = await openStream(job_id);
      appendLog(`Pipeline complete — ${doneEvent.total} responses submitted.`);
      setSubmitProgress(null);
      setSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
      setStatus('done');
      return true;
    },
    [appendLog, getToken, openStream, pipelineId],
  );

  const reset = useCallback(() => {
    stopStream();
    setStatus('idle');
    setSteps(makeSteps());
    setLog([]);
    setResults({});
    setPreview(null);
    setPipelineId(null);
    setSubmitProgress(null);
    setError(null);
  }, [stopStream]);

  return {
    status,
    steps,
    log,
    results,
    error,
    preview,
    pipelineId,
    submitProgress,
    startPreview,
    submitResponses,
    reset,
    setStatus,
  };
}
