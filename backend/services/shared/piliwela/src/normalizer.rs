use unicode_normalization::
    UnicodeNormalization;

/*
    Removes consecutive Zero Width Joiners.

    What:
        Converts:

            ‍‍
        into:

            ‍

    Why:
        Some legacy conversions can
        accidentally generate duplicate
        ZWJs.

    Used by:
        normalize()
*/
fn remove_duplicate_zwj(
    text: &str,
) -> String {
    let mut result =
        String::new();

    let mut prev =
        None;

    for c in text.chars() {
        if c == '\u{200D}'
            && prev == Some(c)
        {
            continue;
        }

        result.push(c);
        prev = Some(c);
    }

    result
}

/*
    Removes consecutive Zero Width
    Non-Joiners.

    What:
        Converts:

            ‌‌
        into:

            ‌

    Why:
        OCR and malformed legacy text
        can sometimes generate duplicate
        ZWNJs.

    Used by:
        normalize()
*/
fn remove_duplicate_zwnj(
    text: &str,
) -> String {
    let mut result =
        String::new();

    let mut prev =
        None;

    for c in text.chars() {
        if c == '\u{200C}'
            && prev == Some(c)
        {
            continue;
        }

        result.push(c);
        prev = Some(c);
    }

    result
}

/*
    Collapses repeated whitespace.

    Example:

        "abc     def"
            ↓
        "abc def"

    Why:
        PDF extraction and OCR often
        introduce excessive spacing.

    Used by:
        normalize()
*/
fn collapse_whitespace(
    text: &str,
) -> String {
    let mut result =
        String::new();

    let mut prev_ws =
        false;

    for c in text.chars() {
        if c.is_whitespace() {
            if !prev_ws {
                result.push(' ');
            }

            prev_ws = true;
        } else {
            prev_ws = false;
            result.push(c);
        }
    }

    result
}

/*
    Final Unicode cleanup stage.

    Flow:

        duplicate ZWJ removal
                ↓
        duplicate ZWNJ removal
                ↓
        whitespace cleanup
                ↓
        Unicode NFC normalization

    Why:
        Ensures every conversion returns
        stable, valid Unicode Sinhala.

    Used by:
        engine::convert_text()
*/
pub fn normalize(
    text: &str,
) -> String {
    let text =
        remove_duplicate_zwj(
            text,
        );

    let text =
        remove_duplicate_zwnj(
            &text,
        );

    let text =
        collapse_whitespace(
            &text,
        );

    text
        .nfc()
        .collect()
}