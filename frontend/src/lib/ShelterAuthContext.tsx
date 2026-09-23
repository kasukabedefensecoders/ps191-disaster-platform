import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, fetchMyShelter, shelterLogin as apiShelterLogin, type Shelter } from "./api";

const STORAGE_KEY = "ps191_shelter_token";

interface ShelterAuthState {
  token: string | null;
  shelter: Shelter | null;
  loading: boolean;
  error: string | null;
  /** Resolves to the shelter's canonical display_code (e.g. "SH-01") on
   * success, so a caller can route to /shelter-dashboard/:code using the
   * server-confirmed code rather than whatever casing the officer typed. */
  login: (shelterCode: string) => Promise<string>;
  logout: () => void;
  refresh: () => void;
}

// Deliberately separate from AuthContext/AuthProvider: a shelter officer's
// session is a different credential (POST /auth/shelter-login, no account
// behind it, see docs/TRD.md §10) and a different token, stored under its
// own localStorage key so the two sessions never collide or get confused
// with each other in the same browser.
const ShelterAuthContext = createContext<ShelterAuthState | null>(null);

export function ShelterAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [shelter, setShelter] = useState<Shelter | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMyShelter(token)
      .then((s) => {
        if (!cancelled) setShelter(s);
      })
      .catch(() => {
        if (!cancelled) {
          setToken(null);
          try {
            localStorage.removeItem(STORAGE_KEY);
          } catch {
            /* ignore */
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, reloadTick]);

  const login = useCallback(async (shelterCode: string) => {
    setError(null);
    try {
      const session = await apiShelterLogin(shelterCode);
      const s = await fetchMyShelter(session.access_token);
      setToken(session.access_token);
      setShelter(s);
      try {
        localStorage.setItem(STORAGE_KEY, session.access_token);
      } catch {
        /* per-viewer convenience only */
      }
      return session.display_code ?? session.shelter_id;
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Invalid shelter code." : "Sign-in failed — is the API reachable?");
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setShelter(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const refresh = useCallback(() => setReloadTick((t) => t + 1), []);

  return (
    <ShelterAuthContext.Provider value={{ token, shelter, loading, error, login, logout, refresh }}>
      {children}
    </ShelterAuthContext.Provider>
  );
}

export function useShelterAuth(): ShelterAuthState {
  const ctx = useContext(ShelterAuthContext);
  if (!ctx) throw new Error("useShelterAuth must be used within ShelterAuthProvider");
  return ctx;
}
