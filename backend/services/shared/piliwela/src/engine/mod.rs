pub mod rules;
pub mod matcher;
pub mod english;
pub mod script;
mod english_words;
pub mod kombuva;
pub mod tokenizer;

pub struct MappingSet {
    pub singles: &'static phf::Map<char, &'static str>,
    pub combos: &'static phf::Map<&'static str, &'static str>,
    pub rules: &'static phf::Map<&'static str, &'static str>,
    pub max_combo_len: usize,
    pub max_rule_len: usize,
}

use crate::options::{
    ConvertOptions,
    EnglishPolicy,
};

pub fn convert(text: &str, mapping: &MappingSet, options: &ConvertOptions) -> String {
    match options.english_policy {
        EnglishPolicy::Auto => {
            let tokens =
                tokenizer::tokenize(
                    text,
                );

            let mut result =
                String::new();

            for token in tokens {
                match token {
                    tokenizer::Token::Whitespace(ws) => {
                        result.push_str(ws);
                    }

                    tokenizer::Token::Word(word) => {
                        if script::should_convert(
                            word,
                        ) {
                            result.push_str(
                                &convert_text(
                                    word,
                                    mapping,
                                ),
                            );
                        } else {
                            result.push_str(
                                word,
                            );
                        }
                    }
                }
            }

            result
        }

        EnglishPolicy::Always => {
            let tokens =
                tokenizer::tokenize(
                    text,
                );

            let mut result =
                String::new();

            for token in tokens {
                match token {
                    tokenizer::Token::Whitespace(ws) => {
                        result.push_str(ws);
                    }

                    tokenizer::Token::Word(word) => {
                        if word
                            .chars()
                            .all(
                                |c| c.is_ascii()
                            )
                        {
                            result.push_str(
                                word,
                            );
                        } else {
                            result.push_str(
                                &convert_text(
                                    word,
                                    mapping,
                                ),
                            );
                        }
                    }
                }
            }

            result
        }

        EnglishPolicy::Never => {
            return convert_text(
            text,
            mapping,
        );
}
    }
}

fn convert_text(text: &str, mapping: &MappingSet,) -> String {
    let text =
        rules::apply_rules(
            text,
            mapping,
        );

    let text =
        matcher::apply_combos_and_singles(
            &text,
            mapping,
        );

    let text =
        kombuva::fix_kombuva(
            &text,
        );

    crate::normalizer::normalize(
        &text,
    )
}