import type { Feature, Progress } from "./types";

export const FEATURES: Feature[] = [
    {
        title: "intelligent_doc_processing()",
        desc: "Handles scanned PDFs, legacy Sinhala fonts, and mixed-language documents. OCR pipeline re-encodes glyphs to Unicode before indexing.",
        color: "bg-emerald-100 text-emerald-500",
        icon: "📄",
    },
    {
        title: "hybrid_rag_retrieval()",
        desc: "Dense vector search + BM25 keyword matching. Answers cite exact page numbers. Folder-scoped or global retrieval.",
        color: "bg-sky-100 text-sky-500",
        icon: "☑",
    },
    {
        title: "realtime_analytics()",
        desc: "Track individual student performance, score distributions, and topic mastery trends. Export reports in one click.",
        color: "bg-amber-100 text-amber-500",
        icon: "〽",
    },
    {
        title: "human_validation_loop()",
        desc: "Low-confidence scores are flagged for educator review. The system learns from corrections to improve over time.",
        color: "bg-pink-100 text-pink-500",
        icon: "🔒",
    },
];

export const PROGRESS: Progress[] = [
    {
        name: "semantic_sim",
        value: 94,
        color: "bg-emerald-400",
    },
    {
        name: "keypoint_nli",
        value: 97,
        color: "bg-amber-400",
    },
    {
        name: "llm_judge",
        value: 98,
        color: "bg-sky-400",
    },
];
