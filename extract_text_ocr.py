import fitz
import sys
from PIL import Image
import pytesseract
import os
import json

# Set tesseract path explicitly in case it hasn't been added to PATH yet
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def extract_text_ocr(pdf_path, page_num, output_path=None, clip_rect=None, page_number_override=None):
    """
    Extract text using OCR by first converting the PDF page to a high-res image.
    Extracts coordinates and scales them to PyMuPDF standard (72 DPI).
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        output_path: Path to save the output JSON
        clip_rect: Optional fitz.Rect to crop the page before OCR
        page_number_override: Optional override for the page number in output
    """
    print(f"Opening {pdf_path} (page {page_num}) for OCR extraction...")
    if clip_rect:
        print(f"Using crop region: ({clip_rect.x0:.1f}, {clip_rect.y0:.1f}) to ({clip_rect.x1:.1f}, {clip_rect.y1:.1f})")
    doc = None
    try:
        doc = fitz.open(pdf_path)

        if page_num >= len(doc):
            print(f"Error: Page {page_num} does not exist.")
            return

        page = doc[page_num]

        # Render page to an image
        DPI = 400
        print(f"Rendering page to image at {DPI} DPI...")
        pix = page.get_pixmap(dpi=DPI, clip=clip_rect)
        x_offset = clip_rect.x0 if clip_rect is not None else 0.0
        y_offset = clip_rect.y0 if clip_rect is not None else 0.0

        # Convert PyMuPDF pixmap to PIL Image
        if pix.alpha:
            img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples).convert("RGB")
        else:
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Pre-process image to improve OCR accuracy
        from PIL import ImageFilter, ImageEnhance
        img = img.convert('L')
        # Increase contrast to separate text from background
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        # Apply median filter to remove grit/salt-and-pepper noise
        img = img.filter(ImageFilter.MedianFilter(size=3))
        # Binarize with a balanced threshold
        img = img.point(lambda p: 255 if p > 160 else 0)

        # Perform OCR with Data
        print("Running OCR with Tesseract (extracting coordinates)...")
        try:
            custom_config = r'--oem 1 --psm 4'
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=custom_config)
        except Exception as e:
            print(f"OCR Failed. Make sure Tesseract is installed and in your PATH. Error: {e}")
            return

        # Group words by block and line
        lines = {}
        for i in range(len(data['text'])):
            text = data['text'][i]

            if not text.strip():
                continue

            # Clean up typographic characters introduced by OCR or the original font
            text = text.replace('’', "'").replace('‘', "'")
            text = text.replace('”', '"').replace('“', '"')
            text = text.replace('—', '--')

            # Clean up consistent Tesseract pixel-hallucinations
            import re
            typo_map = {
                r'\bhin\b': 'him',
                r'\bghe\b': 'the',
                r'\bche\b': 'the',
                r'\bplaylng\b': 'playing',
                r'\bI\'n\b': "I'm",
                r'\bI\’n\b': "I'm"
            }
            for wrong, right in typo_map.items():
                text = re.sub(wrong, right, text)

            block_num = data['block_num'][i]
            par_num = data['par_num'][i]
            line_num = data['line_num'][i]
            key = (block_num, par_num, line_num)

            if key not in lines:
                lines[key] = {
                    'text': [],
                    'left': [],
                    'top': [],
                    'width': [],
                    'height': []
                }

            lines[key]['text'].append(text)
            lines[key]['left'].append(data['left'][i])
            lines[key]['top'].append(data['top'][i])
            lines[key]['width'].append(data['width'][i])
            lines[key]['height'].append(data['height'][i])

        # Convert groups to spans, scaling coordinates back to 72 DPI points
        extracted_data = []
        logical_line_idx = 0
        scale = 72.0 / float(DPI)

        for key, line_info in lines.items():
            block_idx = key[0]

            # Merge words into a single line string
            text = " ".join(line_info['text'])

            # Calculate bounding box of the entire line
            x0 = min(line_info['left']) * scale + x_offset
            y0 = min(line_info['top']) * scale + y_offset
            x1 = max([l + w for l, w in zip(line_info['left'], line_info['width'])]) * scale + x_offset
            y1 = max([t + h for t, h in zip(line_info['top'], line_info['height'])]) * scale + y_offset

            # Estimate font size from average height
            avg_height = sum(line_info['height']) / len(line_info['height'])
            font_size = avg_height * scale

            span_data = {
                "block": block_idx,
                "line": logical_line_idx,
                "span": 0,
                "text": text,
                "bbox": {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1
                },
                "font_size": font_size,
                "font_name": "OCR-Font"
            }
            extracted_data.append(span_data)
            logical_line_idx += 1
    except Exception as e:
        print(f"Failed to open PDF: {e}")
        return
    finally:
        if doc is not None:
            doc.close()

    # Save to JSON
    if output_path is None:
        output_path = "temp_ocr_extracted_coordinates.json"
        
    output_data = {
        "page_number": page_num if page_number_override is None else page_number_override,
        "total_spans": len(extracted_data),
        "spans": extracted_data,
        "space_spans_skipped": 0
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Extracted {len(extracted_data)} bounding boxes from page {page_num}.")
    print(f"Output saved to {output_path}")
    
    # Just to show success checking
    if any("UNDERWATER" in s["text"] for s in extracted_data):
        print("\nSuccess: Found 'UNDERWATER' correctly spelled in the data!")

    return extracted_data

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_text_ocr.py <pdf_file> <page_num> [output_file]")
        sys.exit(1)
        
    pdf_file = sys.argv[1]
    page_num = int(sys.argv[2])
    output_file = sys.argv[3] if len(sys.argv) > 3 else "temp_ocr_extracted_coordinates.json"
    
    extract_text_ocr(pdf_file, page_num, output_file)
