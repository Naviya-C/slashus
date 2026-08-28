import type { ChatResponse, SessionResponse } from "./types";

export function usedPracticeTool(
    tools: ChatResponse["tools_used"],
): boolean {
    return (tools ?? []).some((entry) => {
        const name =
            typeof entry === "string" ? entry : (entry.name ?? entry.tool ?? "");
        return name.includes("practice") || name.includes("question");
    });
}

export function findPracticeSetId(session: SessionResponse): string | null {
    return (
        session.last_practice_set_id ??
        session.practice_set_id ??
        session.session?.last_practice_set_id ??
        session.session?.practice_set_id ??
        [...(session.messages ?? [])]
            .reverse()
            .find((message) => message.practice_set_id)?.practice_set_id ??
        null
    );
}
