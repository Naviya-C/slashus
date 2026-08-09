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
                return null; // Clear any existing errors on success
            } catch (err) {
                return err instanceof Error ? err.message : "Login failed";
            }
        },
        null // Initial error state is null
    );

    return (
        <div
            className="
                w-full
                min-h-screen
                flex
                items-center
                justify-center
                p-6
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
                        mb-10
                    "
                >
                    Welcome Back
                </h2>

                {/* OAuth */}
                <OAuth onSuccess={goToChat}/>

                {/* Divider */}
                <div className="flex items-center mb-8">
                    <div className="flex-1 border-t border-slate-300" />
                    <span className="px-4 text-sm text-slate-500">
                        or sign in with email
                    </span>
                    <div className="flex-1 border-t border-slate-300" />
                </div>

                <form action={formAction}>
                    <TextInput 
                        id="email"
                        label="Email"   
                        type="email" 
                        name="email"
                        required
                    />
                    <br/>
                    <TextInput 
                        id="pword"
                        label="Password"
                        type="password"
                        name="password"
                        required
                    />
                    
                    {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
                    
                    <AuthButton name={isBusy ? "Logging in..." : "Login"} type="submit" disabled={isBusy} />
                </form>

                <p className="mt-8 text-center text-slate-500">
                    Don't have an account?{" "}
                    <button
                        onClick={goToRegister}
                        className="
                            text-indigo-600
                            font-medium
                            hover:text-indigo-700
                            cursor-pointer
                        "
                    >
                        Sign Up
                    </button>
                </p>
            </div>
        </div>
    );
}

export default LoginRight;
