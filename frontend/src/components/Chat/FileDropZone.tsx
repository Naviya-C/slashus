import { useRef, useState } from "react";

import { apiFetch } from "../../lib/api";

type Props = {
    onUploaded?: () => void;
};

const MAX_BYTES = 100 * 1024 * 1024;

function FileDropzone({ onUploaded }: Props) {
    const [dragging, setDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    async function handleFile(file: File) {
        setError(null);
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            setError("Only PDF files are accepted");
            return;
        }
        if (file.size > MAX_BYTES) {
            setError("File is larger than 100 MB");
            return;
        }

        setUploading(true);
        try {
            const form = new FormData();
            form.append("file", file);
            const res = await apiFetch("/uploads", {
                method: "POST",
                body: form,
            });

            if (!res.ok) {
                const body = await res.json().catch(() => null);
                throw new Error(body?.detail ?? "Upload failed");
            }
            onUploaded?.();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
            if (inputRef.current) inputRef.current.value = "";
        }
    }

    return (
        <div>
            <div
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    const file = e.dataTransfer.files?.[0];
                    if (file) handleFile(file);
                }}
                onClick={() => inputRef.current?.click()}
                className={`
			rounded-xl border border-dashed p-6 text-center cursor-pointer
			transition-colors
			${
                dragging
                    ? "border-red-500 bg-red-500/5"
                    : "border-neutral-700 hover:border-neutral-600"
            }
			${uploading ? "opacity-50 pointer-events-none" : ""}
		`}
            >
                <p className="text-sm text-neutral-300">
                    {uploading ? "Uploading…" : "Drop files to index"}
                </p>
                <p className="mt-1 text-xs text-neutral-500">
                    PDF - <span className="text-red-400 underline">browse</span>
                </p>

                <input
                    ref={inputRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFile(file);
                    }}
                />
            </div>

            {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        </div>
    );
}

export default FileDropzone;
