import {
    createContext,
    useContext,
    useEffect,
    useState,
    type ReactNode,
} from "react";

import { apiJson } from "../lib/api";
import { setToken } from "../lib/token";
import { clearGoogleAutoSelect } from "../lib/google";

export type User = {
    userid: string;
    firstName: string;
    lastName: string;
    email: string;
    createdAt: string;
};

type ApiUser = {
    userid?: string;
    user_id?: string;
    id?: string;
    firstName?: string;
    first_name?: string;
    lastName?: string;
    last_name?: string;
    name?: string;
    email: string;
    createdAt?: string;
    created_at?: string;
};

type AuthMeResponse = ApiUser | { user: ApiUser };

type LoginResponse = {
    token: string;
};

type AuthContextValue = {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    loginWithGoogle: (idToken: string) => Promise<void>;
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

    useEffect(() => {
        (async () => {
            try {
                setUser(
                    normalizeUser(
                        await apiJson<AuthMeResponse>("/api/v1/auth/me"),
                    ),
                );
            } catch {
                setUser(null);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    async function login(email: string, password: string) {
        const res = await apiJson<LoginResponse>("/api/v1/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });

        setToken(res.token);
        setUser(
            normalizeUser(await apiJson<AuthMeResponse>("/api/v1/auth/me")),
        );
    }

    async function loginWithGoogle(idToken: string) {
        const res = await apiJson<LoginResponse>("/api/v1/auth/google", {
            method: "POST",
            body: JSON.stringify({ id_token: idToken }),
        });

        setToken(res.token);
        setUser(
            normalizeUser(await apiJson<AuthMeResponse>("/api/v1/auth/me")),
        );
    }

    async function signup(
        firstName: string,
        lastName: string,
        email: string,
        password: string,
    ) {
        await apiJson("/api/v1/auth/register", {
            method: "POST",
            body: JSON.stringify({ firstName, lastName, email, password }),
        });
        await login(email, password);
    }

    async function logout() {
        try {
            await apiJson("/api/v1/auth/logout", { method: "POST" });
        } finally {
            setToken(null);
            setUser(null);
            clearGoogleAutoSelect();
        }
    }

    return (
        <AuthContext.Provider
            value={{ user, loading, login, loginWithGoogle, signup, logout }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
    return ctx;
}

function normalizeUser(response: AuthMeResponse): User {
    const source = "user" in response ? response.user : response;
    const nameParts = source.name?.trim().split(/\s+/) ?? [];

    return {
        userid: source.userid ?? source.user_id ?? source.id ?? "",
        firstName: source.firstName ?? source.first_name ?? nameParts[0] ?? "",
        lastName:
            source.lastName ?? source.last_name ?? nameParts.slice(1).join(" "),
        email: source.email,
        createdAt: source.createdAt ?? source.created_at ?? "",
    };
}
