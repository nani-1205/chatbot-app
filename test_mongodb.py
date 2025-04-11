import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI") # Use the URI from your .env file
if not mongodb_uri:
    print("Error: MONGODB_URI not found in .env file. Please check your .env configuration.")
else:
    try:
        client = pymongo.MongoClient(mongodb_uri)
        client.admin.command('ping') # Send a ping command to test connection
        print("Successfully connected to MongoDB!")
        print(client.server_info()) # Print server info to confirm connection
    except pymongo.errors.ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")