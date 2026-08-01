import { getToken, setToken } from "./token";

const BASE = import.meta.env.VITE_API_URL;

// Single-flight refresh. If three requests 401 at the same moment, they must
// all await ONE refresh call, not fire three.
let refreshPromise: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include", // the refresh token is an HttpOnly cookie
        });
        if (!res.ok) {
          setToken(null);
          return false;
        }
        const data = await res.json();
        setToken(data.token);
        return true;
      } catch {
        setToken(null);
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const send = () => {
    const headers = new Headers(options.headers);

    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body && !(options.body instanceof FormData)) {
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }

    return fetch(`${BASE}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });
  };

  let res = await send();

  if (res.status === 401 && !path.includes("/auth/refresh")) {
    const ok = await refresh();
    if (ok) res = await send();
  }

  return res;
}

export async function apiJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      /* non-JSON error body; keep statusText */
    }
    throw new Error(message);
  }
  // 204 No Content has no body to parse.
  if (res.status === 204) return undefined as T;
  return res.json();
}