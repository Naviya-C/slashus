import type { Document } from "../../features/documents/types";
import FileDropzone from "./FileDropZone";
import DocumentList from "./DocumentList";
import SessionList from "./SessionList";

type Props = {
    documents: Document[];
    loading: boolean;
    error: string | null;
    selectedDocIds: string[];
    activeSessionId: string | null;
    refreshKey: number;
    onUploaded: () => void;
    onToggleSelect: (docId: string) => void;
    onOpenSession: (id: string) => void;
    onCloseMobile?: () => void;
};

export default function ChatSidebar({
    documents,
    loading,
    error,
    selectedDocIds,
    activeSessionId,
    refreshKey,
    onUploaded,
    onToggleSelect,
    onOpenSession,
    onCloseMobile,
}: Props) {
    const openSession = (id: string) => {
        onOpenSession(id);
        onCloseMobile?.();
    };

    return (
        <div className="flex h-full min-h-0 flex-col">
            <section className="shrink-0 border-b border-[var(--bd)] px-3 py-4">
                <PanelLabel number="01" label="Upload" />
                <div className="mt-3">
                    <FileDropzone onUploaded={onUploaded} />
                </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col border-b border-[var(--bd)] px-2 py-4">
                <PanelLabel number="02" label="Documents" />
                <div className="mt-3 min-h-0 flex-1 overflow-y-auto overscroll-contain">
                    <DocumentList
                        documents={documents}
                        loading={loading}
                        error={error}
                        selectedDocIds={selectedDocIds}
                        onToggleSelect={onToggleSelect}
                        onRename={() => undefined}
                        onDelete={() => undefined}
                    />
                </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col px-2 py-4">
                <PanelLabel number="03" label="Sessions" />
                <div className="mt-3 min-h-0 flex-1 overflow-y-auto overscroll-contain">
                    <SessionList
                        activeId={activeSessionId}
                        onOpen={openSession}
                        onDelete={() => undefined}
                        refreshKey={refreshKey}
                    />
                </div>
            </section>
        </div>
    );
}

function PanelLabel({ number, label }: { number: string; label: string }) {
    return (
        <p className="px-2 text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--tx3)]">
            {number} / {label}
        </p>
    );
}
