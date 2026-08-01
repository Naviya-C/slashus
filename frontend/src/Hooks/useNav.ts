import { useNavigate } from "react-router-dom";

export function useNav() {
    const navigate = useNavigate();

    return {
        goToLogin: () => navigate("/login"),
        goToRegister: () => navigate("/register"),
        goToHome: () => navigate("/"),
        goToHow: () => navigate("/how")
    };
}