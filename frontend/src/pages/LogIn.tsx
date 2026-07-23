import LoginLeft from "../components/Auth/LoginLeft";
import LoginRight from "../components/Auth/LoginRight";

function Login() {
    return (
        <div className="min-h-screen flex">
            {/* Hidden on mobile */}
            <div className="hidden lg:block lg:w-2/5">
                <LoginLeft />
            </div>

            {/* Full width on mobile, 3/5 on desktop */}
            <div className="w-full lg:w-3/5">
                <LoginRight />
            </div>
        </div>
    );
}

export default Login;