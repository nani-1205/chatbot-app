# data_processing/text_extractor.py
import os
import PyPDF2
import docx
import pandas as pd

def extract_text_from_file(file_path):
    """Extracts text from different file types."""
    file_extension = os.path.splitext(file_path)[1].lower()
    text = ""
    if file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    elif file_extension == '.pdf':
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
    elif file_extension == '.csv':
        try:
            df = pd.read_csv(file_path)
            text = df.to_string() # Convert DataFrame to string
        except Exception as e:
            print(f"Error reading CSV {file_path}: {e}")
    elif file_extension == '.xlsx' or file_extension == '.xls':
        try:
            df = pd.read_excel(file_path)
            text = df.to_string() # Convert DataFrame to string
        except Exception as e:
            print(f"Error reading Excel {file_path}: {e}")
    elif file_extension == '.docx':
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
    else:
        print(f"Unsupported file type: {file_extension} for file {file_path}")
    return text

if __name__ == '__main__':
    # Example usage (create dummy files for testing)
    os.makedirs("temp_files", exist_ok=True)
    with open("temp_files/test.txt", "w") as f:
        f.write("This is a test text file.")
    with open("temp_files/test.csv", "w") as f:
        f.write("col1,col2\nvalue1,value2\nvalue3,value4")

    text_txt = extract_text_from_file("temp_files/test.txt")
    text_csv = extract_text_from_file("temp_files/test.csv")

    print("Text from TXT:")
    print(text_txt)
    print("\nText from CSV:")
    print(text_csv)