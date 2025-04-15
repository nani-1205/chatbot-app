# data_processing/data_loader.py
import boto3
import os
from dotenv import load_dotenv
from .text_extractor import extract_text_from_file
from .vector_store_manager import chunk_text, add_documents_to_vector_store, needs_initial_processing

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")

# --- S3 Client Initialization ---
# Handle potential missing credentials more gracefully
s3_client = None
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME
    )
    # Perform a simple check like listing buckets if needed to confirm credentials
    # s3_client.list_buckets() # Uncomment to test connection, might need permissions
    print("S3 client initialized successfully.")
except Exception as e:
    print(f"Warning: Could not initialize S3 client. Check AWS credentials/config. Error: {e}")
    print("Proceeding without S3 functionality. Data loading from S3 will fail.")


def list_s3_files(bucket_name):
    """Lists all files in the S3 bucket."""
    if not s3_client:
        print("S3 client not available.")
        return []
    if not bucket_name:
        print("Error: S3_BUCKET_NAME not set.")
        return []

    files = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    files.append(obj['Key'])
        print(f"Found {len(files)} files in bucket '{bucket_name}'.")
    except Exception as e:
        print(f"Error listing files in S3 bucket '{bucket_name}': {e}")
    return files

def download_s3_file(bucket_name, file_key, local_path):
    """Downloads a file from S3 to a local path."""
    if not s3_client:
        print("S3 client not available.")
        return False
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3_client.download_file(bucket_name, file_key, local_path)
        print(f"Successfully downloaded '{file_key}' to '{local_path}'")
        return True
    except Exception as e:
        print(f"Error downloading file {file_key} from S3: {e}")
        return False

def process_and_load_data_from_s3():
    """
    Downloads files from S3, extracts text, chunks it,
    and loads it into the vector store.
    Only processes if the vector store appears empty.
    """
    if not needs_initial_processing():
        print("Vector store already contains data. Skipping initial processing.")
        return

    print("Starting data processing from S3...")
    if not s3_client or not S3_BUCKET_NAME:
        print("S3 client or bucket name not configured. Cannot process S3 data.")
        return

    files_to_process = list_s3_files(S3_BUCKET_NAME)
    if not files_to_process:
        print("No files found in S3 bucket to process.")
        return

    all_doc_chunks = []
    temp_dir = "temp_s3_files"
    os.makedirs(temp_dir, exist_ok=True)

    for file_key in files_to_process:
        # Avoid processing directories or zero-byte objects if listed
        if file_key.endswith('/'):
            print(f"Skipping directory: {file_key}")
            continue

        print(f"Processing file: {file_key}")
        local_file_path = os.path.join(temp_dir, file_key.replace('/', '_')) # Basic flattening of paths

        if download_s3_file(S3_BUCKET_NAME, file_key, local_file_path):
            text = extract_text_from_file(local_file_path)
            if text:
                print(f"Extracted text from {file_key}. Chunking...")
                # Use the file key (or path) as the source metadata
                doc_chunks = chunk_text(text, source_name=file_key)
                all_doc_chunks.extend(doc_chunks)
                print(f"Added {len(doc_chunks)} chunks from {file_key}.")
            else:
                print(f"No text extracted from {file_key}.")
            # Clean up temporary file
            try:
                os.remove(local_file_path)
            except OSError as e:
                print(f"Error removing temporary file {local_file_path}: {e}")
        else:
            print(f"Failed to download {file_key}. Skipping.")

    # Clean up temporary directory if empty
    try:
        if not os.listdir(temp_dir):
            os.rmdir(temp_dir)
        else: # Or remove the whole dir if you are sure
             import shutil
             shutil.rmtree(temp_dir)
             print(f"Cleaned up temp directory: {temp_dir}")
    except OSError as e:
        print(f"Error cleaning up temp directory {temp_dir}: {e}")


    if all_doc_chunks:
        print(f"\nTotal chunks created: {len(all_doc_chunks)}")
        add_documents_to_vector_store(all_doc_chunks)
    else:
        print("\nNo document chunks were created from S3 files.")

    print("Data processing from S3 finished.")


if __name__ == '__main__':
    # Example usage (for testing data loading and processing)
    print("\n--- Testing S3 Data Loading and Processing ---")
    # This will attempt to connect to S3 and process if the vector store is empty
    process_and_load_data_from_s3()
    print("\n--- Test Complete ---")