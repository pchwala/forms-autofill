import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
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
          height: '100vh',
          gap: 2,
        }}
      >
        <Typography variant="h5">Forms Autofill</Typography>
        <Button variant="contained" onClick={() => void signIn()}>
          Sign in with Google
        </Button>
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
