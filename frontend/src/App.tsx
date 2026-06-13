import { useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import { darkTheme } from './theme/theme';
import { AUTH_DISABLED } from './firebase';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import HeroSection from './components/sections/HeroSection';
import HowItWorksSection from './components/sections/HowItWorksSection';
import PipelineSection from './components/sections/PipelineSection';
import HistoryDialog from './components/HistoryDialog';
import PaywallDialog from './components/PaywallDialog';
import AuthGuard from './components/AuthGuard';
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import { useCredits } from './hooks/useCredits';

export default function App() {
  const { getToken, user, loading: authLoading, isAnonymous, signInWithGoogle, signOut } = useAuth();
  const { credits, refresh: refreshCredits } = useCredits(getToken, user, authLoading);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [pendingCodes, setPendingCodes] = useState<string[] | null>(null);
  const [count, setCount] = useState(100);

  const {
    status,
    steps,
    log,
    results,
    error,
    preview,
    submitProgress,
    startPreview,
    submitResponses,
    reset,
    setStatus,
  } = usePipeline(getToken);

  const hasCredits = AUTH_DISABLED || credits > 0;

  async function handleStart(url: string, c: number, desirePrompt: string) {
    setCount(c);
    try {
      await startPreview(url, c, desirePrompt);
    } catch {
      // error state already set inside the hook
    }
  }

  async function runSubmit(codes: string[]) {
    try {
      const ok = await submitResponses(codes, count);
      if (!ok) {
        // Raced out of credits — fall back to the paywall.
        setPendingCodes(codes);
        setPaywallOpen(true);
      }
      void refreshCredits();
    } catch {
      // error state already set inside the hook
    }
  }

  function handleSubmit(codes: string[]) {
    if (hasCredits) {
      void runSubmit(codes);
    } else {
      setPendingCodes(codes);
      setPaywallOpen(true);
    }
  }

  async function handlePaid() {
    await refreshCredits();
    setPaywallOpen(false);
    const codes = pendingCodes;
    setPendingCodes(null);
    if (codes) void runSubmit(codes);
  }

  function handlePaywallClose() {
    setPaywallOpen(false);
    setPendingCodes(null);
    if (status === 'blocked') setStatus('preview');
  }

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <AuthGuard>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar
            user={user}
            isAnonymous={isAnonymous}
            credits={credits}
            onSignIn={() => void signInWithGoogle()}
            onSignOut={() => void signOut()}
            onHistory={() => setHistoryOpen(true)}
          />
          <HistoryDialog
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            getToken={getToken}
          />
          <PaywallDialog
            open={paywallOpen}
            getToken={getToken}
            onClose={handlePaywallClose}
            onPaid={() => void handlePaid()}
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
              preview={preview}
              submitProgress={submitProgress}
              count={count}
              hasCredits={hasCredits}
              onStart={handleStart}
              onSubmit={handleSubmit}
              onReset={reset}
            />
          </Container>
          <Footer />
        </Box>
      </AuthGuard>
    </ThemeProvider>
  );
}
