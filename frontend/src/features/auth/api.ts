import { apiJson } from "../../lib/api";
import { setToken } from "../../lib/token";
import { normalizeUser } from "./normalizers";
import type { AuthMeResponse, LoginResponse, User } from "./types";

let sessionPromise: Promise<User> | null = null;

export function getCurrentUser(): Promise<User> {
    sessionPromise ??= apiJson<AuthMeResponse>("/api/v1/auth/me")
        .then(normalizeUser)
        .finally(() => {
            sessionPromise = null;
        });
    return sessionPromise;
}

export async function loginWithPassword(
    email: string,
    password: string,
): Promise<User> {
    const response = await apiJson<LoginResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        retryAuth: false,
    });
    return establishSession(response.token);
}

export async function loginWithGoogleToken(idToken: string): Promise<User> {
    const response = await apiJson<LoginResponse>("/api/v1/auth/google", {
        method: "POST",
        body: JSON.stringify({ id_token: idToken }),
        retryAuth: false,
    });
    return establishSession(response.token);
}

export async function registerUser(
    firstName: string,
    lastName: string,
    email: string,
    password: string,
): Promise<User> {
    await apiJson<void>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ firstName, lastName, email, password }),
        retryAuth: false,
    });
    return loginWithPassword(email, password);
}

export async function logoutSession(): Promise<void> {
    try {
        await apiJson<void>("/api/v1/auth/logout", { method: "POST" });
    } finally {
        setToken(null);
    }
}

async function establishSession(token: string): Promise<User> {
    setToken(token);
    try {
        const response = await apiJson<AuthMeResponse>("/api/v1/auth/me", {
            accessToken: token,
            retryAuth: false,
        });
        return normalizeUser(response);
    } catch (error) {
        setToken(null);
        throw error;
    }
}
