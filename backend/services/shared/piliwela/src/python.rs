use pyo3::prelude::*;

use crate::{
    converter,
    detector,
    options::ConvertOptions,
};


#[pyfunction]
fn detect(
    text: &str,
) -> String {
/*
    Detects the legacy font family using
    text heuristics.

    Used by:
        Testing
        OCR pipelines
        Plain text conversion
*/
    format!(
        "{:?}",
        detector::detect(
            text,
        )
    )
}

#[pyfunction]
fn detect_from_metadata(
    font_name: &str,
) -> String {
/*
    Detects the legacy font family using
    PDF font metadata.

    Used by:
        PyMuPDF reader pipeline.
*/
    format!(
        "{:?}",
        detector::detect_from_metadata(
            font_name,
        )
    )
}

#[pyfunction]
fn convert_auto(
    text: &str,
) -> String {
/*
    Converts text using heuristic
    detection.

    Flow:

        text
          ↓
        detect()
          ↓
        convert()
*/
    let options =
        ConvertOptions::default();

    converter::convert_auto(
        text,
        &options,
    )
}

#[pyfunction]
fn convert_auto_with_metadata(
    text: &str,
    font_name: &str,
) -> String {
/*
    Converts text using PDF metadata.

    Flow:

        span.text
        span.font
             ↓
        detect_from_metadata()
             ↓
        convert()
*/
    let options =
        ConvertOptions::default();

    converter::convert_auto_with_metadata(
        text,
        font_name,
        &options,
    )
}

#[pyfunction]
fn version() -> String {
/*
    Returns the installed Rust core
    version.

    Useful for:
        debugging
        package compatibility checks
*/
    env!("CARGO_PKG_VERSION")
        .to_string()
}

#[pyfunction]
fn hello() -> String {
/*
    Simple sanity test.
*/
    "Hello from Rust!"
        .to_string()
}

#[pymodule]
fn piliwela(
    m: &Bound<'_, PyModule>,
) -> PyResult<()> {
    m.add_function(
        wrap_pyfunction!(
            detect,
            m
        )?,
    )?;

    m.add_function(
        wrap_pyfunction!(
            detect_from_metadata,
            m
        )?,
    )?;

    m.add_function(
        wrap_pyfunction!(
            convert_auto,
            m
        )?,
    )?;

    m.add_function(
        wrap_pyfunction!(
            convert_auto_with_metadata,
            m
        )?,
    )?;

    m.add_function(
        wrap_pyfunction!(
            version,
            m
        )?,
    )?;

    m.add_function(
        wrap_pyfunction!(
            hello,
            m
        )?,
    )?;

    Ok(())
}
