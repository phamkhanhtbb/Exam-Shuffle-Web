import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

try:
    print("Importing docx_serializer...")
    from docx_serializer import DocxSerializer
    print("DocxSerializer imported successfully.")

    print("Importing server...")
    from server import app
    print("Server imported successfully.")

    print("Importing core processors...")
    from core.image_processor import ImageProcessor
    from core.math_processor import MathProcessor
    print("Processors imported successfully.")

except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    sys.exit(1)
