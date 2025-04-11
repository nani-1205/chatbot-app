# db/db_manager.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "chatbot_db" # You can configure this in .env if needed
COLLECTION_NAME = "chat_history" # You can configure this in .env if needed

client = MongoClient(MONGODB_URI)
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