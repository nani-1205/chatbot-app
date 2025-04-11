import os
from flask import Flask, request, jsonify
from langchain_community.vectorstores import FAISS  # Corrected import
from langchain_community.embeddings import HuggingFaceEmbeddings # Corrected import
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatGoogleGenerativeAI # Corrected import
from langchain.document_loaders import (
    TextLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    JSONLoader,
    UnstructuredXMLLoader,
    PyPDFLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import boto3
import tempfile
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in the project root directory
dotenv_path = Path('../.env')  # Path to .env file relative to app.py
load_dotenv(dotenv_path=dotenv_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Load environment variables from .env file
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_PREFIX = os.getenv("S3_BUCKET_PREFIX", "") # Optional prefix

if not GOOGLE_API_KEY:
    logging.error("GOOGLE_API_KEY environment variable not set in .env file!")
    raise EnvironmentError("GOOGLE_API_KEY environment variable not set in .env file!")
if not S3_BUCKET:
    logging.error("S3_BUCKET environment variable not set in .env file!")
    raise EnvironmentError("S3_BUCKET environment variable not set in .env file!")

# 1. Load Documents from S3
def load_documents_from_s3(bucket_name, bucket_prefix=""):
    documents = []
    s3_client = None # Initialize s3_client outside try block
    try:
        if S3_ACCESS_KEY and S3_SECRET_KEY:
            # Use access key and secret key if provided
            s3_client = boto3.client(
                's3',
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY
            )
            logging.info("Using S3 access key and secret key from .env")
        else:
            # Otherwise, rely on IAM roles or other default AWS credentials
            s3_client = boto3.client('s3')
            logging.info("Using default AWS credentials (IAM role or environment variables)")

        logging.info(f"Listing objects in S3 bucket: {bucket_name}, prefix: {bucket_prefix}")
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=bucket_prefix)
        if 'Contents' in response:
            s3_objects = response['Contents']
        else:
            logging.warning(f"No objects found in S3 bucket: {bucket_name}, prefix: {bucket_prefix}")
            return documents # Return empty if no objects
    except Exception as e:
        logging.error(f"Error listing objects from S3 bucket {bucket_name}: {e}")
        return documents

    for obj in s3_objects:
        s3_key = obj['Key']
        if s3_key.endswith('/'): # Skip directories
            continue

        file_extension = os.path.splitext(s3_key)[1].lower()
        if not file_extension: # Skip files without extension
            continue

        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file: # Create temp file
                logging.info(f"Downloading S3 object: {s3_key} to temp file: {tmp_file.name}")
                s3_client.download_file(bucket_name, s3_key, tmp_file.name)
                temp_file_path = tmp_file.name

            loader = None
            if file_extension == ".txt":
                loader = TextLoader(temp_file_path)
            elif file_extension == ".docx":
                loader = Docx2txtLoader(temp_file_path)
            elif file_extension == ".xlsx":
                loader = UnstructuredExcelLoader(temp_file_path)
            elif file_extension == ".csv":
                loader = CSVLoader(temp_file_path)
            elif file_extension == ".json":
                loader = JSONLoader(temp_file_path)
            elif file_extension == ".xml":
                loader = UnstructuredXMLLoader(temp_file_path)
            elif file_extension == ".pdf":
                loader = PyPDFLoader(temp_file_path)
            else:
                logging.info(f"Skipping unsupported file type: {s3_key}")

            if loader:
                documents.extend(loader.load())
                logging.info(f"Loaded document from S3: {s3_key}")

        except Exception as e:
            logging.error(f"Error processing S3 object {s3_key}: {e}")
        finally:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path): # Clean up temp file
                os.remove(temp_file_path)
                logging.info(f"Deleted temporary file: {temp_file_path}")
    return documents

loaded_documents = load_documents_from_s3(S3_BUCKET, S3_BUCKET_PREFIX)
if not loaded_documents:
    logging.warning("No documents loaded from S3. Check bucket name, prefix, files, and AWS credentials.")
else:
    logging.info(f"Number of documents loaded from S3: {len(loaded_documents)}")

# 2. Split Documents into Chunks (Optional but Recommended)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
text_chunks = text_splitter.split_documents(loaded_documents)
logging.info(f"Number of text chunks generated: {len(text_chunks)}")

# 3. Create Embeddings and Vector Store (Optional - for semantic search)
embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") # Example - Choose embedding model if needed
vectorstore = FAISS.from_documents(text_chunks, embeddings_model) # Create vector store
retriever = vectorstore.as_retriever() # Use vector store retriever if embeddings are used

# 4. Initialize Gemini Chat Model
gemini_llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY)

# 5. Create RetrievalQA Chain
qa_chain = RetrievalQA.from_chain_type(llm=gemini_llm, retriever=retriever, chain_type="stuff")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        response = qa_chain.run(user_message)
        return jsonify({"response": response})
    except Exception as e:
        logging.error(f"Error during chatbot response generation: {e}")
        return jsonify({"error": "Error generating response"}), 500

@app.route('/health', methods=['GET']) # Health check endpoint
def health_check():
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)