import { apiJson } from "../../lib/api";
import type {
    Answer,
    ChatResponse,
    PracticeApiResponse,
    SessionResponse,
} from "./types";

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

export function markPractice(sessionId: string, submission: Answer[]) {
    return apiJson<ChatResponse>("/api/v1/mark", {
        method: "POST",
        body: JSON.stringify({
            session_id: sessionId,
            submission,
        }),
    });
}

export function getSession(sessionId: string) {
    return apiJson<SessionResponse>(`/api/v1/sessions/${sessionId}?limit=30`);
}

export function getPractice(practiceSetId: string) {
    return apiJson<PracticeApiResponse>(`/api/v1/practice/${practiceSetId}`);
}
