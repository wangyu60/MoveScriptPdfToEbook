"""Regenerate HTML and EPUB from already extracted coordinate JSON files."""
import sys
import os
import json
import glob
import re

BUILD_DIR = "build"

def ensure_build_path(path):
    if os.path.isabs(path):
        return os.path.normpath(path)
    normalized = os.path.normpath(path)
    build_normalized = os.path.normpath(BUILD_DIR)
    if normalized == build_normalized or normalized.startswith(build_normalized + os.sep):
        return normalized
    return os.path.normpath(os.path.join(BUILD_DIR, normalized))


def regenerate(pdf_file=None, output_html_file=None):
    os.makedirs("Intermediates", exist_ok=True)
    
    # If no pdf file specified, try to find one to determine title/author
    if not pdf_file:
        pdfs = glob.glob("*.pdf")
        if pdfs:
            pdf_file = pdfs[0]
            
    title = "Unknown Screenplay"
    author = "Unknown"
    cover_path = "Intermediates/cover.jpg"
    
    if pdf_file and os.path.exists(pdf_file):
        title = os.path.splitext(os.path.basename(pdf_file))[0]
        if not output_html_file:
            output_html_file = f"{title}.html"
            
        try:
            import process_file
            author = process_file.extract_author_from_cover(pdf_file)
        except Exception as e:
            print(f"Could not extract author: {e}")
    else:
        if not output_html_file:
            if title != "Unknown Screenplay":
                output_html_file = f"{title}.html"
            else:
                output_html_file = "rebuilt_screenplay.html"
    
    output_html_file = ensure_build_path(output_html_file)
    os.makedirs(os.path.dirname(output_html_file), exist_ok=True)
    
    # Find all coordinate files in Intermediates folder
    coord_files = glob.glob("Intermediates/*_coordinates.json")
    
    # We need to sort them properly (e.g. temp_page_10 comes before temp_page_100)
    def extract_page_num(path):
        m = re.search(r'_page_(\d+)_', path)
        if m:
            return int(m.group(1))
        # fallback for single-page testing (temp_screenplay_pg1_coordinates.json)
        m = re.search(r'_pg(\d+)_', path)
        if m:
            return int(m.group(1))
        return 0
        
    coord_files.sort(key=extract_page_num)
    
    if not coord_files:
        print("No coordinate JSON files found in Intermediates/ folder.")
        print("Please run process_file.py at least once to generate coordinate files.")
        return
        
    print(f"Found {len(coord_files)} coordinate files. Re-analyzing elements...")
    
    all_elements = []
    import analyze_screenplay_elements
    import convert_to_html
    import generate_epub
    
    for c_file in coord_files:
        page_num = extract_page_num(c_file)
        base = os.path.basename(c_file).replace("_coordinates.json", "")
        classified_file = f"Intermediates/{base}_classified.json"
        
        print(f"Analyzing {c_file} -> {classified_file}")
        analyze_screenplay_elements.analyze_screenplay_elements(c_file, classified_file)
        
        with open(classified_file, 'r', encoding='utf-8') as f:
            page_data = json.load(f)
            elements = page_data.get("elements", [])
            if elements:
                all_elements.extend(elements)
                
    print(f"\n=== Converting {len(all_elements)} elements to HTML ===")
    
    combined_data = {
        "page_number": "all",
        "total_elements": len(all_elements),
        "elements": all_elements
    }
    
    combined_file = "Intermediates/temp_all_classified.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
    convert_to_html.convert_to_html(combined_file, output_html_file)
    
    if os.path.exists(cover_path):
        generate_epub.convert_to_epub(output_html_file, title=title, cover_image=cover_path, author=author)
    else:
        generate_epub.convert_to_epub(output_html_file, title=title, author=author)
        
    print(f"\n=== Complete! Regenerated {output_html_file} and {os.path.splitext(output_html_file)[0]}.epub ===")

if __name__ == "__main__":
    print("Regenerating HTML and EPUB from cached JSON files...")
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else None
    output_html = sys.argv[2] if len(sys.argv) > 2 else None
    regenerate(pdf_file, output_html)
