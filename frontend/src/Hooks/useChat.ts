import { useCallback, useState } from "react";

import {
    getPractice,
    getSession,
    markPractice,
    sendChatMessage,
} from "../features/chat/api";
import {
    normalizePractice,
    normalizeSessionMessages,
} from "../features/chat/normalizers";
import type {
    Answer,
    Message,
    Question,
    QuestionResult,
} from "../features/chat/types";

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
    const [questions, setQuestions] = useState<Question[]>([]);
    const [answers, setAnswers] = useState<Record<string, Answer>>({});
    const [results, setResults] = useState<Record<string, QuestionResult>>({});
    const [sending, setSending] = useState(false);
    const [marking, setMarking] = useState(false);
    const [loadingSession, setLoadingSession] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const send = useCallback(
        async (text: string) => {
            const userMessage: Message = {
                id: crypto.randomUUID(),
                role: "user",
                content: text,
            };

            setMessages((current) => [...current, userMessage]);
            setSending(true);
            setError(null);

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

                if (response.kind === "questions" && response.questions) {
                    setQuestions(response.questions);
                    setAnswers({});
                    setResults({});
                }
            } catch (caughtError) {
                setMessages((current) =>
                    current.filter((message) => message.id !== userMessage.id),
                );
                setError(
                    caughtError instanceof Error
                        ? caughtError.message
                        : "Something went wrong",
                );
            } finally {
                setSending(false);
            }
        },
        [documentIds, sessionId],
    );

    const answer = useCallback((value: Answer) => {
        setAnswers((current) => ({
            ...current,
            [value.question_id]: value,
        }));
    }, []);

    const mark = useCallback(async () => {
        const submission = Object.values(answers);

        if (!sessionId || submission.length === 0) {
            return;
        }

        setMarking(true);
        setError(null);

        try {
            const response = await markPractice(sessionId, submission);
            setResults(
                Object.fromEntries(
                    (response.results ?? []).map((result) => [
                        result.question_id,
                        result,
                    ]),
                ),
            );
        } catch (caughtError) {
            setError(
                caughtError instanceof Error
                    ? caughtError.message
                    : "Marking failed",
            );
        } finally {
            setMarking(false);
        }
    }, [answers, sessionId]);

    const openSession = useCallback(async (id: string) => {
        setSessionId(id);
        setLoadingSession(true);
        setError(null);
        clearConversation();

        try {
            const session = await getSession(id);

            setMessages(normalizeSessionMessages(session.messages));

            const practiceSetId =
                session.last_practice_set_id ??
                session.practice_set_id ??
                session.session?.last_practice_set_id ??
                session.session?.practice_set_id ??
                session.messages.find((message) => message.practice_set_id)
                    ?.practice_set_id ??
                null;

            if (practiceSetId) {
                try {
                    const practice = await getPractice(practiceSetId);
                    const restored = normalizePractice(practice);
                    setQuestions(restored.questions);
                    setAnswers(restored.answers);
                    setResults(restored.results);
                } catch {
                    setQuestions([]);
                    setAnswers({});
                    setResults({});
                }
            }
        } catch (caughtError) {
            clearConversation();
            setError(
                caughtError instanceof Error
                    ? caughtError.message
                    : "Could not load this session",
            );
        } finally {
            setLoadingSession(false);
        }
    }, []);

    const newSession = useCallback(() => {
        setSessionId(null);
        setError(null);
        clearConversation();
    }, []);

    function clearConversation() {
        setMessages([]);
        setQuestions([]);
        setAnswers({});
        setResults({});
    }

    return {
        sessionId,
        messages,
        questions,
        answers,
        results,
        sending,
        marking,
        loadingSession,
        error,
        send,
        answer,
        mark,
        openSession,
        newSession,
    };
}
