import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import CodeIcon from '@mui/icons-material/Code';

export default function Footer() {
  return (
    <Box sx={{ textAlign: 'center', py: 3, borderTop: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.75 }}>
        <CodeIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
        <Typography variant="caption" color="text.secondary">
          Ten projekt jest open-source. Jesteś developerem?{' '}
          <Link
            href="https://github.com/pchwala/forms-autofill"
            target="_blank"
            rel="noopener noreferrer"
            underline="hover"
            color="primary"
          >
            Uruchom go samodzielnie
          </Link>
          {' '}w ramach własnej subskrypcji OpenAI.
        </Typography>
      </Box>
      <Typography variant="caption" color="text.disabled">
        © 2026 Przemek Chwała
      </Typography>
    </Box>
  );
}
