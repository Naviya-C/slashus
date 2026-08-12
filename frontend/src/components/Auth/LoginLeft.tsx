import AuthHero from "./AuthHero";
import AuthFooter from "./AuthFooter";
import logo from "../../assets/logo_black.svg";
import { useNav } from "../../Hooks/useNav";

const LoginLeft = () => {
    const { goToHome } = useNav();

    return (
        <div
            className="
                w-full
                h-full
                bg-slate-950
                text-white
                flex
                flex-col
                justify-between
                p-10
                xl:p-12
            "
        >
            <div className="py-2">
                <img
                    onClick={goToHome}
                    src={logo}
                    alt="SLASHUS"
                    className="mb-7 w-30 cursor-pointer"
                />

                <AuthHero />

                <button
                    className="
                        mt-6
                        px-6
                        py-3
                        rounded-xl
                        bg-indigo-600
                        hover:bg-indigo-700
                        transition
                        font-medium
                        cursor-pointer
                    "
                >
                    Learn More
                </button>
            </div>

            <AuthFooter />
        </div>
    );
};

export default LoginLeft;
