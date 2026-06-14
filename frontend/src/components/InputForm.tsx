import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import { useState } from 'react';

interface Props {
  onStart: (url: string, count: number, desirePrompt: string) => void;
  disabled?: boolean;
}

export default function InputForm({ onStart, disabled }: Props) {
  const [url, setUrl] = useState('');
  const [count, setCount] = useState(100);
  const [desirePrompt, setDesirePrompt] = useState('');

  const valid = url.trim().length > 0 && count > 0;

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

      <TextField
        label="Desired outcome (optional)"
        value={desirePrompt}
        onChange={(e) => setDesirePrompt(e.target.value)}
        placeholder="e.g. Most respondents should favor remote work and rate satisfaction highly"
        helperText="Steers the generated responses toward the outcome you want — overrides the research-based defaults."
        disabled={disabled}
        fullWidth
        size="small"
        multiline
        minRows={2}
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
          onClick={() => onStart(url.trim(), count, desirePrompt)}
        >
          Generate preview
        </Button>
      </Box>
    </Box>
  );
}
