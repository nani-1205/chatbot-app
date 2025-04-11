import pymongo
import os
from dotenv import load_dotenv
import urllib.parse  # Import urllib.parse

load_dotenv()

username = urllib.parse.quote_plus(os.getenv("MONGODB_USERNAME", 'jagan')) # Get username from .env or default
password = urllib.parse.quote_plus(os.getenv("MONGODB_PASSWORD", 'Saijagan12')) # Get password from .env or default
hostname = os.getenv("MONGODB_HOST", '18.60.117.100') # Get hostname from .env or default
port = os.getenv("MONGODB_PORT", '27017') # Get port from .env or default
auth_source = os.getenv("MONGODB_AUTH_SOURCE", 'admin') # Get authSource from .env or default

mongodb_uri = f"mongodb://{username}:{password}@{hostname}:{port}/?authSource={auth_source}"

if not mongodb_uri: # This check is now less relevant as we construct URI from parts, but keep it for safety
    print("Error: Could not construct MONGODB_URI. Please check your .env configuration.")
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