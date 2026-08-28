import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";

import {
    getCurrentUser,
    loginWithGoogleToken,
    loginWithPassword,
    logoutSession,
    registerUser,
} from "../features/auth/api";
import type { User } from "../features/auth/types";
import { clearGoogleAutoSelect } from "../lib/google";

export type { User } from "../features/auth/types";

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
        let active = true;

        void getCurrentUser()
            .then((currentUser) => {
                if (active) setUser(currentUser);
            })
            .catch(() => {
                if (active) setUser(null);
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        setUser(await loginWithPassword(email, password));
    }, []);

    const loginWithGoogle = useCallback(async (idToken: string) => {
        setUser(await loginWithGoogleToken(idToken));
    }, []);

    const signup = useCallback(
        async (
            firstName: string,
            lastName: string,
            email: string,
            password: string,
        ) => {
            setUser(
                await registerUser(
                    firstName,
                    lastName,
                    email,
                    password,
                ),
            );
        },
        [],
    );

    const logout = useCallback(async () => {
        try {
            await logoutSession();
        } finally {
            setUser(null);
            clearGoogleAutoSelect();
        }
    }, []);

    const value = useMemo<AuthContextValue>(
        () => ({ user, loading, login, loginWithGoogle, signup, logout }),
        [user, loading, login, loginWithGoogle, signup, logout],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used inside <AuthProvider>");
    }
    return context;
}
