Plan how to find the material needed to handle this request.

STUDENT'S REQUEST: {{query}}
ROUTE: {{intent}}
IS FOLLOW-UP: {{is_followup}}
STUDENT HAS DOCUMENTS SELECTED: {{has_documents}}

CONVERSATION SO FAR:
{{conversation}}

PREVIOUS RETRIEVAL:
{{previous_retrieval}}

Decide:

1. SHOULD RETRIEVE — false only for greetings and small talk. Anything about
   the subject matter needs source material; answering without it invents
   content, which is the worst failure a study tool can have.

2. REUSE PREVIOUS — true when the request names NO new topic and a previous
   retrieval exists. "Explain more", "continue", "give another example",
   "summarise that", "5 more questions on that" all reuse.
   Searching for "explain more" returns whatever sits nearest those words in
   a textbook, which is nothing useful — reuse is not just cheaper, it is more
   correct.

3. SEARCH QUERY — the SUBJECT only. Strip the request wrapper: "give me 5
   questions about X" searches for X, never for the asking. Words like
   "ප්‍රශ්න ලබා දෙන්න" appear in no textbook and pull the search off target.
   Same language as the student.

4. KEYWORDS — the individual terms, same language.

5. LESSON TITLE HINT — if the student named or implied a specific lesson, the
   words they used. An exact title will be matched from the real list later;
   this is only the hint. Empty when no lesson was implied.

6. METADATA FILTERS — only `page_number`, and only when the student named a
   page explicitly. Never guess one. Anything else matches nothing and
   silently excludes the whole corpus.

7. BUDGET — how many chunks. 5-8 for one focused question, 12-20 for a
   summary or several questions, up to 40 for a whole lesson.

Return ONLY JSON:
{
  "should_retrieve": true,
  "reuse_previous": false,
  "search_query": "...",
  "keywords": ["..."],
  "lesson_title_hint": "",
  "metadata_filters": {},
  "budget": 12,
  "use_doc_filter": true,
  "use_conversation_context": false,
  "reasoning": "one short sentence"
}
