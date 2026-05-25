import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useEffect, useRef } from 'react';

interface Props {
  messages: string[];
  liveMessage?: string;
}

export default function StepLog({ messages, liveMessage }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 1.5 }}>
      <Box
        sx={{
          maxHeight: 220,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        {messages.map((msg, i) => (
          <Typography key={i} variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
            {msg}
          </Typography>
        ))}
        {liveMessage && (
          <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'primary.main', fontWeight: 700 }}>
            {liveMessage}
          </Typography>
        )}
        <div ref={bottomRef} />
      </Box>
    </Paper>
  );
}
