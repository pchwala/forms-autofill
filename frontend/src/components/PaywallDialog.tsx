import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Props {
  open: boolean;
  getToken: () => Promise<string>;
  onClose: () => void;
  /** Called after credits are granted so the caller can refresh balance + proceed. */
  onPaid: () => void;
}

export default function PaywallDialog({ open, getToken, onClose, onPaid }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePay() {
    setBusy(true);
    setError(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/credits/grant`, { method: 'POST', headers });
      if (!res.ok) throw new Error(`Payment failed: ${res.status}`);
      onPaid();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Unlock submission</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You've reviewed the predicted results for free. To generate and submit the actual
          responses to your Google Form, you need a submission credit.
        </DialogContentText>
        {error && (
          <DialogContentText color="error" sx={{ mt: 2 }}>
            {error}
          </DialogContentText>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button variant="contained" onClick={handlePay} disabled={busy}>
          {busy ? 'Processing…' : 'Pay (placeholder)'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
