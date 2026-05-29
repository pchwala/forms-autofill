import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

export default function HeroSection() {
  return (
    <Box sx={{ textAlign: 'center', mb: 6, maxWidth: 800, mx: 'auto' }}>
      <Typography
        variant="h3"
        sx={{
          fontWeight: 800,
          background: 'linear-gradient(90deg, #1976d2 0%, #9c27b0 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          mb: 1.5,
        }}
      >
        Forms Autofill
      </Typography>
      <Typography variant="h6" sx={{ color: 'text.secondary', fontWeight: 400, mb: 3 }}>
        Automatically generate and submit AI-powered responses to any Google Form — at scale.
      </Typography>
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
        <Chip label="AI-Powered" size="small" color="primary" variant="outlined" />
        <Chip label="Google Forms" size="small" variant="outlined" />
        <Chip label="Up to 1000 responses" size="small" variant="outlined" />
        <Chip label="Free to try" size="small" color="success" variant="outlined" />
      </Box>
    </Box>
  );
}
