import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export default function Footer() {
  return (
    <Box sx={{ textAlign: 'center', py: 2, borderTop: 1, borderColor: 'divider' }}>
      <Typography variant="caption" color="text.secondary">
        © 2026 Przemek Chwała ·{' '}
        <Box
          component="a"
          href="https://ko-fi.com/pchwala"
          target="_blank"
          rel="noopener noreferrer"
          sx={{ color: '#FF5E5B', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
        >
          Support on Ko-fi
        </Box>
      </Typography>
    </Box>
  );
}
