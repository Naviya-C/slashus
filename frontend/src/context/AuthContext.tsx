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
				setUser(await apiJson<User>("/api/v1/auth/me"));
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
		setUser(await apiJson<User>("/api/v1/auth/me"));
	}

	async function loginWithGoogle(idToken: string) {
		const res = await apiJson<LoginResponse>("/api/v1/auth/google", {
			method: "POST",
			body: JSON.stringify({ id_token: idToken }),
		});

		setToken(res.token);
		setUser(await apiJson<User>("/api/v1/auth/me"));
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

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
	return ctx;
}