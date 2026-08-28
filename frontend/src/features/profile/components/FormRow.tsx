import type { ComponentType, ReactNode } from "react";

type IconProps = {
    size?: number | string;
};

type FormRowProps = {
    label: string;
    children: ReactNode;
    hint?: string;
    icon?: ComponentType<IconProps>;
};

export default function FormRow({
    label,
    children,
    hint,
    icon: Icon,
}: FormRowProps) {
    return (
        <label className="block">
            <span className="flex items-center gap-1.5 text-sm font-medium text-[var(--tx2)]">
                {Icon && <Icon size={14} />}
                {label}
            </span>
            <div className="mt-1.5">{children}</div>
            {hint && (
                <span className="mt-1.5 block text-xs text-[var(--tx3)]">
                    {hint}
                </span>
            )}
        </label>
    );
}
