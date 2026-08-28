type PreferenceToggleProps = {
    checked: boolean;
    onChange: (checked: boolean) => void;
    label: string;
    hint: string;
};

export default function PreferenceToggle({
    checked,
    onChange,
    label,
    hint,
}: PreferenceToggleProps) {
    return (
        <label className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-[var(--bd)] p-4 transition hover:bg-[var(--sf3)]">
            <span className="min-w-0">
                <span className="block text-sm font-medium text-[var(--tx)]">
                    {label}
                </span>
                <span className="mt-0.5 block text-xs text-[var(--tx3)]">
                    {hint}
                </span>
            </span>
            <span
                className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors ${
                    checked ? "bg-blue-600" : "bg-[var(--sf3)]"
                }`}
            >
                <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={(event) => onChange(event.target.checked)}
                />
                <span
                    className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                        checked ? "translate-x-6" : "translate-x-1"
                    }`}
                />
            </span>
        </label>
    );
}
