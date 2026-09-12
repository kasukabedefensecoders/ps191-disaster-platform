import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, getMe, login as apiLogin, type CurrentUser } from "./api";

const STORAGE_KEY = "ps191_access_token";

interface AuthState {
  token: string | null;
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null; // private-browsing / storage-blocked contexts
    }
  });
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setLoading(false);
      return;
    }
    getMe(token)
      .then((u) => {
        if (!cancelled) setUser(u);
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
  }, [token]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const tokens = await apiLogin(email, password);
      const me = await getMe(tokens.access_token);
      setToken(tokens.access_token);
      setUser(me);
      try {
        localStorage.setItem(STORAGE_KEY, tokens.access_token);
      } catch {
        /* per-viewer convenience only — a failed write just means no persistence across reloads */
      }
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Incorrect email or password." : "Login failed — is the API reachable?");
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return <AuthContext.Provider value={{ token, user, loading, error, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
