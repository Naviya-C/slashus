import LoginLeft from "../components/Auth/LoginLeft";
import SignUpRight from "../components/Auth/SignUpRight";

function SignUp() {
    return (
        <div className="flex min-h-dvh lg:h-dvh lg:overflow-hidden">
            <div className="hidden lg:flex lg:w-2/5 lg:overflow-hidden">
                <LoginLeft />
            </div>

            <div className="flex w-full items-center justify-center lg:h-full lg:w-3/5 lg:overflow-hidden">
                <SignUpRight />
            </div>
        </div>
    );
}

export default SignUp;
