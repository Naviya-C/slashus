import type {
    Answer,
    Message,
    PracticeApiResponse,
    PracticeData,
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

    return {
        questions: source.questions ?? [],
        answers: normalizeAnswers(source.answers),
        results: normalizeResults(source.results),
    };
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

    if (!Array.isArray(results)) {
        return results;
    }

    return Object.fromEntries(
        results.map((result) => [result.question_id, result]),
    );
}
