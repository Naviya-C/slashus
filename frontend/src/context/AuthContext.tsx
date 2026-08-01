import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { apiJson } from "../lib/api";
import { setToken } from "../lib/token";

// Mirrors auth-service's MeResponse DTO. If you change that Go struct, change
// this too — nothing checks them against each other at compile time.
export type User = {
  userid: string;
  firstName: string;
  lastName: string;
  email: string;
  createdAt: string;
};

type LoginResponse = {
  token: string;
};

type AuthContextValue = {
  user: User | null;
  /** True until the initial session check finishes. Guard routes on this. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    firstName: string,
    lastName: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Session bootstrap. The access token lives only in memory, so a page reload
  // starts with nothing — but the refresh cookie survives.
  //
  // This calls /me with no token on purpose. The gateway 401s, apiFetch
  // transparently refreshes and retries, and we get the profile back. If there
  // is no valid cookie the refresh fails, apiJson throws, and the user is
  // simply logged out. One code path covers both cases.
  //
  // Without this effect, every page reload logs the user out.
  useEffect(() => {
    (async () => {
      try {
        setUser(await apiJson<User>("/api/v1/auth/me"));
      } catch {
        setUser(null);
      } finally {
        // In a finally block so a thrown error can't leave the app stuck on a
        // permanent loading spinner.
        setLoading(false);
      }
    })();
  }, []);

  async function login(email: string, password: string) {
    const res = await apiJson<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    // Set the token BEFORE fetching the profile — apiFetch reads it from the
    // token module to build the Authorization header.
    setToken(res.token);
    setUser(await apiJson<User>("/api/v1/auth/me"));
  }

  async function signup(
    firstName: string,
    lastName: string,
    email: string,
    password: string,
  ) {
    // Field names must match auth-service's RegisterRequest exactly — it uses
    // camelCase json tags, so firstName/lastName, not first_name.
    await apiJson("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ firstName, lastName, email, password }),
    });
    // Register does not return tokens, so log in to get a session.
    await login(email, password);
  }

  async function logout() {
    try {
      // Authenticates with the refresh cookie, not the bearer token — which is
      // why the gateway registers this route as public. It still works with an
      // expired access token.
      await apiJson("/api/v1/auth/logout", { method: "POST" });
    } finally {
      // Clear locally even if the request failed. A network error must not
      // leave the user apparently still signed in.
      setToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  // Turns a forgotten <AuthProvider> into a clear message instead of
  // "cannot read properties of null".
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}