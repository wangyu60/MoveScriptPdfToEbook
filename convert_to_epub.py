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
    
    # Read HTML content
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract title from HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    title_tag = soup.find('title')
    title = title_tag.get_text() if title_tag else 'Screenplay'
    
    # Read CSS content
    css_file = 'styles.css'
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
    else:
        css_content = '/* No CSS file found */'
    
    # Create EPUB book
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')
    
    # Add CSS
    style = epub.EpubItem(
        uid="style",
        file_name="style/screenplay.css",
        media_type="text/css",
        content=css_content
    )
    book.add_item(style)
    
    # Add chapter
    chapter = epub.EpubHtml(
        title='Script',
        file_name='script.xhtml',
        content=html_content
    )
    chapter.add_item(style)
    book.add_item(chapter)
    
    # Define spine
    book.spine = ['nav', chapter]
    
    # Write EPUB
    epub.write_epub(epub_file, book)
    
    print(f"EPUB created: {epub_file}")
    return epub_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_to_epub.py <html_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    convert_to_epub(html_file)