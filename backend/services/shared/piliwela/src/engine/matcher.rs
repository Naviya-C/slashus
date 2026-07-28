use crate::engine::MappingSet;

/*
    Applies combo and single-character
    mappings.

    What:
        Performs the actual legacy-to-Unicode
        conversion.

    Strategy:

        1. Try longest combo first.
        2. If no combo matches, try single.
        3. If nothing matches, preserve the
           original character.

    Why:
        Legacy Sinhala fonts contain mappings
        such as:

            flda
            ffl
            l%s

        that must be matched before their
        individual characters.

    Used by:
        engine::convert_text()

    Flow:

        rules
            ↓
        apply_combos_and_singles()
            ↓
        kombuva
*/
pub fn apply_combos_and_singles(
    text: &str,
    mapping: &MappingSet,
) -> String {
    let chars: Vec<char> =
        text.chars().collect();

    let mut result =
        String::with_capacity(
            text.len(),
        );

    let mut i = 0;

    while i < chars.len() {
        let mut found_combo =
            false;

        /*
            Only search lengths that can
            actually fit into the remaining
            characters.
        */
        let max_len =
            mapping
                .max_combo_len
                .min(
                    chars.len() - i,
                );

        /*
            Longest-match-first.

            Example:

                ffl
                ff
                f

            We must try:

                3 → 2 → 1

            not:

                1 → 2 → 3
        */
        if max_len >= 2 {
            for len in (2..=max_len).rev() {
                let candidate: String =
                    chars[i..i + len]
                        .iter()
                        .collect();

                if let Some(mapped) =
                    mapping.combos.get(
                        candidate.as_str(),
                    )
                {
                    result.push_str(
                        mapped,
                    );

                    i += len;
                    found_combo = true;
                    break;
                }
            }
        }

        if found_combo {
            continue;
        }

        /*
            No combo matched.

            Fall back to single-character
            mapping.
        */
        let c = chars[i];

        if let Some(mapped) =
            mapping.singles.get(&c)
        {
            result.push_str(
                mapped,
            );
        } else {
            /*
                Unknown character.

                Preserve it exactly as-is.
            */
            result.push(c);
        }

        i += 1;
    }

    result
}