import { Link } from "react-router-dom";
import { FaGithub, FaLinkedinIn, FaXTwitter } from "react-icons/fa6";
import Logo from "../Atomic/Logo";

const columns = [
    {
        title: "Explore",
        links: [
            { label: "Benefits", to: "/#benefits" },
            { label: "Workspace", to: "/#workspace" },
            { label: "Use cases", to: "/#use-cases" },
        ],
    },
    {
        title: "Account",
        links: [
            { label: "Sign in", to: "/login" },
            { label: "Create account", to: "/register" },
            { label: "Open workspace", to: "/chat" },
        ],
    },
    {
        title: "Product",
        links: [
            { label: "Quality", to: "/#quality" },
            { label: "Privacy", to: "/privacy" },
            { label: "Support", to: "/support" },
        ],
    },
];

export default function Footer() {
    return (
        <footer className="bg-neutral-950 px-5 pb-8 pt-16 text-white sm:px-6">
            <div className="mx-auto max-w-7xl">
                <div className="grid gap-12 border-b border-white/10 pb-14 md:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr]">
                    <div>
                        <Logo theme="dark" />
                        <p className="mt-5 max-w-sm text-sm leading-6 text-neutral-400">
                            Turn the learning materials you already trust into
                            clear answers, active practice, and useful feedback.
                        </p>
                    </div>

                    {columns.map((column) => (
                        <div key={column.title}>
                            <h3 className="text-xs font-bold uppercase tracking-[0.18em] text-neutral-500">
                                {column.title}
                            </h3>
                            <ul className="mt-5 space-y-3">
                                {column.links.map((link) => (
                                    <li key={link.label}>
                                        <Link
                                            to={link.to}
                                            className="text-sm text-neutral-300 transition-colors hover:text-white"
                                        >
                                            {link.label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                <div className="flex flex-col gap-5 pt-7 text-xs text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
                    <span>© 2026 Slashus. Built for better learning.</span>
                    <div className="flex items-center gap-2">
                        {[
                            { label: "Twitter", icon: FaXTwitter },
                            { label: "LinkedIn", icon: FaLinkedinIn },
                            { label: "GitHub", icon: FaGithub },
                        ].map(({ label, icon: Icon }) => (
                            <a
                                key={label}
                                href="#"
                                aria-label={label}
                                className="grid h-9 w-9 place-items-center rounded-full border border-white/10 text-neutral-400 transition-colors hover:border-white/20 hover:text-white"
                            >
                                <Icon size={15} />
                            </a>
                        ))}
                    </div>
                </div>
            </div>
        </footer>
    );
}
