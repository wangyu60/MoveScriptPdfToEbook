import json
import re

def analyze_screenplay_elements(coordinates_file, output_file):
    """
    Analyze coordinates to identify screenplay elements dynamically:
    - Automatically discovers indentation clusters per document
    - x0 < Action + 25: Action or Scene Heading
    - x0 >= Character Margin: Character Name or Parenthetical
    - Everything in between: Dialogue
    """
    
    with open(coordinates_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    X0_PAGE_NUMBER_MIN = 450.0
    TRANSITION_SUFFIXES = ("CUT TO:", "DISSOLVE TO:", "FADE TO:", "CUT TO BLACK:", "FADE OUT:")
    SCENE_NUMBER_RE = re.compile(r'^[A-Z]?\d+[A-Z]?(\.[A-Z]?\d+[A-Z]?)*$')

    lines_by_block = {}
    for span in data["spans"]:
        span_text = span["text"].strip()
        if SCENE_NUMBER_RE.match(span_text):
            print(f"Skipping scene number span: '{span_text}' at x0={span['bbox']['x0']:.1f}")
            continue

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

    sorted_lines = sorted(lines_by_block.items(), key=lambda x: x[1]["y0"])

    valid_x0s = []
    for _, line_data in sorted_lines:
        spans = sorted(line_data["spans"], key=lambda s: s["bbox"]["x0"])
        full_text = " ".join(span["text"] for span in spans).strip()
        if not full_text:
            continue
        primary_x0 = spans[0]["bbox"]["x0"]
        is_numeric = bool(re.match(r'^\d+$', full_text))
        if is_numeric and primary_x0 >= X0_PAGE_NUMBER_MIN:
            continue
        valid_x0s.append(primary_x0)

    if valid_x0s:
        # Reject absolute edge bleed (e.g. "CONTINUED" headers printed at the very edge of the page)
        # Standard screenplay action margins are ~72 pts (1 inch). Scans may float down to ~60 pts.
        filtered_x0s = [x for x in valid_x0s if x >= 50.0]
        
        X0_ACTION = min(filtered_x0s) if filtered_x0s else min(valid_x0s)
        clusters = []
        for x in sorted(valid_x0s):
            matched = False
            for c in clusters:
                if abs(sum(c)/len(c) - x) < 20.0:
                    c.append(x)
                    matched = True
                    break
            if not matched:
                clusters.append([x])
                
        cluster_means = sorted([sum(c)/len(c) for c in clusters])
        
        # Detect if this is a dialogue-heavy page (character names + dialogue, no action)
        # Pattern: two clusters, one ~100-150 pts left of the other, with alternating lines
        is_dialogue_page = False
        if len(cluster_means) >= 2:
            gap = cluster_means[1] - cluster_means[0]
            if 80.0 <= gap <= 180.0:
                # Check if the right cluster has character-like text (short, often all caps)
                right_cluster_x0 = cluster_means[1]
                right_cluster_lines = [s for s in data['spans'] if abs(s['bbox']['x0'] - right_cluster_x0) < 15.0]
                short_upper_count = sum(1 for s in right_cluster_lines 
                    if len(s['text'].strip()) <= 20 and s['text'].strip().isupper())
                if short_upper_count >= 3:
                    is_dialogue_page = True
                    X0_DIALOGUE = cluster_means[0]
                    X0_CHARACTER = cluster_means[1]
                    X0_CHARACTER_MIN = X0_CHARACTER - 15.0
                    X0_ACTION = X0_DIALOGUE - 10.0  # Action would be further left (if present)
        
        if not is_dialogue_page:
            X0_DIALOGUE = X0_ACTION + 70.0
            X0_CHARACTER_MIN = X0_ACTION + 100.0
            
            post_action_clusters = [mean for mean in cluster_means if (mean - X0_ACTION) >= 30.0]
            if post_action_clusters:
                # Dialogue and Character Name zones have highly predictable offsets from the Action margin.
                # Dialogue is typically ~40-95 points inward.
                # Character is typically ~100-180 points inward.
                char_candidates = [m for m in post_action_clusters if 100.0 <= (m - X0_ACTION) <= 220.0]
                
                if char_candidates:
                    # Pick the cluster closest to the statistical center of the expected character margin
                    X0_CHARACTER = min(char_candidates, key=lambda m: abs((m - X0_ACTION) - 150.0))
                    X0_CHARACTER_MIN = X0_CHARACTER - 15.0
                else:
                    X0_CHARACTER_MIN = X0_ACTION + 100.0
    else:
        X0_ACTION = 100.0
        X0_DIALOGUE = X0_ACTION + 70.0
        X0_CHARACTER_MIN = X0_ACTION + 100.0

    classified_elements = []
    current_dialogue_group = None
    current_action_group = None
    current_character_name_group = None
    VERTICAL_CLOSE_THRESHOLD = 8.0 

    for (block_num, line_num), line_data in sorted_lines:
        spans = sorted(line_data["spans"], key=lambda s: s["bbox"]["x0"])
        full_text = " ".join(span["text"] for span in spans).strip()

        if not full_text:
            continue

        primary_x0 = spans[0]["bbox"]["x0"]
        y0 = line_data["y0"]
        y1 = line_data["y1"]

        is_numeric = bool(re.match(r'^\d+\.?$', full_text.strip()))
        if is_numeric and primary_x0 >= X0_PAGE_NUMBER_MIN:
            continue
        
        # Skip header elements at the very top of the page (e.g., revision codes)
        if y0 < 60.0:
            continue
        
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
        
        upper_text = full_text.upper().strip()
        if any(upper_text.endswith(suffix) for suffix in TRANSITION_SUFFIXES):
            if current_action_group is not None:
                classified_elements.append(current_action_group)
                current_action_group = None
            if current_dialogue_group is not None:
                classified_elements.append(current_dialogue_group)
                current_dialogue_group = None
            if current_character_name_group is not None:
                classified_elements.append(current_character_name_group)
                current_character_name_group = None
            element_data["type"] = "transition_right"
            element_data["text"] = upper_text 
            classified_elements.append(element_data)
            continue
        
        if is_dialogue_page:
            # Dialogue page: only two zones - dialogue (left) and character (right)
            if primary_x0 >= X0_CHARACTER_MIN:
                # Character name zone
                if current_dialogue_group is not None:
                    classified_elements.append(current_dialogue_group)
                    current_dialogue_group = None
                
                font_name = spans[0].get("font_name", "")
                if "italic" in font_name.lower() or full_text.startswith("("):
                    element_data["line_type"] = "parenthetical"
                else:
                    element_data["line_type"] = "character_name"
                
                if current_character_name_group is None:
                    current_character_name_group = {"type": "character_name", "lines": [element_data], "x0": primary_x0}
                else:
                    last_line = current_character_name_group["lines"][-1]
                    if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                        current_character_name_group["lines"].append(element_data)
                    else:
                        classified_elements.append(current_character_name_group)
                        current_character_name_group = {"type": "character_name", "lines": [element_data], "x0": primary_x0}
            else:
                # Dialogue zone
                if current_character_name_group is not None:
                    classified_elements.append(current_character_name_group)
                    current_character_name_group = None
                
                if current_dialogue_group is None:
                    current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
                elif abs(primary_x0 - current_dialogue_group["x0"]) < 20.0:
                    last_line = current_dialogue_group["lines"][-1]
                    if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                        current_dialogue_group["lines"].append(element_data)
                    else:
                        classified_elements.append(current_dialogue_group)
                        current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
                else:
                    classified_elements.append(current_dialogue_group)
                    current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
            continue
        
        # 1. Action / Scene Heading (standard page with action)
        if primary_x0 < X0_ACTION + 25.0:
            is_action_cont = False
            if current_action_group is not None:
                last_line = current_action_group["lines"][-1]
                if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                    is_action_cont = True

            if full_text.isupper() and len(full_text.split()) <= 5 and not is_action_cont:
                element_type = "scene_heading"
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
                if current_action_group is None:
                    current_action_group = {"type": "action", "lines": [element_data], "x0": primary_x0}
                else:
                    last_line = current_action_group["lines"][-1]
                    if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                        current_action_group["lines"].append(element_data)
                    else:
                        classified_elements.append(current_action_group)
                        current_action_group = {"type": "action", "lines": [element_data], "x0": primary_x0}
                continue 
        
        # 2. Character Name / Parenthetical
        elif primary_x0 >= X0_CHARACTER_MIN and primary_x0 < X0_PAGE_NUMBER_MIN:
            if current_action_group is not None:
                classified_elements.append(current_action_group)
                current_action_group = None
            if current_dialogue_group is not None:
                classified_elements.append(current_dialogue_group)
                current_dialogue_group = None
            
            font_name = spans[0].get("font_name", "")
            if "italic" in font_name.lower() or full_text.startswith("("):
                element_data["line_type"] = "parenthetical"
            else:
                element_data["line_type"] = "character_name"
            
            if current_character_name_group is None:
                current_character_name_group = {"type": "character_name", "lines": [element_data], "x0": primary_x0}
            else:
                last_line = current_character_name_group["lines"][-1]
                if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                    current_character_name_group["lines"].append(element_data)
                else:
                    classified_elements.append(current_character_name_group)
                    current_character_name_group = {"type": "character_name", "lines": [element_data], "x0": primary_x0}
            continue 
        
        # 3. Dialogue (falls between Action and Character margins)
        else:
            if current_action_group is not None:
                classified_elements.append(current_action_group)
                current_action_group = None
            if current_character_name_group is not None:
                classified_elements.append(current_character_name_group)
                current_character_name_group = None
            
            if current_dialogue_group is None:
                current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
            elif abs(primary_x0 - current_dialogue_group["x0"]) < 20.0:
                last_line = current_dialogue_group["lines"][-1]
                if (y0 - last_line["y1"]) < VERTICAL_CLOSE_THRESHOLD:
                    current_dialogue_group["lines"].append(element_data)
                else:
                    classified_elements.append(current_dialogue_group)
                    current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
            else:
                classified_elements.append(current_dialogue_group)
                current_dialogue_group = {"type": "dialogue", "lines": [element_data], "x0": primary_x0}
            continue 
    
    if current_dialogue_group is not None:
        classified_elements.append(current_dialogue_group)
    if current_action_group is not None:
        classified_elements.append(current_action_group)
    if current_character_name_group is not None:
        classified_elements.append(current_character_name_group)
    
    def get_first_y0(elem):
        if "lines" in elem:
            return elem["lines"][0]["y0"]
        else:
            return elem["y0"]
    
    classified_elements.sort(key=get_first_y0)
    
    output_data = {
        "page_number": data["page_number"],
        "total_elements": len(classified_elements),
        "elements": classified_elements
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== CLASSIFICATION SUMMARY ===")
    print(f"Total elements classified: {len(classified_elements)}")
    
    type_counts = {}
    for elem in classified_elements:
        elem_type = elem.get("type", "unknown")
        if elem_type == "dialogue":
            type_counts["dialogue"] = type_counts.get("dialogue", 0) + 1
        else:
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    for elem_type, count in sorted(type_counts.items()):
        print(f"  {elem_type}: {count}")
    
    print(f"\nOutput saved to: {output_file}")
    return output_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        input_file = "temp_extracted_coordinates.json"
        output_file = "temp_classified_elements.json"
    
    analyze_screenplay_elements(input_file, output_file)
