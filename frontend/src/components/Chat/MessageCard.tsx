import type { Reason } from "../../Hooks/useChat";

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

const BLOCKED_STYLE =
  "border border-neutral-800 bg-transparent text-neutral-400";

function MessageCard({ role, content, citations, reason }: Props) {
  const isUser = role === "user";
  const blocked = !isUser && Boolean(reason);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-5`}>
      <div className={isUser ? "max-w-[70%]" : "max-w-[80%]"}>
        <div
          className={`
            rounded-2xl px-4 py-3 text-sm leading-relaxed
            ${isUser
              ? "bg-red-500 text-white"
              : blocked
                ? BLOCKED_STYLE
                : "bg-neutral-900 text-neutral-100"}
          `}
        >
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>

        {!isUser && citations && citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 px-1">
            {citations.map((c, i) => (
              <span
                key={`${c.page}-${i}`}
                title={c.title ?? undefined}
                className="
                  rounded-md bg-neutral-800 px-2 py-0.5
                  text-[11px] text-neutral-400
                "
              >
                p. {c.page ?? "?"}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageCard;