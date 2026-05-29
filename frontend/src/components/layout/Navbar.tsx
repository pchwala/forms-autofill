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
      sx={{ bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}
    >
      <Toolbar disableGutters sx={{ px: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', maxWidth: 1200, mx: 'auto' }}>
          <Typography
            component="a"
            href="https://pchwala.dev"
            target="_blank"
            rel="noopener noreferrer"
            variant="h6"
            sx={{ fontWeight: 700, textDecoration: 'none', color: 'text.primary', letterSpacing: '-0.5px' }}
          >
            pchwala
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          {!AUTH_DISABLED && user && (
            <UserMenu user={user} onSignOut={onSignOut} onHistory={onHistory} />
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
