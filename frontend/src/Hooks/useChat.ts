import { useCallback, useState } from "react";

import { getSession, sendChatMessage } from "../features/chat/api";
import { normalizeSessionMessages } from "../features/chat/normalizers";
import { usedPracticeTool } from "../features/chat/session";
import type { Message } from "../features/chat/types";
import { usePractice } from "../features/chat/usePractice";

export type {
    Answer,
    ChatResponse,
    Message,
    Option,
    Question,
    QuestionResult,
    Reason,
} from "../features/chat/types";

export function useChat(documentIds: string[]) {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [sending, setSending] = useState(false);
    const [loadingSession, setLoadingSession] = useState(false);
    const [chatError, setChatError] = useState<string | null>(null);
    const practice = usePractice();

    const send = useCallback(
        async (text: string) => {
            const userMessage: Message = {
                id: crypto.randomUUID(),
                role: "user",
                content: text,
            };

            setMessages((current) => [...current, userMessage]);
            setSending(true);
            setChatError(null);

            try {
                const response = await sendChatMessage(
                    text,
                    sessionId,
                    documentIds,
                );

                setSessionId(response.session_id);
                setMessages((current) => [
                    ...current,
                    {
                        id: crypto.randomUUID(),
                        role: "assistant",
                        content: response.reply,
                        citations: response.citations,
                        reason: response.reason,
                    },
                ]);

                if (response.practice_set_id) {
                    await practice.loadById(response.practice_set_id);
                } else if (usedPracticeTool(response.tools_used)) {
                    await practice.loadForSession(response.session_id);
                }
            } catch (error) {
                setMessages((current) =>
                    current.filter((message) => message.id !== userMessage.id),
                );
                setChatError(
                    error instanceof Error ? error.message : "Something went wrong",
                );
            } finally {
                setSending(false);
            }
        },
        [
            documentIds,
            practice.loadById,
            practice.loadForSession,
            sessionId,
        ],
    );

    const openSession = useCallback(
        async (id: string) => {
            setSessionId(id);
            setLoadingSession(true);
            setChatError(null);
            setMessages([]);
            practice.clear();

            try {
                const session = await getSession(id);
                setMessages(normalizeSessionMessages(session.messages));
                await practice.loadFromSession(session);
            } catch (error) {
                setMessages([]);
                practice.clear();
                setChatError(
                    error instanceof Error
                        ? error.message
                        : "Could not load this session",
                );
            } finally {
                setLoadingSession(false);
            }
        },
        [practice.clear, practice.loadFromSession],
    );

    const newSession = useCallback(() => {
        setSessionId(null);
        setMessages([]);
        setChatError(null);
        practice.clear();
    }, [practice.clear]);

    return {
        sessionId,
        messages,
        questions: practice.questions,
        answers: practice.answers,
        results: practice.results,
        sending,
        marking: practice.marking,
        loadingSession,
        error: chatError ?? practice.error,
        send,
        answer: practice.answer,
        mark: practice.mark,
        openSession,
        newSession,
    };
}
