import { apiJson } from "../../lib/api";
import type { Document } from "./types";

let documentsRequest: Promise<Document[]> | null = null;

export function listDocuments(): Promise<Document[]> {
    documentsRequest ??= apiJson<Document[]>("/api/v1/user_documents").finally(
        () => {
            documentsRequest = null;
        },
    );

    return documentsRequest;
}
