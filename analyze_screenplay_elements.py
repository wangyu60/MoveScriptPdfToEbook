import json
import re

def analyze_screenplay_elements(coordinates_file, output_file):
    """
    Analyze coordinates to identify screenplay elements:
    - x0 ≈ 93.x: Scene headings or action/descriptions
    - x0 ≈ 165.x: Dialogues (consecutive lines with same x0 = same dialogue paragraph)
    - x0 > 165.x (e.g., 277.x): Character names or Parentheticals (centered)
    - Page numbers (top right, numeric, high x0): Ignore
    """
    
    # Load extracted coordinates
    with open(coordinates_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Thresholds for classification (with tolerance for floating point)
    X0_ACTION = 93.0
    X0_DIALOGUE = 165.0
    X0_CHARACTER_MIN = 200.0  # Character names start after dialogue
    X0_PAGE_NUMBER_MIN = 500.0  # Page numbers are typically far right
    
    TOLERANCE = 5.0  # Tolerance for coordinate matching
    
    # Group spans by block and line to reconstruct full lines
    lines_by_block = {}
    for span in data["spans"]:
        block_num = span["block"]
        line_num = span["line"]
        key = (block_num, line_num)
        
        if key not in lines_by_block:
            lines_by_block[key] = {
                "spans": [],
                "y0": span["bbox"]["y0"],
                "y1": span["bbox"]["y1"]
            }
        
        lines_by_block[key]["spans"].append(span)
    
    # Sort lines by position (y0 coordinate)
    sorted_lines = sorted(lines_by_block.items(), key=lambda x: x[1]["y0"])
    
    # Classify and process lines
    classified_elements = []
    current_dialogue_group = None
    current_action_group = None
    current_character_name_group = None
    VERTICAL_CLOSE_THRESHOLD = 1.0  # Lines with y0 - prev_y1 < this are considered vertically close
    
    for (block_num, line_num), line_data in sorted_lines:
        # Combine all spans in this line
        spans = sorted(line_data["spans"], key=lambda s: s["bbox"]["x0"])
        full_text = "".join(span["text"] for span in spans).strip()
        
        if not full_text:
            continue
        
        # Get the primary x0 (from first span, or average if needed)
        primary_x0 = spans[0]["bbox"]["x0"]
        y0 = line_data["y0"]
        y1 = line_data["y1"]  # Get y1 for vertical proximity checking
        
        # Check if it's a page number (numeric, far right)
        is_numeric = bool(re.match(r'^\d+$', full_text.strip()))
        if is_numeric and primary_x0 >= X0_PAGE_NUMBER_MIN:
            print(f"Skipping page number: '{full_text}' at x0={primary_x0:.1f}")
            continue
        
        # Classify based on x0 position
        element_type = None
        element_data = {
            "block": block_num,
            "line": line_num,
            "text": full_text,
            "x0": primary_x0,
            "y0": y0,
            "y1": y1,
            "spans": spans
        }
        
        if abs(primary_x0 - X0_ACTION) < TOLERANCE:
            # Scene heading or action/description
            # Check if it's uppercase (likely scene heading) or mixed case (action)
            if full_text.isupper() and len(full_text.split()) <= 5:
                element_type = "scene_heading"
                # Scene headings are standalone, so save any current groups first
                if current_action_group is not None:
                    classified_elements.append(current_action_group)
                    current_action_group = None
                if current_character_name_group is not None:
                    classified_elements.append(current_character_name_group)
                    current_character_name_group = None
                element_data["type"] = element_type
                classified_elements.append(element_data)
                continue
            else:
                element_type = "action"
                # Group vertically close consecutive action lines
                if current_action_group is None:
                    # Start new action group
                    current_action_group = {
                        "type": "action",
                        "lines": [element_data],
                        "x0": primary_x0
                    }
                else:
                    # Check if this line is vertically close to the last line in the group
                    last_line = current_action_group["lines"][-1]
                    vertical_gap = y0 - last_line["y1"]
                    if vertical_gap < VERTICAL_CLOSE_THRESHOLD:
                        # Vertically close - continue the action group
                        current_action_group["lines"].append(element_data)
                    else:
                        # Not vertically close - save previous group and start new one
                        classified_elements.append(current_action_group)
                        current_action_group = {
                            "type": "action",
                            "lines": [element_data],
                            "x0": primary_x0
                        }
                continue  # Skip adding to classified_elements for now
        
        elif abs(primary_x0 - X0_DIALOGUE) < TOLERANCE:
            # Dialogue - group consecutive lines with same x0 AND vertically close
            # Save any current action or character name groups first
            if current_action_group is not None:
                classified_elements.append(current_action_group)
                current_action_group = None
            if current_character_name_group is not None:
                classified_elements.append(current_character_name_group)
                current_character_name_group = None
            
            if current_dialogue_group is None:
                # Start new dialogue group
                current_dialogue_group = {
                    "type": "dialogue",
                    "lines": [element_data],
                    "x0": primary_x0
                }
            elif abs(primary_x0 - current_dialogue_group["x0"]) < TOLERANCE:
                # Same x0 - check if vertically close (consecutive dialogue lines)
                last_line = current_dialogue_group["lines"][-1]
                vertical_gap = y0 - last_line["y1"]
                if vertical_gap < VERTICAL_CLOSE_THRESHOLD:
                    # Vertically close - continue the dialogue group
                    current_dialogue_group["lines"].append(element_data)
                else:
                    # Not vertically close - there must be other elements in between
                    # Save previous group and start new one
                    classified_elements.append(current_dialogue_group)
                    current_dialogue_group = {
                        "type": "dialogue",
                        "lines": [element_data],
                        "x0": primary_x0
                    }
            else:
                # Different x0, save previous group and start new one
                classified_elements.append(current_dialogue_group)
                current_dialogue_group = {
                    "type": "dialogue",
                    "lines": [element_data],
                    "x0": primary_x0
                }
            continue  # Skip adding to classified_elements for now
        
        elif primary_x0 >= X0_CHARACTER_MIN:
            # Character name or visual item (centered)
            # Save any current action or dialogue groups first
            if current_action_group is not None:
                classified_elements.append(current_action_group)
                current_action_group = None
            if current_dialogue_group is not None:
                classified_elements.append(current_dialogue_group)
                current_dialogue_group = None
            
            # Character names are typically short (1-4 words) and centered
            # They can be uppercase, title case, or mixed case
            text_clean = full_text.strip()
            word_count = len(text_clean.split())
            # If it's short and centered, it's likely a character name
            # Visual items are typically longer descriptions
            if word_count <= 4 and len(text_clean) < 50:
                element_type = "character_name"
                # Group vertically close consecutive character name lines
                if current_character_name_group is None:
                    # Start new character name group
                    current_character_name_group = {
                        "type": "character_name",
                        "lines": [element_data],
                        "x0": primary_x0
                    }
                else:
                    # Check if this line is vertically close to the last line in the group
                    last_line = current_character_name_group["lines"][-1]
                    vertical_gap = y0 - last_line["y1"]
                    if vertical_gap < VERTICAL_CLOSE_THRESHOLD:
                        # Vertically close - continue the character name group
                        current_character_name_group["lines"].append(element_data)
                    else:
                        # Not vertically close - save previous group and start new one
                        classified_elements.append(current_character_name_group)
                        current_character_name_group = {
                            "type": "character_name",
                            "lines": [element_data],
                            "x0": primary_x0
                        }
                continue  # Skip adding to classified_elements for now
            else:
                element_type = "visual_item"
                # Save any current character name group first
                if current_character_name_group is not None:
                    classified_elements.append(current_character_name_group)
                    current_character_name_group = None
        
        else:
            # Unknown - default to action
            element_type = "action"
            print(f"Warning: Unclassified line at x0={primary_x0:.1f}: '{full_text[:50]}'")
            # Save any current character name group first
            if current_character_name_group is not None:
                classified_elements.append(current_character_name_group)
                current_character_name_group = None
            # Treat as action and group if vertically close
            if current_action_group is None:
                current_action_group = {
                    "type": "action",
                    "lines": [element_data],
                    "x0": primary_x0
                }
            else:
                last_line = current_action_group["lines"][-1]
                vertical_gap = y0 - last_line["y1"]
                if vertical_gap < VERTICAL_CLOSE_THRESHOLD:
                    current_action_group["lines"].append(element_data)
                else:
                    classified_elements.append(current_action_group)
                    current_action_group = {
                        "type": "action",
                        "lines": [element_data],
                        "x0": primary_x0
                    }
            continue
        
        # Add the classified element (for non-grouped types like visual_item, scene_heading)
        # Note: character_name is now grouped, so it won't reach here
        element_data["type"] = element_type
        classified_elements.append(element_data)
    
    # Don't forget the last groups
    if current_dialogue_group is not None:
        classified_elements.append(current_dialogue_group)
    if current_action_group is not None:
        classified_elements.append(current_action_group)
    if current_character_name_group is not None:
        classified_elements.append(current_character_name_group)
    
    # Sort all elements by y0 of their first line to maintain correct vertical order
    def get_first_y0(elem):
        """Get the y0 coordinate of the first line in an element."""
        if "lines" in elem:
            # Grouped element (dialogue, action)
            return elem["lines"][0]["y0"]
        else:
            # Single element (character_name, visual_item, scene_heading)
            return elem["y0"]
    
    classified_elements.sort(key=get_first_y0)
    
    # Save results
    output_data = {
        "page_number": data["page_number"],
        "total_elements": len(classified_elements),
        "elements": classified_elements
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n=== CLASSIFICATION SUMMARY ===")
    print(f"Total elements classified: {len(classified_elements)}")
    
    type_counts = {}
    for elem in classified_elements:
        elem_type = elem.get("type", "unknown")
        if elem_type == "dialogue":
            # Count dialogue groups
            type_counts["dialogue"] = type_counts.get("dialogue", 0) + 1
        else:
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    for elem_type, count in sorted(type_counts.items()):
        print(f"  {elem_type}: {count}")
    
    print(f"\nOutput saved to: {output_file}")
    
    return output_data

if __name__ == "__main__":
    input_file = "temp_extracted_coordinates.json"
    output_file = "temp_classified_elements.json"
    
    analyze_screenplay_elements(input_file, output_file)
