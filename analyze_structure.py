import json

# Load the extracted data
with open("temp_extracted_coordinates.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Analyze structure
print("=== STRUCTURE ANALYSIS ===\n")
print(f"Total spans: {data['total_spans']}")
print(f"Page number: {data['page_number']}\n")

# Count blocks and their lines
blocks_info = {}
for span in data["spans"]:
    block_num = span["block"]
    if block_num not in blocks_info:
        blocks_info[block_num] = {"lines": set(), "spans": 0, "non_space_spans": 0}
    blocks_info[block_num]["lines"].add(span["line"])
    blocks_info[block_num]["spans"] += 1
    if span["text"].strip():  # Non-space text
        blocks_info[block_num]["non_space_spans"] += 1

print(f"Total blocks: {len(blocks_info)}\n")

# Show block structure
for block_num in sorted(blocks_info.keys()):
    info = blocks_info[block_num]
    print(f"Block {block_num}:")
    print(f"  - Lines: {len(info['lines'])} (line indices: {sorted(info['lines'])[:5]}{'...' if len(info['lines']) > 5 else ''})")
    print(f"  - Total spans: {info['spans']}")
    print(f"  - Non-space spans: {info['non_space_spans']}")
    print(f"  - Space-only spans: {info['spans'] - info['non_space_spans']}")
    
    # Show first non-space text from this block
    for span in data["spans"]:
        if span["block"] == block_num and span["text"].strip():
            text_preview = span["text"].strip()[:60]
            print(f"  - Sample text: \"{text_preview}{'...' if len(span['text'].strip()) > 60 else ''}\"")
            break
    print()

# Count space-only spans
space_only = sum(1 for span in data["spans"] if not span["text"].strip())
non_space = sum(1 for span in data["spans"] if span["text"].strip())

print(f"\n=== SPACE ANALYSIS ===")
print(f"Space-only spans: {space_only} ({space_only/data['total_spans']*100:.1f}%)")
print(f"Non-space spans: {non_space} ({non_space/data['total_spans']*100:.1f}%)")

# Show example of lines within a block
print(f"\n=== EXAMPLE: Block 0 structure ===")
block_0_lines = {}
for span in data["spans"]:
    if span["block"] == 0:
        line_num = span["line"]
        if line_num not in block_0_lines:
            block_0_lines[line_num] = []
        block_0_lines[line_num].append(span)

for line_num in sorted(block_0_lines.keys())[:10]:  # Show first 10 lines
    spans = block_0_lines[line_num]
    text_content = "".join(s["text"] for s in spans).strip()
    if text_content:
        print(f"  Line {line_num}: \"{text_content[:70]}{'...' if len(text_content) > 70 else ''}\"")
