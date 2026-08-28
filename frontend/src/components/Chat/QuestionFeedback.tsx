import { CheckCircle2, XCircle } from "lucide-react";

import type { Question, QuestionResult } from "../../features/chat/types";

type QuestionFeedbackProps = {
    question: Question;
    result: QuestionResult;
};

const SINHALA_OPTION_LABELS = ["අ", "ආ", "ඇ", "ඈ", "ඉ", "ඊ", "උ", "ඌ"];
const LATIN_OPTION_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"];

export default function QuestionFeedback({
    question,
    result,
}: QuestionFeedbackProps) {
    const sinhala = /[\u0D80-\u0DFF]/.test(
        `${question.question} ${result.feedback}`,
    );
    const isChoice = question.options.length > 0;
    const correctAnswer = getCorrectAnswer(question, result, sinhala);

    return (
        <section
            aria-live="polite"
            className={`mt-4 rounded-xl border p-3.5 ${
                result.is_correct === true
                    ? "border-emerald-500/25 bg-emerald-500/8"
                    : result.is_correct === false
                      ? "border-red-500/25 bg-red-500/8"
                      : "border-blue-500/25 bg-blue-500/8"
            }`}
        >
            <div className="flex items-start gap-2.5">
                {result.is_correct === false ? (
                    <XCircle className="mt-0.5 shrink-0 text-red-500" size={17} />
                ) : (
                    <CheckCircle2
                        className={`mt-0.5 shrink-0 ${
                            result.is_correct === true
                                ? "text-emerald-500"
                                : "text-blue-500"
                        }`}
                        size={17}
                    />
                )}
                <div className="min-w-0 space-y-2">
                    <p className="text-sm font-medium leading-6 text-[var(--tx)]">
                        {getVerdict(result, sinhala)}
                        {result.is_correct === false && isChoice && correctAnswer && (
                            <>
                                {sinhala ? " නිවැරදි උත්තරය " : " The correct answer is "}
                                <strong>{correctAnswer}</strong>
                                {sinhala ? " වේ." : "."}
                            </>
                        )}
                    </p>

                    {result.feedback && (
                        <p className="whitespace-pre-wrap text-sm leading-6 text-[var(--tx2)]">
                            {result.feedback}
                        </p>
                    )}

                    {!isChoice && result.revealed_answer && (
                        <div className="rounded-lg bg-[var(--sf3)] px-3 py-2.5">
                            <p className="mb-1 text-[10px] font-semibold tracking-widest text-[var(--tx3)]">
                                {sinhala ? "ආදර්ශ පිළිතුර" : "MODEL ANSWER"}
                            </p>
                            <p className="whitespace-pre-wrap text-xs leading-5 text-[var(--tx2)]">
                                {result.revealed_answer}
                            </p>
                        </div>
                    )}

                    {result.rubric_breakdown.length > 0 && (
                        <details className="text-xs">
                            <summary className="cursor-pointer text-[var(--tx3)] hover:text-[var(--tx)]">
                                {sinhala ? "ලකුණු නිර්ණායක" : "Rubric"}
                            </summary>
                            <ul className="mt-2 space-y-1 pl-3">
                                {result.rubric_breakdown.map((point, index) => (
                                    <li key={`${point.point}-${index}`} className="text-[var(--tx2)]">
                                        <span
                                            className={
                                                point.awarded > 0
                                                    ? "text-emerald-500"
                                                    : "text-[var(--tx3)]"
                                            }
                                        >
                                            {point.awarded}/{point.max}
                                        </span>{" "}
                                        {point.point}
                                        {point.note ? ` — ${point.note}` : ""}
                                    </li>
                                ))}
                            </ul>
                        </details>
                    )}
                </div>
            </div>
        </section>
    );
}

function getVerdict(result: QuestionResult, sinhala: boolean): string {
    if (result.is_correct === true) {
        return sinhala ? "ඔබේ උත්තරය නිවැරදියි. ✅" : "Your answer is correct. ✅";
    }
    if (result.is_correct === false) {
        return sinhala ? "ඔබේ උත්තරය වැරදියි. 😅" : "Your answer is incorrect.";
    }
    return sinhala
        ? `ඔබට ලකුණු ${result.marks}/${result.max_marks} ලැබුණි.`
        : `You received ${result.marks}/${result.max_marks} marks.`;
}

function getCorrectAnswer(
    question: Question,
    result: QuestionResult,
    sinhala: boolean,
): string | null {
    if (!result.revealed_answer) return null;

    const index = question.options.findIndex(
        (option) => option.text.trim() === result.revealed_answer?.trim(),
    );
    if (index < 0) return result.revealed_answer;

    const label = (sinhala ? SINHALA_OPTION_LABELS : LATIN_OPTION_LABELS)[index];
    return label
        ? `(${label}) ${question.options[index].text}`
        : question.options[index].text;
}
