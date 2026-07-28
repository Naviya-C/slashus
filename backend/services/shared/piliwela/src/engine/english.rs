use phf::phf_set;

/*
    English-word heuristics.

    What:
        Decides whether an ASCII token looks
        like genuine English rather than legacy
        Sinhala that merely happens to use ASCII
        bytes.

    Why:
        Legacy Sinhala fonts encode text with
        ASCII characters, so a naive converter
        destroys embedded English words such as
        "Python" or "FastAPI". At the same time,
        many real legacy Sinhala words look
        superficially like English (all ASCII,
        contain vowels), so the test must be
        conservative in both directions.

    Used by:
        engine::script (token classifier)
        EnglishPolicy::Auto (via should_preserve)
*/

/*
    High-value English words and technical
    terms/abbreviations. A lexicon hit is
    treated as decisive: keep as English.
*/
static ENGLISH_LEXICON: phf::Set<&'static str> = phf_set! {
    // function words
    "a","an","the","and","or","but","if","then","else","of","to","in","on","at","by",
    "for","from","with","without","within","into","onto","out","off","up","down",
    "is","am","are","was","were","be","been","being","do","does","did","done",
    "has","have","had","having","will","would","shall","should","can","could","may",
    "might","must","not","no","nor","yes","this","that","these","those","it","its",
    "he","she","they","them","we","you","your","our","my","his","her","their","as",
    "so","than","too","very","more","most","much","many","few","some","any","all",
    "each","every","other","such","own","us","me","who","whom","whose","which","what",
    "when","where","why","how","here","there","now","new","one","two","also","only",
    "just","like","over","under","again",
    // common + product words
    "ok","okay","hi","hello","bye","go","email","web","app","apps","data","file","files",
    "code","test","tests","page","pages","user","users","name","names","list","lists",
    "map","set","get","put","post","run","model","models","train","val","build","debug",
    "review","note","notes","item","items","text","line","type","types","main","input","output",
    // tech terms / abbreviations
    "python","rust","react","node","json","yaml","html","css","api","apis","rest","http",
    "https","url","uri","sql","nlp","ml","ai","cv","llm","rag","gpu","cpu","ram","pdf","csv",
    "id","ui","ux","os","pc","db","ip","img","png","jpg","svg","utf","ascii","regex",
    "async","await","vector","vectors","matrix","tensor","kernel","layer","layers","token",
    "tokens","embedding","embeddings","transformer","attention","encoder","decoder",
    "fastapi","pytorch","tensorflow","numpy","pandas","docker","redis","kafka","qdrant",
    "postgres","github","huggingface","vscode","linux",
};

/*
    Valid English two- and three-letter
    consonant onsets. Used to reject tokens
    that begin with clusters English never
    uses (e.g. "dl", "lr", "kj"), which are a
    strong sign of legacy Sinhala.
*/
static ONSET2: phf::Set<&'static str> = phf_set! {
    "bl","br","ch","cl","cr","dr","dw","fl","fr","gl","gr","gw","kl","kr","ph","pl",
    "pr","ps","pt","qu","sc","sh","sk","sl","sm","sn","sp","st","sw","th","tr","ts",
    "tw","vr","wh","wr","kn","gn","mn","sq","sf","sv",
};

static ONSET3: phf::Set<&'static str> = phf_set! {
    "sch","scr","shr","spl","spr","squ","str","thr","phr","chr","sph",
};

fn is_vowel(c: char) -> bool {
    matches!(c, 'a' | 'e' | 'i' | 'o' | 'u')
}

/*
    Strips surrounding ASCII punctuation so
    lexicon / suffix checks see the bare word.
*/
fn core(token: &str) -> &str {
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
    Longest run of consecutive consonants
    (treating 'y' as a vowel). English rarely
    exceeds three; legacy Sinhala pileups do.
*/
fn max_consonant_run(low: &str) -> usize {
    let mut run = 0usize;
    let mut best = 0usize;

    for c in low.chars() {
        if c.is_ascii_alphabetic()
            && !is_vowel(c)
            && c != 'y'
        {
            run += 1;
            best = best.max(run);
        } else {
            run = 0;
        }
    }

    best
}

/*
    True if the token begins with a consonant
    cluster that is not a valid English onset.
*/
fn bad_onset(low: &str) -> bool {
    let a: Vec<char> =
        low.chars()
            .filter(|c| c.is_ascii_alphabetic())
            .collect();

    if a.len() < 2 {
        return false;
    }

    let vowelish = |c: char| is_vowel(c) || c == 'y';

    if vowelish(a[0]) || vowelish(a[1]) {
        return false;
    }

    if a.len() >= 3
        && a[2].is_ascii_alphabetic()
        && !vowelish(a[2])
    {
        let o3: String =
            [a[0], a[1], a[2]].iter().collect();

        return !ONSET3.contains(o3.as_str());
    }

    let o2: String = [a[0], a[1]].iter().collect();

    !ONSET2.contains(o2.as_str())
}

/*
    High-confidence English -> always keep.

    Signals:
        - no letters at all (pure number/punct)
        - single letter
        - lexicon hit
        - a digit next to a letter (GPT4, v2)
        - internal hyphen/underscore identifier
          (rust-lang, scikit-learn, back_end)
        - short all-caps abbreviation (ML, HTTP)
        - CamelCase with a valid onset
          (OpenAI, FastAPI, PyTorch)
*/
pub fn is_hard_english(token: &str) -> bool {
    if !token.chars().any(|c| c.is_alphabetic()) {
        return true;
    }

    let c = core(token);
    let low = c.to_lowercase();
    let letters =
        low.chars()
            .filter(|ch| ch.is_ascii_alphabetic())
            .count();

    if letters == 1 {
        return true;
    }

    if ENGLISH_LEXICON.contains(low.as_str()) {
        return true;
    }

    // digit adjacent to an ASCII letter
    let chars: Vec<char> = token.chars().collect();
    for w in chars.windows(2) {
        let (a, b) = (w[0], w[1]);
        if (a.is_ascii_alphabetic() && b.is_ascii_digit())
            || (a.is_ascii_digit() && b.is_ascii_alphabetic())
        {
            return true;
        }
    }

    // internal hyphen / underscore between letters
    for sep in ['-', '_'] {
        if let Some(pos) = c.find(sep) {
            if pos > 0 && pos < c.len() - 1 {
                let parts: Vec<&str> = c.split(sep).collect();
                if parts.len() >= 2
                    && parts.iter().all(|p| {
                        p.chars().any(|x| x.is_ascii_alphabetic())
                    })
                {
                    return true;
                }
            }
        }
    }

    // short all-caps abbreviation
    if token.is_ascii()
        && (2..=6).contains(&token.len())
        && token.chars().all(|ch| ch.is_ascii_uppercase())
    {
        return true;
    }

    // CamelCase interior lower -> Upper, with a sane onset
    let cc: Vec<char> = c.chars().collect();
    for w in cc.windows(2) {
        if w[0].is_lowercase()
            && w[1].is_uppercase()
            && !bad_onset(&low)
        {
            return true;
        }
    }

    false
}

/*
    Soft signal: the token has the *shape* of an
    English word (vowel ratio in range, no long
    consonant pileup, valid onset). Not decisive
    on its own - the classifier only uses it to
    demand stronger Sinhala evidence before
    converting an ambiguous token.
*/
pub fn has_english_shape(token: &str) -> bool {
    let low = core(token).to_lowercase();

    let letters: Vec<char> =
        low.chars()
            .filter(|c| c.is_ascii_alphabetic())
            .collect();

    if letters.len() < 2 {
        return false;
    }

    // all-vowel tokens ("uu", "oo") are not English-shaped
    if letters.iter().all(|c| is_vowel(*c) || *c == 'y') {
        return false;
    }

    let vc =
        letters
            .iter()
            .filter(|c| is_vowel(**c) || **c == 'y')
            .count();

    let ratio = vc as f64 / letters.len() as f64;

    vc >= 1
        && ratio >= 0.20
        && ratio <= 0.80
        && max_consonant_run(&low) <= 3
        && !bad_onset(&low)
}

/*
    Backwards-compatible entry point.

    Returns true when a token should be left
    unchanged on English grounds alone (no
    mapping / document context required).

    Retained so callers and tests that only need
    the English decision keep working; the full
    script-aware decision lives in engine::script.
*/
pub fn should_preserve(token: &str) -> bool {
    is_hard_english(token)
}