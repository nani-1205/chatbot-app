# data_processing/data_loader.py
import boto3
import os
from dotenv import load_dotenv
import traceback
import shutil

# Import functions from sibling modules
from .text_extractor import extract_text_from_file
from .vector_store_manager import chunk_text, add_documents_to_vector_store, needs_initial_processing

load_dotenv()

# --- AWS S3 Configuration ---
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") # Often None if using IAM Role
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") # Often None if using IAM Role
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")

# --- S3 Client Initialization ---
s3_client = None
if S3_BUCKET_NAME: # Only initialize if bucket name is provided
    try:
        print("Initializing S3 client...")
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME
        )
        s3_client = session.client('s3')
        # Test connection by trying to list buckets (optional, requires ListBuckets permission)
        # s3_client.list_buckets()
        print(f"S3 client initialized successfully for region '{AWS_REGION_NAME}'.")
    except Exception as e:
        print(f"Warning: Could not initialize S3 client. S3 functionality disabled. Error: {e}\n{traceback.format_exc()}")
        s3_client = None # Ensure it's None on failure
else:
     print("S3_BUCKET_NAME not set in .env file. S3 functionality disabled.")


def list_s3_files(bucket_name):
    """Lists all object keys in the S3 bucket."""
    if not s3_client:
        print("S3 client not available.")
        return []
    
    files = []
    try:
        print(f"Listing files in S3 bucket: {bucket_name}...")
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Skip directories/folders if represented as objects ending with '/'
                    if not obj['Key'].endswith('/'):
                        files.append(obj['Key'])
        print(f"Found {len(files)} files in bucket '{bucket_name}'.")
    except Exception as e:
        print(f"Error listing files in S3 bucket '{bucket_name}': {e}\n{traceback.format_exc()}")
    return files

def download_s3_file(bucket_name, file_key, local_path):
    """Downloads a single file from S3 to a local path."""
    if not s3_client:
        print("S3 client not available.")
        return False
    try:
        # Ensure local directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        print(f"Downloading s3://{bucket_name}/{file_key} to {local_path}...")
        s3_client.download_file(bucket_name, file_key, local_path)
        print(f"Successfully downloaded '{file_key}'.")
        return True
    except Exception as e:
        print(f"Error downloading file {file_key} from S3: {e}\n{traceback.format_exc()}")
        # Clean up partially downloaded file if it exists
        if os.path.exists(local_path):
             try: os.remove(local_path)
             except OSError: pass
        return False

def process_and_load_data_from_s3():
    """
    Downloads files from S3, extracts text, chunks it,
    and loads it into the vector store.
    Only processes if the vector store appears empty (needs_initial_processing returns True).
    """
    if not needs_initial_processing():
        print("Vector store already contains data. Skipping S3 processing.")
        return

    print("--- Starting Initial Data Processing from S3 ---")
    if not s3_client or not S3_BUCKET_NAME:
        print("S3 client or bucket name not configured. Cannot process S3 data.")
        print("--- Initial Data Processing Skipped ---")
        return

    files_to_process = list_s3_files(S3_BUCKET_NAME)
    if not files_to_process:
        print("No files found in S3 bucket to process.")
        print("--- Initial Data Processing Finished (No files) ---")
        return

    all_doc_chunks = []
    # Create a temporary directory for downloads relative to this script's location
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_s3_downloads")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Using temporary download directory: {temp_dir}")

    success_count = 0
    fail_count = 0

    for file_key in files_to_process:
        # Construct local path, replacing slashes to avoid subdirectory issues in temp folder
        safe_local_name = file_key.replace('/', '_').replace('\\', '_')
        local_file_path = os.path.join(temp_dir, safe_local_name)

        if download_s3_file(S3_BUCKET_NAME, file_key, local_file_path):
            text = extract_text_from_file(local_file_path)
            if text:
                # Use the S3 file key as the source identifier
                doc_chunks = chunk_text(text, source_name=f"s3://{S3_BUCKET_NAME}/{file_key}")
                if doc_chunks:
                    all_doc_chunks.extend(doc_chunks)
                    success_count += 1
                else:
                    print(f"Text extracted but chunking failed or produced no chunks for {file_key}.")
                    fail_count += 1
            else:
                # extract_text_from_file already prints errors/skips
                fail_count += 1
            # Clean up the downloaded file immediately
            try:
                os.remove(local_file_path)
            except OSError as e:
                print(f"Warning: Error removing temporary file {local_file_path}: {e}")
        else:
            print(f"Failed to download {file_key}. Skipping processing for this file.")
            fail_count += 1

    # Clean up temporary directory
    try:
        print(f"Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)
    except OSError as e:
        print(f"Warning: Error cleaning up temp directory {temp_dir}: {e}")

    # Add all collected chunks to the vector store
    if all_doc_chunks:
        print(f"\nProcessed {success_count} files successfully, {fail_count} files failed or were skipped.")
        print(f"Total document chunks created: {len(all_doc_chunks)}")
        add_documents_to_vector_store(all_doc_chunks)
    else:
        print("\nNo document chunks were created from S3 files (or all processing failed).")

    print("--- Initial Data Processing from S3 Finished ---")


# Example usage (for testing data loading and processing)
if __name__ == '__main__':
    print("\n--- Testing S3 Data Loading and Processing ---")
    # This will attempt to connect to S3 and process if the vector store is empty
    # Ensure .env is configured correctly for S3 access before running this.
    process_and_load_data_from_s3()
    print("\n--- Test Complete ---")