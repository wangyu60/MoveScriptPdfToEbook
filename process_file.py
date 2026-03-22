"""Process PDF files through the screenplay analysis pipeline"""

import subprocess
import sys
import os
import json

def process_page(pdf_file, page_num, output_base_name):
    """Process a single page through the full pipeline."""
    
    # Ensure Intermediates folder exists
    os.makedirs("Intermediates", exist_ok=True)
    
    # Step 1: Extract coordinates
    print(f"\n=== Step 1: Extracting coordinates from page {page_num + 1} ===")
    import extract_text_coordinates
    coords_file = f"Intermediates/{output_base_name}_coordinates.json"
    extract_text_coordinates.extract_text_with_coordinates(pdf_file, page_num, coords_file)
    
    # Step 2: Analyze and classify
    print(f"\n=== Step 2: Analyzing and classifying elements ===")
    import analyze_screenplay_elements
    classified_file = f"Intermediates/{output_base_name}_classified.json"
    analyze_screenplay_elements.analyze_screenplay_elements(coords_file, classified_file)
    
    # Step 3: Convert to HTML
    print(f"\n=== Step 3: Converting to HTML ===")
    import convert_to_html
    convert_to_html.convert_to_html(classified_file, f"{output_base_name}.html")
    
    # Step 4: Convert to EPUB
    print(f"\n=== Step 4: Converting to EPUB ===")
    import generate_epub
    generate_epub.convert_to_epub(f"{output_base_name}.html")
    
    print(f"\n=== Complete! Output saved to {output_base_name}.html and {output_base_name}.epub ===")

def extract_author_from_cover(pdf_file):
    """Extract author name from the cover page (page 0).

    Looks for a line whose text contains the word 'by' (e.g. 'Written by',
    'Screenplay by', 'Adaptation by') and returns the very next non-empty
    line as the author.  Falls back to 'Unknown' if none is found.
    """
    import fitz
    doc = fitz.open(pdf_file)
    page = doc[0]

    # Collect non-empty lines in reading order (top-to-bottom)
    lines = []
    for block in page.get_text("blocks"):
        block_text = block[4]  # raw text for the whole block
        y0 = block[1]
        for raw_line in block_text.split("\n"):
            text = raw_line.strip()
            if text:
                lines.append((y0, text))

    # Sort by vertical position
    lines.sort(key=lambda x: x[0])
    texts = [t for _, t in lines]

    import re
    by_pattern = re.compile(r'\bby\b', re.IGNORECASE)

    for i, text in enumerate(texts):
        if by_pattern.search(text):
            # Return the next non-empty line
            for candidate in texts[i + 1:]:
                if candidate.strip():
                    author = candidate.strip()
                    print(f"Detected author: '{author}'")
                    doc.close()
                    return author

    doc.close()
    print("Warning: could not detect author from cover page, defaulting to 'Unknown'")
    return "Unknown"


def process_file(pdf_file, output_html_file):
    """Process entire PDF file through the full pipeline."""
    import fitz  # PyMuPDF
    
    # Ensure Intermediates folder exists
    os.makedirs("Intermediates", exist_ok=True)
    
    # Derive title from PDF filename
    title = os.path.splitext(os.path.basename(pdf_file))[0]
    
    # Open document
    doc = fitz.open(pdf_file)
    total_pages = len(doc)
    
    # --- Extract author from cover page before closing the document ---
    author = extract_author_from_cover(pdf_file)

    # --- Render page 0 as cover image ---
    cover_path = "Intermediates/cover.jpg"
    cover_page = doc[0]
    cover_page.get_pixmap(dpi=250).save(cover_path)
    print(f"Cover image saved to: {cover_path}")

    doc.close()
    
    print(f"\n=== Processing entire PDF: {total_pages} pages (screenplay starts page 2) ===")
    
    all_elements = []
    
    # Start from page 1 (index), i.e. the second page — page 0 is the cover
    for page_num in range(1, total_pages):
        print(f"\n--- Processing page {page_num + 1}/{total_pages} ---")
        
        # Step 1: Extract coordinates
        import extract_text_coordinates
        coords_file = f"Intermediates/temp_page_{page_num}_coordinates.json"
        extract_text_coordinates.extract_text_with_coordinates(pdf_file, page_num, coords_file)
        
        # Step 2: Analyze and classify
        import analyze_screenplay_elements
        classified_file = f"Intermediates/temp_page_{page_num}_classified.json"
        analyze_screenplay_elements.analyze_screenplay_elements(coords_file, classified_file)
        
        # Load classified elements and add to collection
        with open(classified_file, 'r', encoding='utf-8') as f:
            page_data = json.load(f)
            all_elements.extend(page_data["elements"])
    
    # Step 3: Convert all elements to HTML
    print(f"\n=== Converting {len(all_elements)} elements to HTML ===")
    
    # Create combined data structure
    combined_data = {
        "page_number": "all",
        "total_elements": len(all_elements),
        "elements": all_elements
    }
    
    # Save combined classified data
    combined_file = "Intermediates/temp_all_classified.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    # Convert to HTML
    import convert_to_html
    convert_to_html.convert_to_html(combined_file, output_html_file)
    
    # Convert to EPUB
    import generate_epub
    generate_epub.convert_to_epub(output_html_file, title=title, cover_image=cover_path, author=author)
    
    print(f"\n=== Complete! Full PDF saved to {output_html_file} and {os.path.splitext(output_html_file)[0]}.epub ===")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_file.py <pdf_file> [page_num]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    if len(sys.argv) >= 3:
        # Process single page
        page_num = int(sys.argv[2])
        output_base = f"temp_screenplay_pg{page_num}"
        process_page(pdf_file, page_num, output_base)
    else:
        # Process entire file
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        output_html = f"{base_name}.html"
        process_file(pdf_file, output_html)

