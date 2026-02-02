import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    print("Importing server...")
    import server
    print("Server imported successfully.")

    print("Importing docx_serializer...")
    from docx_serializer import DocxSerializer
    print("DocxSerializer imported successfully.")

    print("Importing image_utils...")
    import image_utils
    print("image_utils imported successfully.")
    
    print("Verification Passed!")

except Exception as e:
    print(f"Verification Failed: {e}")
    sys.exit(1)
