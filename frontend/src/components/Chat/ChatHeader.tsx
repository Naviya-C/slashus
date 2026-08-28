import { Menu, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import Logo from "../Atomic/Logo";
import ThemeToggle from "../Atomic/ThemeToggle";
import UserMenu from "./UserMenu";

type Props = {
    onOpenTools: () => void;
    onNewChat: () => void;
};

export default function ChatHeader({ onOpenTools, onNewChat }: Props) {
    return (
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-[var(--bd)] px-3 sm:px-5">
            <Link
                to="/"
                aria-label="Slashus home"
                className="min-w-0 scale-90 sm:scale-100"
            >
                <Logo />
            </Link>

            <div className="flex items-center gap-1 sm:gap-2">
                <button
                    type="button"
                    onClick={onNewChat}
                    className="flex h-10 items-center gap-2 rounded-xl px-3 text-sm text-[var(--tx2)] transition-colors hover:bg-[var(--sf2)] hover:text-[var(--tx)]"
                    aria-label="Start a new chat"
                >
                    <Plus size={18} />
                    <span className="hidden sm:inline">New chat</span>
                </button>
                <ThemeToggle />

                <div className="hidden 2xl:block">
                    <UserMenu />
                </div>
                <button
                    type="button"
                    onClick={onOpenTools}
                    className="grid h-11 w-11 place-items-center rounded-xl text-[var(--tx2)] transition-colors hover:bg-[var(--sf2)] 2xl:hidden"
                    aria-label="Open workspace menu"
                >
                    <Menu size={22} />
                </button>
            </div>
        </header>
    );
}
