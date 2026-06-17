from models.text_extract import PageContext

import pdfplumber

def extract_tables_on_page(context: PageContext) -> list[dict]:
    tables = []
    with pdfplumber.open(context.pdf_path) as pdf:
        page = pdf.pages[context.page_number]
        raw_tables = page.extract_tables()
        for i, tbl in enumerate(raw_tables):
            cleaned = [
                [context.converter.convert(cell or "") for cell in row]
                for row in tbl
            ]
            tables.append({
                "table_index_on_page": i,
                "rows": cleaned,
                "num_rows": len(cleaned),
                "num_cols": len(cleaned[0]) if cleaned else 0,
            })
    return tables
