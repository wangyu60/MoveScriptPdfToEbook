"""
Process a single page through the full pipeline:
1. Extract text with coordinates
2. Analyze and classify elements
3. Convert to HTML
"""

import subprocess
import sys
import os

def process_page(pdf_file, page_num, output_base_name):
    """
    Process a single page through the full pipeline.
    
    Args:
        pdf_file: Path to PDF file
        page_num: Page number (0-indexed)
        output_base_name: Base name for output files
    """
    
    # Step 1: Extract coordinates
    print(f"\n=== Step 1: Extracting coordinates from page {page_num + 1} ===")
    import extract_text_coordinates
    extract_text_coordinates.extract_text_with_coordinates(
        pdf_file, 
        page_num, 
        f"{output_base_name}_coordinates.json"
    )
    
    # Step 2: Analyze and classify
    print(f"\n=== Step 2: Analyzing and classifying elements ===")
    import analyze_coordinates
    analyze_coordinates.analyze_screenplay_elements(
        f"{output_base_name}_coordinates.json",
        f"{output_base_name}_classified.json"
    )
    
    # Step 3: Convert to HTML
    print(f"\n=== Step 3: Converting to HTML ===")
    import convert_to_html
    convert_to_html.convert_to_html(
        f"{output_base_name}_classified.json",
        f"{output_base_name}.html"
    )
    
    print(f"\n=== Complete! Output saved to {output_base_name}.html ===")

if __name__ == "__main__":
    pdf_file = "true-grit-2010.pdf"
    page_num = 2  # Page 3 (0-indexed: page 1 = index 0, page 2 = index 1, page 3 = index 2)
    output_base = "temp_screenplay_pg2"
    
    process_page(pdf_file, page_num, output_base)
