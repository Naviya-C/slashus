import LoginLeft from "../components/Auth/LoginLeft";
import SignUpRight from "../components/Auth/SignUpRight";

function SignUp() {
    return (
        <div className="min-h-screen flex">
            {/* Hidden on mobile */}
            <div className="hidden lg:flex lg:w-2/5">
                <LoginLeft />
            </div>

            {/* Center the form */}
            <div className="w-full lg:w-3/5 flex items-center justify-center">
                <SignUpRight />
            </div>
        </div>
    );
}

export default SignUp;