import { useEffect, useRef } from "react";
import { BookOpenText, MessageSquareText, Sparkles } from "lucide-react";

import type { Message } from "../../features/chat/types";
import ChatInput from "./ChatInput";
import ChatGreeting from "./ChatGreeting";
import MessageCard from "./MessageCard";

type Props = {
    messages: Message[];
    sending: boolean;
    loadingSession: boolean;
    error: string | null;
    hasSelection: boolean;
    selectedCount: number;
    onSend: (text: string) => void;
};

const suggestions = [
    "Summarize the key ideas",
    "Explain this more simply",
    "Create five practice questions",
];

export default function ChatWorkspace({
    messages,
    sending,
    loadingSession,
    error,
    hasSelection,
    selectedCount,
    onSend,
}: Props) {
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (loadingSession) {
            return;
        }

        endRef.current?.scrollIntoView({
            behavior: sending ? "smooth" : "auto",
            block: "end",
        });
    }, [messages, sending, loadingSession]);

    return (
        <main className="relative flex min-w-0 flex-1 flex-col bg-[var(--bg)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-blue-950/10 to-transparent" />

            <div className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain">
                <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 py-7 sm:px-7 sm:py-10 lg:px-10">
                    {loadingSession ? (
                        <div
                            className="m-auto flex flex-col items-center py-16 text-center"
                            role="status"
                        >
                            <span className="h-7 w-7 animate-spin rounded-full border-2 border-[var(--bd)] border-t-blue-500" />
                            <p className="mt-4 text-sm text-[var(--tx3)]">
                                Opening conversation…
                            </p>
                        </div>
                    ) : messages.length === 0 ? (
                        <div className="m-auto w-full max-w-2xl py-10 text-center">
                            <ChatGreeting />
                            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-[var(--tx3)]">
                                Ask for an explanation, comparison, summary, or
                                practice set. Slashus keeps responses connected
                                to the resources in this conversation.
                            </p>

                            <div className="mt-7 flex flex-wrap justify-center gap-2">
                                {suggestions.map((suggestion) => (
                                    <button
                                        type="button"
                                        key={suggestion}
                                        onClick={() => onSend(suggestion)}
                                        className="rounded-full border border-[var(--bd)] bg-[var(--sf)] px-3.5 py-2 text-xs text-[var(--tx2)] transition-colors hover:border-blue-500/30 hover:bg-blue-500/5 hover:text-blue-300"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>

                            <p className="mt-6 inline-flex items-center gap-2 rounded-full border border-[var(--bd)] px-3 py-1.5 text-xs text-[var(--tx3)]">
                                {hasSelection ? (
                                    <BookOpenText size={14} />
                                ) : (
                                    <MessageSquareText size={14} />
                                )}
                                {hasSelection
                                    ? String(selectedCount) +
                                      " selected resource" +
                                      (selectedCount === 1 ? "" : "s")
                                    : "Using all your available resources"}
                            </p>
                        </div>
                    ) : (
                        <div aria-live="polite" aria-label="Conversation">
                            {messages.map((message) => (
                                <MessageCard
                                    key={message.id}
                                    role={message.role}
                                    content={message.content}
                                    citations={message.citations}
                                    reason={message.reason}
                                />
                            ))}
                            {sending && <ThinkingMessage />}
                        </div>
                    )}
                    <div ref={endRef} />
                </div>
            </div>

            <div className="relative shrink-0 border-t border-[var(--bd)] bg-[var(--bg)] px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl sm:px-6 sm:pb-5 sm:pt-4">
                <div className="mx-auto w-full max-w-3xl">
                    {error && (
                        <p
                            className="mb-2 rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-300"
                            role="alert"
                        >
                            {error}
                        </p>
                    )}
                    <ChatInput
                        onSend={onSend}
                        disabled={sending || loadingSession}
                        selectedCount={selectedCount}
                        placeholder={
                            hasSelection
                                ? "Ask about your selected resources…"
                                : "Ask across your resources…"
                        }
                    />
                    <p className="mt-2 hidden text-center text-[11px] text-[var(--tx3)] sm:block">
                        Enter to send · Shift + Enter for a new line · Verify
                        important details in the source
                    </p>
                </div>
            </div>
        </main>
    );
}

function ThinkingMessage() {
    return (
        <div
            className="mb-8 flex gap-3 sm:gap-4"
            role="status"
            aria-label="Slashus is thinking"
        >
            <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-400 sm:h-9 sm:w-9">
                <Sparkles size={15} />
            </div>
            <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--tx3)]">
                    Slashus
                </p>
                <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-[var(--bd)] bg-[var(--sf2)] px-5 py-4">
                    {[0, 1, 2].map((index) => (
                        <span
                            key={index}
                            className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500"
                            style={{
                                animationDelay: String(index * 160) + "ms",
                            }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
