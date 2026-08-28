import { getToken, setToken } from "./token";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const AUTH_REFRESH_PATH = "/api/v1/auth/refresh";

type ApiRequestInit = RequestInit & {
    accessToken?: string | null;
    retryAuth?: boolean;
};

type ErrorPayload = {
    error?: string;
    message?: string;
    detail?: string;
};

export class ApiError extends Error {
    readonly status: number;
    readonly body?: unknown;

    constructor(
        message: string,
        status: number,
        body?: unknown,
    ) {
        super(message);

        this.name = "ApiError";
        this.status = status;
        this.body = body;
    }
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
    refreshPromise ??= fetch(`${BASE_URL}${AUTH_REFRESH_PATH}`, {
        method: "POST",
        credentials: "include",
    })
        .then(async (response) => {
            if (!response.ok) {
                setToken(null);
                return false;
            }
            const data = (await response.json()) as { token?: string };
            if (!data.token) {
                setToken(null);
                return false;
            }
            setToken(data.token);
            return true;
        })
        .catch(() => {
            setToken(null);
            return false;
        })
        .finally(() => {
            refreshPromise = null;
        });

    return refreshPromise;
}

export async function apiFetch(
    path: string,
    options: ApiRequestInit = {},
): Promise<Response> {
    const {
        accessToken,
        retryAuth = true,
        headers: initialHeaders,
        ...requestOptions
    } = options;

    const send = () => {
        const headers = new Headers(initialHeaders);
        const token = accessToken ?? getToken();

        if (token) headers.set("Authorization", `Bearer ${token}`);
        if (
            requestOptions.body &&
            !(requestOptions.body instanceof FormData) &&
            !headers.has("Content-Type")
        ) {
            headers.set("Content-Type", "application/json");
        }

        return fetch(`${BASE_URL}${path}`, {
            ...requestOptions,
            headers,
            credentials: "include",
        });
    };

    let response = await send();

    if (
        response.status === 401 &&
        retryAuth &&
        path !== AUTH_REFRESH_PATH &&
        (await refreshAccessToken())
    ) {
        response = await send();
    }

    return response;
}

export async function apiJson<T>(
    path: string,
    options: ApiRequestInit = {},
): Promise<T> {
    const response = await apiFetch(path, options);

    if (!response.ok) {
        const body = await readJson<ErrorPayload>(response);
        const message =
            body?.error ??
            body?.message ??
            body?.detail ??
            response.statusText ??
            "Request failed";
        throw new ApiError(message, response.status, body);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
}

async function readJson<T>(response: Response): Promise<T | undefined> {
    try {
        return (await response.json()) as T;
    } catch {
        return undefined;
    }
}
