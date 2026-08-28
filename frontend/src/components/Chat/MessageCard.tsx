import { useState } from "react";
import { Check, Copy, FileText, Sparkles } from "lucide-react";

import type { Reason } from "../../features/chat/types";
import { useAuth } from "../../context/AuthContext";

type Citation = {
    page: number | null;
    title: string | null;
};

type Props = {
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    reason?: Reason | null;
};

export default function MessageCard({
    role,
    content,
    citations,
    reason,
}: Props) {
    const { user } = useAuth();
    const [copied, setCopied] = useState(false);
    const isUser = role === "user";
    const blocked = !isUser && Boolean(reason);
    const initial = (user?.firstName?.[0] ?? "Y").toUpperCase();

    async function copyMessage() {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
    }

    const rowClass =
        "group mb-8 flex gap-3 sm:gap-4 " + (isUser ? "flex-row-reverse" : "");
    const avatarClass =
        "mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl text-xs font-bold sm:h-9 sm:w-9 " +
        (isUser
            ? "bg-blue-600 text-white"
            : "border border-blue-500/20 bg-blue-500/10 text-blue-400");
    const bodyClass =
        "min-w-0 " +
        (isUser ? "max-w-[86%] sm:max-w-[72%]" : "max-w-[92%] sm:max-w-[82%]");
    const bubbleClass =
        "relative rounded-2xl px-4 py-3.5 text-[15px] leading-7 shadow-sm sm:px-5 sm:py-4 " +
        (isUser
            ? "rounded-tr-md bg-blue-600 text-white shadow-blue-950/20"
            : blocked
              ? "rounded-tl-md border border-amber-500/20 bg-amber-500/5 text-[var(--tx2)]"
              : "rounded-tl-md border border-[var(--bd)] bg-[var(--sf2)] text-[var(--tx2)] shadow-black/20");

    return (
        <article className={rowClass}>
            <div className={avatarClass} aria-hidden="true">
                {isUser ? initial : <Sparkles size={15} />}
            </div>

            <div className={bodyClass}>
                <div
                    className={
                        "mb-2 flex items-center gap-2 " +
                        (isUser ? "justify-end" : "")
                    }
                >
                    <span
                        className={
                            "text-[10px] font-bold uppercase tracking-[0.18em] " +
                            (isUser ? "text-blue-400" : "text-[var(--tx3)]")
                        }
                    >
                        {isUser ? user?.firstName || "You" : "Slashus"}
                    </span>
                </div>

                <div className={bubbleClass}>
                    <p className="whitespace-pre-wrap break-words">{content}</p>
                </div>

                {!isUser && citations && citations.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                        {citations.map((citation, index) => (
                            <button
                                type="button"
                                key={[
                                    citation.page,
                                    citation.title,
                                    index,
                                ].join("-")}
                                title={citation.title ?? "Source"}
                                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--bd)] bg-[var(--sf)] px-2.5 py-1 text-[11px] text-[var(--tx2)] transition-colors hover:border-blue-500/30 hover:text-blue-300"
                            >
                                <FileText size={11} />
                                <span className="max-w-32 truncate">
                                    {citation.title || "Source"}
                                </span>
                                <span className="text-[var(--tx3)]">·</span>
                                p. {citation.page ?? "?"}
                            </button>
                        ))}
                    </div>
                )}

                {!isUser && (
                    <button
                        type="button"
                        onClick={copyMessage}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-[var(--tx3)] opacity-100 transition-colors hover:bg-[var(--sf2)] hover:text-[var(--tx)] sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
                        aria-label="Copy response"
                    >
                        {copied ? <Check size={12} /> : <Copy size={12} />}
                        {copied ? "Copied" : "Copy"}
                    </button>
                )}
            </div>
        </article>
    );
}
