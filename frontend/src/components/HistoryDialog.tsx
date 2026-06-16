import { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface PipelineRecord {
  pipeline_id: string;
  form_title: string;
  form_url: string;
  total_responses: number;
  status: 'completed' | 'failed' | 'in_progress' | 'preview_ready' | 'submitting';
  created_at: string;
  completed_at: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  getToken: () => Promise<string>;
  credits: number;
  onResume: (pipelineId: string) => void;
  onResubmit: (pipelineId: string) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

const STATUS_CHIP: Record<string, { label: string; color: 'success' | 'error' | 'warning' | 'info' }> = {
  completed:    { label: 'Ukończone',      color: 'success' },
  failed:       { label: 'Błąd',          color: 'error' },
  in_progress:  { label: 'W trakcie',     color: 'warning' },
  preview_ready:{ label: 'Podgląd gotowy',color: 'info' },
  submitting:   { label: 'Wysyłanie',     color: 'warning' },
};

export default function HistoryDialog({ open, onClose, getToken, credits, onResume, onResubmit }: Props) {
  const [records, setRecords] = useState<PipelineRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);

    getToken()
      .then((token) =>
        fetch(`${API_URL}/history`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
      )
      .then((res) => {
        if (!res.ok) throw new Error(`Błąd ładowania historii: ${res.status}`);
        return res.json() as Promise<PipelineRecord[]>;
      })
      .then((data) => {
        setRecords(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [open, getToken]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Historia</DialogTitle>
      <DialogContent dividers sx={{ p: 0 }}>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={28} />
          </Box>
        )}
        {!loading && error && (
          <Box sx={{ p: 2 }}>
            <Alert severity="error">{error}</Alert>
          </Box>
        )}
        {!loading && !error && records.length === 0 && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Brak historii. Uruchom potok, aby zobaczyć go tutaj.
            </Typography>
          </Box>
        )}
        {!loading && !error && records.length > 0 && (
          <List disablePadding>
            {records.map((record, idx) => {
              const chip = STATUS_CHIP[record.status] ?? { label: record.status, color: 'warning' as const };
              const canResume = record.status === 'preview_ready';
              const canResubmit = record.status === 'completed';
              const hasEnoughCredits = credits >= record.total_responses;

              return (
                <ListItem
                  key={record.pipeline_id}
                  divider={idx < records.length - 1}
                  sx={{ pr: 2, gap: 1, flexWrap: 'wrap', alignItems: 'flex-start', py: 1.5 }}
                >
                  <ListItemText
                    primary={record.form_title || 'Untitled'}
                    secondary={`${formatDate(record.created_at)} · ${record.total_responses} responses`}
                    sx={{ flexShrink: 1 }}
                  />
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0, pt: 0.5 }}>
                    <Chip label={chip.label} color={chip.color} size="small" variant="outlined" />
                    {canResume && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => { onResume(record.pipeline_id); onClose(); }}
                      >
                        Wznów
                      </Button>
                    )}
                    {canResubmit && (
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={!hasEnoughCredits}
                        title={!hasEnoughCredits ? `Potrzeba ${record.total_responses} kredytów` : undefined}
                        onClick={() => { onResubmit(record.pipeline_id); onClose(); }}
                      >
                        Wyślij ponownie
                      </Button>
                    )}
                  </Box>
                </ListItem>
              );
            })}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Zamknij</Button>
      </DialogActions>
    </Dialog>
  );
}
