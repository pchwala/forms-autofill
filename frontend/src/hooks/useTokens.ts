import { useCallback, useEffect, useState } from 'react';
import type { User } from 'firebase/auth';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface TokensState {
  tokens: number;
  loading: boolean;
  refresh: () => Promise<void>;
}

export function useTokens(
  getToken: () => Promise<string>,
  user: User | null,
  authLoading: boolean,
): TokensState {
  const [tokens, setTokens] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchTokens = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/user/status`, { headers });
      if (res.ok) {
        const data = (await res.json()) as { tokens: number };
        setTokens(data.tokens ?? 0);
      }
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    // Wait until Firebase auth resolves before calling an authed endpoint; firing
    // before sign-in completes sends no token and provokes a guaranteed 401.
    if (authLoading) return;
    // Auth resolved but there's no session (anonymous sign-in disabled or failed) —
    // there's no token to send, so skip the call instead of forcing a 401.
    if (!user) {
      setLoading(false);
      return;
    }
    void fetchTokens();
  }, [fetchTokens, user, authLoading]);

  return { tokens, loading, refresh: fetchTokens };
}
