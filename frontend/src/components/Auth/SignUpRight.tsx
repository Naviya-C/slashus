import { useActionState } from "react";

import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";
import { useAuth } from "../../context/AuthContext";

const SignUpRight = () => {
    const { goToLogin, goToChat } = useNav();
    const { signup } = useAuth();

    const [error, formAction, isBusy] = useActionState(
        async (_prevState: string | null, formData: FormData) => {
            const firstName = formData.get("firstName") as string;
            const lastName = formData.get("lastName") as string;
            const email = formData.get("email") as string;
            const password = formData.get("password") as string;
            const confirmPassword = formData.get("confirmPassword") as string;

            if (password !== confirmPassword) {
                return "Passwords do not match";
            }

            try {
                await signup(firstName, lastName, email, password);
                goToChat();
                return null; // Clear errors on success
            } catch (err) {
                return err instanceof Error ? err.message : "Registration failed";
            }
        },
        null // Initial error state
    );

    return (
        <div
            className="
                w-full
                flex
                items-center
                justify-center
                p-6
                sm:p-8
                lg:p-12
            "
        >
            <div className="w-full max-w-md">
                <h2
                    className="
                        text-4xl
                        font-bold
                        text-center
                        text-slate-900
                        mb-3
                    "
                >
                    Create Account
                </h2>

                <p
                    className="
                        text-center
                        text-slate-500
                        mb-8
                    "
                >
                    Join SLASHUS and start learning smarter.
                </p>

                {/* OAuth */}
                <OAuth />

                {/* Divider */}
                <div className="flex items-center my-8">
                    <div className="flex-1 border-t border-slate-300" />
                    <span className="px-4 text-sm text-slate-500">
                        or sign up with email
                    </span>
                    <div className="flex-1 border-t border-slate-300" />
                </div>

                <form action={formAction} className="space-y-4 sm:space-y-4">
                    <TextInput
                        id="firstname"
                        label="First Name"
                        type="text"
                        name="firstName"
                        required
                    />


                    {/* Last Name - removed value and onChange */}
                    <TextInput
                        id="lastname"
                        label="Last Name"
                        type="text"
                        name="lastName"
                        required
                    />

                    {/* Email - removed value and onChange */}
                    <TextInput
                        id="email"
                        label="Email"
                        type="email"
                        name="email"
                        required
                    />

                    {/* Password - removed value and onChange */}
                    <TextInput
                        id="password"
                        label="Password"
                        type="password"
                        name="password"
                        required
                    />

                    {/* Confirm Password - removed value and onChange */}
                    <TextInput
                        id="confirmPassword"
                        label="Confirm Password"
                        type="password"
                        name="confirmPassword"
                        required
                    />

                    {/* Automatically managed error display */}
                    {error && (
                        <p className="mt-4 text-sm text-red-600">{error}</p>
                    )}

                    <div className="mt-8">
                        {/* AuthButton uses the automatically managed isBusy state */}
                        <AuthButton
                            name={isBusy ? "Creating account..." : "Create Account"}
                            type="submit"
                            disabled={isBusy}
                        />
                    </div>
                </form>

                <p
                    className="
                        mt-8
                        text-center
                        text-slate-500
                    "
                >
                    Already have an account?{" "}
                    <button
                        onClick={goToLogin}
                        className="
                            text-indigo-600
                            font-medium
                            hover:text-indigo-700
                            cursor-pointer
                        "
                    >
                        Sign In
                    </button>
                </p>
            </div>
        </div>
    );
}

export default SignUpRight;
