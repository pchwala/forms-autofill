import { useState } from 'react';
import { keyframes } from '@mui/system';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import InputForm from '../InputForm';
import PreviewResults from '../PreviewResults';
import PipelineProgress from '../PipelineProgress';
import type { PipelineStatus, PreviewData, StepInfo } from '../../hooks/usePipeline';

interface SubmitProgress {
  current: number;
  total: number;
  batch?: number;
  totalBatches?: number;
}

interface Props {
  status: PipelineStatus;
  steps: StepInfo[];
  log: string[];
  results: Record<string, unknown>;
  error: string | null;
  preview: PreviewData | null;
  submitProgress: SubmitProgress | null;
  count: number;
  hasTokens: boolean;
  defaultSelectedCodes?: string[] | null;
  onStart: (url: string, count: number, desirePrompt: string) => void;
  onSubmit: (selectedCodes: string[]) => void;
  onReset: () => void;
}

export default function PipelineSection({
  status,
  steps,
  log,
  results,
  error,
  preview,
  submitProgress,
  count,
  hasTokens,
  defaultSelectedCodes,
  onStart,
  onSubmit,
  onReset,
}: Props) {
  const [reviewOpen, setReviewOpen] = useState(false);

  const isIdle = status === 'idle';
  const isRunning = status === 'running';
  const isPreview = status === 'preview';
  const isSubmitting = status === 'submitting';
  const isDone = status === 'done';
  const isError = status === 'error';
  const busy = isRunning || isSubmitting;

  return (
    <>
      <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
        Rozpocznij proces
      </Typography>
      <Paper variant="outlined" sx={{ p: 3, mt: 1.5, mb: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Input form — hidden once we have a preview to focus on */}
        {(isIdle || isRunning) && <InputForm onStart={onStart} disabled={busy} />}

        {/* Stepper while anything is running */}
        {(isRunning || isSubmitting || isDone) && (
          <>
            <Divider />
            <PipelineProgress steps={steps} />
          </>
        )}

        {/* Live status line */}
        {(log.length > 0 || submitProgress) && !isPreview && (
          <Typography
            variant="body2"
            sx={
              busy
                ? {
                    fontFamily: 'monospace',
                    color: 'transparent',
                    background: 'linear-gradient(90deg, #888 20%, #ddd 50%, #888 80%)',
                    backgroundSize: '250% 100%',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                    animation: `${keyframes`
                      from { background-position: 240% 0%; }
                      to   { background-position: -100% 0%; }
                    `} 4s linear infinite`,
                  }
                : { fontFamily: 'monospace', color: 'text.secondary' }
            }
          >
            {submitProgress
              ? (() => {
                  const batchInfo =
                    submitProgress.totalBatches && submitProgress.totalBatches > 1
                      ? `Partia ${submitProgress.batch}/${submitProgress.totalBatches} — `
                      : '';
                  return `${batchInfo}Wysyłanie odpowiedzi do formularza Google — ${submitProgress.current}/${submitProgress.total}`;
                })()
              : log[log.length - 1]}
          </Typography>
        )}

        {/* Preview / persona selection */}
        {isPreview && preview && (
          <PreviewResults
            preview={preview}
            count={count}
            hasTokens={hasTokens}
            busy={busy}
            defaultSelectedCodes={defaultSelectedCodes}
            onSubmit={onSubmit}
          />
        )}

        {/* Done */}
        {isDone && (
          <Alert severity="success">Przetwarzanie zakończone — wszystkie odpowiedzi zostały pomyślnie wysłane.</Alert>
        )}

        {/* Error */}
        {isError && <Alert severity="error">{error ?? 'Wystąpił nieoczekiwany błąd.'}</Alert>}

        {/* Controls */}
        {!isIdle && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={() => setReviewOpen(true)}
              disabled={Object.keys(results).length === 0}
            >
              Szczegóły
            </Button>
            <Button variant="outlined" color="error" onClick={onReset} disabled={busy}>
              Zacznij od nowa
            </Button>
          </Box>
        )}
      </Paper>

      {/* Raw JSON dialog */}
      <Dialog open={reviewOpen} onClose={() => setReviewOpen(false)} maxWidth="md" fullWidth scroll="paper">
        <DialogTitle>Szczegóły</DialogTitle>
        <DialogContent dividers>
          {Object.keys(results).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Brak wyników JSON.
            </Typography>
          ) : (
            Object.entries(results).map(([key, data]) => (
              <Box key={key} sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ mb: 1, textTransform: 'capitalize', fontWeight: 700 }}>
                  {key}
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    m: 0,
                    p: 1.5,
                    bgcolor: 'background.default',
                    border: '1px solid',
                    borderColor: 'divider',
                    color: 'text.primary',
                    borderRadius: 1,
                    fontSize: '0.72rem',
                    fontFamily: 'monospace',
                    overflowX: 'auto',
                    maxHeight: 420,
                    overflowY: 'auto',
                    whiteSpace: 'pre',
                  }}
                >
                  {JSON.stringify(data, null, 2)}
                </Box>
              </Box>
            ))
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewOpen(false)}>Zamknij</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
