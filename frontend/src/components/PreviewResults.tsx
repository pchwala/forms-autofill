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
  defaultSelectedCodes?: string[] | null;
  onSubmit: (selectedCodes: string[]) => void;
}

export default function PreviewResults({ preview, count, hasCredits, busy, defaultSelectedCodes, onSubmit }: Props) {
  const [selected, setSelected] = useState<string[]>(
    () => defaultSelectedCodes ?? preview.personas.map((p) => p.code),
  );

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
          Podgląd — przewidywane wyniki
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Wybierz persony respondentów do uwzględnienia. Poniższe wykresy pokazują przewidywany
          rozkład odpowiedzi dla pierwszych {preview.questions.length} pytań. Nic nie jest wysyłane
          do momentu potwierdzenia.
        </Typography>
      </Box>

      {/* Personas */}
      <Box>
        <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1 }}>
          Persony
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
          Przewidywane rozkłady odpowiedzi
        </Typography>
        {noneSelected ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Wybierz co najmniej jedną personę, aby zobaczyć przewidywane rozkłady.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1.5 }}>
            {distributions.map((d) => (
              <Box key={d.id}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.75 }}>
                  {d.label}
                  {d.skipped_percent > 0 && (
                    <Typography component="span" variant="caption" color="text.secondary">
                      {' '}— {d.skipped_percent}% pomija (routing)
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
            ? `Generuj i wyślij ${count} odpowiedzi (${count} kredytów)`
            : `Odblokuj i wyślij (${count} kredytów potrzebne)`}
        </Button>
        {!hasCredits && (
          <Typography variant="body2" color="text.secondary">
            Zostaniesz przekierowany do płatności — podgląd jest zapisany.
          </Typography>
        )}
      </Box>
    </Box>
  );
}
