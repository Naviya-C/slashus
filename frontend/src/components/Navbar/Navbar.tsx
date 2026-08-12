import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LogIn, Menu, X } from "lucide-react";

import Logo from "../Atomic/Logo";
import { useNavScroll } from "../../Hooks/NavHook";
import { useAuth } from "../../context/AuthContext";
import { navItems } from "./navItems";
import UserMenu from "../Chat/UserMenu";

export default function Navbar() {
    const scrolled = useNavScroll(20);
    const [menuOpen, setMenuOpen] = useState(false);
    const location = useLocation();
    const { user } = useAuth();

    useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);

    useEffect(() => {
        if (!menuOpen) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") setMenuOpen(false);
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, [menuOpen]);

    return (
        <>
            <nav
                aria-label="Main navigation"
                className={`fixed inset-x-4 top-4 z-50 mx-auto max-w-6xl rounded-2xl border border-neutral-200/90 bg-white/90 px-4 py-3 backdrop-blur-xl transition-shadow sm:inset-x-6 sm:px-6 lg:top-5 lg:rounded-full lg:px-8 ${
                    scrolled
                        ? "shadow-[0_16px_50px_rgba(0,0,0,0.12)]"
                        : "shadow-sm"
                }`}
            >
                <div className="flex items-center justify-between gap-6">
                    <Link to="/" aria-label="Slashus home" className="shrink-0">
                        <Logo />
                    </Link>

                    <ul className="hidden items-center gap-[clamp(1.25rem,3vw,3rem)] md:flex">
                        {navItems.map((item) => (
                            <li key={item.label}>
                                <Link
                                    to={item.to}
                                    className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-950"
                                >
                                    {item.label}
                                </Link>
                            </li>
                        ))}
                    </ul>

                    {user ? (
                        <div className="hidden md:block">
                            <UserMenu theme="light" />
                        </div>
                    ) : (
                        <Link
                            to="/login"
                            className="hidden items-center gap-2 rounded-xl border border-neutral-200 px-4 py-2 text-sm font-medium transition-colors hover:bg-neutral-100 md:flex"
                        >
                            <LogIn size={18} />
                            Login
                        </Link>
                    )}

                    <button
                        type="button"
                        aria-label={
                            menuOpen ? "Close navigation" : "Open navigation"
                        }
                        aria-expanded={menuOpen}
                        aria-controls="mobile-navigation"
                        onClick={() => setMenuOpen((open) => !open)}
                        className="grid h-11 w-11 place-items-center rounded-xl text-neutral-800 transition-colors hover:bg-neutral-100 md:hidden"
                    >
                        {menuOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                </div>
            </nav>

            {menuOpen && (
                <div
                    id="mobile-navigation"
                    className="fixed inset-x-4 top-[5.75rem] z-40 rounded-3xl border border-neutral-200 bg-white p-3 shadow-[0_24px_70px_rgba(0,0,0,0.16)] md:hidden"
                >
                    <div className="flex flex-col">
                        {navItems.map((item) => (
                            <Link
                                key={item.label}
                                to={item.to}
                                className="rounded-2xl px-4 py-3.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 hover:text-neutral-950"
                            >
                                {item.label}
                            </Link>
                        ))}
                        {user ? (
                            <div className="mt-2 rounded-2xl border border-neutral-200 p-2">
                                <UserMenu theme="light" align="left" />
                            </div>
                        ) : (
                            <Link
                                to="/login"
                                className="mt-2 flex items-center justify-center gap-2 rounded-2xl bg-neutral-950 px-4 py-3.5 text-sm font-semibold text-white"
                            >
                                <>
                                    <LogIn size={18} />
                                    Login
                                </>
                            </Link>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
