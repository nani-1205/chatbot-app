# db/db_manager.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
import os
from dotenv import load_dotenv
from datetime import datetime
import traceback
import urllib.parse

load_dotenv()

# --- Get individual MongoDB Configuration components ---
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_PORT = os.getenv("MONGODB_PORT")
MONGODB_AUTH_SOURCE = os.getenv("MONGODB_AUTH_SOURCE", "admin")
DATABASE_NAME = os.getenv("DATABASE_NAME", "chatbot_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "chat_history")

# --- Construct MongoDB URI from components ---
constructed_uri = None
log_uri = "mongodb://<details_missing>" # Default log URI if construction fails
if MONGODB_HOST and MONGODB_PORT and MONGODB_USERNAME and MONGODB_PASSWORD:
    try:
        encoded_username = urllib.parse.quote_plus(MONGODB_USERNAME)
        encoded_password = urllib.parse.quote_plus(MONGODB_PASSWORD)
        constructed_uri = (
            f"mongodb://{encoded_username}:{encoded_password}@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/"
            f"?authSource={MONGODB_AUTH_SOURCE}&serverSelectionTimeoutMS=10000" # Added timeout to URI
        )
        log_uri = ( # For logging without password
            f"mongodb://{encoded_username}:<PASSWORD>@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/"
            f"?authSource={MONGODB_AUTH_SOURCE}"
        )
        print(f"Constructed MongoDB URI (Password Masked): {log_uri}")
    except Exception as e:
        print(f"Error constructing MongoDB URI: {e}")
        constructed_uri = None
elif MONGODB_HOST and MONGODB_PORT: # Support connection without auth
     constructed_uri = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/?serverSelectionTimeoutMS=10000"
     log_uri = constructed_uri # Safe to log as no password
     print(f"Constructed MongoDB URI (No Auth): {log_uri}")
else:
    print("MongoDB connection details (HOST, PORT mandatory, USERNAME, PASSWORD optional) missing or incomplete.")


# --- Initialize MongoDB Client ---
client = None
db = None
chat_collection = None

# Use the constructed_uri for connection attempt
if constructed_uri:
    try:
        print(f"Attempting to connect to MongoDB server at {MONGODB_HOST}:{MONGODB_PORT}...")
        client = MongoClient(constructed_uri) # URI now contains timeout
        # The ismaster command is cheap and confirms server reachability.
        client.admin.command('ismaster')
        print("MongoDB server reached successfully.")

        # --- Check/Create Database and Collection ---
        db = client[DATABASE_NAME]
        print(f"Selected database: '{DATABASE_NAME}'")

        collection_names = db.list_collection_names()
        if COLLECTION_NAME not in collection_names:
            print(f"Collection '{COLLECTION_NAME}' not found in database '{DATABASE_NAME}'.")
            # MongoDB implicitly creates collections on first write or index creation.
            # We'll explicitly create an index which also creates the collection.
            print(f"Attempting to create collection '{COLLECTION_NAME}' by ensuring index...")
            # No need for db.create_collection(COLLECTION_NAME) if creating index
        else:
            print(f"Collection '{COLLECTION_NAME}' found in database '{DATABASE_NAME}'.")

        chat_collection = db[COLLECTION_NAME] # Get the collection object

        # --- Ensure Index Exists ---
        # Creating an index is idempotent (safe to run multiple times)
        # and will implicitly create the collection if it doesn't exist.
        try:
            print(f"Ensuring 'timestamp' index exists on '{COLLECTION_NAME}'...")
            # Create index on timestamp field, descending order for fast retrieval of recent items
            chat_collection.create_index([("timestamp", -1)], name="timestamp_desc_idx")
            print("'timestamp' index ensured successfully.")
        except OperationFailure as opf:
            print(f"Warning: Could not ensure 'timestamp' index (may require specific permissions or index exists incompatibly): {opf}")
        # --- End Check/Create ---

        print(f"MongoDB connection and collection '{DATABASE_NAME}.{COLLECTION_NAME}' setup complete.")

    except ConfigurationError as ce:
         print(f"MongoDB Configuration Error: Invalid URI constructed or options? URI used: {log_uri}. Error: {ce}")
         client = db = chat_collection = None
    except OperationFailure as of:
        print(f"MongoDB Operation Failure during setup (Authentication likely failed or insufficient permissions for listing/indexing). Check credentials and DB user roles. Error: {of}")
        client = db = chat_collection = None
    except ConnectionFailure as cf:
        print(f"MongoDB Connection Error: Could not connect to server {MONGODB_HOST}:{MONGODB_PORT}. Check host, port, firewall, and DB status. Error: {cf}")
        client = db = chat_collection = None
    except Exception as e:
        print(f"An unexpected error occurred during MongoDB initialization: {e}\n{traceback.format_exc()}")
        client = db = chat_collection = None
else:
    print("MongoDB URI could not be constructed. Database logging disabled.")


def save_chat_log(question: str, response: str):
    """Saves the question and response to MongoDB if connected."""
    if not chat_collection:
        print("MongoDB collection not available. Skipping chat log save.")
        return False

    log_entry = {
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow()
    }
    try:
        result = chat_collection.insert_one(log_entry)
        # print(f"Chat log saved with ID: {result.inserted_id}") # Can be verbose, uncomment if needed
        return True
    except OperationFailure as of:
         print(f"Error saving chat log (MongoDB Operation Failure - check write permissions): {of}")
    except Exception as e:
        print(f"Error saving chat log to MongoDB: {e}\n{traceback.format_exc()}")
    return False

def get_chat_history(limit: int = 10):
    """Retrieves the latest chat history from MongoDB if connected."""
    if not chat_collection:
        print("MongoDB collection not available. Cannot retrieve history.")
        return []

    try:
        # Use the index for efficient sorting
        history = list(chat_collection.find().sort([('timestamp', -1)]).limit(limit))
        return history
    except Exception as e:
        print(f"Error retrieving chat history from MongoDB: {e}\n{traceback.format_exc()}")
        return []

# Example usage (optional)
if __name__ == '__main__':
     print("\n--- Testing db_manager ---")
     if chat_collection:
         print("Attempting to save a test log...")
         save_chat_log("Test question from db_manager", "Test response from db_manager")
         print("\nAttempting to retrieve history...")
         history = get_chat_history(limit=5)
         if history:
             print("\nRetrieved History:")
             for log in reversed(history):
                  ts = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
                  print(f"- [{ts}] Q: {log['question']} | A: {log['response'][:50]}...")
         else:
             print("No history retrieved or an error occurred.")
     else:
         print("MongoDB connection not established. Skipping tests.")
     print("--- Test Complete ---")