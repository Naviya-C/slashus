import { Check, X } from "lucide-react";

import type {
    Answer,
    Question,
    QuestionResult,
} from "../../features/chat/types";
import QuestionFeedback from "./QuestionFeedback";

type Props = {
    questions: Question[];
    answers: Record<string, Answer>;
    results: Record<string, QuestionResult>;
    onAnswer: (a: Answer) => void;
    onMark: () => void;
    marking: boolean;
};

const REVEAL_BELOW = 5;

function PracticePanel({
    questions,
    answers,
    results,
    onAnswer,
    onMark,
    marking,
}: Props) {
    if (questions.length === 0) {
        return (
            <div className="flex h-full items-center justify-center px-8">
                <p className="text-center text-sm text-[var(--tx3)]">
                    Ask for questions and they'll appear here.
                </p>
            </div>
        );
    }

    const marked = Object.keys(results).length;
    const answered = Object.keys(answers).length;
    const allAnsweredQuestionsMarked = answered > 0 && marked >= answered;

    const totalMarks = Object.values(results).reduce((s, r) => s + r.marks, 0);
    const totalMax = Object.values(results).reduce(
        (s, r) => s + r.max_marks,
        0,
    );
    const pct = totalMax > 0 ? (totalMarks / totalMax) * 100 : 0;

    return (
        <div className="flex h-full flex-col">
            <div className="shrink-0 border-b border-[var(--bd)] px-5 py-4">
                <div className="flex items-baseline justify-between">
                    <span className="text-xs tracking-widest text-[var(--tx3)]">
                        03 / PRACTICE SET
                    </span>
                    <span className="text-xs text-[var(--tx3)]">
                        {answered} of {questions.length} answered
                    </span>
                </div>

                {marked > 0 && (
                    <>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-2xl font-semibold text-[var(--tx)]">
                                {totalMarks}/{totalMax}
                            </span>
                            <span className="text-xs tracking-wide text-[var(--tx3)]">
                                MARKED
                            </span>
                        </div>
                        <div className="mt-2 h-1 w-full overflow-hidden rounded bg-[var(--sf3)]">
                            <div
                                className="h-full rounded bg-red-500 transition-all"
                                style={{ width: `${pct}%` }}
                            />
                        </div>
                    </>
                )}
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 min-h-0">
                {questions.map((q, i) => {
                    const result = results[q.id];
                    const answer = answers[q.id];
                    const isChoice = q.options.length > 0;

                    return (
                        <div
                            key={q.id}
                            className="rounded-xl border border-[var(--bd)] bg-[var(--sf)] p-4"
                        >
                            <div className="mb-3 flex items-center justify-between">
                                <span className="flex items-center gap-2">
                                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                                        {i + 1}
                                    </span>
                                    <span className="text-[10px] tracking-widest text-[var(--tx3)]">
                                        {q.type.toUpperCase()}
                                    </span>
                                </span>

                                {result && (
                                    <span
                                        className={`
                      flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px]
                      ${
                          result.is_correct === true
                              ? "bg-emerald-500/15 text-emerald-400"
                              : result.is_correct === false
                                ? "bg-red-500/15 text-red-400"
                                : "bg-[var(--sf3)] text-[var(--tx2)]"
                      }
                    `}
                                    >
                                        {result.is_correct === true && (
                                            <Check size={11} />
                                        )}
                                        {result.is_correct === false && (
                                            <X size={11} />
                                        )}
                                        {result.is_correct === null
                                            ? `${result.marks}/${result.max_marks}`
                                            : result.is_correct
                                              ? "Correct"
                                              : "Incorrect"}
                                    </span>
                                )}
                            </div>

                            <p className="mb-3 text-sm leading-relaxed text-[var(--tx)]">
                                {q.question}
                            </p>

                            {isChoice ? (
                                <div className="space-y-1.5">
                                    {q.options.map((o) => {
                                        const selected =
                                            answer?.selected_index === o.index;
                                        const isCorrect =
                                            result &&
                                            q.correct_index === o.index;
                                        const isWrongPick =
                                            result && selected && !isCorrect;

                                        return (
                                            <label
                                                key={o.index}
                                                className={`
                          flex cursor-pointer items-start gap-2.5 rounded-lg
                          border px-3 py-2 text-sm transition-colors
                          ${
                              isCorrect
                                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-100"
                                  : isWrongPick
                                    ? "border-red-500/50 bg-red-500/10 text-red-100"
                                    : selected
                                      ? "border-[var(--bd2)] bg-[var(--sf3)] text-[var(--tx)]"
                                      : "border-[var(--bd)] text-[var(--tx2)] hover:border-[var(--bd2)]"
                          }
                        `}
                                            >
                                                <input
                                                    type="radio"
                                                    name={q.id}
                                                    checked={selected ?? false}
                                                    disabled={Boolean(result)}
                                                    onChange={() =>
                                                        onAnswer({
                                                            question_id: q.id,
                                                            selected_index:
                                                                o.index,
                                                        })
                                                    }
                                                    className="mt-0.5 accent-red-500"
                                                />
                                                <span>{o.text}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            ) : (
                                <textarea
                                    rows={4}
                                    value={answer?.answer_text ?? ""}
                                    disabled={Boolean(result)}
                                    placeholder="Write your answer..."
                                    onChange={(e) =>
                                        onAnswer({
                                            question_id: q.id,
                                            answer_text: e.target.value,
                                        })
                                    }
                                    className="
                    w-full resize-none rounded-lg border border-[var(--bd)]
                    bg-[var(--sf)] px-3 py-2 text-sm text-[var(--tx)]
                    placeholder:text-[var(--tx3)] outline-none
                    focus:border-[var(--bd2)] disabled:opacity-60
                  "
                                />
                            )}

                            {result && (
                                <QuestionFeedback question={q} result={result} />
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="shrink-0 border-t border-[var(--bd)] p-4">
                <button
                    type="button"
                    onClick={onMark}
                    disabled={marking || answered === 0 || allAnsweredQuestionsMarked}
                    className="
            w-full rounded-xl bg-red-500 py-3 text-sm font-semibold text-white
            transition-colors hover:bg-red-600
            disabled:cursor-not-allowed disabled:opacity-40
          "
                >
                    {marking
                        ? "Marking..."
                        : allAnsweredQuestionsMarked
                          ? "Marked"
                          : `Mark ${answered} answer${answered === 1 ? "" : "s"}`}
                </button>

                {marked > 0 &&
                    totalMax > 0 &&
                    totalMarks / totalMax < REVEAL_BELOW / 10 && (
                        <p className="mt-2 text-center text-xs text-[var(--tx3)]">
                            Model answers are shown above where you scored below
                            half marks.
                        </p>
                    )}
            </div>
        </div>
    );
}

export default PracticePanel;
