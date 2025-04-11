# db/db_manager.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
import urllib.parse # Make sure this line is present

load_dotenv()

username = urllib.parse.quote_plus(os.getenv("MONGODB_USERNAME", 'jagan')) # Default username if not in .env
password = urllib.parse.quote_plus(os.getenv("MONGODB_PASSWORD", 'Saijagan12')) # Default password if not in .env
hostname = os.getenv("MONGODB_HOST", '18.60.117.100') # Default host if not in .env
port = os.getenv("MONGODB_PORT", '27017') # Default port if not in .env
auth_source = os.getenv("MONGODB_AUTH_SOURCE", 'admin') # Default authSource if not in .env

mongodb_uri = f"mongodb://{username}:{password}@{hostname}:{port}/?authSource={auth_source}"

client = MongoClient(mongodb_uri)
db = client[DATABASE_NAME]
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