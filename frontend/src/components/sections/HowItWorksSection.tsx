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
    title: 'Wklej link do formularza i oczekiwany rezultat',
    description:
      'Wklej dowolny publiczny link do formularza Google i opcjonalnie opisz oczekiwany rezultat. AI pobiera formularz i buduje strategię odpowiedzi — za darmo.',
  },
  {
    icon: <SmartToyIcon sx={{ fontSize: 26, color: '#9c27b0' }} />,
    step: '02',
    title: 'Przejrzyj przewidywane wyniki',
    description:
      'Zobacz persony respondentów i przewidywane rozkłady odpowiedzi, zanim cokolwiek zostanie wysłane. Wybierz persony do uwzględnienia i obserwuj aktualizacje na żywo.',
  },
  {
    icon: <SendIcon sx={{ fontSize: 26, color: '#4caf50' }} />,
    step: '03',
    title: 'Odblokuj i wyślij',
    description:
      'Zadowolony z podglądu? Odblokuj wysyłkę, aby wygenerować i automatycznie wysłać losowe odpowiedzi bezpośrednio do Twojego formularza Google.',
  },
];

export default function HowItWorksSection() {
  return (
    <Box sx={{ mb: 6 }}>
      <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 2 }}>
        Jak to działa
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
