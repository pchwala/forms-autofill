import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import type { User } from 'firebase/auth';
import { AUTH_DISABLED } from '../../firebase';
import UserMenu from '../UserMenu';

interface Props {
  user: User | null;
  onSignOut: () => void;
  onHistory: () => void;
}

export default function Navbar({ user, onSignOut, onHistory }: Props) {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}
    >
      <Toolbar
        sx={{ maxWidth: 1200, width: '100%', mx: 'auto', px: { xs: 2, sm: 3 } }}
      >
        <Typography
          component="a"
          href="https://pchwala.dev"
          target="_blank"
          rel="noopener noreferrer"
          variant="h6"
          sx={{ fontWeight: 700, textDecoration: 'none', color: 'text.primary', flexGrow: 1, letterSpacing: '-0.5px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}
        >
          pchwala
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {!AUTH_DISABLED && user && (
            <UserMenu user={user} onSignOut={onSignOut} onHistory={onHistory} />
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
