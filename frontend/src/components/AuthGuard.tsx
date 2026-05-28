import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import GoogleIcon from '@mui/icons-material/Google';
import { type ReactNode } from 'react';
import { AUTH_DISABLED } from '../firebase';
import { useAuth } from '../hooks/useAuth';

interface Props {
  children: ReactNode;
}

export default function AuthGuard({ children }: Props) {
  const { user, loading, signIn, signOut } = useAuth();

  if (AUTH_DISABLED) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          gap: 3,
          px: 3,
          textAlign: 'center',
        }}
      >
        <Box>
          <Typography
            variant="h4"
            sx={{
              fontWeight: 800,
              background: 'linear-gradient(90deg, #1976d2 0%, #9c27b0 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              mb: 1,
            }}
          >
            Forms Autofill
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 380 }}>
            Automatically generate and submit AI-powered responses to any Google Form — in seconds, at scale.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
          <Chip label="AI-Powered" size="small" color="primary" variant="outlined" />
          <Chip label="Google Forms" size="small" variant="outlined" />
          <Chip label="Free to try" size="small" color="success" variant="outlined" />
        </Box>
        <Divider sx={{ width: '100%', maxWidth: 380 }} />
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<GoogleIcon />}
            onClick={() => void signIn()}
            sx={{ px: 4, py: 1.2, fontWeight: 600 }}
          >
            Sign in with Google
          </Button>
          <Typography variant="caption" color="text.secondary">
            Free to try ·{' '}
            <Box
              component="a"
              href="https://ko-fi.com/pchwala"
              target="_blank"
              rel="noopener noreferrer"
              sx={{ color: '#FF5E5B', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
            >
              Ko-fi donation
            </Box>
            {' '}for unlimited access
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <>
      <Box sx={{ position: 'fixed', top: 16, right: 16, zIndex: 1200 }}>
        <Button variant="outlined" size="small" onClick={() => void signOut()}>
          Sign out
        </Button>
      </Box>
      {children}
    </>
  );
}
