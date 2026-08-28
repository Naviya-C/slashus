import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "slashus:theme";

function readStored(): ThemeChoice {
    if (typeof window === "undefined") return "system";
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" || value === "system"
        ? value
        : "system";
}

function systemTheme(): ResolvedTheme {
    if (typeof window === "undefined" || !window.matchMedia) return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
}

function resolve(choice: ThemeChoice): ResolvedTheme {
    return choice === "system" ? systemTheme() : choice;
}

/** Applies exactly one of `light` / `dark` to <html>. */
export function applyTheme(theme: ResolvedTheme) {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    root.style.colorScheme = theme;
}

// Runs as soon as this module is imported, i.e. before React paints.
applyTheme(resolve(readStored()));

type ThemeContextValue = {
    theme: ThemeChoice;
    resolvedTheme: ResolvedTheme;
    setTheme: (theme: ThemeChoice) => void;
    toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState<ThemeChoice>(readStored);
    const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
        resolve(readStored()),
    );

    useEffect(() => {
        const next = resolve(theme);
        setResolvedTheme(next);
        applyTheme(next);
        window.localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);

    // Follow the OS while the user is on "system".
    useEffect(() => {
        if (theme !== "system" || !window.matchMedia) return;
        const query = window.matchMedia("(prefers-color-scheme: dark)");
        const onChange = () => {
            const next = systemTheme();
            setResolvedTheme(next);
            applyTheme(next);
        };
        query.addEventListener("change", onChange);
        return () => query.removeEventListener("change", onChange);
    }, [theme]);

    // Keep tabs in sync.
    useEffect(() => {
        const onStorage = (event: StorageEvent) => {
            if (event.key === STORAGE_KEY) setThemeState(readStored());
        };
        window.addEventListener("storage", onStorage);
        return () => window.removeEventListener("storage", onStorage);
    }, []);

    const setTheme = useCallback((next: ThemeChoice) => {
        setThemeState(next);
    }, []);

    const toggleTheme = useCallback(() => {
        setThemeState(resolve(readStored()) === "dark" ? "light" : "dark");
    }, []);

    const value = useMemo(
        () => ({ theme, resolvedTheme, setTheme, toggleTheme }),
        [theme, resolvedTheme, setTheme, toggleTheme],
    );

    return (
        <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used inside <ThemeProvider>");
    }
    return context;
}
