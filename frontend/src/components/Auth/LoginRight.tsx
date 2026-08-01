import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

import { useNav } from "../../Hooks/useNav";
import { useState } from "react";

import { useAuth } from "../../context/AuthContext";
import { useNavigate } from "react-router-dom";


function LoginRight(){

    const {goToRegister} = useNav();

    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")


    const { login } = useAuth();
    const navigate = useNavigate();
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    console.log(email, password)

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();           // without this the page reloads and you lose everything
        setBusy(true);
        setError("");
        try {
            await login(email, password);
            navigate("/chat");     // whatever your post-login route is
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        } finally {
            setBusy(false);
        }
        }

    return(
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
                <OAuth />

                {/* Divider */}
                <div className="flex items-center mb-8">
                    <div className="flex-1 border-t border-slate-300" />

                    <span
                        className="
                            px-4
                            text-sm
                            text-slate-500
                        "
                    >
                        or sign in with email
                    </span>

                    <div className="flex-1 border-t border-slate-300" />
                </div>

                <form onSubmit={handleSubmit}>
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
                    <br/>
                    {/* Password */}
                    <TextInput 
                        id="pword"
                        label="Password"
                        type="password"
                        name="password"
                        value={password}
                        required
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    
                    {/* Login */}
                    {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
                    <AuthButton name={busy ? "Loging..." : "Login"} type="submit" disabled={busy} />
                </form>

                <p
                    className="
                        mt-8
                        text-center
                        text-slate-500
                    "
                >
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