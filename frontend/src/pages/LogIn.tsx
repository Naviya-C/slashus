import LoginLeft from "../components/Auth/LoginLeft";
import LoginRight from "../components/Auth/LoginRight";

const Login = () => {
    return (
        <div className="min-h-screen bg-white flex">
            <LoginLeft />
            <LoginRight />
        </div>
    );
};

export default Login;