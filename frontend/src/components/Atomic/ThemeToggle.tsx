import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme, type ThemeChoice } from "../../context/ThemeContext";

type Props = {
    /** "icon" = single toggle button, "group" = light / dark / system segmented. */
    variant?: "icon" | "group";
    className?: string;
};

const options: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
];

/**
 * Styled with the shared --bd / --tx tokens rather than `dark:` utilities,
 * so the same component works on the light-first landing pages and inside
 * the dark-first chat workspace.
 */
export default function ThemeToggle({ variant = "icon", className }: Props) {
    const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

    if (variant === "group") {
        return (
            <div
                role="radiogroup"
                aria-label="Colour theme"
                className={`inline-flex items-center gap-0.5 rounded-full border border-[var(--bd)] bg-[var(--sf2)] p-1 ${className ?? ""}`}
            >
                {options.map(({ value, label, icon: Icon }) => {
                    const active = theme === value;
                    return (
                        <button
                            key={value}
                            type="button"
                            role="radio"
                            aria-checked={active}
                            title={label}
                            onClick={() => setTheme(value)}
                            className={`grid h-8 w-8 place-items-center rounded-full transition-colors ${
                                active
                                    ? "bg-[var(--bg)] text-[var(--tx)] shadow-sm"
                                    : "text-[var(--tx3)] hover:text-[var(--tx)]"
                            }`}
                        >
                            <Icon size={15} />
                        </button>
                    );
                })}
            </div>
        );
    }

    return (
        <button
            type="button"
            onClick={toggleTheme}
            aria-label={
                resolvedTheme === "dark"
                    ? "Switch to light mode"
                    : "Switch to dark mode"
            }
            title={
                resolvedTheme === "dark"
                    ? "Switch to light mode"
                    : "Switch to dark mode"
            }
            className={`relative grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl border border-[var(--bd)] text-[var(--tx2)] transition-colors hover:bg-[var(--sf3)] hover:text-[var(--tx)] ${className ?? ""}`}
        >
            <Sun
                size={18}
                className="absolute transition-all duration-300 dark:-rotate-90 dark:scale-0 dark:opacity-0"
            />
            <Moon
                size={18}
                className="absolute rotate-90 scale-0 opacity-0 transition-all duration-300 dark:rotate-0 dark:scale-100 dark:opacity-100"
            />
        </button>
    );
}
