import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, LogOut, MessageSquareText, Settings, User } from "lucide-react";

import { useAuth } from "../../context/AuthContext";

type Props = {
    theme?: "dark" | "light";
    align?: "left" | "right";
};

export default function UserMenu({ theme = "dark", align = "right" }: Props) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        function closeOutside(event: MouseEvent) {
            if (ref.current && !ref.current.contains(event.target as Node))
                setOpen(false);
        }
        function closeWithKeyboard(event: KeyboardEvent) {
            if (event.key === "Escape") setOpen(false);
        }
        document.addEventListener("mousedown", closeOutside);
        document.addEventListener("keydown", closeWithKeyboard);
        return () => {
            document.removeEventListener("mousedown", closeOutside);
            document.removeEventListener("keydown", closeWithKeyboard);
        };
    }, [open]);

    if (!user) return null;
    const initial = (user.firstName?.[0] ?? "?").toUpperCase();
    const isLight = theme === "light";

    async function handleLogout() {
        setOpen(false);
        await logout();
        navigate("/login", { replace: true });
    }

    const items = [
        {
            label: "Open workspace",
            icon: MessageSquareText,
            onClick: () => navigate("/chat"),
        },
        { label: "Profile", icon: User, onClick: () => navigate("/profile") },
        {
            label: "Settings",
            icon: Settings,
            onClick: () => navigate("/settings"),
        },
        { label: "Privacy", icon: Lock, onClick: () => navigate("/privacy") },
    ];

    return (
        <div className="relative" ref={ref}>
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-expanded={open}
                aria-haspopup="menu"
                className={
                    "flex items-center gap-2 rounded-full py-1 pl-3 pr-1 transition-colors " +
                    (isLight
                        ? "text-neutral-700 hover:bg-neutral-100"
                        : "text-neutral-300 hover:bg-neutral-800")
                }
            >
                <span className="hidden text-sm font-medium sm:inline">
                    Hi, {user.firstName}
                </span>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-red-500 text-sm font-semibold text-white">
                    {initial}
                </span>
            </button>

            {open && (
                <div
                    role="menu"
                    className={
                        "absolute z-[80] mt-2 w-60 overflow-hidden rounded-2xl border shadow-2xl " +
                        (align === "right" ? "right-0 " : "left-0 ") +
                        (isLight
                            ? "border-neutral-200 bg-white shadow-neutral-300/50"
                            : "border-neutral-800 bg-neutral-900 shadow-black/40")
                    }
                >
                    <div
                        className={
                            "border-b px-4 py-3 " +
                            (isLight
                                ? "border-neutral-200"
                                : "border-neutral-800")
                        }
                    >
                        <p
                            className={`truncate text-sm font-medium ${isLight ? "text-neutral-950" : "text-neutral-100"}`}
                        >
                            {user.firstName} {user.lastName}
                        </p>
                        <p
                            className={`truncate text-xs ${isLight ? "text-neutral-500" : "text-neutral-500"}`}
                        >
                            {user.email}
                        </p>
                    </div>

                    <div className="py-1.5">
                        {items.map(({ label, icon: Icon, onClick }) => (
                            <button
                                key={label}
                                role="menuitem"
                                type="button"
                                onClick={() => {
                                    setOpen(false);
                                    onClick();
                                }}
                                className={
                                    "flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors " +
                                    (isLight
                                        ? "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-950"
                                        : "text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100")
                                }
                            >
                                <Icon size={16} />
                                {label}
                            </button>
                        ))}
                    </div>

                    <div
                        className={
                            "border-t py-1.5 " +
                            (isLight
                                ? "border-neutral-200"
                                : "border-neutral-800")
                        }
                    >
                        <button
                            role="menuitem"
                            type="button"
                            onClick={handleLogout}
                            className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-red-500 transition-colors hover:bg-red-500/10"
                        >
                            <LogOut size={16} />
                            Log out
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
