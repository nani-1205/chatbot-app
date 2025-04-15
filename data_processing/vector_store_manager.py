# data_processing/vector_store_manager.py
import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings # Or use GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document # Correct import for Document schema

load_dotenv()

# --- Configuration ---
# Use environment variables or defaults
# EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2")
EMBEDDING_MODEL_NAME = "all-mpnet-base-v2" # Example, choose your preferred model
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
CHUNK_SIZE = 1000 # Size of text chunks
CHUNK_OVERLAP = 150 # Overlap between chunks

# Ensure the persist directory exists
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# --- Initialize Embedding Model ---
# Using HuggingFace embeddings (requires sentence-transformers)
# Make sure you have transformer models downloaded or internet access
# You could also use: from langchain_google_genai import GoogleGenerativeAIEmbeddings
# embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001") # Example using Google
try:
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'} # Use 'cuda' if GPU is available
    )
    print("Embedding model loaded successfully.")
except Exception as e:
    print(f"Error loading embedding model: {e}")
    # Handle error appropriately, maybe exit or use a fallback
    embedding_model = None

# --- Initialize Chroma Vector Store ---
# Loads from disk if exists, otherwise creates new
vector_store = Chroma(
    persist_directory=CHROMA_PERSIST_DIR,
    embedding_function=embedding_model # Pass the embedding function instance
)
print(f"Vector store initialized. Persisting to: {CHROMA_PERSIST_DIR}")
# Check if the vector store is empty (useful for initial setup)
print(f"Vector store collection count: {vector_store._collection.count()}")


def chunk_text(text, source_name=""):
    """Splits text into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    # Create Document objects with metadata
    documents = [Document(page_content=chunk, metadata={"source": source_name}) for chunk in chunks]
    return documents

def add_documents_to_vector_store(documents):
    """Adds Langchain Document objects to the Chroma vector store."""
    if not documents:
        print("No documents to add.")
        return
    if embedding_model is None:
        print("Embedding model not loaded. Cannot add documents.")
        return

    print(f"Adding {len(documents)} document chunks to the vector store...")
    try:
        vector_store.add_documents(documents)
        vector_store.persist() # Save changes to disk
        print("Documents added and vector store persisted.")
        print(f"Vector store collection count after adding: {vector_store._collection.count()}")
    except Exception as e:
        print(f"Error adding documents to vector store: {e}")

def get_vector_store():
    """Returns the initialized vector store instance."""
    # Ensure it's loaded (might be redundant if initialized globally, but safe)
    if embedding_model is None:
       raise Exception("Embedding model could not be initialized.")

    # Reload from disk to ensure consistency if multiple processes were involved
    # (though Flask dev server is usually single-process)
    vs = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embedding_model
    )
    return vs

def needs_initial_processing():
    """Checks if the vector store seems empty or non-existent."""
    try:
        # A simple check: does the collection exist and is it empty?
        count = vector_store._collection.count()
        print(f"Checking initial processing need. Current count: {count}")
        return count == 0
    except Exception as e:
        # Handle cases where the collection/directory might not exist yet properly
        print(f"Error checking vector store count (may indicate need for processing): {e}")
        return True

if __name__ == '__main__':
    # Example usage (for testing this module)
    if embedding_model: # Proceed only if embedding model loaded
        print("\n--- Testing vector_store_manager ---")
        sample_text = "This is the first sentence. This is the second sentence, which is a bit longer. The third sentence provides more context. Finally, the fourth sentence concludes the paragraph."
        sample_source = "test_document.txt"

        print("\nChunking text...")
        doc_chunks = chunk_text(sample_text, sample_source)
        print(f"Created {len(doc_chunks)} chunks:")
        for i, doc in enumerate(doc_chunks):
            print(f"  Chunk {i+1}: {doc.page_content[:50]}... (Source: {doc.metadata['source']})")

        print("\nAdding documents to vector store...")
        add_documents_to_vector_store(doc_chunks)

        print("\nRetrieving vector store instance...")
        retrieved_vs = get_vector_store()
        print(f"Retrieved vector store object: {retrieved_vs}")
        print(f"Retrieved vector store count: {retrieved_vs._collection.count()}")

        print("\nPerforming a similarity search...")
        query = "What is the second sentence?"
        results = retrieved_vs.similarity_search(query, k=2)
        print(f"Search results for '{query}':")
        for res in results:
            print(f"  - {res.page_content[:80]}... (Source: {res.metadata.get('source', 'N/A')})")

        print("\n--- Test Complete ---")
    else:
        print("Cannot run tests: Embedding model failed to load.")