import { useEffect, useRef, useState } from "react";
import { Download, MoreVertical, Pencil, Trash2 } from "lucide-react";

import type { Document } from "../../features/documents/types";

export const MAX_SELECTED = 3;

type Props = {
    documents: Document[];
    loading: boolean;
    error: string | null;
    selectedDocIds: string[];
    onToggleSelect: (docId: string) => void;
    onRename?: (doc: Document) => void;
    onDelete?: (doc: Document) => void;
    onDownload?: (doc: Document) => void;
};

function relativeDate(iso: string): string {
    const days = Math.floor(
        (Date.now() - new Date(iso).getTime()) / 86_400_000,
    );
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
    const [menuFor, setMenuFor] = useState<string | null>(null);
    const listRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!menuFor) return;

        function onPointerDown(e: MouseEvent) {
            if (
                listRef.current &&
                !listRef.current.contains(e.target as Node)
            ) {
                setMenuFor(null);
            }
        }
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === "Escape") setMenuFor(null);
        }

        document.addEventListener("mousedown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("mousedown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [menuFor]);

    if (loading) {
        return <p className="px-1 text-xs text-[var(--tx3)]">Loading…</p>;
    }

    if (error) {
        return <p className="px-1 text-xs text-red-400">{error}</p>;
    }

    if (documents.length === 0) {
        return (
            <p className="px-1 text-xs text-[var(--tx3)]">
                No documents yet. Upload a PDF to get started.
            </p>
        );
    }

    const atCap = selectedDocIds.length >= MAX_SELECTED;
    const hasActions = Boolean(onRename || onDelete || onDownload);

    return (
        <div ref={listRef} className="space-y-2">
            {atCap && (
                <p className="px-1 pb-1 text-xs text-[var(--tx3)]">
                    {MAX_SELECTED} of {MAX_SELECTED} selected — deselect one to
                    change.
                </p>
            )}

            {documents.map((doc) => {
                const selected = selectedDocIds.includes(doc.doc_id);
                const locked = !selected && atCap;
                const menuOpen = menuFor === doc.doc_id;

                return (
                    <div
                        key={doc.doc_id}
                        className={`
              relative flex items-center gap-2 rounded-xl border
              transition-colors
              ${
                  selected
                      ? "border-red-500/60 bg-red-500/10"
                      : locked
                        ? "border-[var(--bd)]"
                        : "border-[var(--bd)] hover:border-[var(--bd2)]"
              }
            `}
                    >
                        <button
                            type="button"
                            onClick={() => onToggleSelect(doc.doc_id)}
                            disabled={locked}
                            title={
                                locked
                                    ? `Limit is ${MAX_SELECTED} documents`
                                    : undefined
                            }
                            className="
                flex min-w-0 flex-1 items-center gap-3 px-3 py-3 text-left
                disabled:cursor-not-allowed disabled:opacity-40
              "
                        >
                            <span
                                className={`
                  flex h-4 w-4 shrink-0 items-center justify-center rounded
                  border text-[10px] font-bold
                  ${
                      selected
                          ? "border-red-500 bg-red-500 text-white"
                          : "border-[var(--bd2)]"
                  }
                `}
                            >
                                {selected ? "✓" : ""}
                            </span>

                            <span
                                className="
                  shrink-0 rounded-md bg-[var(--sf3)] px-2 py-1
                  text-[10px] font-semibold tracking-wider text-[var(--tx2)]
                "
                            >
                                PDF
                            </span>

                            <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm text-[var(--tx)]">
                                    {doc.name}
                                </span>
                                <span className="block text-xs text-[var(--tx3)]">
                                    {relativeDate(doc.created_at)}
                                </span>
                            </span>
                        </button>

                        {hasActions && (
                            <button
                                type="button"
                                aria-label={`Actions for ${doc.name}`}
                                aria-haspopup="menu"
                                aria-expanded={menuOpen}
                                onClick={() =>
                                    setMenuFor(menuOpen ? null : doc.doc_id)
                                }
                                className="
                mr-2 shrink-0 rounded-md p-1.5 text-[var(--tx3)]
                transition-colors hover:bg-[var(--sf3)] hover:text-[var(--tx)]
              "
                            >
                                <MoreVertical size={16} />
                            </button>
                        )}

                        {menuOpen && hasActions && (
                            <div
                                role="menu"
                                className="
                  absolute right-2 top-full z-50 mt-1 w-40
                  overflow-hidden rounded-lg border border-[var(--bd)]
                  bg-[var(--sf)] shadow-xl shadow-black/40
                "
                            >
                                {[
                                    onRename && {
                                        label: "Rename",
                                        icon: Pencil,
                                        action: onRename,
                                    },
                                    onDownload && {
                                        label: "Download",
                                        icon: Download,
                                        action: onDownload,
                                    },
                                ]
                                    .filter(Boolean)
                                    .map((item) => {
                                        const {
                                            label,
                                            icon: Icon,
                                            action,
                                        } = item as {
                                            label: string;
                                            icon: typeof Pencil;
                                            action: (doc: Document) => void;
                                        };
                                        return (
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
                      text-left text-xs text-[var(--tx2)]
                      transition-colors hover:bg-[var(--sf3)]
                      hover:text-[var(--tx)]
                    "
                                            >
                                                <Icon size={14} />
                                                {label}
                                            </button>
                                        );
                                    })}

                                {onDelete && (
                                    <button
                                        role="menuitem"
                                        type="button"
                                        onClick={() => {
                                            setMenuFor(null);
                                            onDelete(doc);
                                        }}
                                        className="
                    flex w-full items-center gap-2.5 border-t
                    border-[var(--bd)] px-3 py-2 text-left text-xs text-red-400
                    transition-colors hover:bg-red-500/10
                  "
                                    >
                                        <Trash2 size={14} />
                                        Delete
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default DocumentList;
