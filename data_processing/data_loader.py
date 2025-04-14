# data_processing/data_loader.py
import boto3
import os
from dotenv import load_dotenv
from .text_extractor import extract_text_from_file
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma

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

# Langchain components for text splitting and embeddings
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200) # настройте chunk_size и chunk_overlap по необходимости
embeddings_model = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2") # You can choose different embedding models

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
    """Loads data from S3, chunks it using Langchain, generates embeddings, and stores in ChromaDB."""
    files = list_s3_files(S3_BUCKET_NAME)
    all_texts = [] # List to hold Langchain Document objects
    for file_key in files:
        print(f"Processing file: {file_key}")
        local_file_path = f"temp_files/{file_key}"
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        download_s3_file(S3_BUCKET_NAME, file_key, local_file_path)
        text_content = extract_text_from_file(local_file_path)

        # Create Langchain Document object
        from langchain.docstore.document import Document
        document = Document(page_content=text_content, metadata={"source": file_key}) # Add metadata if needed
        all_texts.append(document)

        os.remove(local_file_path)

    print("Chunking documents using Langchain...")
    text_chunks = text_splitter.split_documents(all_texts) # Chunk using Langchain

    print("Generating embeddings and storing in ChromaDB...")
    vectorstore = Chroma.from_documents(texts=text_chunks, embedding=embeddings_model, persist_directory="chroma_db") # Store in ChromaDB
    vectorstore.persist() # Persist to disk

    print("Data loaded, chunked, embedded, and stored in ChromaDB.")
    return vectorstore # Return the ChromaDB vectorstore

if __name__ == '__main__':
    # Example usage (for testing)
    if not S3_BUCKET_NAME:
        print("Error: S3_BUCKET_NAME not set in .env file")
    else:
        vector_db = load_data_from_s3()
        print("ChromaDB vectorstore loaded.")
        # You can now test querying the vectorstore here if needed