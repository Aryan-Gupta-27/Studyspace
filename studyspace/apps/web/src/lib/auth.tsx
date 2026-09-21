"use client";

/**
 * Authentication context.
 *
 * The MVP keeps the session in localStorage so a page refresh stays signed in.
 * The access token is short-lived and refreshed automatically; this
 * trade-off is documented in the README's known limitations.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, apiRequest, type AuthSession, type Tokens, type User } from "./api";

const ACCESS_KEY = "studyspace.access_token";
const REFRESH_KEY = "studyspace.refresh_token";

interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    username: string;
    full_name: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  updateUser: (user: User) => void;
  /** Runs a request with the current token, refreshing once when it expires. */
  withAuth: <T>(run: (token: string) => Promise<T>) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStored(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const refreshToken = useRef<string | null>(null);
  const refreshing = useRef<Promise<string> | null>(null);

  const applySession = useCallback((tokens: Tokens, nextUser: User) => {
    refreshToken.current = tokens.refresh_token;
    setAccessToken(tokens.access_token);
    setUser(nextUser);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
      window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    }
  }, []);

  const clearSession = useCallback(() => {
    refreshToken.current = null;
    setAccessToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(ACCESS_KEY);
      window.localStorage.removeItem(REFRESH_KEY);
    }
  }, []);

  // Restore the session on first paint; a missing or invalid token simply
  // leaves the user signed out.
  useEffect(() => {
    const storedAccess = readStored(ACCESS_KEY);
    const storedRefresh = readStored(REFRESH_KEY);
    refreshToken.current = storedRefresh;

    if (!storedAccess) {
      setReady(true);
      return;
    }
    setAccessToken(storedAccess);
    apiRequest<User>("/users/me", { accessToken: storedAccess })
      .then(setUser)
      .catch(() => {
        // The access token may have expired while the tab was closed; the
        // first authenticated request below will refresh it transparently.
      })
      .finally(() => setReady(true));
  }, []);

  const doRefresh = useCallback(async (): Promise<string> => {
    if (refreshing.current) return refreshing.current;
    const current = refreshToken.current;
    if (!current) {
      clearSession();
      throw new ApiError(401, "UNAUTHORIZED", "Please sign in to continue.");
    }
    const pending = apiRequest<Tokens>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: current },
    })
      .then((tokens) => {
        refreshToken.current = tokens.refresh_token;
        setAccessToken(tokens.access_token);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
          window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
        }
        return tokens.access_token;
      })
      .catch((error) => {
        clearSession();
        throw error;
      })
      .finally(() => {
        refreshing.current = null;
      });
    refreshing.current = pending;
    return pending;
  }, [clearSession]);

  /**
   * Runs `run` with a valid token. On a 401 the token is refreshed once and
   * the call is retried, so expiry never surfaces as a dead end for the user.
   */
  const withAuth = useCallback(
    async <T,>(run: (token: string) => Promise<T>): Promise<T> => {
      let token = accessToken;
      if (!token) token = await doRefresh();
      try {
        return await run(token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          const next = await doRefresh();
          return run(next);
        }
        throw error;
      }
    },
    [accessToken, doRefresh],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const session = await apiRequest<AuthSession>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      applySession(session.tokens, session.user);
    },
    [applySession],
  );

  const register = useCallback(
    async (input: { email: string; username: string; full_name: string; password: string }) => {
      const session = await apiRequest<AuthSession>("/auth/register", {
        method: "POST",
        body: input,
      });
      applySession(session.tokens, session.user);
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    const token = refreshToken.current;
    if (token) {
      try {
        await apiRequest("/auth/logout", { method: "POST", body: { refresh_token: token } });
      } catch {
        // Signing out must always succeed locally, even if the API call fails.
      }
    }
    clearSession();
  }, [clearSession]);

  const refreshProfile = useCallback(async () => {
    const next = await withAuth((token) => apiRequest<User>("/users/me", { accessToken: token }));
    setUser(next);
  }, [withAuth]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      ready,
      login,
      register,
      logout,
      refreshProfile,
      updateUser: setUser,
      withAuth,
    }),
    [user, accessToken, ready, login, register, logout, refreshProfile, withAuth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside an AuthProvider");
  return context;
}
