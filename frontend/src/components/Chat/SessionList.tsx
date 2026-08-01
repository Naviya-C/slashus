import { useCallback, useEffect, useState } from "react";

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

function SessionList({ activeId, onOpen, refreshKey = 0 }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (from?: string | null, isActive: () => boolean = () => true) => {
      try {
        const qs = from ? `?limit=20&cursor=${encodeURIComponent(from)}` : "?limit=20";
        const res = await apiJson<{ sessions: Session[]; next_cursor: string | null }>(
          `/api/v1/sessions${qs}`,
        );
        if (!isActive()) return;
        setSessions((prev) => (from ? [...prev, ...res.sessions] : res.sessions));
        setCursor(res.next_cursor);
        setError(null);
      } catch (err) {
        if (!isActive()) return;
        setError(err instanceof Error ? err.message : "Could not load sessions");
      } finally {
        if (isActive()) setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
    <div className="space-y-1 px-2">
      {sessions.map((s, i) => {
        const active = s.id === activeId;
        return (
          <button
            key={s.id}
            onClick={() => onOpen(s.id)}
            className={`
              w-full rounded-lg px-3 py-2.5 text-left transition-colors
              ${active
                ? "bg-neutral-800"
                : "hover:bg-neutral-900"}
            `}
          >
            <div className="flex items-baseline gap-2">
              <span className="shrink-0 text-[10px] tabular-nums text-neutral-600">
                {String(i + 1).padStart(2, "0")}
              </span>

              <span className="min-w-0 flex-1">
                <span
                  className={`block truncate text-sm ${
                    active ? "text-neutral-100" : "text-neutral-300"
                  }`}
                >
                  {s.title || "Untitled"}
                </span>
                <span className="block text-xs text-neutral-500">
                  {active ? "Active now" : relativeTime(s.last_message_at)}
                </span>
              </span>
            </div>
          </button>
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