use crate::engine::MappingSet;

/*
    Applies preprocessing rules.

    What:
        Rewrites legacy character sequences
        before combo and single-character
        matching begins.

    Why:
        Some legacy fonts encode modifiers
        in an order that does not match
        Unicode.

    Example:

        %a
            ↓
        a%

        s%
            ↓
        %s

    Used by:
        engine::convert_text()

    Flow:

        raw text
            ↓
        apply_rules()
            ↓
        matcher.rs
*/
pub fn apply_rules(
    text: &str,
    mapping: &MappingSet,
) -> String {
    if mapping.rules.is_empty()
        || mapping.max_rule_len == 0
    {
        return text.to_string();
    }

    let chars: Vec<char> =
        text.chars().collect();

    let mut result =
        String::with_capacity(
            text.len(),
        );

    let mut i = 0;

    while i < chars.len() {
        let mut matched =
            false;

        let max_len =
            mapping
                .max_rule_len
                .min(
                    chars.len() - i,
                );

        for len in (1..=max_len).rev() {
            let candidate: String =
                chars[i..i + len]
                    .iter()
                    .collect();

            if let Some(replacement) =
                mapping.rules.get(
                    candidate.as_str(),
                )
            {
                result.push_str(
                    replacement,
                );

                i += len;
                matched = true;
                break;
            }
        }

        if matched {
            continue;
        }

        result.push(
            chars[i],
        );

        i += 1;
    }

    result
}