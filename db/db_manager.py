# db/db_manager.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
import urllib.parse

load_dotenv()

username = urllib.parse.quote_plus(os.getenv("MONGODB_USERNAME", 'jagan'))
password = urllib.parse.quote_plus(os.getenv("MONGODB_PASSWORD", 'Saijagan12'))
hostname = os.getenv("MONGODB_HOST", '18.60.117.100')
port = os.getenv("MONGODB_PORT", '27017')
auth_source = os.getenv("MONGODB_AUTH_SOURCE", 'admin')
DATABASE_NAME = os.getenv("DATABASE_NAME", "chatbot_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "chat_history") # Added to .env and here

mongodb_uri = f"mongodb://{username}:{password}@{hostname}:{port}/?authSource={auth_source}"

client = MongoClient(mongodb_uri)

# Check if database exists, create if not (MongoDB creates DB on first use, so explicit create is often not needed)
db_list = client.list_database_names()
if DATABASE_NAME not in db_list:
    print(f"Database '{DATABASE_NAME}' not found. MongoDB will create it on first use.")
else:
    print(f"Database '{DATABASE_NAME}' found.")

db = client[DATABASE_NAME]

# Check if collection exists, create if not (MongoDB creates collection on first use)
collection_list = db.list_collection_names()
if COLLECTION_NAME not in collection_list:
    print(f"Collection '{COLLECTION_NAME}' not found. MongoDB will create it on first use.")
else:
    print(f"Collection '{COLLECTION_NAME}' found.")

chat_collection = db[COLLECTION_NAME]

def save_chat_log(question, response):
    """Saves the question and response to MongoDB."""
    log_entry = {
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow()
    }
    chat_collection.insert_one(log_entry)

def get_chat_history(limit=10):
    """Retrieves the latest chat history from MongoDB."""
    history = list(chat_collection.find().sort([('timestamp', -1)]).limit(limit))
    return history

if __name__ == '__main__':
    # Example usage (for testing)
    save_chat_log("Hello chatbot!", "Hello user!")
    history = get_chat_history()
    print("Chat History:")
    for log in history:
        print(f"Q: {log['question']}")
        print(f"A: {log['response']}")
        print(f"Time: {log['timestamp']}")