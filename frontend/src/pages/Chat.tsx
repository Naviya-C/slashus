import { useCallback, useState } from "react";

import { useChat } from "../Hooks/useChat";
import { useDocuments } from "../Hooks/useDocuments";
import { MAX_SELECTED } from "../components/Chat/DocumentList";
import ChatHeader from "../components/Chat/ChatHeader";
import ChatSidebar from "../components/Chat/ChatSidebar";
import ChatWorkspace from "../components/Chat/ChatWorkspace";
import MobileChatDrawer from "../components/Chat/MobileChatDrawer";
import PracticePanel from "../components/Chat/PracticePanel";
import PanelResizer from "../components/Chat/PanelResizer";

export default function Chat() {
    const { documents, loading, error, refetch } = useDocuments();
    const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [leftWidth, setLeftWidth] = useState(304);
    const [rightWidth, setRightWidth] = useState(440);
    const chat = useChat(selectedDocIds);

    const toggleSelect = useCallback((docId: string) => {
        setSelectedDocIds((current) =>
            current.includes(docId)
                ? current.filter((id) => id !== docId)
                : current.length >= MAX_SELECTED
                  ? current
                  : [...current, docId],
        );
    }, []);

    const closeDrawer = useCallback(() => setDrawerOpen(false), []);

    const sidebarProps = {
        documents,
        loading,
        error,
        selectedDocIds,
        activeSessionId: chat.sessionId,
        refreshKey: chat.messages.length,
        onUploaded: refetch,
        onToggleSelect: toggleSelect,
        onOpenSession: chat.openSession,
    };

    return (
        <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-[var(--bg)] text-[var(--tx)]">
            <ChatHeader
                onOpenTools={() => setDrawerOpen(true)}
                onNewChat={chat.newSession}
            />

            <div className="flex min-h-0 flex-1">
                <aside
                    className="hidden shrink-0 lg:block"
                    style={{ width: leftWidth }}
                >
                    <ChatSidebar {...sidebarProps} />
                </aside>
                <PanelResizer
                    label="Resize resources panel"
                    value={leftWidth}
                    min={240}
                    max={420}
                    resetValue={304}
                    side="left"
                    onChange={setLeftWidth}
                />

                <ChatWorkspace
                    messages={chat.messages}
                    sending={chat.sending}
                    loadingSession={chat.loadingSession}
                    error={chat.error}
                    hasSelection={selectedDocIds.length > 0}
                    selectedCount={selectedDocIds.length}
                    onSend={chat.send}
                />

                <div className="hidden xl:flex">
                    <PanelResizer
                        label="Resize practice panel"
                        value={rightWidth}
                        min={340}
                        max={720}
                        resetValue={440}
                        side="right"
                        onChange={setRightWidth}
                    />
                </div>
                <aside
                    className="hidden shrink-0 xl:block"
                    style={{ width: rightWidth }}
                >
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

            <MobileChatDrawer
                open={drawerOpen}
                documents={documents}
                documentsLoading={loading}
                documentsError={error}
                selectedDocIds={selectedDocIds}
                activeSessionId={chat.sessionId}
                refreshKey={chat.messages.length}
                questions={chat.questions}
                answers={chat.answers}
                results={chat.results}
                marking={chat.marking}
                onClose={closeDrawer}
                onUploaded={refetch}
                onToggleSelect={toggleSelect}
                onOpenSession={chat.openSession}
                onAnswer={chat.answer}
                onMark={chat.mark}
            />
        </div>
    );
}
