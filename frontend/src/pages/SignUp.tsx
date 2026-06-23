import { FcGoogle } from "react-icons/fc";
import { FaFacebookF } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";

{/* Right Side */}
function SignUp(){
    return(
        <div
            className="
                w-1/2
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

                {/* Username */}
                <div className="mb-5">
                    <label
                        className="
                            block
                            mb-2
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Username
                    </label>

                    <input
                        type="text"
                        className="
                            w-full
                            h-12
                            px-4
                            rounded-xl
                            border
                            border-slate-300
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-100
                        "
                    />
                </div>

                {/* First Name */}
                <div className="mb-5">
                    <label
                        className="
                            block
                            mb-2
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        First Name
                    </label>

                    <input
                        type="text"
                        className="
                            w-full
                            h-12
                            px-4
                            rounded-xl
                            border
                            border-slate-300
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-100
                        "
                    />
                </div>

                {/* Second Name */}
                <div className="mb-5">
                    <label
                        className="
                            block
                            mb-2
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Second Name
                    </label>

                    <input
                        type="text"
                        className="
                            w-full
                            h-12
                            px-4
                            rounded-xl
                            border
                            border-slate-300
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-100
                        "
                    />
                </div>

                {/* Password */}
                <div className="mb-5">
                    <label
                        className="
                            block
                            mb-2
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Password
                    </label>

                    <input
                        type="password"
                        className="
                            w-full
                            h-12
                            px-4
                            rounded-xl
                            border
                            border-slate-300
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-100
                        "
                    />
                </div>

                {/* Confirm Password */}
                <div className="mb-6">
                    <label
                        className="
                            block
                            mb-2
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Re-enter Password
                    </label>

                    <input
                        type="password"
                        className="
                            w-full
                            h-12
                            px-4
                            rounded-xl
                            border
                            border-slate-300
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-100
                        "
                    />
                </div>

                {/* Signup Button */}
                <button
                    className="
                        w-full
                        h-14
                        rounded-full
                        bg-slate-950
                        text-white
                        font-semibold
                        hover:bg-slate-800
                        transition
                        cursor-pointer
                    "
                >
                    Create Account
                </button>

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
                        or continue with
                    </span>

                    <div className="flex-1 border-t border-slate-300" />
                </div>

                {/* OAuth */}
                <div className="flex justify-center gap-4">
                    <button
                        className="
                            w-14
                            h-14
                            border
                            border-slate-300
                            rounded-xl
                            flex
                            items-center
                            justify-center
                            hover:bg-slate-50
                            transition
                        "
                    >
                        <FcGoogle size={28} />
                    </button>

                    <button
                        className="
                            w-14
                            h-14
                            border
                            border-slate-300
                            rounded-xl
                            flex
                            items-center
                            justify-center
                            hover:bg-slate-50
                            transition
                        "
                    >
                        <FaFacebookF
                            size={24}
                            className="text-blue-600"
                        />
                    </button>

                    <button
                        className="
                            w-14
                            h-14
                            border
                            border-slate-300
                            rounded-xl
                            flex
                            items-center
                            justify-center
                            hover:bg-slate-50
                            transition
                        "
                    >
                        <FaXTwitter
                            size={22}
                            className="text-black"
                        />
                    </button>
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

export default SignUp;
