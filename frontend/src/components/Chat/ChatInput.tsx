import { useRef, useState } from "react";
import { ArrowUp, Paperclip } from "lucide-react";

type Props = {
    onSend: (text: string) => void;
    disabled?: boolean;
    placeholder?: string;
    selectedCount?: number;
};

const MAX_HEIGHT = 176;

export default function ChatInput({
    onSend,
    disabled = false,
    placeholder = "Ask about your indexed materials…",
    selectedCount = 0,
}: Props) {
    const [text, setText] = useState("");
    const ref = useRef<HTMLTextAreaElement>(null);

    function resize() {
        const element = ref.current;
        if (!element) return;
        element.style.height = "auto";
        element.style.height =
            String(Math.min(element.scrollHeight, MAX_HEIGHT)) + "px";
    }

    function send() {
        const value = text.trim();
        if (!value || disabled) return;
        onSend(value);
        setText("");
        if (ref.current) ref.current.style.height = "auto";
    }

    function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.nativeEvent.isComposing
        ) {
            event.preventDefault();
            send();
        }
    }

    return (
        <div className="rounded-[1.35rem] border border-[var(--bd2)] bg-[var(--sf2)] p-2 shadow-2xl shadow-black/20 transition-colors focus-within:border-blue-500/50">
            <textarea
                ref={ref}
                rows={1}
                value={text}
                placeholder={placeholder}
                disabled={disabled}
                onChange={(event) => {
                    setText(event.target.value);
                    resize();
                }}
                onKeyDown={handleKeyDown}
                className="min-h-11 w-full resize-none bg-transparent px-3 py-2.5 text-[15px] leading-6 text-[var(--tx)] placeholder:text-[var(--tx3)] outline-none disabled:opacity-50"
                aria-label="Message"
            />

            <div className="flex items-center justify-between gap-3 pl-2">
                <div className="flex min-w-0 items-center gap-2">
                    <button
                        type="button"
                        aria-label="Attach resource"
                        className="grid h-8 w-8 place-items-center rounded-lg text-[var(--tx3)] transition-colors hover:bg-[var(--sf3)] hover:text-[var(--tx)]"
                    >
                        <Paperclip size={17} />
                    </button>
                    <span className="truncate text-[11px] text-[var(--tx3)]">
                        {selectedCount > 0
                            ? String(selectedCount) +
                              " resource" +
                              (selectedCount === 1 ? "" : "s") +
                              " selected"
                            : "All resources"}
                    </span>
                </div>
                <button
                    type="button"
                    onClick={send}
                    disabled={disabled || !text.trim()}
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-600 text-white transition-all hover:bg-blue-500 active:scale-95 disabled:cursor-not-allowed disabled:bg-[var(--sf3)] disabled:text-[var(--tx3)]"
                    aria-label="Send message"
                >
                    <ArrowUp size={18} strokeWidth={2.5} />
                </button>
            </div>
        </div>
    );
}
