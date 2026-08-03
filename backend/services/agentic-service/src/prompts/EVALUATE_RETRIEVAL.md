Judge whether this material is enough to handle the student's request.

REQUEST: {{query}}
ATTEMPT: {{attempt}}

RETRIEVED MATERIAL:
{{chunks}}

Decide:

1. SUFFICIENT — can the request be handled well from this material alone?
   Be strict for questions (you need enough substance for several distinct
   ones) and lenient for a focused explanation (one good passage is often
   enough).

2. MISSING CONCEPTS — what the request needs that is not here.

3. NEXT ACTION:
   - `proceed`  good enough, use it
   - `rewrite`  search again with different wording — supply it
   - `widen`    search again with a bigger budget and no lesson filter
   - `give_up`  further searching will not help; answer with what there is,
                or say the documents do not cover it

By attempt 3, prefer `proceed` or `give_up`. The student is waiting, and a
partial answer beats a fourth search.

Return ONLY JSON:
{
  "sufficient": true,
  "confidence": 0.8,
  "missing_concepts": [],
  "next_action": "proceed",
  "rewritten_query": "",
  "reasoning": "one short sentence"
}
