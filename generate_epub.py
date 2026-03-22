import os
import sys
from ebooklib import epub
from bs4 import BeautifulSoup

def convert_to_epub(html_file, title=None, cover_image=None):
    """
    Convert HTML file to EPUB format using the same base name.
    
    Args:
        html_file: Path to HTML file
        title: Optional book title. If None, extracted from HTML <title> tag.
        cover_image: Optional path to a cover image (JPEG/PNG).
    """
    # Generate output EPUB filename
    base_name = os.path.splitext(html_file)[0]
    epub_file = f"{base_name}.epub"
    
    # Resolve title: use provided value or fall back to HTML <title> tag
    if title is None:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else 'Screenplay'
    
    create_epub(html_file, "styles.css", epub_file, title, cover_image=cover_image)
    return epub_file

def create_epub(html_path, css_path, output_epub_path, title="Screenplay", author="Unknown", cover_image=None):
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f'screenplay-{hash(title)}')
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    # Embed cover image if provided
    if cover_image and os.path.exists(cover_image):
        _, ext = os.path.splitext(cover_image)
        media_type = "image/jpeg" if ext.lower() in (".jpg", ".jpeg") else "image/png"
        with open(cover_image, 'rb') as f:
            cover_bytes = f.read()
        book.set_cover(f"cover{ext}", cover_bytes)
        print(f"Cover image embedded: {cover_image}")

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
    
    # The HTML references "styles.css" but inside the EPUB the CSS is at "style/nav.css".
    # Rewrite the link so the EPUB reader resolves it correctly.
    html_content = html_content.replace(
        'href="styles.css"', 'href="style/nav.css"'
    )
    
    c1 = epub.EpubHtml(title=title, file_name='chap_01.xhtml', lang='en')
    c1.content = html_content
    c1.add_item(nav_css)  # Link CSS to the chapter
    book.add_item(c1)

    # Define Table Of Contents
    book.toc = (epub.Link('chap_01.xhtml', title, 'intro'),)

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
