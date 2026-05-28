import { useEffect, useState } from 'react';
import { keyframes } from '@mui/system';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Container from '@mui/material/Container';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import FavoriteIcon from '@mui/icons-material/Favorite';
import LinkIcon from '@mui/icons-material/Link';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import InputForm, { type PipelineMode } from './components/InputForm';
import PipelineProgress from './components/PipelineProgress';
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import { useUserStatus } from './hooks/useUserStatus';
import AuthGuard from './components/AuthGuard';

const HOW_IT_WORKS = [
  {
    icon: <LinkIcon sx={{ fontSize: 26, color: '#1976d2' }} />,
    step: '01',
    title: 'Paste your Google Form URL',
    description:
      'Drop in any publicly accessible Google Form link. The AI fetches and analyzes the form structure automatically.',
  },
  {
    icon: <SmartToyIcon sx={{ fontSize: 26, color: '#9c27b0' }} />,
    step: '02',
    title: 'AI generates realistic responses',
    description:
      'The AI analyzes each question and produces diverse, human-like answers at scale — no templates, no repetition.',
  },
  {
    icon: <SendIcon sx={{ fontSize: 26, color: '#4caf50' }} />,
    step: '03',
    title: 'Responses are auto-submitted',
    description:
      'All generated responses are shuffled and submitted directly to Google Forms on your behalf.',
  },
];

export default function App() {
  const { getToken } = useAuth();
  const [reviewOpen, setReviewOpen] = useState(false);
  const [resubmitCount, setResubmitCount] = useState(100);
  const { freeUsed, paid, refresh: refreshStatus } = useUserStatus(getToken);
  const {
    status,
    steps,
    log,
    results,
    error,
    submitProgress,
    resultId,
    sessionId,
    startFullPipeline,
    createSession,
    advanceSession,
    resubmit,
    reset,
  } = usePipeline(getToken);

  const isIdle = status === 'idle';
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isDone = status === 'done';
  const isError = status === 'error';
  const isBlocked = status === 'blocked';
  const canResubmit = isDone && (resultId !== null || sessionId !== null);

  useEffect(() => {
    if (isBlocked) void refreshStatus();
  }, [isBlocked, refreshStatus]);

  async function handleStart(url: string, count: number, mode: PipelineMode) {
    setResubmitCount(count);
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

  async function handleResubmit() {
    try {
      await resubmit(resubmitCount);
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

        {/* ── Hero ── */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography
            variant="h3"
            sx={{
              fontWeight: 800,
              background: 'linear-gradient(90deg, #1976d2 0%, #9c27b0 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              mb: 1.5,
            }}
          >
            Forms Autofill
          </Typography>
          <Typography variant="h6" sx={{ color: 'text.secondary', fontWeight: 400, mb: 3 }}>
            Automatically generate and submit AI-powered responses to any Google Form — at scale.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Chip label="AI-Powered" size="small" color="primary" variant="outlined" />
            <Chip label="Google Forms" size="small" variant="outlined" />
            <Chip label="Up to 1000 responses" size="small" variant="outlined" />
            <Chip label="Free to try" size="small" color="success" variant="outlined" />
          </Box>
        </Box>

        {/* ── How it works ── */}
        <Box sx={{ mb: 6 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
            How it works
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
              gap: 2,
              mt: 1.5,
            }}
          >
            {HOW_IT_WORKS.map(({ icon, step, title, description }) => (
              <Card
                key={step}
                variant="outlined"
                sx={{
                  bgcolor: '#1a1f26',
                  border: '1px solid #2d3136',
                  borderRadius: 2,
                  transition: 'border-color 0.2s',
                  '&:hover': { borderColor: '#1976d2' },
                }}
              >
                <CardContent sx={{ p: 2.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
                    {icon}
                    <Typography
                      variant="caption"
                      sx={{ color: 'text.secondary', fontWeight: 700, letterSpacing: 1 }}
                    >
                      STEP {step}
                    </Typography>
                  </Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
                    {title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {description}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>

        {/* ── Main tool ── */}
        <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
          Run the pipeline
        </Typography>
        <Paper variant="outlined" sx={{ p: 3, mt: 1.5, mb: 4, display: 'flex', flexDirection: 'column', gap: 3, bgcolor: '#1a1f26', border: '1px solid #2d3136', borderRadius: 2 }}>
          {/* Input form — always visible, disabled while running */}
          <InputForm onStart={handleStart} disabled={isRunning || isPaused || isDone} freeUsed={freeUsed} paid={paid} />

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
                onChange={(e) => setResubmitCount(Math.min(1000, Math.max(1, parseInt(e.target.value, 10) || 1)))}
                size="small"
                slotProps={{ htmlInput: { min: 1, max: 1000 } }}
                sx={{ width: 100 }}
              />
              <Button variant="outlined" onClick={handleResubmit}>
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

        {/* ── Ko-fi support ── */}
      <Card
        variant="outlined"
        sx={{
          mb: 4,
          bgcolor: '#1a1f26',
          border: '1px solid #2d3136',
          borderRadius: 2,
          background: 'linear-gradient(135deg, rgba(25,118,210,0.05) 0%, rgba(156,39,176,0.05) 100%)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <FavoriteIcon sx={{ color: '#e53935', fontSize: 20 }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Support this project
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Forms Autofill is free to try. If you find it useful, consider supporting development on Ko-fi —
            a €10+ donation also unlocks unlimited pipeline runs for your account.
          </Typography>
          <Button
            variant="contained"
            component="a"
            href="https://ko-fi.com/pchwala"
            target="_blank"
            rel="noopener noreferrer"
            startIcon={<FavoriteIcon />}
            sx={{
              bgcolor: '#FF5E5B',
              color: '#fff',
              fontWeight: 700,
              '&:hover': { bgcolor: '#e54e4b' },
            }}
          >
            Support on Ko-fi
          </Button>
        </CardContent>
      </Card>

      {/* ── Footer ── */}
      <Box sx={{ textAlign: 'center', py: 2, borderTop: '1px solid #2d3136' }}>
        <Typography variant="caption" color="text.secondary">
          © 2026 Przemek Chwała ·{' '}
          <Box
            component="a"
            href="https://ko-fi.com/pchwala"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ color: '#FF5E5B', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
          >
            Support on Ko-fi
          </Box>
        </Typography>
      </Box>

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
