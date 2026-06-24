function plTokens(n: number): string {
  if (n === 1) return 'token';
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return 'tokeny';
  return 'tokenów';
}

import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import GoogleIcon from '@mui/icons-material/Google';
import type { User } from 'firebase/auth';
import UserMenu from '../UserMenu';

interface Props {
  user: User | null;
  isAnonymous: boolean;
  tokens: number;
  onSignIn: () => void;
  onSignOut: () => void;
  onHistory: () => void;
}

export default function Navbar({ user, isAnonymous, tokens, onSignIn, onSignOut, onHistory }: Props) {
  const signedInWithGoogle = user && !isAnonymous;
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}
    >
      <Toolbar
        sx={{ maxWidth: 1200, width: '100%', mx: 'auto', px: { xs: 2, sm: 3 } }}
      >
        <Box sx={{ flexGrow: 1 }} />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            {tokens} {plTokens(tokens)}
          </Typography>
          {signedInWithGoogle ? (
            <UserMenu user={user!} onSignOut={onSignOut} onHistory={onHistory} />
          ) : (
            <Button
              variant="outlined"
              size="small"
              startIcon={<GoogleIcon />}
              onClick={onSignIn}
            >
              Zaloguj się
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
