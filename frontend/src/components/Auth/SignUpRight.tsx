import { useActionState, useState } from "react";

import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import PasswordRequirements, { isPasswordValid } from "./PasswordRequirements";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";
import { useAuth } from "../../context/AuthContext";

const SignUpRight = () => {
    const { goToLogin, goToChat } = useNav();
    const { signup } = useAuth();
    const [password, setPassword] = useState("");

    const [error, formAction, isBusy] = useActionState(
        async (_prevState: string | null, formData: FormData) => {
            const firstName = formData.get("firstName") as string;
            const lastName = formData.get("lastName") as string;
            const email = formData.get("email") as string;
            const password = formData.get("password") as string;
            const confirmPassword = formData.get("confirmPassword") as string;

            if (!isPasswordValid(password)) {
                return "Password must meet all requirements";
            }

            if (password !== confirmPassword) {
                return "Passwords do not match";
            }

            try {
                await signup(firstName, lastName, email, password);
                goToChat();
                return null;
            } catch (err) {
                return err instanceof Error
                    ? err.message
                    : "Registration failed";
            }
        },
        null,
    );

    return (
        <div className="w-full max-w-md">
            <h2 className="mb-3 text-center text-3xl font-bold text-slate-900 dark:text-white">
                Create Account
            </h2>

            <p className="mb-4 text-center text-slate-500 dark:text-neutral-400">
                Join SLASHUS and start learning smarter.
            </p>

            <OAuth onSuccess={goToChat} compact />

            <div className="my-4 flex items-center">
                <div className="flex-1 border-t border-slate-300 dark:border-neutral-800" />
                <span className="px-4 text-sm text-slate-500 dark:text-neutral-500">
                    or sign up with email
                </span>
                <div className="flex-1 border-t border-slate-300 dark:border-neutral-800" />
            </div>

            <form action={formAction} className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                    <TextInput
                        id="firstname"
                        label="First Name"
                        type="text"
                        name="firstName"
                        required
                    />

                    <TextInput
                        id="lastname"
                        label="Last Name"
                        type="text"
                        name="lastName"
                        required
                    />
                </div>

                <TextInput
                    id="email"
                    label="Email"
                    type="email"
                    name="email"
                    required
                />

                <TextInput
                    id="password"
                    label="Password"
                    type="password"
                    name="password"
                    value={password}
                    minLength={9}
                    autoComplete="new-password"
                    onChange={(event) => setPassword(event.target.value)}
                    required
                />

                <PasswordRequirements password={password} />

                <TextInput
                    id="confirmPassword"
                    label="Confirm Password"
                    type="password"
                    name="confirmPassword"
                    minLength={9}
                    autoComplete="new-password"
                    required
                />

                {error && (
                    <p className="mt-4 text-sm text-red-600 dark:text-red-400">
                        {error}
                    </p>
                )}

                <div className="pt-1">
                    <AuthButton
                        name={isBusy ? "Creating account..." : "Create Account"}
                        type="submit"
                        disabled={isBusy || !isPasswordValid(password)}
                    />
                </div>
            </form>

            <p className="mt-4 text-center text-slate-500 dark:text-neutral-400">
                Already have an account?{" "}
                <button
                    onClick={goToLogin}
                    className="cursor-pointer font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                    Sign In
                </button>
            </p>
        </div>
    );
};

export default SignUpRight;
