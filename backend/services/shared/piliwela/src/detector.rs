use crate::mappings::{
    common::FontFamily,
    signatures::{
        FM_SIGNATURES,
        // DL_SIGNATURES,
        // WIJEYA_SIGNATURES,
        // KAPUTA_SIGNATURES,
    },
};

const FM_METADATA_PREFIXES: &[&str] = &[
    "fmabhaya",
    "fmababld",
    "fmemanee",
    "fmedwerdbance",
    "fmprabhath",
    "fmsamantha",
];

// ========================Font-Detect Using PDF Words & Symbols(..Document Level Detection/ Major Wins..)========================
// ===============================================================================================================================

fn score_chars(text: &str, signatures: &[char],) -> usize {
/*
    Counts how many signature characters from
    a particular font family appear in the text.

    What:
        Generic scoring utility.

    Why:
        Every text-based detector uses the same
        algorithm.

    Used by:
        score_fm()
        score_dl()
        score_wijeya()
        score_kaputa()
*/
    text.chars()
        .filter(|c| signatures.contains(c))
        .count()
}


fn score_fm(text: &str,) -> usize {
/*
    Calculates the likelihood that the text
    belongs to the FM font family.

    What:
        Counts FM-specific signature characters.

    Why:
        Used by the heuristic detector when
        font metadata does not exist.

    Used by:
        detect()
*/
    score_chars(
        text,
        FM_SIGNATURES,
    )
}

/*
fn score_dl(
    text: &str,
) -> usize {
    score_chars(
        text,
        DL_SIGNATURES,
    )
}

fn score_wijeya(
    text: &str,
) -> usize {
    score_chars(
        text,
        WIJEYA_SIGNATURES,
    )
}

fn score_kaputa(
    text: &str,
) -> usize {
    score_chars(
        text,
        KAPUTA_SIGNATURES,
    )
}
*/


pub fn detect(
    text: &str,
) -> FontFamily {
/*
    Detects the font family purely from text.
*/
    if text.is_empty() {
        return FontFamily::Unknown;
    }

    if text.chars().count() < 2 {
        return FontFamily::Unknown;
    }

    let fm = score_fm(text);

    let scores = [
        (FontFamily::FM, fm),
        // ...
    ];

    let (family, score) =
        scores
            .into_iter()
            .max_by_key(
                |(_, score)| *score
            )
            .unwrap();

    if score == 0 {
        FontFamily::Unknown
    } else {
        family
    }
}

// ==============================Font-Detect Using PDF EMBEDDING METADATA============================
// ==================================================================================================

fn strip_subset_prefix(font_name: &str,) -> &str {
/*
    Removes a PDF font subset tag.

    What:
        Embedded/subset fonts are named like
        "BCDEEE+FMAbhaya": six uppercase ASCII
        letters followed by '+', then the real
        font name.

    Why:
        Without stripping this tag, prefix
        matching such as starts_with("fmabhaya")
        fails for every subset-embedded font,
        so whole spans are classified Unknown
        and never converted. This is the most
        common reason "not all text converts".

    Used by:
        detect_from_metadata()
*/
    if let Some(plus) = font_name.find('+') {
        if plus == 6
            && font_name[..6]
                .bytes()
                .all(|b| b.is_ascii_uppercase())
        {
            return &font_name[plus + 1..];
        }
    }

    font_name
}


pub fn detect_from_metadata(font_name: &str,) -> FontFamily {
/*
    Detects the font family from a PDF span's
    embedded font metadata.

    What:
        Maps font names into FontFamily.

    Why:
        PDF metadata is usually far more
        accurate than text heuristics and
        should be preferred whenever available.

    Used by:
        PDF reader pipeline.

    Returns:
        The detected FontFamily or Unknown.
*/
    /*
        1. Drop the subset tag ("BCDEEE+").
        2. Lowercase.
        3. Remove spaces / hyphens / underscores
           so "FM-Abhaya", "FM Abhaya" and
           "FMAbhaya" all normalise the same.
    */
    let stripped =
        strip_subset_prefix(font_name);

    let normalized: String =
        stripped
            .to_lowercase()
            .chars()
            .filter(|c| {
                !matches!(c, ' ' | '-' | '_')
            })
            .collect();

    /*
        Any FM font ("FMAbhaya", "FMBindumathi",
        "FMMalithi", ...) starts with "fm".
        This covers the whole family instead of
        a fixed handful of names.
    */
    if normalized.starts_with("fm") {
        return FontFamily::FM;
    }

    /*
        Fallback for the explicit legacy names
        that do not begin with "fm".
    */
    if FM_METADATA_PREFIXES
        .iter()
        .any(
            |prefix|
                normalized.starts_with(
                    prefix,
                )
        )
    {
        return FontFamily::FM;
    }

    /*
    if DL_METADATA_PREFIXES
        .iter()
        .any(
            |prefix|
                lower.starts_with(
                    prefix,
                )
        )
    {
        return FontFamily::DL;
    }

    if WIJEYA_METADATA_PREFIXES
        .iter()
        .any(
            |prefix|
                lower.starts_with(
                    prefix,
                )
        )
    {
        return FontFamily::Wijeya;
    }

    if KAPUTA_METADATA_PREFIXES
        .iter()
        .any(
            |prefix|
                lower.starts_with(
                    prefix,
                )
        )
    {
        return FontFamily::Kaputa;
    }
    */

    FontFamily::Unknown
}



pub fn detect_best(font_name: Option<&str>,text: &str,) -> FontFamily {
/*
    Hybrid detector.

    What:
        Tries metadata detection first and
        falls back to text heuristics.

    Why:
        PDFs usually preserve font metadata,
        but OCR and malformed documents may
        not.

    Strategy:

        metadata
            ↓
         known?
         /     \
       yes      no
        ↓        ↓
      return   detect(text)

    Returns:
        The best detected FontFamily.
*/
    /*
        A present, non-empty font name is authoritative.

        If it names a known legacy family we return that. If it does
        not, the span is genuinely non-legacy — English, numbers or
        symbols set in Times / Minion / a Tamil font, etc. — and MUST
        be left untouched.

        We deliberately do NOT fall back to the text heuristic here.
        detect() scores any FM signature character as FM, and because
        FM uses ordinary ASCII codes, plain English scores as FM too.
        That fallback would convert lines like
        "Published by : Educational Publications Department" into
        Sinhala gibberish.

        The text heuristic is used only when there is no usable font
        name at all (OCR output, malformed PDFs, copied plain text).
    */
    if let Some(font) = font_name {
        if !font.trim().is_empty() {
            return detect_from_metadata(font);
        }
    }

    detect(text)
}

/*
==============Later Development=============
wfa I love u 

Output:

[
    {
        text: "wfa",
        start: 0,
        end: 3,
        family: FM,
        should_convert: true,
    },
    {
        text: "I",
        start: 4,
        end: 5,
        family: Unknown,
        should_convert: false,
    },
    {
        text: "love",
        start: 6,
        end: 10,
        family: Unknown,
        should_convert: false,
    },
    {
        text: "u",
        start: 11,
        end: 12,
        family: Unknown,
        should_convert: false,
    },
]
*/