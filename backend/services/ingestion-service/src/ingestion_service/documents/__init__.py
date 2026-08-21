from .base import DocumentLimitError, UnsupportedDocumentError

__all__ = [
    "CSVReader",
    "DOCXReader",
    "DocumentLimitError",
    "HTMLReader",
    "ImageReader",
    "JSONReader",
    "PDFReader",
    "PPTXReader",
    "ReaderRegistry",
    "TextReader",
    "UnsupportedDocumentError",
    "XLSXReader",
]


def __getattr__(name: str):
    modules = {
        "CSVReader": ("text", "CSVReader"),
        "DOCXReader": ("docx", "DOCXReader"),
        "HTMLReader": ("text", "HTMLReader"),
        "ImageReader": ("image", "ImageReader"),
        "JSONReader": ("text", "JSONReader"),
        "PDFReader": ("pdf", "PDFReader"),
        "PPTXReader": ("pptx", "PPTXReader"),
        "ReaderRegistry": ("registry", "ReaderRegistry"),
        "TextReader": ("text", "TextReader"),
        "XLSXReader": ("xlsx", "XLSXReader"),
    }
    if name not in modules:
        raise AttributeError(name)
    module_name, attribute = modules[name]
    module = __import__(f"{__name__}.{module_name}", fromlist=[attribute])
    return getattr(module, attribute)
