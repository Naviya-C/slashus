import { useActionState } from "react";

import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";
import { useAuth } from "../../context/AuthContext";

const LoginRight = () => {
    const { login } = useAuth();
    const { goToRegister, goToChat } = useNav();

    const [error, formAction, isBusy] = useActionState(
        async (_prevState: string | null, formData: FormData) => {
            const email = formData.get("email") as string;
            const password = formData.get("password") as string;

            try {
                await login(email, password);
                goToChat();
                return null;
            } catch (err) {
                return err instanceof Error ? err.message : "Login failed";
            }
        },
        null,
    );

    return (
        <div className="w-full max-w-md">
            <h2 className="mb-2 text-center text-4xl font-bold text-slate-900 dark:text-white">
                Welcome Back
            </h2>
            <p className="mb-6 text-center text-slate-500 dark:text-neutral-400">
                Sign in to pick up where you left off.
            </p>

            <OAuth onSuccess={goToChat} compact />

            <div className="mb-6 flex items-center">
                <div className="flex-1 border-t border-slate-300 dark:border-neutral-800" />
                <span className="px-4 text-sm text-slate-500 dark:text-neutral-500">
                    or sign in with email
                </span>
                <div className="flex-1 border-t border-slate-300 dark:border-neutral-800" />
            </div>

            <form action={formAction} className="space-y-4">
                <TextInput
                    id="email"
                    label="Email"
                    type="email"
                    name="email"
                    required
                />
                <TextInput
                    id="pword"
                    label="Password"
                    type="password"
                    name="password"
                    required
                />

                {error && (
                    <p className="mb-3 text-sm text-red-600 dark:text-red-400">
                        {error}
                    </p>
                )}

                <div className="pt-3">
                    <AuthButton
                        name={isBusy ? "Logging in..." : "Login"}
                        type="submit"
                        disabled={isBusy}
                    />
                </div>
            </form>

            <p className="mt-6 text-center text-slate-500 dark:text-neutral-400">
                Don't have an account?{" "}
                <button
                    onClick={goToRegister}
                    className="cursor-pointer font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                    Sign Up
                </button>
            </p>
        </div>
    );
};

export default LoginRight;
