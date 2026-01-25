import json
from html import escape

def convert_to_html(classified_file, output_html_file):
    """
    Convert classified screenplay elements to HTML format.
    Preserves formatting like italics from font information.
    """
    
    # Load classified elements
    with open(classified_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    html_lines = []
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html>')
    html_lines.append('<head>')
    html_lines.append('  <meta charset="UTF-8">')
    html_lines.append('  <title>True Grit - Movie Script</title>')
    html_lines.append('  <link href="styles.css" rel="stylesheet"/>')
    html_lines.append('</head>')
    html_lines.append('<body>')
    
    # Process each element
    for elem in data["elements"]:
        elem_type = elem.get("type")
        
        if elem_type == "scene_heading":
            # Scene heading: <h3 class="scene-heading">
            text = escape(elem["text"].strip())
            html_lines.append(f'  <h3 class="scene-heading">{text}</h3>')
        
        elif elem_type == "action":
            # Action: <p class="action"> (may have multiple lines)
            if "lines" in elem:
                # Grouped action lines - combine them
                combined_text = " ".join(line["text"].strip() for line in elem["lines"])
                # Preserve formatting from spans
                formatted_text = format_text_with_spans(elem["lines"])
                html_lines.append(f'  <p class="action">{formatted_text}</p>')
            else:
                # Single action line
                formatted_text = format_text_with_spans([elem])
                html_lines.append(f'  <p class="action">{formatted_text}</p>')
        
        elif elem_type == "character_name":
            # Character name: <h4 class="character-name">
            # May be grouped (multiple lines) or single
            if "lines" in elem:
                # Grouped character name lines - combine them
                formatted_text = format_text_with_spans(elem["lines"])
            elif "spans" in elem:
                # Single character name with spans
                formatted_text = format_text_with_spans([elem])
            else:
                # Single character name without spans
                formatted_text = escape(elem["text"].strip())
            html_lines.append(f'  <h4 class="character-name">{formatted_text}</h4>')
        
        elif elem_type == "dialogue":
            # Dialogue: <p class="dialogue"> (may have multiple lines)
            if "lines" in elem:
                # Grouped dialogue lines - combine them
                formatted_text = format_text_with_spans(elem["lines"])
                html_lines.append(f'  <p class="dialogue">{formatted_text}</p>')
            else:
                # Single dialogue line
                formatted_text = format_text_with_spans([elem])
                html_lines.append(f'  <p class="dialogue">{formatted_text}</p>')
        
        elif elem_type == "visual_item":
            # Visual item: treat as action for now
            if "lines" in elem:
                formatted_text = format_text_with_spans(elem["lines"])
            else:
                formatted_text = format_text_with_spans([elem])
            html_lines.append(f'  <p class="action">{formatted_text}</p>')
        
        else:
            # Unknown type - default to action
            print(f"Warning: Unknown element type '{elem_type}', treating as action")
            if "lines" in elem:
                formatted_text = format_text_with_spans(elem["lines"])
            else:
                formatted_text = format_text_with_spans([elem])
            html_lines.append(f'  <p class="action">{formatted_text}</p>')
    
    html_lines.append('</body>')
    html_lines.append('</html>')
    
    # Write HTML file
    with open(output_html_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))
    
    print(f"HTML file created: {output_html_file}")
    print(f"Total elements converted: {len(data['elements'])}")


def format_text_with_spans(lines):
    """
    Format text preserving italics from span font information.
    Checks if font name contains 'Italic' to determine italic formatting.
    """
    formatted_parts = []
    
    for line in lines:
        if "spans" in line:
            # Process each span
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                
                # Check if italic (font name contains 'Italic')
                font_name = span.get("font_name", "")
                is_italic = "Italic" in font_name or "italic" in font_name.lower()
                
                escaped_text = escape(text)
                
                if is_italic:
                    formatted_parts.append(f"<i>{escaped_text}</i>")
                else:
                    formatted_parts.append(escaped_text)
        else:
            # No spans, just use the text
            text = line.get("text", "").strip()
            if text:
                formatted_parts.append(escape(text))
    
    # Join parts with spaces, but preserve natural spacing
    return " ".join(formatted_parts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        input_file = "temp_classified_elements.json"
        output_file = "temp_screenplay.html"
    
    convert_to_html(input_file, output_file)
