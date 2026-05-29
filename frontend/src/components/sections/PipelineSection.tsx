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
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import InputForm from '../InputForm';
import type { PipelineMode } from '../InputForm';
import PipelineProgress from '../PipelineProgress';
import type { StepInfo } from '../../hooks/usePipeline';

interface SubmitProgress {
  current: number;
  total: number;
  batch?: number;
  totalBatches?: number;
}

interface HistoryRecord {
  pipelineId: string;
  formTitle: string;
  totalResponses: number;
}

interface Props {
  status: string;
  steps: StepInfo[];
  log: string[];
  results: Record<string, unknown>;
  error: string | null;
  submitProgress: SubmitProgress | null;
  resultId: string | null;
  sessionId: string | null;
  historyRecord: HistoryRecord | null;
  historyResubmitCount: number;
  resubmitCount: number;
  freeUsed?: boolean;
  paid?: boolean;
  onStart: (url: string, count: number, mode: PipelineMode) => void;
  onAdvance: () => void;
  onResubmit: () => void;
  onReset: () => void;
  onHistoryResubmit: () => void;
  onHistoryResubmitCountChange: (count: number) => void;
  onHistoryRecordClear: () => void;
  onResubmitCountChange: (count: number) => void;
}

export default function PipelineSection({
  status,
  steps,
  log,
  results,
  error,
  submitProgress,
  resultId,
  sessionId,
  historyRecord,
  historyResubmitCount,
  resubmitCount,
  freeUsed,
  paid,
  onStart,
  onAdvance,
  onResubmit,
  onReset,
  onHistoryResubmit,
  onHistoryResubmitCountChange,
  onHistoryRecordClear,
  onResubmitCountChange,
}: Props) {
  const [reviewOpen, setReviewOpen] = useState(false);

  const isIdle = status === 'idle';
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isDone = status === 'done';
  const isError = status === 'error';
  const canResubmit = isDone && (resultId !== null || sessionId !== null);

  return (
    <>
      <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
        Run the pipeline
      </Typography>
      <Paper
        variant="outlined"
        sx={{ p: 3, mt: 1.5, mb: 4, display: 'flex', flexDirection: 'column', gap: 3, bgcolor: 'background.paper', borderRadius: 2 }}
      >
        {/* History resubmit panel */}
        {historyRecord && isIdle && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.25 }}>
                Resubmit from History
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {historyRecord.formTitle || 'Untitled form'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                label="Responses"
                type="number"
                value={historyResubmitCount}
                onChange={(e) => onHistoryResubmitCountChange(Math.min(1000, Math.max(1, parseInt(e.target.value, 10) || 1)))}
                size="small"
                slotProps={{ htmlInput: { min: 1, max: 1000 } }}
                sx={{ width: 120 }}
              />
              <Button variant="contained" onClick={onHistoryResubmit}>
                Resubmit
              </Button>
              <Button variant="outlined" color="error" onClick={onHistoryRecordClear}>
                Cancel
              </Button>
            </Box>
            <Divider />
          </Box>
        )}

        {/* Input form — always visible, disabled while running */}
        <InputForm onStart={onStart} disabled={isRunning || isPaused || isDone} freeUsed={freeUsed} paid={paid} />

        <Divider />

        {/* Button row — always visible */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button variant="contained" onClick={onAdvance} disabled={!isPaused}>
            Next Step
          </Button>
          <Button
            variant="outlined"
            onClick={() => setReviewOpen(true)}
            disabled={log.length === 0}
          >
            Review Details
          </Button>
          <Button variant="outlined" color="error" onClick={onReset} disabled={isIdle}>
            Reset
          </Button>
        </Box>

        {/* Stepper — always visible */}
        <PipelineProgress steps={steps} />

        {/* Current step message */}
        {(log.length > 0 || submitProgress) && (
          <Typography
            variant="body2"
            sx={isRunning ? {
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
            } : {
              fontFamily: 'monospace',
              color: 'text.secondary',
            }}
          >
            {submitProgress
              ? (() => {
                  const batchInfo = submitProgress.totalBatches && submitProgress.totalBatches > 1
                    ? `Batch ${submitProgress.batch}/${submitProgress.totalBatches} — `
                    : '';
                  return `${batchInfo}Submitting responses to Google Form — ${submitProgress.current}/${submitProgress.total}`;
                })()
              : log[log.length - 1]}
          </Typography>
        )}

        {/* Done state */}
        {isDone && (
          <Alert severity="success">
            Pipeline complete — all responses submitted successfully.
          </Alert>
        )}

        {/* Resubmit */}
        {canResubmit && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="body2" color="text.secondary">
              Submit again with existing AI responses:
            </Typography>
            <TextField
              label="Count"
              type="number"
              value={resubmitCount}
              onChange={(e) => onResubmitCountChange(Math.min(1000, Math.max(1, parseInt(e.target.value, 10) || 1)))}
              size="small"
              slotProps={{ htmlInput: { min: 1, max: 1000 } }}
              sx={{ width: 100 }}
            />
            <Button variant="outlined" onClick={onResubmit}>
              Submit Again
            </Button>
          </Box>
        )}

        {/* Error state */}
        {isError && (
          <Alert severity="error">
            {error ?? 'An unexpected error occurred.'}
          </Alert>
        )}
      </Paper>

      {/* Review Details dialog */}
      <Dialog
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        maxWidth="md"
        fullWidth
        scroll="paper"
      >
        <DialogTitle>Step Details</DialogTitle>
        <DialogContent dividers>
          {Object.keys(results).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No JSON results available yet.
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
          <Button onClick={() => setReviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
