import LoginLeft from "../components/Auth/LoginLeft";
import LoginRight from "../components/Auth/LoginRight";

function Login() {
    return (
        <div className="flex min-h-dvh lg:h-dvh lg:overflow-hidden">
            <div className="hidden lg:block lg:w-2/5 lg:overflow-hidden">
                <LoginLeft />
            </div>

            <div className="w-full lg:h-full lg:w-3/5 lg:overflow-hidden">
                <LoginRight />
            </div>
        </div>
    );
}

export default Login;
