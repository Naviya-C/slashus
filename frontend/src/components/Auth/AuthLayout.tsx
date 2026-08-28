import { useRef, type ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import AuthShowcase from "./AuthShowcase";
import Logo3D from "../Brand/Logo3D";
import ThemeToggle from "../Atomic/ThemeToggle";
import { useScrollDrive } from "../../Hooks/useScrollDrive";

type Props = {
    children: ReactNode;
};

/**
 * Shared shell for /login and /register.
 *
 * Left  : full-cover 3D logo showcase (lg and up).
 * Right : the form. This is the scroll container.
 *
 * The scroll signal is a position, so the showcase animates forward on the
 * way down and backward on the way up — every scroll, both directions.
 */
export default function AuthLayout({ children }: Props) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const drive = useScrollDrive(scrollRef);

    return (
        <div className="flex h-dvh overflow-hidden bg-white transition-colors duration-300 dark:bg-neutral-950">
            <aside className="hidden h-dvh lg:block lg:w-1/2">
                <AuthShowcase drive={drive} />
            </aside>

            <div
                ref={scrollRef}
                className="relative h-dvh w-full overflow-y-auto overscroll-contain lg:w-1/2"
            >
                <header className="sticky top-0 z-20 flex items-center justify-between gap-3 bg-white/85 px-5 py-4 backdrop-blur-xl sm:px-8 dark:bg-neutral-950/85">
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white"
                    >
                        <ArrowLeft size={17} />
                        Back home
                    </Link>
                    <ThemeToggle />
                </header>

                {/* Compact 3D mark on small screens, where the side panel is hidden. */}
                <div className="relative mx-auto h-40 w-32 lg:hidden">
                    <Logo3D
                        progress={drive.progress}
                        velocity={drive.velocity}
                        size={132}
                        depth={9}
                        ambient={false}
                        interactive={false}
                    />
                </div>

                <div className="flex min-h-[calc(100dvh-9.5rem)] items-center justify-center px-5 pb-12 sm:px-8 lg:min-h-[calc(100dvh-4.5rem)] lg:pb-16">
                    {children}
                </div>
            </div>
        </div>
    );
}
