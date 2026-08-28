import { useCallback, useEffect, useState } from "react";

import { listDocuments } from "../features/documents/api";
import type { Document } from "../features/documents/types";

export type { Document } from "../features/documents/types";

export function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchDocuments = useCallback(async () => {
        setLoading(true);
        try {
            const nextDocuments = await listDocuments();
            setDocuments(nextDocuments);
            setError(null);
        } catch (reason) {
            setError(
                reason instanceof Error
                    ? reason.message
                    : "Could not load documents",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchDocuments();
    }, [fetchDocuments]);

    return {
        documents,
        loading,
        error,
        refetch: fetchDocuments,
    };
}
