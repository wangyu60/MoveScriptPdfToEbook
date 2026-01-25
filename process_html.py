from bs4 import BeautifulSoup
import re

def parse_css_value(style_str, prop):
    match = re.search(rf'{prop}:\s*([0-9.]+)\s*pt', style_str)
    if match:
        return float(match.group(1))
    return None

def process_html(input_html_path, output_html_path):
    with open(input_html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    new_body_content = []
    front_matter_elements = []

    # Remove the redundant div wrappers around each page and unwrap inner spans
    for div_tag in soup.find_all('div', id=re.compile(r'page\d+')):
        for span_tag in div_tag.find_all('span'):
            # Preserve italics within spans by replacing span with its italic content if present
            i_tag = span_tag.find('i')
            if i_tag:
                span_tag.replace_with(i_tag)
            else:
                span_tag.unwrap()
        div_tag.unwrap()

    # Define thresholds for left-alignment to categorize content
    LEFT_ALIGN_ACTION = 90.0
    LEFT_ALIGN_DIALOGUE = 165.0
    LEFT_ALIGN_CHARACTER_MIN = 150.0 # Adjusted lower bound for centered text
    LEFT_ALIGN_CHARACTER_MAX = 450.0 # Adjusted upper bound for centered text
    LEFT_ALIGN_PAGE_NUMBER = 520.0
    
    # Heuristics for the first page to identify front matter
    is_front_matter_section = True
    front_matter_line_limit = 30 # Assuming front matter is within the first 30 non-empty lines
    processed_lines_count = 0

    all_p_tags = soup.find_all('p')
    current_p_index = 0

    while current_p_index < len(all_p_tags):
        p_tag = all_p_tags[current_p_index]
        
        # Get the inner HTML to preserve italics
        original_content = str(p_tag)
        text = p_tag.get_text(strip=True)
        style = p_tag.get('style', '')
        left_position = parse_css_value(style, 'left')

        if not text:
            current_p_index += 1
            continue # Skip empty paragraphs
        
        processed_lines_count += 1
        
        new_tag = None

        # --- Front Matter Processing (within the first few lines) ---
        if is_front_matter_section and processed_lines_count <= front_matter_line_limit:
            # Try to combine "This Draft:" and the date
            if "THIS DRAFT:" in text.upper():
                next_p_index = current_p_index + 1
                if next_p_index < len(all_p_tags):
                    next_p_tag = all_p_tags[next_p_index]
                    next_text = next_p_tag.get_text(strip=True)
                    next_style = next_p_tag.get('style', '')
                    next_top_position = parse_css_value(next_style, 'top')
                    current_top_position = parse_css_value(style, 'top')

                    if "JUNE 12, 2009" in next_text.upper() and next_top_position == current_top_position: 
                        new_tag = soup.new_tag('p')
                        new_tag['class'] = 'front-matter-date'
                        new_tag.string = f"{text} {next_text}"
                        front_matter_elements.append(str(new_tag))
                        current_p_index += 2 # Skip the next p_tag as it's merged
                        continue
                
            # Main Front Matter Heuristics - Prioritize text content for classification
            if "TRUE GRIT" in text.upper():
                new_tag = soup.new_tag('h1')
                new_tag['class'] = 'script-title'
            elif "ADAPTATION BY" in text.upper() or "BASED ON THE NOVEL BY" in text.upper():
                new_tag = soup.new_tag('h2')
                new_tag['class'] = 'script-credit-label'
            elif "JOEL AND ETHAN COEN" in text.upper(): 
                new_tag = soup.new_tag('h2')
                new_tag['class'] = 'script-credit-name'
            elif "VOICE-OVER" in text.upper() and left_position is not None and LEFT_ALIGN_CHARACTER_MIN < left_position < LEFT_ALIGN_CHARACTER_MAX: 
                 new_tag = soup.new_tag('h4')
                 new_tag['class'] = 'character-name'
            else:
                # Default to front-matter for other lines in the front matter section
                new_tag = soup.new_tag('p')
                new_tag['class'] = 'front-matter'
            
            if new_tag.string is None: # Only assign string if not already done by merging
                new_tag.string = text
            front_matter_elements.append(str(new_tag))

        # --- Main Content Processing ---
        else:
            is_front_matter_section = False # End front matter section
            
            if left_position is not None:
                if left_position > LEFT_ALIGN_PAGE_NUMBER and re.match(r'^\d+$', text):
                    new_tag = soup.new_tag('span')
                    new_tag['class'] = 'page-number'
                    new_tag.string = text
                elif (left_position > LEFT_ALIGN_CHARACTER_MIN and left_position < LEFT_ALIGN_CHARACTER_MAX and len(text.split()) <= 4 and text.isupper()) or "VOICE-OVER" in text.upper():
                    new_tag = soup.new_tag('h4')
                    new_tag['class'] = 'character-name'
                    new_tag.string = text
                elif left_position >= LEFT_ALIGN_ACTION and len(text.split()) <= 6 and text.isupper():
                    new_tag = soup.new_tag('h3')
                    new_tag['class'] = 'scene-heading'
                    new_tag.string = text
                elif left_position >= LEFT_ALIGN_DIALOGUE:
                    # Re-parse content to preserve <i> tags
                    temp_soup = BeautifulSoup(original_content, 'html.parser')
                    # Find the <p> tag within the temporary soup to extract its contents
                    p_content_tag = temp_soup.find('p')
                    if p_content_tag:
                        # Iterate through its children to replace <i> with <em> and then decode
                        for i_tag in p_content_tag.find_all('i'):
                            em_tag = temp_soup.new_tag('em')
                            em_tag.string = i_tag.string
                            i_tag.replace_with(em_tag)
                        processed_dialogue_content = str(p_content_tag.decode_contents())
                    else:
                        processed_dialogue_content = text

                    new_tag = soup.new_tag('p')
                    new_tag['class'] = 'dialogue'
                    new_tag.append(BeautifulSoup(processed_dialogue_content, 'html.parser'))
                else:
                    new_tag = soup.new_tag('p')
                    new_tag['class'] = 'action'
                    new_tag.string = text
            else:
                new_tag = soup.new_tag('p')
                new_tag['class'] = 'action'
                new_tag.string = text

            if new_tag:
                new_body_content.append(str(new_tag))
        
        current_p_index += 1

    # Combine front matter and main content
    final_content_for_body = front_matter_elements + new_body_content

    final_html = BeautifulSoup("", 'html.parser')
    html_tag = final_html.new_tag('html')
    final_html.append(html_tag)

    head_tag = final_html.new_tag('head')
    html_tag.append(head_tag)
    title_tag = final_html.new_tag('title')
    title_tag.string = "True Grit - Movie Script"
    head_tag.append(title_tag)
    link_tag = final_html.new_tag('link', rel="stylesheet", href="styles.css")
    head_tag.append(link_tag)

    body_tag = final_html.new_tag('body')
    html_tag.append(body_tag)
    
    for item in final_content_for_body:
        body_tag.append(BeautifulSoup(item, 'html.parser'))

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(final_html.prettify())

if __name__ == "__main__":
    input_file = "true-grit-2010.html"
    output_file = "true-grit-2010_processed.html"
    process_html(input_file, output_file)
    print(f"'{input_file}' successfully processed to '{output_file}'")