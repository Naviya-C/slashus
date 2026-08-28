import { Check, Circle } from "lucide-react";

type Props = {
    password: string;
};

export function passwordRequirements(password: string) {
    return {
        length: password.length > 8,
        number: /\d/.test(password),
        symbol: /[^A-Za-z0-9\s]/.test(password),
    };
}

export function isPasswordValid(password: string) {
    return Object.values(passwordRequirements(password)).every(Boolean);
}

export default function PasswordRequirements({ password }: Props) {
    const requirements = passwordRequirements(password);
    const items = [
        { label: "More than 8 characters", valid: requirements.length },
        { label: "At least one number", valid: requirements.number },
        { label: "At least one symbol", valid: requirements.symbol },
    ];

    return (
        <div
            className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3 sm:grid-cols-2 dark:border-neutral-800 dark:bg-neutral-900/60"
            aria-label="Password requirements"
        >
            {items.map((item) => (
                <div
                    key={item.label}
                    className={`flex items-center gap-2 text-xs font-medium transition-colors ${
                        item.valid
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-slate-400 dark:text-neutral-500"
                    }`}
                >
                    <span
                        className={`grid h-4 w-4 shrink-0 place-items-center rounded-full transition-colors ${
                            item.valid
                                ? "bg-emerald-500 text-white"
                                : "text-slate-300 dark:text-neutral-600"
                        }`}
                    >
                        {item.valid ? (
                            <Check size={11} />
                        ) : (
                            <Circle size={14} />
                        )}
                    </span>
                    {item.label}
                </div>
            ))}
        </div>
    );
}
