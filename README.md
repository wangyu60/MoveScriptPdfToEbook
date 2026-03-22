# PDF to Screenplay Converter

A Python-based tool that converts PDF screenplay files (including Final Draft exports) into properly formatted HTML and EPUB e-books, preserving screenplay structure and formatting.

## Technical Design

### Architecture Overview

The project follows a multi-stage pipeline architecture:

1. **Text Extraction** — Extract text with coordinate information from every page of the PDF
2. **Element Classification** — Analyse coordinates to identify screenplay elements
3. **HTML Generation** — Convert classified elements to formatted HTML
4. **EPUB Creation** — Package HTML into EPUB with metadata, cover image, and embedded CSS

### Core Components

#### 1. Text Extraction (`extract_text_coordinates.py`)
- Uses PyMuPDF to extract text with precise coordinate information
- Preserves font information (name, size, style)
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
- Detects screenplay transitions (`CUT TO:`, `DISSOLVE TO:`, `FADE TO:`) and classifies them as `transition_right`
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
- Renders page 0 as a cover image (250 DPI JPEG)
- Auto-detects author name from the cover page by finding the line after "Written by" / "Screenplay by" / "Adaptation by" etc.
- Derives title from the PDF filename
- Processes all pages from page 1 onwards (page 0 is the cover)
- Collects all classified elements and converts them to a single HTML + EPUB output

### File Structure

```
├── process_file.py                # Main pipeline orchestrator
├── extract_text_coordinates.py    # PDF → coordinate JSON
├── analyze_screenplay_elements.py # Coordinate JSON → classified JSON
├── convert_to_html.py             # Classified JSON → HTML
├── generate_epub.py               # HTML → EPUB
├── styles.css                     # Screenplay formatting styles
├── Intermediates/                 # Per-page intermediate files
└── README.md
```

## Usage

### Prerequisites

```bash
pip install PyMuPDF ebooklib beautifulsoup4
```

### Process Entire PDF

```bash
python process_file.py screenplay.pdf
```

Outputs:
- `screenplay.html` — Formatted HTML version
- `screenplay.epub` — EPUB e-book (with cover image, title, and author)

### Process Single Page (for debugging)

```bash
python process_file.py screenplay.pdf 5
```

Outputs:
- `temp_screenplay_pg5.html`
- `temp_screenplay_pg5.epub`

### Individual Components

```bash
# Step 1 — Extract coordinates from a specific page (0-indexed)
python extract_text_coordinates.py <pdf_file> <page_num>
# Output: temp_extracted_coordinates.json

# Step 2 — Classify elements from the coordinate JSON
python analyze_screenplay_elements.py
# Output: temp_classified_elements.json

# Step 3 — Convert to HTML
python convert_to_html.py
# Output: temp_screenplay.html
```

## Screenplay Element Classification

The tool automatically identifies and formats:

| Element | CSS Class | Description |
|---|---|---|
| Scene Heading | `scene-heading` | Uppercase location/time indicators |
| Action | `action` | Narrative descriptions and stage directions |
| Character Name | `character-name-group` | Speaker identification (centered, uppercase) |
| Parenthetical | `parenthetical` | Stage directions within dialogue (italic) |
| Dialogue | `dialogue` | Character speech (indented) |
| Transition | `transition-right` | CUT TO:, DISSOLVE TO:, FADE TO: (right-aligned) |

## Output Formats

### HTML
- Semantic markup with CSS classes
- Preserved font formatting (bold/italic)
- Proper indentation and spacing
- Linked `styles.css` — open in any browser and press F5 to preview changes instantly

### EPUB
- Valid EPUB 3.0 format
- Embedded CSS styling
- Cover image from page 0 of the PDF (250 DPI)
- Title from PDF filename; author auto-detected from cover page text

## Configuration

Edit `styles.css` to customise:
- Font families and sizes
- Margins and indentation
- Line spacing
- Character name positioning

## File Management

- Intermediate JSON files stored in `Intermediates/` folder
- Temporary files automatically replaced on re-run
- Git ignores output files (`*.html`, `*.pdf`, `*.epub`, `temp_*`)