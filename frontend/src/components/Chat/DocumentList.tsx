import { useEffect, useRef, useState } from "react";
import { Download, MoreVertical, Pencil, Trash2 } from "lucide-react";

import type { Document } from "../../Hooks/useDocuments";

/** Retrieval quality drops as you widen the filter, and the Qdrant query gets
 *  slower — so the cap is a real constraint, not arbitrary UI polish. */
export const MAX_SELECTED = 3;

type Props = {
  documents: Document[];
  loading: boolean;
  error: string | null;
  selectedDocIds: string[];
  onToggleSelect: (docId: string) => void;
  onRename: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onDownload: (doc: Document) => void;
};

function relativeDate(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

function DocumentList({
  documents,
  loading,
  error,
  selectedDocIds,
  onToggleSelect,
  onRename,
  onDelete,
  onDownload,
}: Props) {
  // Which row's menu is open, by doc_id. A single value rather than per-row
  // state means opening one menu closes any other — two menus open at once is
  // never what the user wants.
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuFor) return;

    function onPointerDown(e: MouseEvent) {
      if (listRef.current && !listRef.current.contains(e.target as Node)) {
        setMenuFor(null);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuFor(null);
    }

    // mousedown, not click: click fires after mouseup, by which point the menu
    // may have unmounted and swallowed the interaction.
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuFor]);

  if (loading) {
    return <p className="px-1 text-xs text-neutral-500">Loading…</p>;
  }

  if (error) {
    return <p className="px-1 text-xs text-red-400">{error}</p>;
  }

  if (documents.length === 0) {
    return (
      <p className="px-1 text-xs text-neutral-500">
        No documents yet. Upload a PDF to get started.
      </p>
    );
  }

  const atCap = selectedDocIds.length >= MAX_SELECTED;

  return (
    <div ref={listRef} className="space-y-2">
      {/* Only shown once the cap is reached — a permanent hint would be noise,
          but silence at the moment a click stops working is worse. */}
      {atCap && (
        <p className="px-1 pb-1 text-xs text-neutral-500">
          {MAX_SELECTED} of {MAX_SELECTED} selected — deselect one to change.
        </p>
      )}

      {documents.map((doc) => {
        const selected = selectedDocIds.includes(doc.doc_id);
        // Locked = not selected and no slots left. Selected rows always stay
        // clickable, or the user could never get back under the cap.
        const locked = !selected && atCap;
        const menuOpen = menuFor === doc.doc_id;

        return (
          // A div, not a button. The row and the ⋮ are both interactive, and a
          // button inside a button is invalid HTML — browsers drop the inner
          // one, so the menu would silently stop working.
          <div
            key={doc.doc_id}
            className={`
              relative flex items-center gap-2 rounded-xl border
              transition-colors
              ${selected
                ? "border-red-500/60 bg-red-500/10"
                : locked
                  ? "border-neutral-800/60"
                  : "border-neutral-800 hover:border-neutral-700"}
            `}
          >
            <button
              type="button"
              onClick={() => onToggleSelect(doc.doc_id)}
              disabled={locked}
              title={locked ? `Limit is ${MAX_SELECTED} documents` : undefined}
              className="
                flex min-w-0 flex-1 items-center gap-3 px-3 py-3 text-left
                disabled:cursor-not-allowed disabled:opacity-40
              "
            >
              {/* Checkbox rendered rather than a real <input>: it's inside a
                  button, and a nested focusable control would need its own
                  click handling and stopPropagation to behave. */}
              <span
                className={`
                  flex h-4 w-4 shrink-0 items-center justify-center rounded
                  border text-[10px] font-bold
                  ${selected
                    ? "border-red-500 bg-red-500 text-white"
                    : "border-neutral-600"}
                `}
              >
                {selected ? "✓" : ""}
              </span>

              <span
                className="
                  shrink-0 rounded-md bg-neutral-800 px-2 py-1
                  text-[10px] font-semibold tracking-wider text-neutral-400
                "
              >
                PDF
              </span>

              {/* min-w-0 is what makes `truncate` work: without it the flex
                  child refuses to shrink below its content and a long filename
                  widens the whole row. */}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-neutral-100">
                  {doc.name}
                </span>
                <span className="block text-xs text-neutral-500">
                  {relativeDate(doc.created_at)}
                </span>
              </span>
            </button>

            <button
              type="button"
              aria-label={`Actions for ${doc.name}`}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuFor(menuOpen ? null : doc.doc_id)}
              className="
                mr-2 shrink-0 rounded-md p-1.5 text-neutral-500
                transition-colors hover:bg-neutral-800 hover:text-neutral-300
              "
            >
              <MoreVertical size={16} />
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="
                  absolute right-2 top-full z-50 mt-1 w-40
                  overflow-hidden rounded-lg border border-neutral-800
                  bg-neutral-900 shadow-xl shadow-black/40
                "
              >
                {[
                  { label: "Rename", icon: Pencil, action: onRename },
                  { label: "Download", icon: Download, action: onDownload },
                ].map(({ label, icon: Icon, action }) => (
                  <button
                    key={label}
                    role="menuitem"
                    type="button"
                    onClick={() => {
                      setMenuFor(null);
                      action(doc);
                    }}
                    className="
                      flex w-full items-center gap-2.5 px-3 py-2
                      text-left text-xs text-neutral-300
                      transition-colors hover:bg-neutral-800
                      hover:text-neutral-100
                    "
                  >
                    <Icon size={14} />
                    {label}
                  </button>
                ))}

                {/* Divider: delete is destructive and shouldn't share a group
                    with the reversible actions above it. */}
                <button
                  role="menuitem"
                  type="button"
                  onClick={() => {
                    setMenuFor(null);
                    onDelete(doc);
                  }}
                  className="
                    flex w-full items-center gap-2.5 border-t
                    border-neutral-800 px-3 py-2 text-left text-xs text-red-400
                    transition-colors hover:bg-red-500/10
                  "
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default DocumentList;