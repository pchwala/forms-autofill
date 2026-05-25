import { useState } from 'react';
import { keyframes } from '@mui/system';
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
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import AuthGuard from './components/AuthGuard';

export default function App() {
  const { getToken } = useAuth();
  const [reviewOpen, setReviewOpen] = useState(false);
  const {
    status,
    steps,
    log,
    results,
    error,
    submitProgress,
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

  async function handleStart(url: string, count: number, mode: PipelineMode) {
    try {
      if (mode === 'full') {
        await startFullPipeline(url, count);
      } else {
        await createSession(url, count);
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

        <Divider />

        {/* Button row — always visible */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button variant="contained" onClick={handleAdvance} disabled={!isPaused}>
            Next Step
          </Button>
          <Button
            variant="outlined"
            onClick={() => setReviewOpen(true)}
            disabled={log.length === 0}
          >
            Review Details
          </Button>
          <Button variant="outlined" color="error" onClick={reset} disabled={isIdle}>
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
              ? `Submitting responses to Google Form — ${submitProgress.current}/${submitProgress.total}`
              : log[log.length - 1]}
          </Typography>
        )}

        {/* Done state */}
        {isDone && (
          <Alert severity="success">
            Pipeline complete — all responses submitted successfully.
          </Alert>
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
                    bgcolor: '#111418',
                    border: '1px solid',
                    borderColor: '#2d3136',
                    color: '#e8eaed',
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
    </Container>
    </AuthGuard>
  );
}
