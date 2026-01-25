from ebooklib import epub
from bs4 import BeautifulSoup

def create_epub(html_path, css_path, output_epub_path, title="True Grit - Movie Script", author="Joel and Ethan Coen"):
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier('true-grit-2010-script')
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    # Add CSS file
    with open(css_path, 'r', encoding='utf-8') as f:
        style_content = f.read()
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style_content)
    book.add_item(nav_css)

    # Add HTML content as a chapter
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    c1 = epub.EpubHtml(title='Movie Script', file_name='chap_01.xhtml', lang='en')
    c1.content = html_content
    book.add_item(c1)

    # Define Table Of Contents
    book.toc = (epub.Link('chap_01.xhtml', 'Movie Script', 'intro'),)

    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine (order of contents)
    book.spine = ['nav', c1]

    # Write the EPUB file
    epub.write_epub(output_epub_path, book, {})
    print(f"EPUB file created successfully at '{output_epub_path}'")

if __name__ == "__main__":
    html_file = "true-grit-2010_processed.html"
    css_file = "styles.css"
    epub_file = "true-grit-2010.epub"
    create_epub(html_file, css_file, epub_file)
