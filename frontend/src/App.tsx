import { useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import InputForm, { type PipelineMode } from './components/InputForm';
import PipelineProgress from './components/PipelineProgress';
import StepLog from './components/StepLog';
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import AuthGuard from './components/AuthGuard';

const STEP_STATUS_MESSAGES: Record<string, string> = {
  'Extract form': 'Extracting form...',
  'Generate strategy': 'Generating strategy...',
  'Generate responses': 'Generating responses...',
  'Shuffle responses': 'Shuffling responses...',
  'Submit responses': 'Submitting responses...',
};

export default function App() {
  const { getToken } = useAuth();
  const [reviewOpen, setReviewOpen] = useState(false);
  const {
    status,
    steps,
    log,
    error,
    startFullPipeline,
    createSession,
    advanceSession,
    reset,
  } = usePipeline(getToken);

  const isIdle = status === 'idle';
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isDone = status === 'done';
  const isError = status === 'error';

  async function handleStart(url: string, count: number, mode: PipelineMode, model: string) {
    try {
      if (mode === 'full') {
        await startFullPipeline(url, count, model);
      } else {
        await createSession(url, count, model);
      }
    } catch {
      // error state already set inside the hook
    }
  }

  async function handleAdvance() {
    try {
      await advanceSession();
    } catch {
      // error state already set inside the hook
    }
  }

  const activeStep = steps.find((s) => s.status === 'active');
  const statusMessage = activeStep
    ? (STEP_STATUS_MESSAGES[activeStep.label] ?? `${activeStep.label}...`)
    : isPaused
    ? 'Ready for next step.'
    : isRunning
    ? 'Running...'
    : null;

  return (
    <AuthGuard>
      <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
        Forms Autofill
      </Typography>
      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 4 }}>
        Automatically generate and submit responses to a Google Form using AI.
      </Typography>

      <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Input form — always visible, disabled while running */}
        <InputForm onStart={handleStart} disabled={isRunning || isPaused || isDone} />

        {/* Progress section — shown once started */}
        {!isIdle && (
          <>
            <Divider />

            {/* Button row — above stepper */}
            {isPaused && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button variant="contained" onClick={handleAdvance}>
                  Next Step
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setReviewOpen(true)}
                  disabled={log.length === 0}
                >
                  Review Details
                </Button>
                <Button variant="outlined" color="error" onClick={reset}>
                  Cancel
                </Button>
              </Box>
            )}

            {/* Stepper */}
            <PipelineProgress steps={steps} />

            {/* Simple status message */}
            {statusMessage && (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: -1 }}>
                {statusMessage}
              </Typography>
            )}
          </>
        )}

        {/* Done state */}
        {isDone && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Alert severity="success" sx={{ flex: 1 }}>
              Pipeline complete — all responses submitted successfully.
            </Alert>
            <Button variant="outlined" onClick={reset}>
              Start over
            </Button>
          </Box>
        )}

        {/* Error state */}
        {isError && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Alert severity="error" sx={{ flex: 1 }}>
              {error ?? 'An unexpected error occurred.'}
            </Alert>
            <Button variant="outlined" onClick={reset}>
              Retry
            </Button>
          </Box>
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
          <StepLog messages={log} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
    </AuthGuard>
  );
}
