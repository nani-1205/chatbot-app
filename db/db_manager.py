# db/db_manager.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
import os
from dotenv import load_dotenv
from datetime import datetime
import traceback
import urllib.parse # For encoding username/password

# Load environment variables from .env file
load_dotenv()

# --- Get individual MongoDB Configuration components from environment ---
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_PORT = os.getenv("MONGODB_PORT")
# Default authSource to 'admin' if not specified in .env
MONGODB_AUTH_SOURCE = os.getenv("MONGODB_AUTH_SOURCE", "admin")
DATABASE_NAME = os.getenv("DATABASE_NAME", "chatbot_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "chat_history")

# --- Construct MongoDB URI from components ---
constructed_uri = None
log_uri = "mongodb://<details_missing_or_no_auth>" # Default log URI
if MONGODB_HOST and MONGODB_PORT and MONGODB_USERNAME and MONGODB_PASSWORD:
    # Case: Full credentials provided
    try:
        # URL-encode username and password to handle special characters
        encoded_username = urllib.parse.quote_plus(MONGODB_USERNAME)
        encoded_password = urllib.parse.quote_plus(MONGODB_PASSWORD)

        # Construct the full URI including authSource and a reasonable timeout
        constructed_uri = (
            f"mongodb://{encoded_username}:{encoded_password}@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/"
            f"?authSource={MONGODB_AUTH_SOURCE}&serverSelectionTimeoutMS=10000" # 10 sec timeout
        )
        # Create a version for logging that masks the password
        log_uri = (
            f"mongodb://{encoded_username}:<PASSWORD>@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/"
            f"?authSource={MONGODB_AUTH_SOURCE}"
        )
        print(f"Constructed MongoDB URI (Password Masked): {log_uri}")

    except Exception as e:
        print(f"Error constructing MongoDB URI: {e}")
        constructed_uri = None

elif MONGODB_HOST and MONGODB_PORT:
    # Case: Host and Port provided, but no username/password (attempt connection without auth)
     constructed_uri = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/?serverSelectionTimeoutMS=10000"
     log_uri = constructed_uri # Safe to log as no password
     print(f"Constructed MongoDB URI (No Authentication): {log_uri}")

else:
    # Case: Insufficient details provided
    print("MongoDB connection details incomplete (HOST, PORT required; USERNAME, PASSWORD optional).")


# --- Initialize MongoDB Client, Database, and Collection Variables ---
client = None
db = None
chat_collection = None

# --- Attempt Connection and Setup ---
if constructed_uri:
    try:
        print(f"Attempting to connect to MongoDB server at {MONGODB_HOST}:{MONGODB_PORT}...")
        # Initialize the MongoClient with the constructed URI
        client = MongoClient(constructed_uri)

        # Verify server reachability using a lightweight command
        client.admin.command('ismaster')
        print("MongoDB server reached successfully.")

        # Get the database object
        db = client[DATABASE_NAME]
        print(f"Selected database: '{DATABASE_NAME}'")

        # --- Check if Collection Exists ---
        collection_names = db.list_collection_names()
        if COLLECTION_NAME not in collection_names:
            print(f"Collection '{COLLECTION_NAME}' not found. It will be created implicitly by index creation or first write.")
            # No explicit creation needed here, index creation below handles it.
        else:
            print(f"Collection '{COLLECTION_NAME}' found in database '{DATABASE_NAME}'.")

        # Get the collection object
        chat_collection = db[COLLECTION_NAME]

        # --- Ensure Timestamp Index Exists ---
        # This is idempotent (safe to run multiple times) and crucial for performance.
        # It also implicitly creates the collection if it doesn't exist.
        try:
            index_name = "timestamp_desc_idx"
            print(f"Ensuring '{index_name}' index exists on '{COLLECTION_NAME}'...")
            chat_collection.create_index([("timestamp", -1)], name=index_name)
            print(f"'{index_name}' index ensured successfully.")
        except OperationFailure as opf:
            # Log a warning but don't necessarily stop the app if index creation fails
            print(f"Warning: Could not ensure '{index_name}' index (may require specific permissions or index exists incompatibly): {opf}")
        # --- End Index Check ---

        # If we reached here, setup is mostly successful
        print(f"MongoDB connection and collection '{DATABASE_NAME}.{COLLECTION_NAME}' setup complete.")

    except ConfigurationError as ce:
         # Error related to URI format or options
         print(f"MongoDB Configuration Error: Invalid URI or options? URI used (masked): {log_uri}. Error: {ce}")
         client = db = chat_collection = None # Reset state
    except OperationFailure as of:
        # Error during operations like listing collections or creating index (often auth/permissions)
        print(f"MongoDB Operation Failure during setup (Authentication failed or insufficient permissions?). Check credentials and DB user roles for '{DATABASE_NAME}'. Error: {of}")
        client = db = chat_collection = None # Reset state
    except ConnectionFailure as cf:
        # Error connecting to the server itself
        print(f"MongoDB Connection Error: Could not connect to server {MONGODB_HOST}:{MONGODB_PORT}. Check network, firewall, and DB server status. Error: {cf}")
        client = db = chat_collection = None # Reset state
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during MongoDB initialization: {e}\n{traceback.format_exc()}")
        client = db = chat_collection = None # Reset state
else:
    # If URI couldn't be constructed in the first place
    print("MongoDB URI could not be constructed. Database logging disabled.")


# --- Database Interaction Functions ---

def save_chat_log(question: str, response: str):
    """Saves the question and response to MongoDB if the collection is available."""
    # Use 'is None' check
    if chat_collection is None:
        print("MongoDB collection not available. Skipping chat log save.")
        return False

    log_entry = {
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow() # Use UTC timestamp
    }
    try:
        result = chat_collection.insert_one(log_entry)
        # print(f"Chat log saved with ID: {result.inserted_id}") # Optional: uncomment for verbose logging
        return True
    except OperationFailure as of:
         # Error during the insert operation (e.g., write permissions)
         print(f"Error saving chat log (MongoDB Operation Failure - check write permissions for '{DATABASE_NAME}.{COLLECTION_NAME}'): {of}")
    except Exception as e:
        print(f"Error saving chat log to MongoDB: {e}\n{traceback.format_exc()}")
    return False

def get_chat_history(limit: int = 10):
    """Retrieves the latest chat history documents from MongoDB if the collection is available."""
    # Use 'is None' check
    if chat_collection is None:
        print("MongoDB collection not available. Cannot retrieve history.")
        return [] # Return empty list if no connection

    try:
        # Retrieve documents, sorting by timestamp descending using the index
        history = list(chat_collection.find().sort([('timestamp', -1)]).limit(limit))
        # print(f"Retrieved {len(history)} chat history entries.") # Optional: uncomment for verbose logging
        return history
    except Exception as e:
        print(f"Error retrieving chat history from MongoDB: {e}\n{traceback.format_exc()}")
        return [] # Return empty list on error

# --- Test Block (Optional) ---
# This code runs only when the script is executed directly (e.g., python db/db_manager.py)
if __name__ == '__main__':
     print("\n--- Testing db_manager Module ---")
     # Use 'is not None' check
     if chat_collection is not None:
         print("\nAttempting to save a test log...")
         save_success = save_chat_log("Test question from db_manager execution",
                                      "Test response from db_manager execution")
         if save_success:
             print("Test log saved successfully (check MongoDB).")
         else:
             print("Failed to save test log.")

         print("\nAttempting to retrieve history...")
         history = get_chat_history(limit=5)
         if history:
             print(f"\nRetrieved {len(history)} Recent History Entries:")
             # Print newest first as they are retrieved
             for i, log in enumerate(history):
                  ts = log.get('timestamp', datetime.min).strftime('%Y-%m-%d %H:%M:%S UTC')
                  q = log.get('question', 'N/A')
                  a = log.get('response', 'N/A')[:60] # Truncate long answers
                  print(f"{i+1}. [{ts}] Q: {q} | A: {a}...")
         else:
             print("No history retrieved or an error occurred during retrieval.")
     else:
         print("\nMongoDB connection not established. Cannot perform DB operations.")
     print("\n--- db_manager Test Complete ---")