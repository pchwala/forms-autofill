import { useEffect, useRef, useState } from 'react';
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
import PaywallDialog from './components/PaywallDialog';
import AuthGuard from './components/AuthGuard';
import { usePipeline } from './hooks/usePipeline';
import { useAuth } from './hooks/useAuth';
import { useCredits } from './hooks/useCredits';
import { useBilling } from './hooks/useBilling';

export default function App() {
  const { getToken, user, loading: authLoading, isAnonymous, signInWithGoogle, signOut } = useAuth();
  const { credits, refresh: refreshCredits } = useCredits(getToken, user, authLoading);
  const { confirm } = useBilling(getToken);
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
    restore,
    reset,
    setStatus,
  } = usePipeline(getToken);

  const hasCredits = credits > 0;

  // After auth resolves, restore an in-flight preview and handle Stripe return params.
  const restoredRef = useRef(false);
  useEffect(() => {
    if (authLoading) return;
    if (!user) return;
    if (restoredRef.current) return;
    restoredRef.current = true;
    void (async () => {
      const params = new URLSearchParams(window.location.search);
      const checkoutStatus = params.get('checkout');
      const sessionId = params.get('session_id');

      if (checkoutStatus) {
        // Strip Stripe params from the URL immediately so a refresh doesn't re-trigger.
        const clean = window.location.pathname;
        window.history.replaceState(null, '', clean);
      }

      if (checkoutStatus === 'success' && sessionId) {
        // Confirm the session (idempotent — safe even if the webhook already ran).
        try {
          await confirm(sessionId);
        } catch {
          // Non-fatal: credits may already have been granted by the webhook.
        }
        await refreshCredits();
        const pending = await restore();
        if (pending) {
          setCount(pending.count);
          // Auto-retry submit if we now have enough credits.
          if (pending.selectedCodes && pending.selectedCodes.length > 0) {
            void runSubmit(pending.selectedCodes);
          }
        }
      } else if (checkoutStatus === 'cancel') {
        // Restore the preview so the user can pick a pack again.
        const pending = await restore();
        if (pending) setCount(pending.count);
        setPaywallOpen(true);
      } else {
        // Normal load — just restore any in-flight preview.
        const pending = await restore();
        if (pending) setCount(pending.count);
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user]);

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
            creditsNeeded={count}
            creditsHeld={credits}
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
