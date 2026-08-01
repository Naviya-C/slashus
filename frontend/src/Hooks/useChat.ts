import { useCallback, useState } from "react";

import { apiJson } from "../lib/api";


export type Option = { index: number; text: string };

export type Question = {
  id: string;
  type: "mcq" | "true_false" | "short" | "structured" | "essay";
  question: string;
  /** Non-empty means render a radio group; empty means a textarea. The data
   *  says which widget to use — no separate hint field to fall out of sync. */
  options: Option[];
  /** Present for mcq/true_false so the UI can mark instantly with no round
   *  trip. Readable in devtools — acceptable for self-directed study, not for
   *  anything graded. */
  correct_index: number | null;
  /** Shown only after the student submits. */
  explanation: string | null;
  max_marks: number;
};

export type QuestionResult = {
  question_id: string;
  marks: number;
  max_marks: number;
  /** null for written answers — they are graded on a scale, not correct/wrong. */
  is_correct: boolean | null;
  feedback: string;
  rubric_breakdown: { point: string; awarded: number; max: number; note?: string }[];
  /** Populated only when marks < 5. */
  revealed_answer: string | null;
};

/** Why a request could not be served. Switch on this rather than
 *  string-matching the reply — telling a user with no documents to "refresh"
 *  is useless, and telling a user who has documents to "upload files" is
 *  wrong. */
export type Reason = "no_documents" | "no_relevant" | "not_in_source";

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
  citations?: { page: number | null; title: string | null }[];
  reason?: Reason | null;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { page: number | null; title: string | null }[];
  reason?: Reason | null;
};

export type Answer = {
  question_id: string;
  selected_index?: number;
  answer_text?: string;
};

/* ----------------------------------------------------------------- hook */

export function useChat(docIds: string[]) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [results, setResults] = useState<Record<string, QuestionResult>>({});
  const [sending, setSending] = useState(false);
  const [marking, setMarking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      // Optimistic: the user's own message appears immediately. Waiting for
      // the server to echo it back makes the UI feel broken on a slow turn,
      // and generation takes 10-30 seconds.
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);

      try {
        const res = await apiJson<ChatResponse>("/api/v1/chat", {
          method: "POST",
          body: JSON.stringify({
            message: text,
            session_id: sessionId,
            doc_ids: docIds,
          }),
        });

        setSessionId(res.session_id);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: res.reply,
            citations: res.citations,
            reason: res.reason,
          },
        ]);

        // `kind` is the routing flag: questions go to the practice panel,
        // everything else stays in the conversation. The reply renders in
        // chat either way, so a generation produces both.
        if (res.kind === "questions" && res.questions) {
          setQuestions(res.questions);
          // A new set invalidates the old answers — leaving them would show
          // marks against questions that no longer exist.
          setAnswers({});
          setResults({});
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
        // Roll back the optimistic message. Leaving it makes the user think
        // it was sent when it never reached the server.
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      } finally {
        setSending(false);
      }
    },
    [sessionId, docIds],
  );

  const answer = useCallback((a: Answer) => {
    setAnswers((prev) => ({ ...prev, [a.question_id]: a }));
  }, []);

  const mark = useCallback(async () => {
    const submission = Object.values(answers);
    if (!submission.length || !sessionId) return;

    setMarking(true);
    setError(null);
    try {
      const res = await apiJson<ChatResponse>("/api/v1/mark", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, submission }),
      });
      setResults(
        Object.fromEntries((res.results ?? []).map((r) => [r.question_id, r])),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Marking failed");
    } finally {
      setMarking(false);
    }
  }, [answers, sessionId]);

  /** Load an existing session from the sidebar. */
  const openSession = useCallback(async (id: string) => {
    setSessionId(id);
    setQuestions([]);
    setAnswers({});
    setResults({});
    try {
      const res = await apiJson<{ messages: Message[] }>(
        `/api/v1/sessions/${id}?limit=30`,
      );
      setMessages(res.messages);
    } catch {
      setMessages([]);
    }
  }, []);

  const newSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setQuestions([]);
    setAnswers({});
    setResults({});
  }, []);

  return {
    sessionId,
    messages,
    questions,
    answers,
    results,
    sending,
    marking,
    error,
    send,
    answer,
    mark,
    openSession,
    newSession,
  };
}