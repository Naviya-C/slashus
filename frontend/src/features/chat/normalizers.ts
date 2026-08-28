import type {
    Answer,
    Message,
    PracticeApiResponse,
    PracticeData,
    MarkApiResponse,
    PracticeQuestion,
    QuestionResult,
} from "./types";

export function normalizeSessionMessages(messages: Message[]): Message[] {
    const ordered = messages
        .map((message, index) => ({
            message,
            index,
            time: messageTime(message),
        }))
        .sort((first, second) => {
            if (first.time !== null && second.time !== null) {
                return (
                    first.time - second.time ||
                    roleOrder(first.message) - roleOrder(second.message) ||
                    first.index - second.index
                );
            }

            if (first.time !== null) {
                return -1;
            }

            if (second.time !== null) {
                return 1;
            }

            return first.index - second.index;
        })
        .map(({ message }) => message);

    const firstUserIndex = ordered.findIndex(
        (message) => message.role === "user",
    );

    return firstUserIndex === -1 ? [] : ordered.slice(firstUserIndex);
}

function roleOrder(message: Message) {
    return message.role === "user" ? 0 : 1;
}

function messageTime(message: Message): number | null {
    const value = message.created_at ?? message.createdAt;

    if (!value) {
        return null;
    }

    const time = Date.parse(value);
    return Number.isNaN(time) ? null : time;
}

export function normalizePractice(response: PracticeApiResponse): PracticeData {
    const source =
        response.practice_set ?? response.latest_practice ?? response;

    const questions = source.questions ?? [];
    const embedded = normalizeEmbeddedAnswers(questions);

    return {
        questions,
        answers: {
            ...embedded.answers,
            ...normalizeAnswers(source.answers),
        },
        results: {
            ...embedded.results,
            ...normalizeResults(source.results),
        },
    };
}

export function normalizeQuestionResult(
    result: MarkApiResponse,
): QuestionResult {
    return {
        ...result,
        revealed_answer: normalizeRevealedAnswer(
            (result as { revealed_answer?: unknown }).revealed_answer,
        ),
        rubric_breakdown:
            result.rubric_breakdown ??
            (result.rubric_results ?? []).map((item) => ({
                point: item.point,
                awarded: item.awarded_marks,
                max: item.max_marks,
                note: item.feedback,
            })),
    };
}

function normalizeRevealedAnswer(value: unknown): string | null {
    if (typeof value === "string") return value;
    if (value && typeof value === "object" && "text" in value) {
        return String((value as { text: unknown }).text);
    }
    return value == null ? null : String(value);
}

function normalizeEmbeddedAnswers(questions: PracticeQuestion[]): {
    answers: Record<string, Answer>;
    results: Record<string, QuestionResult>;
} {
    const answers: Record<string, Answer> = {};
    const results: Record<string, QuestionResult> = {};

    for (const question of questions) {
        const stored = question.answer;
        if (!stored) continue;

        answers[question.id] = {
            question_id: question.id,
            ...(stored.selected_index === null
                ? {}
                : { selected_index: stored.selected_index }),
            ...(stored.answer_text ? { answer_text: stored.answer_text } : {}),
        };

        if (stored.marks !== null) {
            results[question.id] = normalizeQuestionResult({
                question_id: question.id,
                marks: stored.marks,
                max_marks: question.max_marks,
                is_correct: stored.is_correct,
                feedback: stored.feedback ?? "",
                revealed_answer: stored.revealed_answer,
                rubric_results: stored.rubric_results,
            });
        }
    }

    return { answers, results };
}

function normalizeAnswers(
    answers: PracticeApiResponse["answers"],
): Record<string, Answer> {
    if (!answers) {
        return {};
    }

    if (!Array.isArray(answers)) {
        return answers;
    }

    return Object.fromEntries(
        answers.map((answer) => [answer.question_id, answer]),
    );
}

function normalizeResults(
    results: PracticeApiResponse["results"],
): Record<string, QuestionResult> {
    if (!results) {
        return {};
    }

    const values = Array.isArray(results) ? results : Object.values(results);
    return Object.fromEntries(
        values.map((result) => [
            result.question_id,
            normalizeQuestionResult(result),
        ]),
    );
}
