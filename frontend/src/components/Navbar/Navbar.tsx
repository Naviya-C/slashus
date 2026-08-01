import { useState } from "react";
import Logo from "../Atomic/Logo";
import { LogIn, Menu, X } from "lucide-react";
import { useNavScroll } from "../../Hooks/NavHook";
import NavButton from "../Atomic/NavButton";

import { useNav } from "../../Hooks/useNav";


function Navbar() {
    const scrolled = useNavScroll(20);
    const [menuOpen, setMenuOpen] = useState(false);

    const { goToLogin, goToHow, goToHome} = useNav();

    const closeMenu = () => setMenuOpen(false);

    return (
        <>
            <nav
                className={`4
                    fixed top-0 left-0 right-0 z-50
                    mx-4 md:mx-10 lg:mx-40
                    mt-5
                    rounded-full
                    border
                    border-gray-200
                    bg-white
                    px-10
                    py-4
                    transition-all
                    duration-300
                    ${
                        scrolled
                            ? "shadow-[0_20px_60px_rgba(0,0,0,0.12)]"
                            : ""
                    }
                `}
            >
                <div className="flex items-center justify-between">
                    {/* Logo */}
                    <button onClick={goToHome} className="hover:cursor-pointer">
                        <Logo />
                    </button>

                    {/* Desktop Links */}
                    <ul
                        className="
                            hidden
                            md:flex
                            items-center
                            gap-[clamp(1rem,2vw,3rem)]
                        "
                    >
                        <li>
                            <NavButton name="How Works" onClick={goToHow}/ >

                        </li>

                        <li>
                            <NavButton name="Privacy" />
                        </li>

                        <li>
                            <NavButton name="About Us" />
                        </li>

                        <li>
                            <NavButton name="Pricing" />
                        </li>
                    </ul>

                    {/* Desktop CTA */}
                    <div
                        className="
                            hidden
                            md:flex
                            items-center
                        "
                    >
                        <button
                            onClick={goToLogin}
                            className="
                                flex
                                items-center
                                gap-2
                                rounded-xl
                                border
                                border-gray-200
                                px-4
                                py-2
                                hover:bg-gray-100
                                transition
                                cursor-pointer
                            "
                        >
                            <LogIn size={20} />
                            <span>Login</span>
                        </button>
                    </div>

                    {/* Mobile Hamburger */}
                    <button
                        className="md:hidden hover:cursor-pointer"
                        onClick={() =>
                            setMenuOpen(
                                (v) => !v
                            )
                        }
                    >
                        {menuOpen ? (
                            <X size={24} />
                        ) : (
                            <Menu size={24} />
                        )}
                    </button>
                </div>
            </nav>

            {/* Mobile Menu */}
            {menuOpen && (
                <div
                    className="
                        md:hidden
                        mx-4
                        mt-4
                        rounded-3xl
                        bg-white
                        p-6
                        shadow-[0_20px_60px_rgba(0,0,0,0.12)]
                    "
                >
                    <div className="flex flex-col gap-5">
                        <button
                            onClick={closeMenu}
                            className="
                                text-left
                                text-gray-700
                                hover:text-black
                            "
                        >
                            How Works
                        </button>

                        <button
                            onClick={closeMenu}
                            className="
                                text-left
                                text-gray-700
                                hover:text-black
                            "
                        >
                            Privacy
                        </button>

                        <button
                            onClick={closeMenu}
                            className="
                                text-left
                                text-gray-700
                                hover:text-black
                            "
                        >
                            About Us
                        </button>

                        <button
                            onClick={closeMenu}
                            className="
                                text-left
                                text-gray-700
                                hover:text-black
                            "
                        >
                            Pricing
                        </button>

                        <button
                            onClick={() => {
                                closeMenu();
                                goToLogin();
                            }}
                            className="
                                mt-2
                                flex
                                items-center
                                justify-center
                                gap-2
                                rounded-xl
                                border
                                border-gray-200
                                px-4
                                py-3
                                hover:bg-gray-100
                            "
                        >
                            <LogIn size={20} />
                            Login
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}

export default Navbar;