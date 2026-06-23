import { useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import type { PreviewData, PreviewDistribution } from '../hooks/usePipeline';
import { aggregateDistributions } from '../utils/distributions';

/** A grid header followed by its rows, or a single standalone question. */
type DistGroup =
  | { kind: 'single'; dist: PreviewDistribution }
  | { kind: 'grid'; gridId: string; gridLabel: string; rows: PreviewDistribution[] };

/** Collapse consecutive grid_row distributions (same grid_id) into one group. */
function groupDistributions(distributions: PreviewDistribution[]): DistGroup[] {
  const groups: DistGroup[] = [];
  for (const d of distributions) {
    if (d.grid_id) {
      const last = groups[groups.length - 1];
      if (last && last.kind === 'grid' && last.gridId === d.grid_id) {
        last.rows.push(d);
      } else {
        groups.push({
          kind: 'grid',
          gridId: d.grid_id,
          gridLabel: d.grid_label ?? d.label,
          rows: [d],
        });
      }
    } else {
      groups.push({ kind: 'single', dist: d });
    }
  }
  return groups;
}

function OptionBars({ options }: { options: PreviewDistribution['options'] }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
      {options.map((o) => (
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
  );
}

function SkippedNote({ percent }: { percent: number }) {
  if (percent <= 0) return null;
  return (
    <Typography component="span" variant="caption" color="text.secondary">
      {' '}— {percent}% pomija (routing)
    </Typography>
  );
}

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
            {groupDistributions(distributions).map((group) =>
              group.kind === 'grid' ? (
                <Box key={group.gridId}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    {group.gridLabel}
                  </Typography>
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 1.5,
                      pl: 1.5,
                      borderLeft: 2,
                      borderColor: 'divider',
                    }}
                  >
                    {group.rows.map((d) => (
                      <Box key={d.id}>
                        <Typography
                          variant="caption"
                          sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}
                        >
                          {d.row_label ?? d.label}
                          <SkippedNote percent={d.skipped_percent} />
                        </Typography>
                        <OptionBars options={d.options} />
                      </Box>
                    ))}
                  </Box>
                </Box>
              ) : (
                <Box key={group.dist.id}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.75 }}>
                    {group.dist.label}
                    <SkippedNote percent={group.dist.skipped_percent} />
                  </Typography>
                  <OptionBars options={group.dist.options} />
                </Box>
              ),
            )}
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
