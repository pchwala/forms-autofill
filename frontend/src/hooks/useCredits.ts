import { useCallback, useEffect, useState } from 'react';
import { AUTH_DISABLED } from '../firebase';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface CreditsState {
  credits: number;
  loading: boolean;
  refresh: () => Promise<void>;
}

export function useCredits(getToken: () => Promise<string>): CreditsState {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(!AUTH_DISABLED);

  const fetchCredits = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/user/status`, { headers });
      if (res.ok) {
        const data = (await res.json()) as { credits: number };
        setCredits(data.credits ?? 0);
      }
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    void fetchCredits();
  }, [fetchCredits]);

  return { credits, loading, refresh: fetchCredits };
}
