# data_processing/data_loader.py
import boto3
import os
from dotenv import load_dotenv
from .text_extractor import extract_text_from_file
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import S3DirectoryLoader

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

def load_data_from_s3():
    """Loads data from S3, chunks it using Langchain, generates embeddings, and stores in ChromaDB."""

    s3_loader = S3DirectoryLoader(
        bucket=S3_BUCKET_NAME,
        prefix='', # Load all files in the bucket (you can specify a prefix if needed)
        aws_access_key_id=AWS_ACCESS_KEY_ID, # Optional if EC2 instance has IAM role
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY, # Optional if EC2 instance has IAM role
        region_name=AWS_REGION_NAME, # Optional if configured in AWS CLI or instance metadata
        recursive=True, # Load files from subdirectories as well if present
        silent=True, # Suppress progress output
        show_progress=False, # Suppress progress bar
        use_multithreading=True, # Enable multithreading for faster loading
        load_hidden=False, # Do not load hidden files (files starting with .)
    )

    print("Loading documents from S3 using Langchain S3DirectoryLoader...")
    documents = s3_loader.load()
    print(f"Loaded {len(documents)} documents from S3.")

    print("Chunking documents using Langchain...")
    text_chunks = text_splitter.split_documents(documents) # Chunk using Langchain
    print(f"Created {len(text_chunks)} text chunks.")


    print("Generating embeddings and storing in ChromaDB...")
    vectorstore = Chroma.from_documents(documents=text_chunks, embedding=embeddings_model, persist_directory="chroma_db") # Store in ChromaDB
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