pub enum EnglishPolicy {
    Never,
    Auto,
    Always,
}

pub struct ConvertOptions {
    pub english_policy: EnglishPolicy,
}


impl Default for ConvertOptions {
    fn default() -> Self {
        Self {
            english_policy:
                EnglishPolicy::Auto,
        }
    }
}


