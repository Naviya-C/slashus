import { useEffect, type ReactNode } from "react";
import {
    BookOpenText,
    ChevronDown,
    Clock3,
    Dumbbell,
    Upload,
    X,
} from "lucide-react";

import type {
    Answer,
    Question,
    QuestionResult,
} from "../../features/chat/types";
import type { Document } from "../../features/documents/types";
import DocumentList from "./DocumentList";
import FileDropzone from "./FileDropZone";
import PracticePanel from "./PracticePanel";
import SessionList from "./SessionList";
import UserMenu from "./UserMenu";

type Props = {
    open: boolean;
    documents: Document[];
    documentsLoading: boolean;
    documentsError: string | null;
    selectedDocIds: string[];
    activeSessionId: string | null;
    refreshKey: number;
    questions: Question[];
    answers: Record<string, Answer>;
    results: Record<string, QuestionResult>;
    marking: boolean;
    onClose: () => void;
    onUploaded: () => void;
    onToggleSelect: (docId: string) => void;
    onOpenSession: (id: string) => void;
    onAnswer: (answer: Answer) => void;
    onMark: () => void;
};

export default function MobileChatDrawer({
    open,
    documents,
    documentsLoading,
    documentsError,
    selectedDocIds,
    activeSessionId,
    refreshKey,
    questions,
    answers,
    results,
    marking,
    onClose,
    onUploaded,
    onToggleSelect,
    onOpenSession,
    onAnswer,
    onMark,
}: Props) {
    useEffect(() => {
        if (!open) return;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.body.style.overflow = previousOverflow;
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div
            className="fixed inset-0 z-[100] 2xl:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Workspace menu"
        >
            <button
                type="button"
                aria-label="Close workspace menu"
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            />

            <aside className="absolute inset-y-0 right-0 flex w-[min(92vw,27rem)] flex-col border-l border-[var(--bd)] bg-[var(--bg)] shadow-2xl">
                <div className="flex h-16 shrink-0 items-center justify-between border-b border-[var(--bd)] px-4">
                    <UserMenu />
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close workspace menu"
                        className="grid h-10 w-10 place-items-center rounded-xl text-[var(--tx2)] hover:bg-[var(--sf2)]"
                    >
                        <X size={21} />
                    </button>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
                    <DrawerSection icon={Upload} label="Upload" defaultOpen>
                        <FileDropzone onUploaded={onUploaded} />
                    </DrawerSection>

                    <DrawerSection
                        icon={BookOpenText}
                        label="Documents"
                        badge={`${selectedDocIds.length}/3`}
                        defaultOpen
                    >
                        <div className="max-h-[42dvh] overflow-y-auto">
                            <DocumentList
                                documents={documents}
                                loading={documentsLoading}
                                error={documentsError}
                                selectedDocIds={selectedDocIds}
                                onToggleSelect={onToggleSelect}
                                onRename={() => undefined}
                                onDelete={() => undefined}
                            />
                        </div>
                    </DrawerSection>

                    <DrawerSection icon={Clock3} label="Sessions">
                        <div className="max-h-[42dvh] overflow-y-auto">
                            <SessionList
                                activeId={activeSessionId}
                                refreshKey={refreshKey}
                                onDelete={() => undefined}
                                onOpen={(id) => {
                                    onOpenSession(id);
                                    onClose();
                                }}
                            />
                        </div>
                    </DrawerSection>

                    <DrawerSection
                        icon={Dumbbell}
                        label="Practice"
                        badge={
                            questions.length
                                ? String(questions.length)
                                : undefined
                        }
                    >
                        <div className="h-[65dvh] min-h-[30rem] overflow-hidden rounded-xl border border-[var(--bd)]">
                            <PracticePanel
                                questions={questions}
                                answers={answers}
                                results={results}
                                onAnswer={onAnswer}
                                onMark={onMark}
                                marking={marking}
                            />
                        </div>
                    </DrawerSection>
                </div>
            </aside>
        </div>
    );
}

type DrawerSectionProps = {
    icon: typeof Upload;
    label: string;
    badge?: string;
    defaultOpen?: boolean;
    children: ReactNode;
};

function DrawerSection({
    icon: Icon,
    label,
    badge,
    defaultOpen,
    children,
}: DrawerSectionProps) {
    return (
        <details
            className="group mb-2 rounded-2xl border border-[var(--bd)] bg-[var(--sf)]"
            open={defaultOpen}
        >
            <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3.5 text-sm font-medium text-[var(--tx2)]">
                <Icon size={17} className="text-[var(--tx3)]" />
                <span className="flex-1">{label}</span>
                {badge && (
                    <span className="rounded-full bg-[var(--sf3)] px-2 py-0.5 text-[10px] text-[var(--tx2)]">
                        {badge}
                    </span>
                )}
                <ChevronDown
                    size={16}
                    className="text-[var(--tx3)] transition-transform group-open:rotate-180"
                />
            </summary>
            <div className="border-t border-[var(--bd)] p-3">{children}</div>
        </details>
    );
}
