import AuthHero from "./AuthHero";
import AuthFooter from "./AuthFooter";
import logo from "../../assets/logo_black.svg";


function LoginLeft(){
    return(
        <div
                className="
                    w-2/5
                    bg-slate-950
                    text-white
                    flex
                    flex-col
                    justify-between
                    p-16
                "
            >
                <div>
                    <img
                        src={logo}
                        alt="SLASHUS"
                        className="w-30 mb-12"
                    />

                    <AuthHero />

                    <button
                        className="
                            mt-10
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
}

export default LoginLeft;