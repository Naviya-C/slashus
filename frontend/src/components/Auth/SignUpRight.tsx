import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";

function SignUpRight() {
    const { goToLogin } = useNav();

    return (
        <div
            className="
                w-3/5
                flex
                items-center
                justify-center
                p-12
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

                {/* Username */}
                <TextInput
                    id="username"
                    label="Username"
                />
                <br />

                {/* First Name */}
                <TextInput
                    id="firstname"
                    label="First Name"
                />
                <br />

                {/* Last Name */}
                <TextInput
                    id="lastname"
                    label="Last Name"
                />
                <br />

                {/* Email */}
                <TextInput
                    id="email"
                    label="Email"
                    type="email"
                />
                <br />

                {/* Password */}
                <TextInput
                    id="password"
                    label="Password"
                    type="password"
                />
                <br />

                {/* Confirm Password */}
                <TextInput
                    id="confirmPassword"
                    label="Confirm Password"
                    type="password"
                />

                <div className="mt-8">
                    <AuthButton name="Create Account" />
                </div>

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