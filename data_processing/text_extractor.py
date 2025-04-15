# data_processing/text_extractor.py
import os
import PyPDF2
import docx
import pandas as pd
import traceback

def extract_text_from_file(file_path):
    """Extracts text from different file types."""
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    text = ""
    print(f"Attempting to extract text from: {file_path} (type: {file_extension})")
    try:
        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        elif file_extension == '.pdf':
            try:
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file, strict=False) # Use strict=False for robustness
                    # Check if encrypted
                    if pdf_reader.is_encrypted:
                         print(f"Skipping encrypted PDF: {file_path}")
                         # You might try decrypting if you have the password, but that's complex
                         # try:
                         #     pdf_reader.decrypt('') # Try empty password
                         # except Exception as decrypt_err:
                         #     print(f"Could not decrypt {file_path}: {decrypt_err}")
                         #     return "" # Skip if decryption fails
                    
                    for i, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except Exception as page_err:
                             print(f"Error extracting text from page {i+1} in {file_path}: {page_err}")
                             # Continue to next page
            except FileNotFoundError:
                 print(f"File not found during PDF processing: {file_path}")
                 return ""
            except PyPDF2.errors.PdfReadError as pdf_err:
                 print(f"Error reading PDF structure {file_path}: {pdf_err}. File might be corrupted or invalid.")
                 return "" # Skip corrupted PDFs
            except Exception as e:
                print(f"General error reading PDF {file_path}: {e}\n{traceback.format_exc()}")
                return "" # Skip on general errors

        elif file_extension == '.csv':
            try:
                # Read CSV trying different encodings if needed
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file_path, encoding='latin1')
                except Exception as e_csv_read:
                     print(f"Error reading CSV {file_path} with multiple encodings: {e_csv_read}")
                     return "" # Skip if unreadable
            except Exception as e:
                print(f"Error processing CSV {file_path}: {e}")
                return "" # Skip on other pandas errors
            text = df.to_string() # Convert DataFrame to string

        elif file_extension in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(file_path, sheet_name=None) # Read all sheets
                all_sheets_text = []
                for sheet_name, sheet_df in df.items():
                    all_sheets_text.append(f"--- Sheet: {sheet_name} ---\n{sheet_df.to_string()}")
                text = "\n\n".join(all_sheets_text)
            except Exception as e:
                print(f"Error reading Excel {file_path}: {e}")
                return "" # Skip on errors

        elif file_extension == '.docx':
            try:
                doc = docx.Document(file_path)
                full_text = []
                for para in doc.paragraphs:
                    full_text.append(para.text)
                text = '\n'.join(full_text)
            except Exception as e:
                print(f"Error reading DOCX {file_path}: {e}")
                return "" # Skip on errors
        else:
            print(f"Unsupported file type: {file_extension} for file {file_path}. Skipping.")

    except Exception as e:
        print(f"An unexpected error occurred while processing {file_path}: {e}\n{traceback.format_exc()}")
        return "" # Return empty string on unexpected failure

    if text:
      print(f"Successfully extracted text from {file_path} (length: {len(text)} chars)")
    else:
      print(f"No text extracted or file skipped: {file_path}")
      
    return text.strip()

# Example usage for testing (optional)
if __name__ == '__main__':
    # Create dummy files for testing
    os.makedirs("temp_test_files", exist_ok=True)
    with open("temp_test_files/test.txt", "w") as f: f.write("This is a test text file.")
    with open("temp_test_files/test.csv", "w") as f: f.write("col1,col2\nvalue1,value2")
    # You'd need actual .pdf, .docx, .xlsx files for full testing

    text_txt = extract_text_from_file("temp_test_files/test.txt")
    text_csv = extract_text_from_file("temp_test_files/test.csv")

    print("\n--- Test Extraction Results ---")
    print(f"Text from TXT: {text_txt}")
    print(f"Text from CSV:\n{text_csv}")
    print("--- Test Complete ---")
    # Clean up dummy files
    import shutil
    # shutil.rmtree("temp_test_files") # Uncomment to cleanup