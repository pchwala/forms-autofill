import { useCallback, useEffect, useState } from 'react';
import { AUTH_DISABLED } from '../firebase';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface UserStatus {
  freeUsed: boolean;
  paid: boolean;
  loading: boolean;
  refresh: () => void;
}

export function useUserStatus(getToken: () => Promise<string>): UserStatus {
  const [freeUsed, setFreeUsed] = useState(false);
  const [paid, setPaid] = useState(false);
  const [loading, setLoading] = useState(!AUTH_DISABLED);

  const fetchStatus = useCallback(async () => {
    if (AUTH_DISABLED) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/user/status`, { headers });
      if (res.ok) {
        const data = (await res.json()) as { free_used: boolean; paid: boolean };
        setFreeUsed(data.free_used);
        setPaid(data.paid);
      }
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  return { freeUsed, paid, loading, refresh: fetchStatus };
}
