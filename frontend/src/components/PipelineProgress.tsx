import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import type { StepInfo } from '../hooks/usePipeline';

interface Props {
  progress: number;
  steps: StepInfo[];
}

function StepChip({ step, index }: { step: StepInfo; index: number }) {
  const icon =
    step.status === 'done' ? (
      <CheckCircleIcon fontSize="small" />
    ) : step.status === 'active' ? (
      <CircularProgress size={14} color="inherit" />
    ) : (
      <RadioButtonUncheckedIcon fontSize="small" />
    );

  return (
    <Chip
      key={index}
      label={`${index + 1}. ${step.label}`}
      icon={icon}
      size="small"
      color={step.status === 'done' ? 'success' : step.status === 'active' ? 'primary' : 'default'}
      variant={step.status === 'pending' ? 'outlined' : 'filled'}
    />
  );
}

export default function PipelineProgress({ progress, steps }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Overall progress
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
          {Math.round(progress)}%
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={Math.min(progress, 100)}
        sx={{ height: 10, borderRadius: 5 }}
      />

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
        {steps.map((step, i) => (
          <StepChip key={i} step={step} index={i} />
        ))}
      </Box>
    </Box>
  );
}
