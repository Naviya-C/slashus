import { useState } from "react";
import { useNavigate } from "react-router-dom";

import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";
import { useAuth } from "../../context/AuthContext";

function SignUpRight() {
    const { goToLogin } = useNav();
    const { signup } = useAuth();
    const navigate = useNavigate();

    // All hooks must live INSIDE the component. At module level they run once
    // at import, outside any render, and React throws.
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        // Without this the browser does a full page navigation and the request
        // never fires.
        e.preventDefault();
        setError("");

        // Checked before setBusy so an early return can't leave the button
        // permanently disabled.
        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        setBusy(true);
        try {
            // signup() registers and then logs in, so there is a session by the
            // time this resolves.
            await signup(firstName, lastName, email, password);
            navigate("/chat");
        } catch (err) {
            // apiJson surfaces the server's {"error": "..."} message, so this
            // shows "email already registered" rather than a generic failure.
            setError(err instanceof Error ? err.message : "Registration failed");
        } finally {
            setBusy(false);
        }
    }

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

                    <span
                        className="
                            px-4
                            text-sm
                            text-slate-500
                        "
                    >
                        or sign up with email
                    </span>

                    <div className="flex-1 border-t border-slate-300" />
                </div>

                <form onSubmit={handleSubmit}>
                    {/* First Name */}
                    <TextInput
                        id="firstname"
                        label="First Name"
                        type="text"
                        name="firstName"
                        value={firstName}
                        required
                        onChange={(e) => setFirstName(e.target.value)}
                    />
                    <br />

                    {/* Last Name */}
                    <TextInput
                        id="lastname"
                        label="Last Name"
                        type="text"
                        name="lastName"
                        value={lastName}
                        required
                        onChange={(e) => setLastName(e.target.value)}
                    />
                    <br />

                    {/* Email */}
                    <TextInput
                        id="email"
                        label="Email"
                        type="email"
                        name="email"
                        value={email}
                        required
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <br />

                    {/* Password */}
                    <TextInput
                        id="password"
                        label="Password"
                        type="password"
                        name="password"
                        value={password}
                        required
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    <br />

                    {/* Confirm Password */}
                    <TextInput
                        id="confirmPassword"
                        label="Confirm Password"
                        type="password"
                        name="confirmPassword"
                        value={confirmPassword}
                        required
                        onChange={(e) => setConfirmPassword(e.target.value)}
                    />

                    {error && (
                        <p className="mt-4 text-sm text-red-600">{error}</p>
                    )}

                    <div className="mt-8">
                        <AuthButton
                            name={busy ? "Creating account..." : "Create Account"}
                            type="submit"
                            disabled={busy}
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