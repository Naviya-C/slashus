import { useState } from "react";

import Logo from "../components/Atomic/Logo";
import ChatInput from "../components/Chat/ChatInput";
import DocumentList, { MAX_SELECTED } from "../components/Chat/DocumentList";
import FileDropzone from "../components/Chat/FileDropZone";
import UserMenu from "../components/Chat/UserMenu";
import { useDocuments } from "../Hooks/useDocuments";
import MessageCard from "../components/Chat/MessageCard";

import { useChat } from "../Hooks/useChat";
import SessionList from "../components/Chat/SessionList";
import PracticePanel from "../components/Chat/PracticePanel";

function Chat() {
    const { documents, loading, error, refetch } = useDocuments();
    const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
    const chat = useChat(selectedDocIds);

    function toggleSelect(docId: string) {
        setSelectedDocIds((prev) =>
        prev.includes(docId)
            ? prev.filter((id) => id !== docId)
            : prev.length >= MAX_SELECTED
            ? prev 
            : [...prev, docId],
        );
    }

    const hasSelection = selectedDocIds.length > 0;

  return (
        <div className="h-screen flex flex-col overflow-hidden bg-neutral-950 text-neutral-100">
            <header className="h-16 shrink-0 border-b border-neutral-800 flex items-center justify-between px-6">
            {/* Left: logo */}
            <div className="m-2 pl-5 hover:cursor-pointer">
                <Logo />
            </div>

            {/* Right: user menu */}
                <UserMenu />
            </header>

            <div className="flex-1 flex min-h-0">
                <aside className="w-72 shrink-0 border-r border-neutral-800 flex flex-col min-h-0 px-2 pt-5">
                    <span className="px-3 text-xs tracking-widest text-neutral-500">
                        01 / UPLOADS
                    </span>
                    <div className="shrink-0">
                        <FileDropzone onUploaded={refetch} />
                    </div>

                    <div className="flex-1 overflow-y-auto pt-4 min-h-0">
                        <DocumentList
                            documents={documents}
                            loading={loading}
                            error={error}
                            selectedDocIds={selectedDocIds}
                            onToggleSelect={toggleSelect}
                            onRename={(doc) => console.log("rename", doc)}
                            onDelete={(doc) => console.log("delete", doc)}
                            onDownload={(doc) => console.log("download", doc)}
                        />
                    </div>

                    <div className="flex-1 border-t border-neutral-800 py-4">
                        <span className="px-3 text-xs tracking-widest text-neutral-500">
                            02 / SESSIONS
                            <div className="flex-1 overflow-y-auto border-t border-neutral-800 py-4 min-h-0">
                            <div className="mt-3">
                                <SessionList
                                    activeId={chat.sessionId}
                                    onOpen={chat.openSession}
                                    refreshKey={chat.messages.length}
                                />
                            </div>
                            </div>
                        </span>
                    </div>
                </aside>

                <main className="flex-1 flex flex-col min-h-0">
                    <div className="flex-1 overflow-y-auto px-6 py-4">
                        {chat.messages.map((m) => (
                            <MessageCard key={m.id} role={m.role} content={m.content}
                            citations={m.citations} reason={m.reason} />
                        ))}
                    </div>

                    <div className="shrink-0 mx-auto mb-6 w-full max-w-3xl px-4">
                        {chat.sending && (
                            <p className="mb-2 px-1 text-sm text-neutral-500">Thinking…</p>
                        )}
                        {chat.error && (
                            <p className="mb-2 px-1 text-sm text-red-400">{chat.error}</p>
                        )}
                        <ChatInput
                            onSend={chat.send}
                            disabled={chat.sending}
                            placeholder={
                                hasSelection
                                ? "Ask about your materials..."
                                : "Write a message..."
                            }
                        />
                    </div>
                </main>

                <aside className="w-170 shrink-0 border-l border-neutral-800 overflow-y-auto">
                    <PracticePanel
                        questions={chat.questions}
                        answers={chat.answers}
                        results={chat.results}
                        onAnswer={chat.answer}
                        onMark={chat.mark}
                        marking={chat.marking}
                    />
                </aside>
            </div>
        </div>
    );
}

export default Chat;