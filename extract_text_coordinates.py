import fitz
import json

def extract_text_with_coordinates(pdf_path, page_num, output_path, filter_spaces=True, y0_tolerance=1.0):
    """
    Extract text with positional data from a specific page of a PDF.
    
    PyMuPDF Structure:
    - Block: A paragraph or distinct text region (can contain multiple lines)
    - Line: A single line within a block
    - Span: A text segment within a line (for different formatting/fonts)
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to extract (0-indexed)
        output_path: Path to save the output file
        filter_spaces: If True, ignore spans containing only whitespace
        y0_tolerance: Tolerance for grouping spans with similar y0 (horizontal lines)
    """
    doc = fitz.open(pdf_path)
    
    # Check if page exists
    if page_num >= len(doc):
        print(f"Error: Page {page_num} does not exist. PDF has {len(doc)} pages.")
        doc.close()
        return
    
    page = doc[page_num]
    blocks = page.get_text("dict")["blocks"]
    
    extracted_data = []
    space_spans_skipped = 0
    
    for block_idx, block in enumerate(blocks):
        if "lines" in block:
            # Group lines by y0 coordinate to detect spaced-out characters
            lines_by_y0 = {}
            line_order = []  # Track order of first appearance for each y0
            
            for line_idx, line in enumerate(block["lines"]):
                for span_idx, span in enumerate(line["spans"]):
                    text = span["text"]
                    
                    # Filter out space-only spans if requested
                    if filter_spaces and not text.strip():
                        space_spans_skipped += 1
                        continue
                    
                    bbox = span["bbox"]  # (x0, y0, x1, y1)
                    y0 = bbox[1]
                    
                    # Find if this y0 matches an existing group (within tolerance)
                    matched_y0 = None
                    for existing_y0 in lines_by_y0:
                        if abs(y0 - existing_y0) < y0_tolerance:
                            matched_y0 = existing_y0
                            break
                    
                    if matched_y0 is None:
                        matched_y0 = y0
                        line_order.append(matched_y0)
                        lines_by_y0[matched_y0] = []
                    
                    font_size = span["size"]
                    font_name = span.get("font", "unknown")
                    
                    # Store the extracted data
                    span_data = {
                        "block": block_idx,
                        "line": line_idx,
                        "span": span_idx,
                        "text": text,
                        "bbox": {
                            "x0": bbox[0],
                            "y0": bbox[1],
                            "x1": bbox[2],
                            "y1": bbox[3]
                        },
                        "font_size": font_size,
                        "font_name": font_name
                    }
                    lines_by_y0[matched_y0].append(span_data)
            
            # Now flatten the grouped lines, assigning new logical line numbers
            logical_line_idx = 0
            for y0 in line_order:
                for span_data in lines_by_y0[y0]:
                    span_data["line"] = logical_line_idx
                    extracted_data.append(span_data)
                logical_line_idx += 1
    
    doc.close()
    
    # Save to output file (JSON format for easy review)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "page_number": page_num,
            "total_spans": len(extracted_data),
            "spans": extracted_data,
            "space_spans_skipped": space_spans_skipped if filter_spaces else 0
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(extracted_data)} text spans from page {page_num}")
    if filter_spaces and space_spans_skipped > 0:
        print(f"Skipped {space_spans_skipped} space-only spans")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python extract_text_coordinates.py <pdf_file> <page_num>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    page_num = int(sys.argv[2])
    output_file = "temp_extracted_coordinates.json"
    
    extract_text_with_coordinates(pdf_file, page_num, output_file)
