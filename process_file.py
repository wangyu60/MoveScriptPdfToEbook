"""Process PDF files through the screenplay analysis pipeline"""

import subprocess
import sys
import os
import json
import fitz
from PIL import Image
import concurrent.futures

BUILD_DIR = "build"

def ensure_build_path(path):
    if os.path.isabs(path):
        return os.path.normpath(path)
    normalized = os.path.normpath(path)
    build_normalized = os.path.normpath(BUILD_DIR)
    if normalized == build_normalized or normalized.startswith(build_normalized + os.sep):
        return normalized
    return os.path.normpath(os.path.join(BUILD_DIR, normalized))


def ensure_output_dir(output_path):
    dir_path = os.path.dirname(output_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def _rect_to_tuple(rect):
    return (rect.x0, rect.y0, rect.x1, rect.y1) if rect is not None else None


def _tuple_to_rect(rect_tuple):
    return fitz.Rect(rect_tuple) if rect_tuple is not None else None


def is_scanned_pdf(pdf_file):
    """
    Auto-detect if a PDF is a scanned document (OCR'd) by checking
    the variance of font sizes across the page. OCR text layers 
    have wildly varying font sizes (dozens of unique exact floats) 
    per page, whereas native PDFs have very consistent font sizes.
    """
    import fitz
    try:
        doc = fitz.open(pdf_file)
        page_to_check = 1 if len(doc) > 1 else 0
        page = doc[page_to_check]
        
        unique_sizes = set()
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"].strip()
                        if text:
                            unique_sizes.add(round(s["size"], 2))
                            
        # If there are dozens of unique font sizes, it's OCR generated.
        if len(unique_sizes) > 15:
            doc.close()
            return True
            
        doc.close()
    except Exception as e:
        print(f"Error during auto-detect: {e}")
        
    return False

def process_page(pdf_file, page_num, output_base_name, use_ocr=False, crop_rect=None):
    """Process a single page through the full pipeline."""
    
    os.makedirs("Intermediates", exist_ok=True)
    
    print(f"\n=== Step 1: Extracting coordinates from page {page_num + 1} ===")
    coords_file = f"Intermediates/{output_base_name}_coordinates.json"
    
    if use_ocr:
        import extract_text_ocr
        extract_text_ocr.extract_text_ocr(pdf_file, page_num, coords_file, clip_rect=crop_rect)
    else:
        import extract_text_coordinates
        extract_text_coordinates.extract_text_with_coordinates(pdf_file, page_num, coords_file)

    if not os.path.exists(coords_file):
        print(f"Extraction failed for page {page_num + 1}; skipping downstream steps.")
        return
    
    print(f"\n=== Step 2: Analyzing and classifying elements ===")
    import analyze_screenplay_elements
    classified_file = f"Intermediates/{output_base_name}_classified.json"
    analyze_screenplay_elements.analyze_screenplay_elements(coords_file, classified_file)
    
    print(f"\n=== Step 3: Converting to HTML ===")
    output_html_file = ensure_build_path(f"{output_base_name}.html")
    ensure_output_dir(output_html_file)
    import convert_to_html
    convert_to_html.convert_to_html(classified_file, output_html_file)
    
    print(f"=== Step 4: Converting to EPUB ===")
    import generate_epub
    generate_epub.convert_to_epub(output_html_file)
    
    print(f"=== Complete! Output saved to {output_html_file} and {os.path.splitext(output_html_file)[0]}.epub ===")

def process_page_for_pool(args):
    page_num, pdf_file, use_ocr, crop_rect_tuple = args
    crop_rect = _tuple_to_rect(crop_rect_tuple)
    os.makedirs("Intermediates", exist_ok=True)

    coords_file = f"Intermediates/temp_page_{page_num}_coordinates.json"
    classified_file = f"Intermediates/temp_page_{page_num}_classified.json"

    if use_ocr:
        import extract_text_ocr
        import analyze_screenplay_elements
        extract_text_ocr.extract_text_ocr(pdf_file, page_num, coords_file, clip_rect=crop_rect)
    else:
        import extract_text_coordinates
        import analyze_screenplay_elements
        extract_text_coordinates.extract_text_with_coordinates(pdf_file, page_num, coords_file)

    if not os.path.exists(coords_file):
        print(f"Extraction failed for page {page_num + 1}; skipping this page.")
        return {"page_number": page_num, "elements": []}

    analyze_screenplay_elements.analyze_screenplay_elements(coords_file, classified_file)

    with open(classified_file, 'r', encoding='utf-8') as f:
        page_data = json.load(f)

    return {"page_number": page_num, "elements": page_data.get("elements", [])}


def extract_author_from_cover(pdf_file):
    """Extract author name from the cover page (page 0)."""
    import fitz
    doc = fitz.open(pdf_file)
    page = doc[0]

    lines = []
    for block in page.get_text("blocks"):
        block_text = block[4]
        y0 = block[1]
        for raw_line in block_text.split("\n"):
            text = raw_line.strip()
            if text:
                lines.append((y0, text))

    lines.sort(key=lambda x: x[0])
    texts = [t for _, t in lines]

    import re
    by_pattern = re.compile(r'\bby\b', re.IGNORECASE)

    for i, text in enumerate(texts):
        if by_pattern.search(text):
            for candidate in texts[i + 1:]:
                if candidate.strip():
                    author = candidate.strip()
                    print(f"Detected author: '{author}'")
                    doc.close()
                    return author

    doc.close()
    print("Warning: could not detect author from cover page, defaulting to 'Unknown'")
    return "Unknown"


def process_file(pdf_file, output_html_file, use_ocr=False, crop_rect=None, max_workers=None):
    """Process entire PDF file through the full pipeline."""
    import fitz  
    
    os.makedirs("Intermediates", exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    output_html_file = ensure_build_path(output_html_file)
    ensure_output_dir(output_html_file)
    
    title = os.path.splitext(os.path.basename(pdf_file))[0]
    
    doc = fitz.open(pdf_file)
    total_pages = len(doc)
    
    author = extract_author_from_cover(pdf_file)

    cover_path = "Intermediates/cover.jpg"
    cover_page = doc[0]

    page_rect = cover_page.rect
    upper_limit = page_rect.y1 * 0.70
    text_blocks = [
        b for b in cover_page.get_text("blocks")
        if b[4].strip() and b[1] < upper_limit
    ]
    if text_blocks:
        x0 = min(b[0] for b in text_blocks)
        y0 = min(b[1] for b in text_blocks)
        x1 = max(b[2] for b in text_blocks)
        y1 = max(b[3] for b in text_blocks)

        pw = (x1 - x0) * 0.10
        ph = (y1 - y0) * 0.10
        clip = fitz.Rect(
            max(0,            x0 - pw),
            max(0,            y0 - ph),
            min(page_rect.x1, x1 + pw),
            min(page_rect.y1, y1 + ph),
        )
        cover_page.get_pixmap(dpi=300, clip=clip).save(cover_path)
    else:
        cover_page.get_pixmap(dpi=250).save(cover_path)

    print(f"Cover image saved to: {cover_path}")
    doc.close()
    doc = fitz.open(pdf_file)
    
    extracted_extractor = "OCR" if use_ocr else "Standard"
    print(f"\n=== Processing entire PDF: {total_pages} pages using {extracted_extractor} extractor===")
    
    all_elements = []
    
    page_args = [
        (page_num, pdf_file, use_ocr, _rect_to_tuple(crop_rect))
        for page_num in range(1, total_pages)
    ]

    if max_workers is None:
        max_workers = os.cpu_count() or 1
    if max_workers < 1:
        max_workers = 1

    if max_workers == 1:
        print("Using sequential page processing (no parallel workers).")
        for page_num in range(1, total_pages):
            result = process_page_for_pool((page_num, pdf_file, use_ocr, _rect_to_tuple(crop_rect)))
            all_elements.extend(result.get("elements", []))
    else:
        print(f"Using up to {max_workers} worker processes for page extraction and classification.")

        results_by_page = {}
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {
                executor.submit(process_page_for_pool, args): args[0]
                for args in page_args
            }

            for future in concurrent.futures.as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    result = future.result()
                except Exception as exc:
                    print(f"Page {page_num + 1} failed in worker process: {exc}")
                    continue
                else:
                    results_by_page[page_num] = result.get("elements", [])

        for page_num in sorted(results_by_page.keys()):
            all_elements.extend(results_by_page[page_num])
    
    print(f"\n=== Converting {len(all_elements)} elements to HTML ===")
    
    combined_data = {
        "page_number": "all",
        "total_elements": len(all_elements),
        "elements": all_elements
    }
    
    combined_file = "Intermediates/temp_all_classified.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    import convert_to_html
    convert_to_html.convert_to_html(combined_file, output_html_file)
    
    import generate_epub
    generate_epub.convert_to_epub(output_html_file, title=title, cover_image=cover_path, author=author)
    
    doc.close()
    print(f"\n=== Complete! Full PDF saved to {output_html_file} and {os.path.splitext(output_html_file)[0]}.epub ===")





if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process a screenplay PDF with optional OCR detection.")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument("page_num", type=int, nargs='?', help="Process a single page (0-indexed). If omitted, processes entire document.")
    parser.add_argument("--ocr", choices=['auto', 'force', 'skip'], default='auto', help="OCR extraction mode (default: auto)")
    parser.add_argument("--select-crop", action="store_true", help="Interactively select crop region for OCR (excludes page numbers, dates, etc.)")
    parser.add_argument("--crop-json", help="Path to crop selection JSON file (skip interactive selection)")
    parser.add_argument("--workers", type=int, help="Number of worker processes to use when processing the full PDF")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel page processing and run sequentially")


    args = parser.parse_args()

    # Handle crop region selection
    crop_rect = None
    if args.select_crop or args.crop_json:
        if not args.ocr or args.ocr == 'skip':
            print("Warning: --select-crop/--crop-json requires OCR mode. Forcing OCR mode.")
            use_ocr = True
        
        if args.crop_json:
            # Load from JSON file
            import select_crop_region
            crop_rect = select_crop_region.load_crop_selection(args.crop_json)
            if crop_rect:
                print(f"Loaded crop region from {args.crop_json}")
            else:
                print(f"Warning: Could not load crop region from {args.crop_json}")
        elif args.select_crop:
            # Interactive selection
            import select_crop_region
            print("Opening interactive crop selector...")
            print("Instructions:")
            print("  - Click and drag to select the OCR region")
            print("  - Press Enter to confirm")
            print("  - Press R to reselect")
            print("  - Press Q to cancel")
            
            # Use specified page number, or default to page 1 for full document processing
            test_page = args.page_num if args.page_num is not None else 1
            crop_rect = select_crop_region.select_crop_region(args.pdf_file, test_page)
            
            if crop_rect:
                # Save selection for reuse
                base_name = os.path.splitext(os.path.basename(args.pdf_file))[0]
                crop_json_path = f"Intermediates/{base_name}_crop.json"
                select_crop_region.save_crop_selection(crop_rect, args.pdf_file, test_page, crop_json_path)
                print(f"Crop selection saved to {crop_json_path}")
                print(f"Use --crop-json {crop_json_path} to reuse this selection")
            else:
                print("Crop selection cancelled. Proceeding without crop region.")

    use_ocr = False
    if args.ocr == 'force':
        use_ocr = True
        print("OCR Mode: FORCED")
    elif args.ocr == 'skip':
        use_ocr = False
        print("OCR Mode: SKIPPED (Native Text Only)")
    else:
        print("OCR Mode: AUTO-DETECTING...")
        use_ocr = is_scanned_pdf(args.pdf_file)
        if use_ocr:
            print(" -> Detected scanned/OCR PDF. Utilizing OCR Extractor.")
        else:
            print(" -> Detected native text PDF. Utilizing Standard Extractor.")

    if args.page_num is not None:
        output_base = f"temp_screenplay_pg{args.page_num}"
        print(f"DEBUG: crop_rect passed to process_page: {crop_rect}")
        process_page(args.pdf_file, args.page_num, output_base, use_ocr=use_ocr, crop_rect=crop_rect)
    else:
        base_name = os.path.splitext(os.path.basename(args.pdf_file))[0]
        output_html = f"{base_name}.html"
        process_file(
            args.pdf_file,
            output_html,
            use_ocr=use_ocr,
            crop_rect=crop_rect,
            max_workers=1 if args.no_parallel else args.workers,
        )
