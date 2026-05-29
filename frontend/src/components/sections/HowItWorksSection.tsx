import type { ReactNode } from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import LinkIcon from '@mui/icons-material/Link';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';

interface HowItWorksItem {
  icon: ReactNode;
  step: string;
  title: string;
  description: string;
}

const HOW_IT_WORKS: HowItWorksItem[] = [
  {
    icon: <LinkIcon sx={{ fontSize: 26, color: '#1976d2' }} />,
    step: '01',
    title: 'Paste your Google Form URL',
    description:
      'Drop in any publicly accessible Google Form link. The AI fetches and analyzes the form structure automatically.',
  },
  {
    icon: <SmartToyIcon sx={{ fontSize: 26, color: '#9c27b0' }} />,
    step: '02',
    title: 'AI generates realistic responses',
    description:
      'The AI analyzes each question and produces diverse, human-like answers at scale — no templates, no repetition.',
  },
  {
    icon: <SendIcon sx={{ fontSize: 26, color: '#4caf50' }} />,
    step: '03',
    title: 'Responses are auto-submitted',
    description:
      'All generated responses are shuffled and submitted directly to Google Forms on your behalf.',
  },
];

export default function HowItWorksSection() {
  return (
    <Box sx={{ mb: 6 }}>
      <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
        How it works
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
          gap: 2,
          mt: 1.5,
        }}
      >
        {HOW_IT_WORKS.map(({ icon, step, title, description }) => (
          <Card
            key={step}
            variant="outlined"
            sx={{
              borderRadius: 2,
              transition: 'border-color 0.2s',
              '&:hover': { borderColor: 'primary.main' },
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
                {icon}
                <Typography
                  variant="caption"
                  sx={{ color: 'text.secondary', fontWeight: 700, letterSpacing: 1 }}
                >
                  STEP {step}
                </Typography>
              </Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
                {title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {description}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
