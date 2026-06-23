import pdfplumber

def extract_tables_on_page(context):
    tables = []

    with pdfplumber.open(context.pdf_path) as pdf:
        page = pdf.pages[context.page_number]

        for i, table in enumerate(page.find_tables()):

            cleaned = [
                [context.converter.convert(cell or "")
                 for cell in row]
                for row in table.extract()
            ]

            tables.append({
                "table_index_on_page": i,
                "rows": cleaned,
                "bbox": table.bbox,
                "num_rows": len(cleaned),
                "num_cols": len(cleaned[0]) if cleaned else 0,
            })

    return tables