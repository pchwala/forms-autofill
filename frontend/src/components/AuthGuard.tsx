import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import { type ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

interface Props {
  children: ReactNode;
}

export default function AuthGuard({ children }: Props) {
  const { loading } = useAuth();

  // While the (anonymous or Google) session is resolving, show a spinner.
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Everyone gets in — anonymous users included. Sign-in becomes an optional upgrade.
  return <>{children}</>;
}
