import { useCallback, useEffect, useRef, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? 'test-key';

export type StepStatus = 'pending' | 'active' | 'done';
export type PipelineStatus = 'idle' | 'running' | 'paused' | 'done' | 'error';

export interface StepInfo {
  label: string;
  status: StepStatus;
}

interface StepConfig {
  startPct: number;
  endPct: number;
  /** Estimated duration in ms for the animation to reach 95% of the step range */
  estMs: number;
}

const STEP_CONFIGS: StepConfig[] = [
  { startPct: 0,     endPct: 5,     estMs: 15_000  }, // step 1: extract
  { startPct: 5,     endPct: 23.33, estMs: 45_000  }, // step 2: strategy
  { startPct: 23.33, endPct: 63.33, estMs: 180_000 }, // step 3: generate
  { startPct: 63.33, endPct: 81.67, estMs: 3_000   }, // step 4: shuffle
  { startPct: 81.67, endPct: 100,   estMs: 60_000  }, // step 5: submit
];

const STEP_LABELS = [
  'Extract form',
  'Generate strategy',
  'Generate responses',
  'Shuffle responses',
  'Submit responses',
];

const TICK_MS = 100;

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
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StepInfo[]>(makeSteps());
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0); // steps completed so far

  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const appendLog = useCallback((msg: string) => {
    setLog((prev) => [...prev, msg]);
  }, []);

  const stopAnimation = useCallback(() => {
    if (animRef.current !== null) {
      clearInterval(animRef.current);
      animRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopAnimation();
      stopStream();
    };
  }, [stopAnimation, stopStream]);

  /** Animate progress from current value toward the ceiling of a step */
  const animateStep = useCallback(
    (stepIdx: number) => {
      stopAnimation();
      const cfg = STEP_CONFIGS[stepIdx];
      const ceiling = cfg.startPct + (cfg.endPct - cfg.startPct) * 0.95;
      const totalIncrement = ceiling - cfg.startPct;
      const ticks = cfg.estMs / TICK_MS;
      const perTick = totalIncrement / ticks;

      setProgress(cfg.startPct);

      animRef.current = setInterval(() => {
        setProgress((prev) => {
          const next = prev + perTick;
          if (next >= ceiling) {
            stopAnimation();
            return ceiling;
          }
          return next;
        });
      }, TICK_MS);
    },
    [stopAnimation],
  );

  /** Snap progress to the exact end of a step */
  const snapStep = useCallback((stepIdx: number) => {
    stopAnimation();
    setProgress(STEP_CONFIGS[stepIdx].endPct);
  }, [stopAnimation]);

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
        const url = `${API_URL}/stream/${jobId}?x_api_key=${encodeURIComponent(API_KEY)}`;
        // SSE doesn't support custom headers, so we pass the key as a query param.
        // The backend currently uses the Header() mechanism; we need to proxy or
        // adjust. For now, use fetch-based polling fallback via EventSource with
        // the key in the URL only if backend supports it. We'll use a fetch stream.
        void url; // suppress unused warning; we use fetch below

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
                    animateStep(stepIdx);
                  } else if (event.status === 'done') {
                    snapStep(stepIdx);
                    completeStep(stepIdx);
                  }
                  if (event.message) appendLog(event.message as string);
                } else if (event.type === 'step_complete') {
                  // step-by-step mode: step finished, wait for user
                  resolve();
                } else if (event.type === 'done') {
                  appendLog(`Pipeline complete — ${event.total} responses submitted.`);
                  setStatus('done');
                  setProgress(100);
                  setSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
                  resolve();
                } else if (event.type === 'error') {
                  appendLog(`Error: ${event.message}`);
                  setError(event.message as string);
                  setStatus('error');
                  stopAnimation();
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
    [activateStep, animateStep, appendLog, completeStep, getToken, snapStep, stopAnimation, stopStream],
  );

  // ─── Public actions ─────────────────────────────────────────────────────────

  const startFullPipeline = useCallback(
    async (formUrl: string, totalResponses: number, model: string) => {
      setStatus('running');
      setProgress(0);
      setSteps(makeSteps());
      setLog([]);
      setError(null);
      appendLog('Starting full pipeline...');

      const res = await fetch(`${API_URL}/run`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({ form_url: formUrl, total_responses: totalResponses, model }),
      });
      if (!res.ok) throw new Error(`Failed to start: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      await openStream(job_id);
    },
    [appendLog, openStream],
  );

  const createSession = useCallback(
    async (formUrl: string, totalResponses: number, model: string) => {
      setStatus('running');
      setProgress(0);
      setSteps(makeSteps());
      setLog([]);
      setError(null);
      setCurrentStep(0);
      appendLog('Starting session...');

      const res = await fetch(`${API_URL}/session`, {
        method: 'POST',
        headers: await buildHeaders(getToken),
        body: JSON.stringify({ form_url: formUrl, total_responses: totalResponses, model }),
      });
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
        appendLog(`Step ${step} complete. Ready for step ${step + 1}.`);
      }
    },
    [appendLog, openStream],
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
      appendLog(`Step ${step} complete. Ready for step ${step + 1}.`);
    }
  }, [appendLog, openStream, sessionId]);

  const reset = useCallback(() => {
    stopAnimation();
    stopStream();
    setStatus('idle');
    setProgress(0);
    setSteps(makeSteps());
    setLog([]);
    setError(null);
    setSessionId(null);
    setCurrentStep(0);
  }, [stopAnimation, stopStream]);

  return {
    status,
    progress,
    steps,
    log,
    error,
    sessionId,
    currentStep,
    startFullPipeline,
    createSession,
    advanceSession,
    reset,
  };
}
