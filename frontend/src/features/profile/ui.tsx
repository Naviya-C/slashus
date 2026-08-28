import type { ReactNode } from "react";
import { AlertCircle, LoaderCircle } from "lucide-react";

export const inputClass =
    "h-11 w-full rounded-xl border border-[var(--bd)] bg-[var(--bg)] px-3 text-sm text-[var(--tx)] placeholder:text-[var(--tx3)] focus:border-blue-500 focus:outline-none";
export const textareaClass =
    "min-h-24 w-full resize-y rounded-xl border border-[var(--bd)] bg-[var(--bg)] px-3 py-2.5 text-sm text-[var(--tx)] placeholder:text-[var(--tx3)] focus:border-blue-500 focus:outline-none";
export const primaryButton =
    "inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50";
export const secondaryButton =
    "inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-[var(--bd)] bg-[var(--bg)] px-4 text-sm font-medium text-[var(--tx)] transition hover:bg-[var(--sf2)] disabled:opacity-50";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
    return <section className={`rounded-2xl border border-[var(--bd)] bg-[var(--sf)] ${className}`}>{children}</section>;
}

export function PageTitle({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
    return (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight text-[var(--tx)] sm:text-3xl">{title}</h1>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--tx2)]">{description}</p>
            </div>
            {action}
        </div>
    );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
    return <div className="flex items-center gap-2 py-12 text-sm text-[var(--tx2)]"><LoaderCircle className="animate-spin" size={18} />{label}</div>;
}

export function ErrorState({ message }: { message: string }) {
    return <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500"><AlertCircle className="mt-0.5 shrink-0" size={17} />{message}</div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
    return <div className="rounded-2xl border border-dashed border-[var(--bd2)] px-6 py-12 text-center"><h2 className="font-medium text-[var(--tx)]">{title}</h2><p className="mx-auto mt-1 max-w-md text-sm text-[var(--tx2)]">{description}</p></div>;
}

export function StatusBadge({ status }: { status: string }) {
    const active = status === "published" || status === "ready" || status === "accepted" || status === "approved";
    return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${active ? "bg-emerald-500/12 text-emerald-500" : "bg-amber-500/12 text-amber-500"}`}>{status.replaceAll("_", " ")}</span>;
}
