import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export default function Footer() {
  return (
    <Box sx={{ textAlign: 'center', py: 2, borderTop: 1, borderColor: 'divider' }}>
      <Typography variant="caption" color="text.secondary">
        © 2026 Przemek Chwała
      </Typography>
    </Box>
  );
}
