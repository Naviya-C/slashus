import { useCallback, useEffect, useRef, useState } from "react";
import { MoreVertical, Trash2 } from "lucide-react";

import { apiJson } from "../../lib/api";

type Session = {
    id: string;
    title: string;
    doc_ids: string[];
    last_message_at: string;
};

type Props = {
    activeId: string | null;
    onOpen: (id: string) => void;
    onDelete?: (session: Session) => void;
    refreshKey?: number;
};

function relativeTime(iso: string): string {
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
    const days = Math.floor(mins / 1440);
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    return new Date(iso).toLocaleDateString();
}

function SessionList({ activeId, onOpen, onDelete, refreshKey = 0 }: Props) {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [cursor, setCursor] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [menuFor, setMenuFor] = useState<string | null>(null);
    const listRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!menuFor) return;
        const close = (event: MouseEvent) => {
            if (
                listRef.current &&
                !listRef.current.contains(event.target as Node)
            ) {
                setMenuFor(null);
            }
        };
        const closeWithKeyboard = (event: KeyboardEvent) => {
            if (event.key === "Escape") setMenuFor(null);
        };
        document.addEventListener("mousedown", close);
        document.addEventListener("keydown", closeWithKeyboard);
        return () => {
            document.removeEventListener("mousedown", close);
            document.removeEventListener("keydown", closeWithKeyboard);
        };
    }, [menuFor]);

    const load = useCallback(
        async (from?: string | null, isActive: () => boolean = () => true) => {
            try {
                const qs = from
                    ? `?limit=20&cursor=${encodeURIComponent(from)}`
                    : "?limit=20";
                const res = await apiJson<{
                    sessions: Session[];
                    next_cursor: string | null;
                }>(`/api/v1/sessions${qs}`);
                if (!isActive()) return;
                setSessions((prev) =>
                    from ? [...prev, ...res.sessions] : res.sessions,
                );
                setCursor(res.next_cursor);
                setError(null);
            } catch (err) {
                if (!isActive()) return;
                setError(
                    err instanceof Error
                        ? err.message
                        : "Could not load sessions",
                );
            } finally {
                if (isActive()) setLoading(false);
            }
        },
        [],
    );

    useEffect(() => {
        let active = true;
        void load(null, () => active);

        return () => {
            active = false;
        };
    }, [load, refreshKey]);

    if (loading) {
        return <p className="px-3 text-xs text-neutral-500">Loading…</p>;
    }

    if (error) {
        return <p className="px-3 text-xs text-red-400">{error}</p>;
    }

    if (sessions.length === 0) {
        return (
            <p className="px-3 text-xs text-neutral-500">
                No conversations yet.
            </p>
        );
    }

    return (
        <div ref={listRef} className="space-y-1 px-2">
            {sessions.map((s, i) => {
                const active = s.id === activeId;
                return (
                    <div
                        key={s.id}
                        className={`
              relative flex w-full items-center rounded-lg transition-colors
              ${active ? "bg-neutral-800" : "hover:bg-neutral-900"}
            `}
                    >
                        <button
                            type="button"
                            onClick={() => onOpen(s.id)}
                            className="min-w-0 flex-1 px-3 py-2.5 text-left"
                        >
                            <div className="flex items-baseline gap-2">
                                <span className="shrink-0 text-[10px] tabular-nums text-neutral-600">
                                    {String(i + 1).padStart(2, "0")}
                                </span>

                                <span className="min-w-0 flex-1">
                                    <span
                                        className={`block truncate text-sm ${
                                            active
                                                ? "text-neutral-100"
                                                : "text-neutral-300"
                                        }`}
                                    >
                                        {s.title || "Untitled"}
                                    </span>
                                    <span className="block text-xs text-neutral-500">
                                        {active
                                            ? "Active now"
                                            : relativeTime(s.last_message_at)}
                                    </span>
                                </span>
                            </div>
                        </button>

                        <button
                            type="button"
                            aria-label={`Actions for ${s.title || "Untitled session"}`}
                            aria-expanded={menuFor === s.id}
                            aria-haspopup="menu"
                            onClick={() =>
                                setMenuFor((current) =>
                                    current === s.id ? null : s.id,
                                )
                            }
                            className="mr-2 grid h-8 w-8 shrink-0 place-items-center rounded-lg text-neutral-500 hover:bg-neutral-700 hover:text-neutral-200"
                        >
                            <MoreVertical size={16} />
                        </button>

                        {menuFor === s.id && (
                            <div
                                role="menu"
                                className="absolute right-2 top-full z-50 mt-1 w-36 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900 shadow-xl shadow-black/40"
                            >
                                <button
                                    role="menuitem"
                                    type="button"
                                    onClick={() => {
                                        setMenuFor(null);
                                        onDelete?.(s);
                                    }}
                                    className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-red-400 transition-colors hover:bg-red-500/10"
                                >
                                    <Trash2 size={14} />
                                    Delete
                                </button>
                            </div>
                        )}
                    </div>
                );
            })}

            {cursor && (
                <button
                    onClick={() => load(cursor)}
                    className="w-full px-3 py-2 text-xs text-neutral-500 hover:text-neutral-300"
                >
                    Load older
                </button>
            )}
        </div>
    );
}

export default SessionList;
