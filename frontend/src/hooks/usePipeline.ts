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
  'Pobieranie formularza',
  'Generowanie strategii',
  'Generowanie odpowiedzi',
  'Mieszanie odpowiedzi',
  'Wysyłanie odpowiedzi',
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

// ─── Pending-pipeline persistence (localStorage) ────────────────────────────
// The backend pipeline record is authoritative (Firestore); localStorage only remembers
// *what the user was doing* so a reload or the Stripe redirect can restore the preview and
// resume the submit. Holds no business data beyond the id + the user's choices.
const PENDING_KEY = 'forms-autofill:pending';

export interface PendingPipeline {
  pipelineId: string;
  count: number;
  selectedCodes?: string[];
}

function loadPending(): PendingPipeline | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    return raw ? (JSON.parse(raw) as PendingPipeline) : null;
  } catch {
    return null;
  }
}

function savePending(p: PendingPipeline): void {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable — non-fatal */
  }
}

function mergePending(patch: Partial<PendingPipeline>): void {
  const current = loadPending();
  if (!current) return;
  savePending({ ...current, ...patch });
}

function clearPending(): void {
  try {
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* no-op */
  }
}

export function usePipeline(getToken: () => Promise<string>) {
  const [status, setStatus] = useState<PipelineStatus>('idle');
  const [steps, setSteps] = useState<StepInfo[]>(makeSteps());
  const [log, setLog] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [defaultSelectedCodes, setDefaultSelectedCodes] = useState<string[] | null>(null);
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
              if (done) {
                // Stream closed without a terminal 'done'/'error' event — settle so the
                // caller never hangs. A no-op if the promise was already resolved/rejected.
                reject(new Error('Połączenie przerwane przed zakończeniem'));
                break;
              }
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
      setDefaultSelectedCodes(null);
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
      if (!res.ok) throw new Error(`Błąd uruchamiania podglądu: ${res.status}`);
      const { job_id, pipeline_id } = (await res.json()) as {
        job_id: string;
        pipeline_id: string;
      };
      setPipelineId(pipeline_id);
      await openStream(job_id);
      setStatus('preview');
      // Remember the run so a reload / Stripe redirect can restore this preview.
      savePending({ pipelineId: pipeline_id, count: totalResponses });
    },
    [getToken, openStream],
  );

  /**
   * Restore a preview-ready pipeline from localStorage + the backend store (no re-run).
   * Returns the pending intent (incl. count and selected personas) when it restored, else null.
   */
  const restore = useCallback(async (): Promise<PendingPipeline | null> => {
    const pending = loadPending();
    if (!pending) return null;
    try {
      const res = await fetch(`${API_URL}/pipelines/${pending.pipelineId}`, {
        headers: await buildHeaders(getToken),
      });
      if (!res.ok) {
        clearPending();
        return null;
      }
      const data = (await res.json()) as {
        status: string;
        preview: PreviewData | null;
      };
      if (!data.preview) {
        clearPending();
        return null;
      }
      setPipelineId(pending.pipelineId);
      setPreview(data.preview);
      setSteps((prev) =>
        prev.map((s, i) => (i <= 1 ? { ...s, status: 'done' } : { ...s, status: 'pending' })),
      );
      setStatus('preview');
      return pending;
    } catch {
      return null;
    }
  }, [getToken]);

  /**
   * Load a pipeline from history (by id) without touching localStorage as a source.
   * Returns the response count so the caller can sync its own count state.
   */
  const loadFromHistory = useCallback(
    async (pipelineId: string): Promise<number> => {
      setLog([]);
      setResults({});
      setError(null);
      setSubmitProgress(null);

      const res = await fetch(`${API_URL}/pipelines/${pipelineId}`, {
        headers: await buildHeaders(getToken),
      });
      if (!res.ok) throw new Error(`Błąd ładowania potoku: ${res.status}`);
      const data = (await res.json()) as {
        status: string;
        preview: PreviewData | null;
        total_responses: number;
        selected_persona_codes: string[] | null;
      };
      if (!data.preview) throw new Error('Brak podglądu dla tego potoku');

      setPipelineId(pipelineId);
      setPreview(data.preview);
      setDefaultSelectedCodes(data.selected_persona_codes ?? null);
      setSteps((prev) =>
        prev.map((s, i) => (i <= 1 ? { ...s, status: 'done' } : { ...s, status: 'pending' })),
      );
      setStatus('preview');
      savePending({ pipelineId, count: data.total_responses });
      return data.total_responses;
    },
    [getToken],
  );

  /** Paid phase: generate + submit responses for the selected personas. */
  const submitResponses = useCallback(
    async (selectedCodes: string[], totalResponses: number): Promise<boolean> => {
      if (!pipelineId) return false;
      // Persist the chosen personas so a Stripe redirect mid-paywall can resume this submit.
      mergePending({ selectedCodes });
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
      if (!res.ok) throw new Error(`Błąd wysyłania: ${res.status}`);
      const { job_id } = (await res.json()) as { job_id: string };
      const doneEvent = await openStream(job_id);
      appendLog(`Pipeline complete — ${doneEvent.total} responses submitted.`);
      setSubmitProgress(null);
      setSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
      setStatus('done');
      clearPending();
      return true;
    },
    [appendLog, getToken, openStream, pipelineId],
  );

  const reset = useCallback(() => {
    stopStream();
    clearPending();
    setStatus('idle');
    setSteps(makeSteps());
    setLog([]);
    setResults({});
    setPreview(null);
    setDefaultSelectedCodes(null);
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
    defaultSelectedCodes,
    pipelineId,
    submitProgress,
    startPreview,
    submitResponses,
    restore,
    loadFromHistory,
    reset,
    setStatus,
  };
}
