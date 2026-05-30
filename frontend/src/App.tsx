import { useEffect, useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import { darkTheme } from './theme/theme';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import HeroSection from './components/sections/HeroSection';
import HowItWorksSection from './components/sections/HowItWorksSection';
import PipelineSection from './components/sections/PipelineSection';
import HistoryDialog from './components/HistoryDialog';
import AuthGuard from './components/AuthGuard';
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import { useUserStatus } from './hooks/useUserStatus';
import type { PipelineMode } from './components/InputForm';

export default function App() {
  const { getToken, user, signOut } = useAuth();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyRecord, setHistoryRecord] = useState<{ pipelineId: string; formTitle: string; totalResponses: number } | null>(null);
  const [historyResubmitCount, setHistoryResubmitCount] = useState(100);
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
    resubmitFromHistory,
    reset,
  } = usePipeline(getToken);

  const isBlocked = status === 'blocked';

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

  function handleHistorySelect(pipelineId: string, totalResponses: number, formTitle: string) {
    reset();
    setHistoryRecord({ pipelineId, formTitle, totalResponses });
    setHistoryResubmitCount(totalResponses);
    setHistoryOpen(false);
  }

  async function handleHistoryResubmit() {
    if (!historyRecord) return;
    try {
      await resubmitFromHistory(historyRecord.pipelineId, historyResubmitCount);
    } catch {
      // error state already set inside the hook
    }
  }

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <AuthGuard>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar
            user={user}
            onSignOut={() => void signOut()}
            onHistory={() => setHistoryOpen(true)}
          />
          <HistoryDialog
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            getToken={getToken}
            onSelect={handleHistorySelect}
          />
          <Container maxWidth="lg" sx={{ py: 6 }}>
            <HeroSection />
            <HowItWorksSection />
            <PipelineSection
              status={status}
              steps={steps}
              log={log}
              results={results}
              error={error}
              submitProgress={submitProgress}
              resultId={resultId}
              sessionId={sessionId}
              historyRecord={historyRecord}
              historyResubmitCount={historyResubmitCount}
              resubmitCount={resubmitCount}
              freeUsed={freeUsed}
              paid={paid}
              onStart={handleStart}
              onAdvance={() => void handleAdvance()}
              onResubmit={() => void handleResubmit()}
              onReset={reset}
              onHistoryResubmit={() => void handleHistoryResubmit()}
              onHistoryResubmitCountChange={setHistoryResubmitCount}
              onHistoryRecordClear={() => setHistoryRecord(null)}
              onResubmitCountChange={setResubmitCount}
            />
          </Container>
          <Footer />
        </Box>
      </AuthGuard>
    </ThemeProvider>
  );
}
