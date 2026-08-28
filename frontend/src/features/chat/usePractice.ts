import { useCallback, useState } from "react";

import { getPractice, getSession, markAnswer } from "./api";
import { normalizePractice } from "./normalizers";
import { findPracticeSetId } from "./session";
import type {
    Answer,
    Question,
    QuestionResult,
    SessionResponse,
} from "./types";

export function usePractice() {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [answers, setAnswers] = useState<Record<string, Answer>>({});
    const [results, setResults] = useState<Record<string, QuestionResult>>({});
    const [marking, setMarking] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const clear = useCallback(() => {
        setQuestions([]);
        setAnswers({});
        setResults({});
        setError(null);
    }, []);

    const answer = useCallback((value: Answer) => {
        setAnswers((current) => ({
            ...current,
            [value.question_id]: value,
        }));
    }, []);

    const mark = useCallback(async () => {
        const submission = Object.values(answers).filter(
            (entry) =>
                !results[entry.question_id] &&
                (entry.selected_index !== undefined ||
                    Boolean((entry.answer_text ?? "").trim())),
        );
        if (submission.length === 0) return;

        setMarking(true);
        setError(null);

        const outcomes = await Promise.allSettled(
            submission.map(async (entry) => {
                const result = await markAnswer(entry);
                setResults((current) => ({
                    ...current,
                    [entry.question_id]: {
                        ...result,
                        question_id: entry.question_id,
                        rubric_breakdown: result.rubric_breakdown ?? [],
                    },
                }));
            }),
        );

        const failures = outcomes.filter(
            (outcome) => outcome.status === "rejected",
        ).length;
        if (failures > 0) {
            setError(
                `${failures} answer${failures === 1 ? "" : "s"} could not be marked. Try again.`,
            );
        }
        setMarking(false);
    }, [answers, results]);

    const loadFromSession = useCallback(async (session: SessionResponse) => {
        try {
            const practiceSetId = findPracticeSetId(session);
            if (!practiceSetId) {
                setQuestions([]);
                setAnswers({});
                setResults({});
                return;
            }

            const restored = normalizePractice(await getPractice(practiceSetId));
            setQuestions(restored.questions);
            setAnswers(restored.answers);
            setResults(restored.results);
        } catch {
            setQuestions([]);
            setAnswers({});
            setResults({});
        }
    }, []);

    const loadById = useCallback(async (practiceSetId: string) => {
        try {
            const restored = normalizePractice(await getPractice(practiceSetId));
            setQuestions(restored.questions);
            setAnswers(restored.answers);
            setResults(restored.results);
        } catch {
            setError("Questions were generated, but the Practice Panel could not load them.");
        }
    }, []);

    const loadForSession = useCallback(
        async (sessionId: string) => {
            try {
                const session = await getSession(sessionId);
                await loadFromSession(session);
            } catch {
                // The chat response remains useful even if its practice panel
                // cannot be restored immediately.
            }
        },
        [loadFromSession],
    );

    return {
        questions,
        answers,
        results,
        marking,
        error,
        answer,
        mark,
        loadFromSession,
        loadById,
        loadForSession,
        clear,
    };
}
