export type Option = {
    index: number;
    text: string;
};

export type Question = {
    id: string;
    type: "mcq" | "true_false" | "short" | "structured" | "essay";
    question: string;
    options: Option[];
    correct_index: number | null;
    explanation: string | null;
    max_marks: number;
};

export type RubricPoint = {
    point: string;
    awarded: number;
    max: number;
    note?: string;
};

export type QuestionResult = {
    question_id: string;
    marks: number;
    max_marks: number;
    is_correct: boolean | null;
    feedback: string;
    rubric_breakdown: RubricPoint[];
    revealed_answer: string | null;
};

export type Reason = "no_documents" | "no_relevant" | "not_in_source";

export type Citation = {
    page: number | null;
    title: string | null;
};

export type Message = {
    id: string;
    role: "user" | "assistant";
    content: string;
    created_at?: string;
    createdAt?: string;
    citations?: Citation[];
    reason?: Reason | null;
    practice_set_id?: string | null;
};

export type Answer = {
    question_id: string;
    selected_index?: number;
    answer_text?: string;
};

export type ChatResponse = {
    session_id: string;
    kind: "message" | "questions" | "marking";
    reply: string;
    intent?: string;
    practice_set_id?: string;
    questions?: Question[];
    results?: QuestionResult[];
    total_marks?: number;
    total_max?: number;
    citations?: Citation[];
    reason?: Reason | null;
};

export type SessionResponse = {
    messages: Message[];
    practice_set_id?: string | null;
    last_practice_set_id?: string | null;
    session?: {
        practice_set_id?: string | null;
        last_practice_set_id?: string | null;
    };
};

export type PracticeData = {
    questions: Question[];
    answers: Record<string, Answer>;
    results: Record<string, QuestionResult>;
};

export type PracticeApiResponse = {
    questions?: Question[];
    answers?: Answer[] | Record<string, Answer>;
    results?: QuestionResult[] | Record<string, QuestionResult>;
    practice_set?: PracticeApiResponse | null;
    latest_practice?: PracticeApiResponse | null;
};
