import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Step from '@mui/material/Step';
import StepConnector, { stepConnectorClasses } from '@mui/material/StepConnector';
import type { StepIconProps } from '@mui/material/StepIcon';
import StepLabel from '@mui/material/StepLabel';
import Stepper from '@mui/material/Stepper';
import { styled } from '@mui/material/styles';
import CheckIcon from '@mui/icons-material/Check';
import type { StepInfo } from '../hooks/usePipeline';

interface Props {
  steps: StepInfo[];
}

// Styled connector line between circles
const PipelineConnector = styled(StepConnector)(({ theme }) => ({
  [`&.${stepConnectorClasses.alternativeLabel}`]: {
    top: 11,
  },
  [`&.${stepConnectorClasses.active}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      borderColor: theme.palette.primary.main,
    },
  },
  [`&.${stepConnectorClasses.completed}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      borderColor: theme.palette.primary.main,
    },
  },
  [`& .${stepConnectorClasses.line}`]: {
    borderColor: '#2d3136',
    borderTopWidth: 3,
    borderRadius: 1,
  },
}));

// Styled circle icon
const PipelineIconRoot = styled('div')<{ ownerState: { status: 'done' | 'active' | 'pending' } }>(
  ({ theme, ownerState }) => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 36,
    height: 36,
    borderRadius: '50%',
    fontSize: '0.875rem',
    fontWeight: 700,
    zIndex: 1,
    ...(ownerState.status === 'done' && {
      backgroundColor: theme.palette.primary.main,
      color: '#fff',
    }),
    ...(ownerState.status === 'active' && {
      backgroundColor: '#4caf50',
      color: '#fff',
      boxShadow: '0 0 0 4px rgba(76,175,80,0.2)',
    }),
    ...(ownerState.status === 'pending' && {
      backgroundColor: '#1a1f26',
      color: '#9aa0a6',
      border: '2px solid #2d3136',
    }),
  }),
);

function PipelineStepIcon(props: StepIconProps & { stepStatus: 'done' | 'active' | 'pending' }) {
  const { icon, stepStatus } = props;
  return (
    <PipelineIconRoot ownerState={{ status: stepStatus }}>
      {stepStatus === 'done' ? (
        <CheckIcon sx={{ fontSize: 18 }} />
      ) : stepStatus === 'active' ? (
        <CircularProgress size={16} thickness={5} sx={{ color: '#fff' }} />
      ) : (
        icon
      )}
    </PipelineIconRoot>
  );
}

export default function PipelineProgress({ steps }: Props) {
  const activeIndex = steps.findIndex((s) => s.status === 'active');
  // MUI Stepper activeStep: index of the step currently in progress
  const activeStep = activeIndex === -1 ? steps.filter((s) => s.status === 'done').length : activeIndex;

  return (
    <Box sx={{ width: '100%' }}>
      <Stepper alternativeLabel activeStep={activeStep} connector={<PipelineConnector />}>
        {steps.map((step, i) => (
          <Step key={i} completed={step.status === 'done'}>
            <StepLabel
              StepIconComponent={(iconProps) => (
                <PipelineStepIcon {...iconProps} stepStatus={step.status} />
              )}
              sx={{
                '& .MuiStepLabel-label': {
                  fontSize: '0.75rem',
                  mt: 0.5,
                  color: step.status === 'active' ? '#4caf50' : undefined,
                  fontWeight: step.status === 'active' ? 700 : undefined,
                },
              }}
            >
              {step.label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}
