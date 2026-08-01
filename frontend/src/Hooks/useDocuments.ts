import { useCallback, useEffect, useState } from "react";

import { apiJson } from "../lib/api";

export type Document = {
  doc_id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export function useDocuments() {
	const [documents, setDocuments] = useState<Document[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);


	const fetchDocs = useCallback(
		async (isActive: () => boolean = () => true) => {
		try {
			const docs = await apiJson<Document[]>("/api/v1/user_documents");
			if (!isActive()) return;
			setDocuments(docs);
			setError(null);
		} catch (err) {
			if (!isActive()) return;
			setError(err instanceof Error ? err.message : "Could not load documents");
		} finally {
			if (isActive()) setLoading(false);
		}
		},
		[],
	);

	useEffect(() => {
		let active = true;
		// eslint-disable-next-line react-hooks/set-state-in-effect
		void fetchDocs(() => active);
		return () => {
		active = false;
		};
	}, [fetchDocs]);

	const refetch = useCallback(() => fetchDocs(), [fetchDocs]);

	return { documents, loading, error, refetch };
}