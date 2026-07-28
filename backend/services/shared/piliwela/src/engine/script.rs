/*
    Script-aware token filter (EnglishPolicy::Auto).

    What:
        Decides, per whitespace-delimited token in an
        FM-detected span, whether to convert it to
        Unicode Sinhala or keep it verbatim.

    Why:
        Inside an FM span the bytes are FM codes, so an
        FM-Sinhala word looks like ASCII ("th" is the
        code for එය, "uu" for මම). Genuine English that
        an author embeds in the same span must NOT be
        converted. The two are told apart with a
        dictionary: a token is kept only if it is a real
        English word (or a known technical term /
        acronym); everything else is treated as FM and
        converted.

        A dictionary is used rather than shape heuristics
        (CamelCase / ALL CAPS / vowel patterns) because
        those signals are meaningless in FM encoding and
        misclassify ordinary Sinhala as English.

    Notes on thresholds:
        - Only tokens of length >= 3 are matched against
          the English dictionary. Two-letter Latin
          strings coincide constantly with Sinhala
          syllables (my -> පහ..., th -> එය) and must
          convert.
        - A short FORCE_CONVERT_SINHALA set lists the few
          FM-Sinhala tokens whose romanisation happens to
          equal a common English word (leg -> කැට, ...);
          these always convert.

    Used by:
        engine::convert (EnglishPolicy::Auto)
*/

use phf::phf_set;

use super::english_words::ENGLISH_WORDS;

/*
    Short acronyms, matched ONLY in their exact
    upper-case form so a lower-case Sinhala token can
    never collide ("ML" is kept, "ml" from an FM word is
    converted).
*/
static TECH_ACRONYMS: phf::Set<&'static str> = phf_set! {
    "ML","AI","UI","UX","OS","ID","IP","API","GPU","CPU","RAM","ROM","SQL","XML","CSS","PHP",
    "USB","GPS","LED","LCD","DNA","RNA","HTML","HTTP","URL","PDF","NLP","LLM","RAG","CNN",
    "RNN","GAN","TV","PC","IT","UN","US","UK","EU","IoT","3D","2D",
};

/*
    FM-Sinhala tokens whose Latin form is also a common
    English word. Without this they would be wrongly kept
    as English. Extend as needed for other documents.
*/
static FORCE_CONVERT_SINHALA: phf::Set<&'static str> = phf_set! {
    "leg","tall","isis","sir","kid",
};

/*
    Strips surrounding ASCII punctuation so "Python," or
    "(model)" can be matched against the word lists.
*/
fn strip_edges(token: &str) -> &str {
    token.trim_matches(
        |c: char| matches!(
            c,
            '.' | ',' | ':' | ';' | '!' | '?'
                | '\'' | '"' | '(' | ')'
                | '[' | ']' | '{' | '}'
                | '<' | '>'
        )
    )
}

/*
    Per-token decision: keep (do not convert) only if the
    token is recognisably English; otherwise convert.
*/
pub fn should_convert(token: &str) -> bool {
    let core = strip_edges(token);
    let low = core.to_lowercase();

    // Known Sinhala look-alikes always convert.
    if FORCE_CONVERT_SINHALA.contains(low.as_str()) {
        return true;
    }

    // Exact-case acronym -> English.
    if TECH_ACRONYMS.contains(core) {
        return false;
    }

    // Real English word (3+ letters) -> keep.
    if low.chars().count() >= 3 && ENGLISH_WORDS.contains(low.as_str()) {
        return false;
    }

    true
}