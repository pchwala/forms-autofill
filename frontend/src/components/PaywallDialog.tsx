import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';
import { useBilling, type Pack, type PackKey } from '../hooks/useBilling';

const PACK_LABELS: Record<PackKey, string> = {
  small: 'Mały',
  medium: 'Średni',
  large: 'Duży',
};

function plCredits(n: number): string {
  if (n === 1) return 'kredyt';
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return 'kredyty';
  return 'kredytów';
}

const PACK_ORDER: PackKey[] = ['small', 'medium', 'large'];

const DISCOUNT_LABEL: Record<PackKey, string | null> = {
  small: null,
  medium: '15% taniej',
  large: '25% taniej',
};

interface Props {
  open: boolean;
  getToken: () => Promise<string>;
  onClose: () => void;
  creditsNeeded: number;
  creditsHeld: number;
}

export default function PaywallDialog({
  open,
  getToken,
  onClose,
  creditsNeeded,
  creditsHeld,
}: Props) {
  const { packs, checkout } = useBilling(getToken);

  const [packData, setPackData] = useState<Record<PackKey, Pack> | null>(null);
  const [selectedPack, setSelectedPack] = useState<PackKey>('small');
  const [quantity, setQuantity] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && !packData) {
      packs()
        .then(setPackData)
        .catch((err: Error) => setError(err.message));
    }
  }, [open, packData, packs]);

  async function handleCheckout() {
    setBusy(true);
    setError(null);
    try {
      const url = await checkout(selectedPack, quantity);
      window.location.href = url;
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const selectedCredits = packData ? packData[selectedPack].credits * quantity : 0;
  const still_short = creditsNeeded > creditsHeld + selectedCredits;

  function formatPrice(cents: number): string {
    return `${(cents / 100).toFixed(2).replace('.', ',')} zł`;
  }

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pr: 6 }}>
        Wybierz pakiet
        <IconButton
          onClick={onClose}
          disabled={busy}
          size="small"
          sx={{ position: 'absolute', right: 12, top: 12 }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 3, pb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Masz <strong>{creditsHeld}</strong> {plCredits(creditsHeld)} · potrzebujesz{' '}
          <strong>{creditsNeeded}</strong> do wysyłki
        </Typography>

        {/* Pack cards */}
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          {PACK_ORDER.map((key) => {
            const pack = packData?.[key];
            const isSelected = selectedPack === key;
            const discount = DISCOUNT_LABEL[key];
            return (
              <Card
                key={key}
                variant="outlined"
                sx={{
                  flex: 1,
                  borderColor: isSelected ? 'primary.main' : 'divider',
                  borderWidth: isSelected ? 2 : 1,
                  transition: 'border-color 0.15s',
                }}
              >
                <CardActionArea onClick={() => setSelectedPack(key)} sx={{ height: '100%' }}>
                  <CardContent sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="subtitle2" fontWeight={700}>
                      {PACK_LABELS[key]}
                    </Typography>
                    <Typography variant="h6" fontWeight={700} sx={{ my: 0.5 }}>
                      {pack ? pack.credits : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      kredytów
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      {pack ? formatPrice(pack.pln) : '—'}
                    </Typography>
                    {discount && (
                      <Chip label={discount} size="small" color="success" sx={{ mt: 0.5 }} />
                    )}
                  </CardContent>
                </CardActionArea>
              </Card>
            );
          })}
        </Box>

        {/* Quantity */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <TextField
            label="Ilość"
            type="number"
            size="small"
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
            inputProps={{ min: 1 }}
            sx={{ width: 100 }}
          />
          {packData && (
            <Typography variant="body2" color="text.secondary">
              = {selectedCredits} {plCredits(selectedCredits)} ·{' '}
              {formatPrice(packData[selectedPack].pln * quantity)}
              {still_short && (
                <Typography component="span" variant="body2" color="warning.main">
                  {' '}(brak jeszcze {creditsNeeded - creditsHeld - selectedCredits})
                </Typography>
              )}
            </Typography>
          )}
        </Box>

        {error && (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        )}

        <Button
          variant="contained"
          size="large"
          onClick={handleCheckout}
          disabled={busy || !packData}
          fullWidth
        >
          {busy ? 'Przekierowywanie…' : 'Przejdź do płatności'}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
