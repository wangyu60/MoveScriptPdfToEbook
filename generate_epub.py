import os
import sys
from ebooklib import epub
from bs4 import BeautifulSoup

BUILD_DIR = "build"

def epub_output_path(html_file):
    normalized_html = os.path.normpath(html_file)
    base_name = os.path.splitext(normalized_html)[0]
    build_normalized = os.path.normpath(BUILD_DIR)
    if os.path.isabs(html_file) or normalized_html == build_normalized or normalized_html.startswith(build_normalized + os.sep):
        return f"{base_name}.epub"
    return os.path.normpath(os.path.join(BUILD_DIR, f"{base_name}.epub"))


def convert_to_epub(html_file, title=None, cover_image=None, author="Unknown"):
    """
    Convert HTML file to EPUB format using the same base name.
    
    Args:
        html_file: Path to HTML file
        title: Optional book title. If None, extracted from HTML <title> tag.
        cover_image: Optional path to a cover image (JPEG/PNG).
        author: Author name to embed in EPUB metadata.
    """
    # Generate output EPUB filename
    epub_file = epub_output_path(html_file)
    os.makedirs(os.path.dirname(epub_file), exist_ok=True)
    
    # Resolve title: use provided value or fall back to HTML <title> tag
    if title is None:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else 'Screenplay'
    
    create_epub(html_file, "styles.css", epub_file, title, author=author, cover_image=cover_image)
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

    html_dir = os.path.dirname(os.path.abspath(html_path))

    # Add HTML content as a chapter
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # The HTML references "styles.css" but inside the EPUB the CSS is at "style/nav.css".
    # Rewrite the link so the EPUB reader resolves it correctly.
    html_content = html_content.replace(
        'href="styles.css"', 'href="style/nav.css"'
    )

    # Embed any local <img src="..."> files referenced by the HTML.
    # This is required for the "scanned half-page renders" EPUB.
    soup_for_imgs = BeautifulSoup(html_content, 'html.parser')
    img_srcs = []
    for img in soup_for_imgs.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        if src.startswith('data:'):
            continue
        img_srcs.append(src)

    unique_img_srcs = []
    seen = set()
    for src in img_srcs:
        if src in seen:
            continue
        seen.add(src)
        unique_img_srcs.append(src)

    def media_type_for_ext(ext):
        ext = ext.lower()
        if ext in ('.jpg', '.jpeg'):
            return 'image/jpeg'
        if ext in ('.png',):
            return 'image/png'
        return 'application/octet-stream'

    for i, src in enumerate(unique_img_srcs):
        abs_img_path = os.path.join(html_dir, src)
        if not os.path.exists(abs_img_path):
            # Don't fail the build if an image path is wrong.
            print(f"Warning: image not found for EPUB embedding: {src}")
            continue

        _, ext = os.path.splitext(src)
        media_type = media_type_for_ext(ext)
        with open(abs_img_path, 'rb') as f:
            img_bytes = f.read()

        # Keep the same relative path in the EPUB so <img src="..."> continues to work.
        img_item = epub.EpubItem(
            uid=f"img_{i}",
            file_name=src,
            media_type=media_type,
            content=img_bytes
        )
        book.add_item(img_item)
    
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
