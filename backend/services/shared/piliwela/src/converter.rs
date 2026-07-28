use crate::detector;
use crate::engine;
use crate::options::ConvertOptions;

use crate::mappings::{
    common::FontFamily,
    fm,
    // dl,
    // wijeya,
    // kaputa,
};


pub fn convert(
    text: &str,
    family: FontFamily,
    options: &ConvertOptions,
) -> String {
/*
    Converts text using an explicitly supplied
    FontFamily.

    What:
        Entry point into the conversion engine.

    Why:
        Sometimes the caller already knows the
        font family and does not need detection.

    Used by:
        - convert_auto()
        - PDF metadata pipeline
        - Future token conversion pipeline
*/
    match family {
        FontFamily::FM => {
            engine::convert(
                text,
                &fm::FM_MAPPING,
                options,
            )
        }

        /*
        FontFamily::DL => {
            engine::convert(
                text,
                &dl::DL_MAPPING,
                options,
            )
        }

        FontFamily::Wijeya => {
            engine::convert(
                text,
                &wijeya::WIJEYA_MAPPING,
                options,
            )
        }

        FontFamily::Kaputa => {
            engine::convert(
                text,
                &kaputa::KAPUTA_MAPPING,
                options,
            )
        }
        */

        FontFamily::DL
        | FontFamily::Wijeya
        | FontFamily::Kaputa => {
            text.to_string()
        }

        FontFamily::Unknown => {
            /*
                Metadata detection failed.

                Fall back to text heuristics.

                Useful for:
                    - malformed PDFs
                    - OCR output
                    - copied text
                    - missing font metadata
            */
            text.to_string()
        }
    }
}


pub fn convert_auto(text: &str,options: &ConvertOptions,) -> String {
/*
    Converts an entire document using text
    heuristic detection.

    What:
        Detects the document's legacy font
        family from its content.

    Why:
        Useful for:
            - plain text
            - OCR output
            - malformed PDFs
            - copied text

    Flow:

        text
          ↓
        detect()
          ↓
        convert()
*/
    let family = detector::detect(text);

    convert(
        text,
        family,
        options,
    )
}


pub fn convert_auto_with_metadata(
    text: &str,
    font_name: &str,
    options: &ConvertOptions,
) -> String {
/*
    Converts text using PDF metadata.

    What:
        Detects the font family from the
        embedded PDF font name.

    Why:
        PDF metadata is usually more accurate
        than text heuristics.

        If metadata fails, falls back to
        text heuristics.

    Used by:
        PyMuPDF reader pipeline.

    Flow:

        span.font
             ↓
        detect_best()
             ↓
        convert()
*/
    let family =
        detector::detect_best(
            Some(font_name),
            text,
        );

    convert(
        text,
        family,
        options,
    )
}

/*
    Future development.

    Converts mixed-language text by first
    detecting individual tokens.

    Example:

        Input:
            "wfa I love u"

        Detection:
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
                ...
            ]

        Output:
            "කා I love u"

    Flow:

        detect_tokens()
              ↓
        convert only legacy tokens
              ↓
        rebuild original string

    NOTE:
        Not implemented yet.
*/
/*
pub fn convert_auto_tokens(
    text: &str,
    options: &ConvertOptions,
) -> String {

}
*/