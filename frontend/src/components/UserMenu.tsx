import { useState } from 'react';
import Avatar from '@mui/material/Avatar';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import type { User } from 'firebase/auth';

const AVATAR_COLORS = ['#1976d2', '#7b1fa2', '#388e3c', '#f57c00', '#c62828'];

function avatarColor(email: string): string {
  return AVATAR_COLORS[email.charCodeAt(0) % AVATAR_COLORS.length];
}

interface Props {
  user: User;
  onSignOut: () => void;
  onHistory: () => void;
}

export default function UserMenu({ user, onSignOut, onHistory }: Props) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const initials = (user.email ?? '?')[0].toUpperCase();
  const bgColor = avatarColor(user.email ?? '');

  function handleOpen(e: React.MouseEvent<HTMLElement>) {
    setAnchorEl(e.currentTarget);
  }

  function handleClose() {
    setAnchorEl(null);
  }

  function handleHistory() {
    handleClose();
    onHistory();
  }

  function handleSignOut() {
    handleClose();
    onSignOut();
  }

  return (
    <>
      <IconButton onClick={handleOpen} size="small" aria-label="menu konta">
        <Avatar sx={{ width: 32, height: 32, bgcolor: bgColor, fontSize: '0.875rem', fontWeight: 700 }}>
          {initials}
        </Avatar>
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        slotProps={{ paper: { sx: { mt: 0.5, minWidth: 160 } } }}
      >
        <MenuItem disabled sx={{ opacity: '1 !important' }}>
          <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
            {user.email}
          </Typography>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleHistory}>Historia</MenuItem>
        <Divider />
        <MenuItem onClick={handleSignOut}>Wyloguj się</MenuItem>
      </Menu>
    </>
  );
}
