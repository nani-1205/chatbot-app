# data_processing/vector_store_manager.py
import os
from dotenv import load_dotenv
import traceback

# Langchain components
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings # Or use GoogleGenerativeAIEmbeddings
# >>> Updated Chroma import <<<
from langchain_chroma import Chroma
from langchain.schema import Document # For creating Document objects

load_dotenv()

# --- Configuration ---
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))

# Ensure the persist directory exists
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
print(f"ChromaDB persistence directory: {os.path.abspath(CHROMA_PERSIST_DIR)}")

# --- Initialize Embedding Model ---
embedding_model = None
try:
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'}, # Use 'cuda' if GPU is available and configured
        encode_kwargs={'normalize_embeddings': True} # Normalize for better similarity search
    )
    print("Embedding model loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR loading embedding model: {e}\n{traceback.format_exc()}")
    # Application might not function correctly without embeddings

# --- Initialize or Load Chroma Vector Store ---
# This will try to load from CHROMA_PERSIST_DIR if it exists,
# otherwise, it initializes an empty store that will be saved there later.
vector_store = None
if embedding_model: # Only proceed if embedding model loaded
    try:
        print(f"Initializing Chroma vector store from: {CHROMA_PERSIST_DIR}")
        # Pass the embedding function directly
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embedding_model
        )
        count = vector_store._collection.count() # Access underlying collection count
        print(f"Chroma vector store initialized/loaded. Current document chunk count: {count}")
    except Exception as e:
        print(f"CRITICAL ERROR initializing Chroma vector store: {e}\n{traceback.format_exc()}")
        # This is a critical failure for the RAG functionality
else:
    print("Skipping vector store initialization because embedding model failed to load.")


def chunk_text(text, source_name=""):
    """Splits text into chunks and creates Langchain Document objects."""
    if not text:
        return []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True, # Optionally add start index to metadata
    )
    # Create Document objects directly from splitter
    documents = text_splitter.create_documents([text], metadatas=[{"source": source_name}])
    print(f"Chunked text from '{source_name}' into {len(documents)} documents.")
    return documents

def add_documents_to_vector_store(documents):
    """Adds Langchain Document objects to the Chroma vector store."""
    global vector_store
    if not documents:
        print("No document chunks provided to add.")
        return
    if not vector_store:
        print("Vector store is not available. Cannot add documents.")
        return
    if not embedding_model:
         print("Embedding model is not available. Cannot add documents.")
         return

    print(f"Adding {len(documents)} document chunks to the vector store...")
    try:
        # Add documents in batches if necessary (though Chroma handles this reasonably well)
        vector_store.add_documents(documents)
        # Persist changes explicitly after adding (important!)
        vector_store.persist()
        count = vector_store._collection.count()
        print(f"Documents added and vector store persisted. New count: {count}")
    except Exception as e:
        print(f"Error adding documents to vector store: {e}\n{traceback.format_exc()}")

def get_vector_store():
    """Returns the initialized vector store instance. Reloads if necessary."""
    global vector_store
    # If vector_store wasn't initialized properly at startup, try again (e.g., if dir was created later)
    # However, relying on initial load is generally better.
    if vector_store is None and embedding_model:
         print("Attempting to reload vector store...")
         try:
             vector_store = Chroma(
                 persist_directory=CHROMA_PERSIST_DIR,
                 embedding_function=embedding_model
             )
             print(f"Vector store reloaded successfully. Count: {vector_store._collection.count()}")
         except Exception as e:
              print(f"Failed to reload vector store: {e}")
              return None # Return None if reload fails
    elif vector_store is None and not embedding_model:
         print("Cannot get vector store because embedding model is not loaded.")
         return None

    # Return the globally loaded instance
    return vector_store

def needs_initial_processing():
    """Checks if the vector store seems empty or non-existent."""
    vs = get_vector_store() # Use the getter to ensure it tries to load
    if vs is None:
        print("Vector store is unavailable, assuming initial processing is needed.")
        return True # If store can't be loaded, assume processing needed

    try:
        count = vs._collection.count()
        print(f"Checking initial processing need. Vector store count: {count}")
        return count == 0 # If count is 0, needs processing
    except Exception as e:
        # Handle cases where the collection/directory might not exist yet properly
        print(f"Error checking vector store count (assuming processing needed): {e}")
        return True

# Example usage for testing (optional)
if __name__ == '__main__':
    if embedding_model and vector_store:
        print("\n--- Testing vector_store_manager ---")
        # ... (keep the test code from previous versions if desired) ...
        print("\n--- Test Complete ---")
    else:
        print("\n--- Cannot run tests: Embedding model or vector store failed to load. ---")