import AuthButton from "../Atomic/AuthButton";
import OAuth from "./OAuth";
import TextInput from "./TextInput";

function LoginRight(){
    return(
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

                {/* Username */}
                <TextInput 
                    id="uname"
                    label="UserName"   
                    type="text" 
                />
                <br/>
                {/* Password */}
                <TextInput 
                    id="pword"
                    label="Password"
                    type="password"
                />

                {/* Login */}
                <AuthButton name="Login"/>

                <p
                    className="
                        mt-8
                        text-center
                        text-slate-500
                    "
                >
                    Don't have an account?{" "}
                    <button
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