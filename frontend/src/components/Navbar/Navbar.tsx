import Logo from "../Atomic/Logo";
import { LogIn } from "lucide-react";

function Navbar() {
    return (
        <nav className="mx-20 mt-5 rounded-full border-gray bg-white px-8 py-4 shadow-[0_20px_60px_rgba(0,0,0,0.12)]">
            <div className="flex items-center justify-between">
                <Logo />

                <div className="flex items-center gap-8">
                    <a
                        href=""
                        className="text-gray-700 hover:text-black"
                    >
                        Pricing
                    </a>

                    <a
                        href=""
                        className="text-gray-700 hover:text-black"
                    >
                        Privacy
                    </a>

                    <button className="flex items-center gap-2 rounded-xl border px-4 py-2 hover:bg-gray-100">
                        <LogIn size={20} />
                        <span>Login</span>
                    </button>
                </div>
            </div>
        </nav>
    );
}

export default Navbar;