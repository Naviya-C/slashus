<h1 align="center"> 📝 Piliwela</h1>

<p align="center">
  <strong>High-performance Sinhala Legacy Font Converter for Python.</strong>
</p>

<p align="center">
Convert FM family legacy Sinhala fonts to modern Unicode while preserving mixed Sinhala and English content.
</p>

---

## ✨ Features

* ⚡ Rust-powered conversion engine
* 🇱🇰 Legacy Sinhala → Unicode conversion
* 📄 PDF font metadata support
* 🔍 Automatic font detection
* 🔤 Preserves English and mixed-language text
* 🐍 Python bindings via PyO3
* 🚀 Designed for AI, NLP, and document processing pipelines

---

## Supported Fonts

[FM family]
* FM Abhaya
* FM Samantha
* FM Emanee

---

# Installation

## From PyPI

```bash
pip install piliwela
```

---

## Development Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/piliwela.git
cd piliwela
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install maturin:

```bash
pip install maturin
```

Build the extension:

```bash
maturin develop
```

---

# Quick Start

## Automatic Conversion

```python
import piliwela

text = piliwela.convert_auto(
    "Y%S ,xld"
)

print(text)
```

Output:

```text
ශ්‍රී ලංකා
```

---

## Conversion Using PDF Font Metadata

```python
import piliwela

text = piliwela.convert_auto_with_metadata(
    "Y%S ,xld",
    "FMAbhaya"
)

print(text)
```

Output:

```text
ශ්‍රී ලංකා
```

---

# API

## `convert_auto(text)`

Automatically detects the legacy font and converts the text.

```python
piliwela.convert_auto(text)
```

Returns:

```python
str
```

---

## `convert_auto_with_metadata(text, font_name)`

Converts text using PDF font metadata.

```python
piliwela.convert_auto_with_metadata(
    text,
    font_name,
)
```

Returns:

```python
str
```

Example:

```python
piliwela.convert_auto_with_metadata(
    "Y%S ,xld",
    "FMAbhaya"
)
```

---

## `version()`

Returns the installed version.

```python
piliwela.version()
```

Example:

```python
'0.1.0'
```

---

## `hello()`

Simple sanity check.

```python
piliwela.hello()
```

Output:

```python
'Hello from Rust!'
```

---

# Why Piliwela?

Many existing Sinhala legacy converters convert every ASCII character indiscriminately, causing English words to become corrupted.

Example:

```text
Input:
Voices from Ancient Y%S ,xld

Output:
Voices from Ancient ශ්‍රී ලංකා
```

Piliwela is designed to preserve mixed-language content while accurately converting legacy Sinhala text.

---

# Example: PDF Processing

```python
import fitz
import piliwela

doc = fitz.open("book.pdf")

for page in doc:
    data = page.get_text("dict")

    for block in data["blocks"]:
        if "lines" not in block:
            continue

        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                font = span["font"]

                converted = (
                    piliwela
                    .convert_auto_with_metadata(
                        text,
                        font,
                    )
                )

                print(converted)
```

---

# Use Cases

* 📚 Digital libraries
* 🤖 RAG pipelines
* 🧠 NLP preprocessing
* 🔎 Search indexing
* 🏛️ Historical document digitization
* 📄 PDF processing pipelines

---

# Roadmap

## v0.1.0

* [x] Metadata-based conversion
* [x] Automatic conversion
* [x] Mixed Sinhala-English support

## Future Releases

* [ ] Better font detection
* [ ] ML-based legacy classification
* [ ] Additional font support
* [ ] OCR integrations
* [ ] LangChain integration helpers

---

# License

MIT License.

See the `LICENSE` file for details.
