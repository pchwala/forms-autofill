import { useCallback, useEffect, useState } from 'react';
import {
  linkWithPopup,
  onAuthStateChanged,
  signInAnonymously,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';
import { auth, googleProvider, AUTH_DISABLED } from '../firebase';

export interface AuthState {
  user: User | null;
  loading: boolean;
  isAnonymous: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string>;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!AUTH_DISABLED);

  useEffect(() => {
    if (AUTH_DISABLED || !auth) {
      setLoading(false);
      return;
    }
    const unsubscribe = onAuthStateChanged(auth, (u) => {
      if (!u) {
        // No session yet — sign in anonymously so every visitor has a uid + token.
        void signInAnonymously(auth!);
        return;
      }
      setUser(u);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  // Upgrade an anonymous account to Google (keeps the same uid/credits), or sign in
  // with Google directly if there's no anonymous session to link.
  const signInWithGoogle = useCallback(async () => {
    if (AUTH_DISABLED || !auth || !googleProvider) return;
    const current = auth.currentUser;
    if (current?.isAnonymous) {
      try {
        await linkWithPopup(current, googleProvider);
        return;
      } catch (err: unknown) {
        // Account already exists for this Google identity — fall back to plain sign-in.
        const code = (err as { code?: string }).code;
        if (code !== 'auth/credential-already-in-use' && code !== 'auth/email-already-in-use') {
          throw err;
        }
      }
    }
    await signInWithPopup(auth, googleProvider);
  }, []);

  const signOut = useCallback(async () => {
    if (AUTH_DISABLED || !auth) return;
    await firebaseSignOut(auth);
    // onAuthStateChanged will re-trigger anonymous sign-in.
  }, []);

  const getToken = useCallback(async (): Promise<string> => {
    if (AUTH_DISABLED) return '';
    if (!user) return '';
    return user.getIdToken();
  }, [user]);

  return {
    user,
    loading,
    isAnonymous: user?.isAnonymous ?? false,
    signInWithGoogle,
    signOut,
    getToken,
  };
}
