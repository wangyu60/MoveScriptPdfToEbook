import os
import sys
from ebooklib import epub
from bs4 import BeautifulSoup

def convert_to_epub(html_file):
    """
    Convert HTML file to EPUB format using the same base name.
    
    Args:
        html_file: Path to HTML file
    """
    # Generate output EPUB filename
    base_name = os.path.splitext(html_file)[0]
    epub_file = f"{base_name}.epub"
    
    # Extract title from HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    title_tag = soup.find('title')
    title = title_tag.get_text() if title_tag else 'Screenplay'
    
    create_epub(html_file, "styles.css", epub_file, title)
    return epub_file

def create_epub(html_path, css_path, output_epub_path, title="Screenplay", author="Unknown"):
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f'screenplay-{hash(title)}')
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    # Add CSS file
    if os.path.exists(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            style_content = f.read()
    else:
        style_content = '/* No CSS file found */'
    
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style_content)
    book.add_item(nav_css)

    # Add HTML content as a chapter
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    c1 = epub.EpubHtml(title='Movie Script', file_name='chap_01.xhtml', lang='en')
    c1.content = html_content
    c1.add_item(nav_css)  # Link CSS to the chapter
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
    if len(sys.argv) < 2:
        print("Usage: python generate_epub.py <html_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    convert_to_epub(html_file)
