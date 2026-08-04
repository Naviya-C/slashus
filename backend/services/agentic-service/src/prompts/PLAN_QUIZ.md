Plan a practice set from the material available.

STUDENT'S REQUEST: {{query}}
MATERIAL: {{material}} ({{chunk_count}} passages)

CONVERSATION SO FAR:
{{conversation}}

Decide:

1. QUESTION TYPE — `mcq`, `true_false`, `short`, `structured`, or `essay`.
   Honour what the student asked for. Otherwise choose by material: factual
   and definitional content suits MCQ; discursive content suits `short` or
   `essay`. If the student struggled with a topic earlier, prefer types that
   make them produce the answer rather than recognise it.

2. COUNT — what the student asked for, else 5. Never more than the material
   supports: five questions from two short passages means overlap and
   repetition.

3. DIFFICULTY — `easy`, `medium`, `hard`. Consider what they got wrong
   earlier in the conversation.

4. BLOOM LEVEL — remember, understand, apply, analyse, evaluate, create.

Return ONLY JSON:
{
  "question_type": "mcq",
  "count": 5,
  "difficulty": "medium",
  "bloom_level": "understand",
  "topics": ["..."],
  "include_explanations": true,
  "reasoning": "one short sentence"
}
