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

export type MarkApiResponse = Omit<QuestionResult, "rubric_breakdown"> & {
    rubric_breakdown?: RubricPoint[];
    rubric_results?: Array<{
        point: string;
        awarded_marks: number;
        max_marks: number;
        feedback?: string;
    }>;
};

export type StoredAnswer = {
    selected_index: number | null;
    answer_text: string | null;
    marks: number | null;
    is_correct: boolean | null;
    feedback: string | null;
    revealed_answer: string | null;
    rubric_results?: MarkApiResponse["rubric_results"];
};

export type PracticeQuestion = Question & {
    answer?: StoredAnswer | null;
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

/**
 * What POST /api/v1/chat actually returns.
 *
 * There is no `questions` array here. When the agent writes a practice set it
 * calls its `save_practice_questions` tool, and the set is fetched separately
 * from /api/v1/practice/{id}. `tools_used` is how we know to go looking.
 */
export type ChatResponse = {
    session_id: string;
    reply: string;
    tools_used?: Array<string | { name?: string; tool?: string }>;
    iterations?: number;
    timed_out?: boolean;
    citations?: Citation[];
    reason?: Reason | null;
    practice_set_id?: string | null;
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
    questions?: PracticeQuestion[];
    answers?: Answer[] | Record<string, Answer>;
    results?: QuestionResult[] | Record<string, QuestionResult>;
    practice_set?: PracticeApiResponse | null;
    latest_practice?: PracticeApiResponse | null;
};
