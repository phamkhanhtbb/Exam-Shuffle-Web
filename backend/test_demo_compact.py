import os
import sys

# Ensure backend module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.parsers import parse_exam_template
from core.generators import generate_variant_from_structure

def test_demo():
    input_file = "de-thi-mau.docx"
    output_file = "demo-output-v4.docx"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        sys.exit(1)
        
    # Read file
    with open(input_file, "rb") as f:
        doc_bytes = f.read()
        
    # Parse structure
    print("Parsing document...")
    exam_structure = parse_exam_template(doc_bytes)
    print(f"Parsed {len(exam_structure.sections)} sections.")
    
    # Generate variant
    print("Generating demo variant...")
    output_bytes, answers = generate_variant_from_structure(
        source_bytes=doc_bytes,
        structure=exam_structure,
        seed=12345, # fixed seed for reproducible layout test
        exam_code="DEMO",
        shuffle_questions=True,
        shuffle_options=True
    )
    
    # Save variant
    with open(output_file, "wb") as f:
        f.write(output_bytes)
        
    print(f"\nGenerated successfully: {output_file}")
    print(f"Answers count: {len(answers)}")
    print(f"Answers preview: {answers[:10]}")

if __name__ == "__main__":
    test_demo()
