# PDF to Screenplay Converter

A Python-based tool that converts PDF screenplay files (including Final Draft exports and scanned image PDFs) into properly formatted HTML and EPUB e-books, preserving screenplay structure and formatting.

## Recent Updates

### ffc07be: Enhance EPUB and HTML generation pipeline

- Introduced a new function `epub_output_path` in `generate_epub.py` to determine the output path for EPUB files based on the input HTML file.
- Improved image embedding in EPUB by adding support for local images referenced in HTML, ensuring they are included in the generated EPUB.
- Added a new `regenerate_from_coordinates.py` script to allow regeneration of HTML and EPUB from existing coordinate JSON files.
- Implemented interactive crop region selection for OCR processing in `select_crop_region.py`, allowing users to define specific areas of a PDF page for text extraction.
- Enhanced `process_file.py` to support OCR mode selection and crop region handling, improving the flexibility of PDF processing.
- Added parallel page processing to `process_file.py` with `--workers N`, and added `--no-parallel` to force sequential execution when needed.
- Extended screenplay transition detection in `analyze_screenplay_elements.py` to recognize `CUT TO BLACK:` and `FADE OUT:`, and added logic to skip top-of-page header elements.
- Updated `process_html.py` to ensure output paths are correctly managed and directories are created as needed.
- Added CSS styles for page breaks and image handling in `styles.css` to improve formatting in generated documents.
- Refactored code for better organization and maintainability across multiple modules.

## Technical Design

### Architecture Overview

The project follows a multi-stage pipeline architecture:

1. **Text Extraction** — Extract text with coordinate information from every page of the PDF using either standard text extraction or OCR for scanned documents
2. **Element Classification** — Analyse coordinates to identify screenplay elements
3. **HTML Generation** — Convert classified elements to formatted HTML
4. **EPUB Creation** — Package HTML into EPUB with metadata, cover image, and embedded CSS

### Core Components

#### 1. Text Extraction (`extract_text_coordinates.py` / `extract_text_ocr.py`)
- Standard extraction uses PyMuPDF to extract text with precise coordinate information
- OCR extraction uses Tesseract OCR for scanned image PDFs
- Preserves font information (name, size, style) where available
- Groups text spans by blocks and lines
- Filters out whitespace-only spans

#### 2. Element Analysis (`analyze_screenplay_elements.py`)
- Filters scene-number spans (e.g. `1`, `20`, `A8`, `2.2`, `A2.2`) **at the span level** before grouping, so they never contaminate the concatenated line text or `x0` classification
- Classifies text based on x-coordinate positioning:
  - `x0 ≈ 100`: Scene headings (uppercase, ≤ 5 words) and action descriptions
  - `x0 ≈ 170`: Dialogue text
  - `x0 ≥ 200`: Character names and parentheticals
  - Far-right (`x0 ≥ 450`): Page numbers — skipped
- Uses font information to distinguish character names (normal) from parentheticals (italic)
- Detects screenplay transitions (`CUT TO:`, `DISSOLVE TO:`, `FADE TO:`, `CUT TO BLACK:`, `FADE OUT:`) and classifies them as `transition_right`
- Skips top-of-page header elements such as revision codes and page headers before classifying page content
- Groups consecutive lines with minimal vertical spacing into single elements

#### 3. HTML Conversion (`convert_to_html.py`)
- Generates semantic HTML with proper CSS classes
- Preserves font formatting (bold, italic) from span data
- Groups character names and parentheticals with minimal line spacing
- Links `styles.css` for screenplay-specific formatting

#### 4. EPUB Generation (`generate_epub.py`)
- Creates valid EPUB files using ebooklib
- Embeds CSS directly into the EPUB package
- Supports cover image, title, and author metadata

#### 5. Main Orchestrator (`process_file.py`)
- Auto-detects scanned vs. native PDFs and selects appropriate extraction method
- Renders page 0 as a cover image (250-300 DPI JPEG)
- Auto-detects author name from the cover page by finding the line after "Written by" / "Screenplay by" / "Adaptation by" etc.
- Derives title from the PDF filename
- Processes all pages from page 1 onwards (page 0 is the cover)
- Supports OCR mode selection and crop region handling for scanned documents
- Collects all classified elements and converts them to a single HTML + EPUB output

### File Structure

```
├── process_file.py                # Main pipeline orchestrator with OCR support
├── extract_text_coordinates.py    # Standard text extraction with coordinates
├── extract_text_ocr.py            # OCR text extraction for scanned PDFs
├── analyze_screenplay_elements.py # Coordinate JSON → classified JSON
├── convert_to_html.py             # Classified JSON → HTML
├── generate_epub.py               # HTML → EPUB with image embedding
├── regenerate_from_coordinates.py # Rebuild HTML/EPUB from cached coordinates
├── select_crop_region.py          # Interactive crop region selection for OCR
├── styles.css                     # Screenplay formatting styles
├── Intermediates/                 # Per-page intermediate files and crop selections
├── build/                         # Output directory for HTML and EPUB files
└── README.md
```

## Usage

### Prerequisites

```bash
pip install PyMuPDF ebooklib beautifulsoup4 pillow pytesseract opencv-python
```

**Note:** For OCR functionality, you also need to install Tesseract OCR:
- Windows: Download from [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

### Command Line Options

```
python process_file.py <pdf_file> [page_num] [--ocr MODE] [--select-crop] [--crop-json FILE] [--workers N] [--no-parallel]

Arguments:
  pdf_file      Path to the PDF file
  page_num      Optional: Process a single page (0-indexed). If omitted, processes entire document.

Options:
  --ocr MODE    OCR extraction mode:
                - auto (default): Auto-detect scanned vs native PDFs
                - force: Force OCR extraction for all pages
                - skip: Skip OCR, use native text extraction only
  --select-crop Interactively select crop region for OCR (excludes page numbers, dates, etc.)
  --crop-json FILE Load crop selection from JSON file (skip interactive selection)
  --workers N  Number of worker processes to use for full-document processing
  --no-parallel Disable parallel page processing and run sequentially
```

### Basic Usage

#### Process Entire PDF (Auto-detect OCR)

```bash
python process_file.py screenplay.pdf
```

#### Process Entire PDF with Parallel Workers

```bash
python process_file.py screenplay.pdf --workers 6
```

This uses up to 6 worker processes to extract and classify pages concurrently.

#### Process Entire PDF Sequentially (disable parallelism)

```bash
python process_file.py screenplay.pdf --no-parallel
```

Outputs:
- `build/screenplay.html` — Formatted HTML version
- `build/screenplay.epub` — EPUB e-book (with cover image, title, and author)

### Performance Tips

- Use `--workers N` when processing large PDFs on a multi-core machine to parallelize page extraction and classification.
- For small PDFs, low-memory environments, or when debugging, use `--no-parallel` to avoid process overhead and keep execution sequential.
- If you notice high CPU but low I/O, increasing `N` may speed up processing; if you see memory pressure, lower `N` or use `--no-parallel`.

#### Process Single Page (for debugging)

```bash
python process_file.py screenplay.pdf 5
```

Outputs:
- `build/temp_screenplay_pg5.html`
- `build/temp_screenplay_pg5.epub`

### OCR Usage for Scanned PDFs

#### Auto-detect Scanned PDFs

```bash
python process_file.py scanned_screenplay.pdf
```

The tool automatically detects if the PDF contains scanned images and switches to OCR mode.

#### Force OCR Mode

```bash
python process_file.py screenplay.pdf --ocr force
```

Use this for PDFs with mixed content or when auto-detection fails.

#### Skip OCR (Native Text Only)

```bash
python process_file.py native_screenplay.pdf --ocr skip
```

Forces native text extraction even for scanned-looking PDFs.

### Crop Region Selection for OCR

For scanned PDFs with headers, footers, or page numbers that interfere with text extraction:

#### Interactive Crop Selection

```bash
python process_file.py scanned.pdf --select-crop
```

This opens an interactive window where you can:
- Click and drag to select the text region
- Press Enter to confirm
- Press R to reselect
- Press Q to cancel

The crop selection is saved to `Intermediates/scanned_crop.json` for reuse.

#### Reuse Saved Crop Selection

```bash
python process_file.py scanned.pdf --crop-json Intermediates/scanned_crop.json
```

### Regenerate from Cached Coordinates

If you have already extracted coordinates and want to re-run analysis/HTML generation:

```bash
python regenerate_from_coordinates.py [pdf_file] [output_html]
```

Arguments:
- `pdf_file`: Optional PDF file for title/author extraction
- `output_html`: Optional output HTML filename

Example:
```bash
python regenerate_from_coordinates.py screenplay.pdf rebuilt.html
```

This re-analyzes all coordinate JSON files in `Intermediates/` and generates fresh HTML/EPUB.

## Screenplay Element Classification

The tool automatically identifies and formats:

| Element | CSS Class | Description |
|---|---|---|
| Scene Heading | `scene-heading` | Uppercase location/time indicators |
| Action | `action` | Narrative descriptions and stage directions |
| Character Name | `character-name-group` | Speaker identification (centered, uppercase) |
| Parenthetical | `parenthetical` | Stage directions within dialogue (italic) |
| Dialogue | `dialogue` | Character speech (indented) |
| Transition | `transition-right` | CUT TO:, DISSOLVE TO:, FADE TO:, CUT TO BLACK:, FADE OUT: (right-aligned) |

## Output Formats

### HTML
- Semantic markup with CSS classes
- Preserved font formatting (bold/italic)
- Proper indentation and spacing
- Linked `styles.css` — open in any browser and press F5 to preview changes instantly

### EPUB
- Valid EPUB 3.0 format
- Embedded CSS styling
- Cover image from page 0 of the PDF (250-300 DPI)
- Title from PDF filename; author auto-detected from cover page text
- Supports embedded images referenced in HTML

## Configuration

Edit `styles.css` to customise:
- Font families and sizes
- Margins and indentation
- Line spacing
- Character name positioning

## File Management

- Intermediate JSON files and crop selections stored in `Intermediates/` folder
- Final outputs saved to `build/` directory
- Temporary files automatically replaced on re-run
- Git ignores output files (`*.html`, `*.pdf`, `*.epub`, `temp_*`)