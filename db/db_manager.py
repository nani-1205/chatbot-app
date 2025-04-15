# db/db_manager.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
import os
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()

# --- MongoDB Configuration ---
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "chatbot_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "chat_history")

# --- Initialize MongoDB Client ---
client = None
db = None
chat_collection = None

if MONGODB_URI:
    try:
        print(f"Connecting to MongoDB at: {MONGODB_URI.split('@')[-1]}...") # Avoid logging credentials
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000) # 5 second timeout
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        db = client[DATABASE_NAME]
        chat_collection = db[COLLECTION_NAME]
        print("MongoDB connection successful.")
        # Optionally create index for faster history retrieval
        # chat_collection.create_index([("timestamp", -1)])
    except ConfigurationError as ce:
         print(f"MongoDB Configuration Error: Invalid URI or options? {ce}")
         client = db = chat_collection = None
    except ConnectionFailure as cf:
        print(f"MongoDB Connection Error: Could not connect to server. Check URI, firewall, and DB status. {cf}")
        client = db = chat_collection = None
    except Exception as e:
        print(f"An unexpected error occurred during MongoDB initialization: {e}\n{traceback.format_exc()}")
        client = db = chat_collection = None # Ensure state is consistent on error
else:
    print("MONGODB_URI not found in environment variables. Database logging disabled.")


def save_chat_log(question: str, response: str):
    """Saves the question and response to MongoDB if connected."""
    if not chat_collection:
        print("MongoDB collection not available. Skipping chat log save.")
        return False

    log_entry = {
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow() # Use UTC for consistency
    }
    try:
        result = chat_collection.insert_one(log_entry)
        print(f"Chat log saved to MongoDB with ID: {result.inserted_id}")
        return True
    except OperationFailure as of:
         print(f"MongoDB Operation Failure (e.g., auth issue): {of}")
    except Exception as e:
        print(f"Error saving chat log to MongoDB: {e}\n{traceback.format_exc()}")
    return False

def get_chat_history(limit: int = 10):
    """Retrieves the latest chat history from MongoDB if connected."""
    if not chat_collection:
        print("MongoDB collection not available. Cannot retrieve history.")
        return [] # Return empty list if no connection

    try:
        # Sort by timestamp descending and limit results
        history = list(chat_collection.find().sort([('timestamp', -1)]).limit(limit))
        print(f"Retrieved {len(history)} chat history entries from MongoDB.")
        # Convert ObjectId to string if needed for JSON serialization later, though Flask handles it
        # for entry in history:
        #     entry['_id'] = str(entry['_id'])
        return history
    except Exception as e:
        print(f"Error retrieving chat history from MongoDB: {e}\n{traceback.format_exc()}")
        return [] # Return empty list on error

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
            for log in reversed(history): # Print oldest first for readability here
                 ts = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
                 print(f"- [{ts}] Q: {log['question']} | A: {log['response'][:50]}...")
        else:
            print("No history retrieved or an error occurred.")
    else:
        print("MongoDB connection not established. Skipping tests.")
    print("--- Test Complete ---")