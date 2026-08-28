import { apiJson } from "../../lib/api";
import type {
    Answer,
    ChatResponse,
    MarkApiResponse,
    PracticeApiResponse,
    SessionResponse,
} from "./types";
import { normalizeQuestionResult } from "./normalizers";

export function sendChatMessage(
    message: string,
    sessionId: string | null,
    documentIds: string[],
) {
    return apiJson<ChatResponse>("/api/v1/chat", {
        method: "POST",
        body: JSON.stringify({
            message,
            session_id: sessionId,
            doc_ids: documentIds,
        }),
    });
}

/**
 * Mark a single answer.
 *
 * The marking endpoint takes one question at a time — it needs the question id
 * to look up the owner's approved answer key. Sending a batch under a session
 * id silently marks nothing, which is why results never appeared.
 */
export function markAnswer(answer: Answer) {
    return apiJson<MarkApiResponse>("/api/v1/mark", {
        method: "POST",
        body: JSON.stringify({
            question_id: answer.question_id,
            selected_index: answer.selected_index ?? null,
            answer_text: answer.answer_text ?? null,
        }),
    }).then(normalizeQuestionResult);
}

export function getSession(sessionId: string) {
    return apiJson<SessionResponse>(`/api/v1/sessions/${sessionId}?limit=30`);
}

export function getPractice(practiceSetId: string) {
    return apiJson<PracticeApiResponse>(`/api/v1/practice/${practiceSetId}`);
}
