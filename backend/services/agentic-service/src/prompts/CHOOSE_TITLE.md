Which lesson is this request about?

REQUEST: {{query}}

LESSONS:
{{titles}}

Return the NUMBER of the best match. If none clearly matches, return null —
a wrong lesson excludes the right material entirely, so guessing is worse
than not choosing.

Do NOT return a title string. Only the number.

CONFIDENCE matters more than usual here, because it decides how the match is
used rather than just how it is logged:

  0.8-1.0  the request names this lesson unmistakably. The search will be
           RESTRICTED to it, so be sure — a wrong answer here hides the
           correct material entirely.
  0.5-0.8  probably this lesson, but the wording is loose or another could
           fit. Chunks from it are ranked higher; nothing is excluded.
  0.4-0.5  a weak hint.
  below    return null instead.

Return ONLY JSON: {"index": 3, "confidence": 0.9}
