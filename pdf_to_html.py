import fitz  # PyMuPDF

def convert_pdf_to_html(pdf_path, html_path):
    doc = fitz.open(pdf_path)
    html_content = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        html_content += page.get_text("html")

    with open(html_path, 'w', encoding='utf-8') as out_file:
        out_file.write(html_content)
    doc.close()

if __name__ == "__main__":
    pdf_file = "true-grit-2010.pdf"
    html_file = "true-grit-2010.html"
    convert_pdf_to_html(pdf_file, html_file)
    print(f"'{pdf_file}' successfully converted to '{html_file}'")
