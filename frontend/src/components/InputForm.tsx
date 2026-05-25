import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

export type PipelineMode = 'full' | 'step';

interface Props {
  onStart: (url: string, count: number, mode: PipelineMode) => void;
  disabled?: boolean;
}

export default function InputForm({ onStart, disabled }: Props) {
  const [url, setUrl] = useState('');
  const [count, setCount] = useState(100);
  const [mode, setMode] = useState<PipelineMode>('full');

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

      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          label="Number of responses"
          type="number"
          value={count}
          onChange={(e) => setCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
          disabled={disabled}
          size="small"
          slotProps={{ htmlInput: { min: 1 } }}
          sx={{ width: 200 }}
        />
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Mode:
        </Typography>
        <ToggleButtonGroup
          value={mode}
          exclusive
          size="small"
          onChange={(_, v: PipelineMode | null) => { if (v) setMode(v); }}
          disabled={disabled}
        >
          <ToggleButton value="full">Full pipeline</ToggleButton>
          <ToggleButton value="step">Step by step</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box>
        <Button
          variant="contained"
          disabled={disabled || !valid}
          onClick={() => onStart(url.trim(), count, mode)}
        >
          Start
        </Button>
      </Box>
    </Box>
  );
}
