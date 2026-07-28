#[derive(Debug, PartialEq)]
pub enum Token<'a> {
    Word(&'a str),
    Whitespace(&'a str),
}

pub fn tokenize(text: &str) -> Vec<Token<'_>> {
    let mut tokens = Vec::new();

    if text.is_empty() {
        return tokens;
    }

    let mut start = 0;

    let mut current_is_whitespace = text
        .chars()
        .next()
        .unwrap()
        .is_whitespace();

    for (i, c) in text.char_indices() {
        let is_whitespace = c.is_whitespace();

        if is_whitespace != current_is_whitespace {
            let slice = &text[start..i];

            if current_is_whitespace {
                tokens.push(Token::Whitespace(slice));
            } else {
                tokens.push(Token::Word(slice));
            }

            start = i;
            current_is_whitespace = is_whitespace;
        }
    }

    let slice = &text[start..];

    if current_is_whitespace {
        tokens.push(Token::Whitespace(slice));
    } else {
        tokens.push(Token::Word(slice));
    }

    tokens
}