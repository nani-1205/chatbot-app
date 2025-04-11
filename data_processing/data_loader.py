# data_processing/data_loader.py
import boto3
import os
from dotenv import load_dotenv
from .text_extractor import extract_text_from_file
from .embeddings import generate_embeddings

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID, # Optional if EC2 instance has IAM role
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY, # Optional if EC2 instance has IAM role
    region_name=AWS_REGION_NAME # Optional if configured in AWS CLI or instance metadata
)

def list_s3_files(bucket_name):
    """Lists all files in the S3 bucket."""
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            files.append(obj['Key'])
    return files

def download_s3_file(bucket_name, file_key, local_path):
    """Downloads a file from S3 to a local path."""
    s3_client.download_file(bucket_name, file_key, local_path)

def load_data_from_s3():
    """Loads text data from all files in the S3 bucket, chunks it, and generates embeddings."""
    files = list_s3_files(S3_BUCKET_NAME)
    all_text_chunks = []
    all_chunk_embeddings = []

    for file_key in files:
        print(f"Processing file: {file_key}") # For debugging
        local_file_path = f"temp_files/{file_key}" # Create temp_files directory
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True) # Ensure directory exists
        download_s3_file(S3_BUCKET_NAME, file_key, local_file_path)
        text = extract_text_from_file(local_file_path)

        # Chunk text into smaller pieces (e.g., sentences or paragraphs)
        # For simplicity, let's split by sentences. You can use more sophisticated chunking.
        file_chunks = text.split(". ") # Simple sentence splitting, might need improvement
        file_chunks = [chunk.strip() for chunk in file_chunks if chunk.strip()] # Remove empty chunks
        all_text_chunks.extend(file_chunks)

        os.remove(local_file_path) # Clean up temporary file

    print("Generating embeddings for all text chunks...")
    all_chunk_embeddings = generate_embeddings(all_text_chunks)
    print("Embeddings generated.")

    return all_text_chunks, all_chunk_embeddings # Return both chunks and embeddings

if __name__ == '__main__':
    # Example usage (for testing)
    if not S3_BUCKET_NAME:
        print("Error: S3_BUCKET_NAME not set in .env file")
    else:
        text_chunks, chunk_embeddings = load_data_from_s3()
        print(f"Number of text chunks loaded: {len(text_chunks)}")
        print(f"Number of embeddings generated: {len(chunk_embeddings)}")
        print("Sample text chunks:")
        for i in range(min(5, len(text_chunks))): # Print first 5 chunks as sample
            print(f"- {text_chunks[i][:100]}...") # Print first 100 chars of each chunk