import { useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import type { PreviewData } from '../hooks/usePipeline';
import { aggregateDistributions } from '../utils/distributions';

interface Props {
  preview: PreviewData;
  count: number;
  hasCredits: boolean;
  busy?: boolean;
  onSubmit: (selectedCodes: string[]) => void;
}

export default function PreviewResults({ preview, count, hasCredits, busy, onSubmit }: Props) {
  const [selected, setSelected] = useState<string[]>(() => preview.personas.map((p) => p.code));

  const distributions = useMemo(
    () => aggregateDistributions(preview.personas, selected, preview.questions),
    [preview, selected],
  );

  function toggle(code: string) {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  }

  const noneSelected = selected.length === 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
          Preview — predicted results
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Pick which respondent personas to include. The charts below show the predicted answer
          distribution for the first {preview.questions.length} question
          {preview.questions.length === 1 ? '' : 's'}. Nothing is submitted until you confirm.
        </Typography>
      </Box>

      {/* Personas */}
      <Box>
        <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1 }}>
          Personas
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
          {preview.personas.map((p) => (
            <Box
              key={p.code}
              sx={{
                border: 1,
                borderColor: selected.includes(p.code) ? 'primary.main' : 'divider',
                borderRadius: 1,
                p: 1.5,
                transition: 'border-color 0.2s',
              }}
            >
              <FormControlLabel
                control={
                  <Checkbox
                    checked={selected.includes(p.code)}
                    onChange={() => toggle(p.code)}
                    disabled={busy}
                  />
                }
                label={
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {p.name}
                      </Typography>
                      <Chip label={`${p.count_percent}%`} size="small" variant="outlined" />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {p.description}
                    </Typography>
                  </Box>
                }
              />
            </Box>
          ))}
        </Box>
      </Box>

      <Divider />

      {/* Distributions */}
      <Box>
        <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1 }}>
          Predicted answer distributions
        </Typography>
        {noneSelected ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Select at least one persona to see predicted distributions.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1.5 }}>
            {distributions.map((d) => (
              <Box key={d.id}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.75 }}>
                  {d.label}
                  {d.skipped_percent > 0 && (
                    <Typography component="span" variant="caption" color="text.secondary">
                      {' '}— {d.skipped_percent}% skip (routing)
                    </Typography>
                  )}
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  {d.options.map((o) => (
                    <Box key={o.option} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography
                        variant="caption"
                        sx={{ width: 160, flexShrink: 0, color: 'text.secondary' }}
                        noWrap
                        title={o.option}
                      >
                        {o.option}
                      </Typography>
                      <Box sx={{ flexGrow: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(100, o.percent)}
                          sx={{ height: 8, borderRadius: 1 }}
                        />
                      </Box>
                      <Typography variant="caption" sx={{ width: 44, textAlign: 'right' }}>
                        {o.percent}%
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            ))}
          </Box>
        )}
      </Box>

      <Divider />

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          size="large"
          disabled={noneSelected || busy}
          onClick={() => onSubmit(selected)}
        >
          {hasCredits
            ? `Generate & submit ${count} responses (${count} credits)`
            : `Unlock & submit (${count} credits needed)`}
        </Button>
        {!hasCredits && (
          <Typography variant="body2" color="text.secondary">
            You'll be redirected to checkout — your preview is saved.
          </Typography>
        )}
      </Box>
    </Box>
  );
}
