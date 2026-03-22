# PDF to Screenplay Converter

A Python-based tool that converts PDF screenplay files into properly formatted HTML and EPUB formats, preserving screenplay structure and formatting.

> **Coming back?** See [TODO.md](TODO.md) for your next steps and reminders.

## Technical Design

### Architecture Overview

The project follows a multi-stage pipeline architecture:

1. **Text Extraction** - Extract text with coordinate information from PDF
2. **Element Classification** - Analyze coordinates to identify screenplay elements
3. **HTML Generation** - Convert classified elements to formatted HTML
4. **EPUB Creation** - Package HTML into EPUB format

### Core Components

#### 1. Text Extraction (`extract_text_coordinates.py`)
- Uses PyMuPDF to extract text with precise coordinate information
- Preserves font information (name, size, style)
- Groups text spans by blocks and lines

#### 2. Element Analysis (`analyze_screenplay_elements.py`)
- Classifies text based on x-coordinate positioning:
  - `x0 ≈ 93`: Scene headings and action descriptions
  - `x0 ≈ 165`: Dialogue text
  - `x0 ≥ 200`: Character names and parentheticals
- Uses font information to distinguish:
  - Normal font → Character names
  - Italic font → Parentheticals
  - Bold font → Emphasized text
- Groups consecutive lines with minimal vertical spacing

#### 3. HTML Conversion (`convert_to_html.py`)
- Generates semantic HTML with proper CSS classes
- Preserves font formatting (bold, italic)
- Groups character names and parentheticals with minimal line spacing
- Uses `styles.css` for screenplay-specific formatting

#### 4. EPUB Generation (`generate_epub.py`)
- Creates valid EPUB files using ebooklib
- Links CSS for proper formatting preservation
- Extracts title from HTML metadata

### File Structure

```
├── process_file.py          # Main pipeline orchestrator
├── extract_text_coordinates.py
├── analyze_screenplay_elements.py
├── convert_to_html.py
├── generate_epub.py
├── styles.css              # Screenplay formatting styles
├── Intermediates/          # Temporary processing files
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
- `screenplay.html` - Formatted HTML version
- `screenplay.epub` - EPUB e-book format

### Process Single Page

```bash
python process_file.py screenplay.pdf 5
```

Outputs:
- `temp_screenplay_pg5.html`
- `temp_screenplay_pg5.epub`

### Individual Components

Each component can be run independently:

```bash
# Extract coordinates (specify PDF and page number to test)
python extract_text_coordinates.py <pdf_file> <page_num>

# Analyze coordinates and classify screenplay elements
python analyze_screenplay_elements.py
# Or: python analyze_coordinates.py
```

**Usage notes:**

1. **`extract_text_coordinates.py`** — Extracts text with coordinates from the PDF script file. Specify the page number (0-based) to test a single page. Output: `temp_extracted_coordinates.json`.

2. **`analyze_coordinates.py`** / **`analyze_screenplay_elements.py`** — Analyze the coordinate JSON and classify screenplay elements (scene headings, action, dialogue, character names, parentheticals).

## Screenplay Element Classification

The tool automatically identifies and formats:

- **Scene Headings**: Uppercase location/time indicators
- **Action**: Narrative descriptions and stage directions
- **Character Names**: Speaker identification (centered, uppercase)
- **Dialogue**: Character speech (indented)
- **Parentheticals**: Stage directions within dialogue (italic, centered)

## Output Formats

### HTML Features
- Semantic markup with CSS classes
- Preserved font formatting (bold/italic)
- Proper indentation and spacing
- Responsive design

### EPUB Features
- Valid EPUB 3.0 format
- Embedded CSS styling
- Proper metadata
- Compatible with e-readers

## Configuration

Edit `styles.css` to customize:
- Font families and sizes
- Margins and indentation
- Line spacing
- Character name positioning

## File Management

- Intermediate JSON files stored in `Intermediates/` folder
- Temporary files automatically replaced on re-run
- Git ignores output files (*.html, *.pdf, *.epub, temp_*)