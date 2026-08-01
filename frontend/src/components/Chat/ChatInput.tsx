import { useRef, useState } from "react";
import { ArrowRight } from "lucide-react";

type Props = {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

const MAX_HEIGHT = 160;

function ChatInput({
    onSend,
    disabled = false,
    placeholder = "Ask about your indexed materials...",
    }: Props) {
    const [text, setText] = useState("");
    const ref = useRef<HTMLTextAreaElement>(null);

    function resize() {
        const el = ref.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
    }

    function send() {
        const value = text.trim();
        if (!value || disabled) return;

        onSend(value);
        setText("");
        if (ref.current) ref.current.style.height = "auto";
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        send();
        }
    }

    return (
        <div
            className="
                flex items-end gap-2
                rounded-3xl border border-neutral-800 bg-neutral-900/50
                p-2
                transition-colors
                focus-within:border-neutral-600
            "
        >
                <textarea
                    ref={ref}
                    rows={1}
                    value={text}
                    placeholder={placeholder}
                    disabled={disabled}
                    onChange={(e) => {
                        setText(e.target.value);
                        resize();
                    }}
                    onKeyDown={handleKeyDown}
                    className="
                        flex-1 resize-none bg-transparent px-3 py-2.5
                        text-sm text-neutral-100 placeholder:text-neutral-500
                        outline-none disabled:opacity-50
                    "
                />

                <button
                    type="button"
                    onClick={send}
                    disabled={disabled || !text.trim()}
                    className="
                        shrink-0 flex items-center gap-2 rounded-3xl
                        bg-white px-5 py-2.5 text-sm font-semibold text-black
                        transition-colors hover:bg-stone-300
                        hover:cursor-pointer
                        disabled:cursor-not-allowed disabled:opacity-40
                    "
                >
                    <ArrowRight size={20} />
                </button>
        </div>
    );
}

export default ChatInput;