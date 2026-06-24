const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface Pack {
  tokens: number;
  pln: number;
}

export type PackKey = 'small' | 'medium' | 'large';

export function useBilling(getToken: () => Promise<string>) {
  async function packs(): Promise<Record<PackKey, Pack>> {
    const res = await fetch(`${API_URL}/billing/packs`);
    if (!res.ok) throw new Error(`Failed to load packs: ${res.status}`);
    return res.json() as Promise<Record<PackKey, Pack>>;
  }

  async function checkout(pack: PackKey, quantity: number): Promise<string> {
    const token = await getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_URL}/billing/checkout`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ pack, quantity }),
    });
    if (!res.ok) throw new Error(`Checkout failed: ${res.status}`);
    const data = (await res.json()) as { url: string };
    return data.url;
  }

  async function confirm(sessionId: string): Promise<number> {
    const token = await getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_URL}/billing/confirm`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`Confirm failed: ${res.status}`);
    const data = (await res.json()) as { tokens: number };
    return data.tokens;
  }

  return { packs, checkout, confirm };
}
