import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import { useState } from 'react';

interface Props {
  onStart: (url: string, count: number) => void;
  disabled?: boolean;
  freeUsed?: boolean;
  paid?: boolean;
}

export default function InputForm({ onStart, disabled, freeUsed, paid }: Props) {
  const [url, setUrl] = useState('');
  const [count, setCount] = useState(100);

  const valid = url.trim().length > 0 && count > 0;

  if (freeUsed && !paid) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="body1" fontWeight="medium">
          You've used your free run.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Premium access is coming soon. Stay tuned!
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This project is also open source at{' '}
          <a href="https://github.com/pchwala/forms-autofill" target="_blank" rel="noopener noreferrer">
            pchwala/forms-autofill
          </a>
          {' '}— if you're a developer, feel free to run your own local instance for free!
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <TextField
        label="Google Form URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://docs.google.com/forms/..."
        disabled={disabled}
        fullWidth
        size="small"
      />

      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          label="Number of responses"
          type="number"
          value={count}
          onChange={(e) => setCount(Math.min(1000, Math.max(1, parseInt(e.target.value, 10) || 1)))}
          disabled={disabled}
          size="small"
          slotProps={{ htmlInput: { min: 1, max: 1000 } }}
          sx={{ width: 200 }}
        />
      </Box>

      <Box>
        <Button
          variant="contained"
          disabled={disabled || !valid}
          onClick={() => onStart(url.trim(), count)}
        >
          Start
        </Button>
      </Box>
    </Box>
  );
}
