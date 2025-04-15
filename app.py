# app.py

# <<< --- ADD THIS SQLITE PATCH AT THE VERY TOP --- >>>
try:
    # Try to import the binary pysqlite3 module
    # This module needs to be installed: pip install pysqlite3-binary
    __import__('pysqlite3')
    import sys
    # Swap the stdlib sqlite3 module with the binary one
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("Successfully patched sqlite3 with pysqlite3-binary.")
except ImportError:
    print("pysqlite3-binary not found or import failed, falling back to system sqlite3.")
    # Check the system version if fallback occurs (optional)
    try:
        import sqlite3
        print(f"System sqlite3 version: {sqlite3.sqlite_version}")
        if sqlite3.sqlite_version_info < (3, 35, 0):
             print("Warning: System sqlite3 version is older than 3.35.0. ChromaDB might not work correctly.")
    except Exception as e:
        print(f"Could not check system sqlite3 version: {e}")
    pass
# <<< --- END SQLITE PATCH --- >>>

# --- Standard Imports ---
from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
import traceback # For detailed error logging

# Load environment variables AFTER the patch, but BEFORE other imports using them
load_dotenv()

# --- Import custom modules ---
# These imports might trigger ChromaDB initialization, so they must come AFTER the patch
from data_processing.data_loader import process_and_load_data_from_s3
from data_processing.vector_store_manager import get_vector_store
from llm.gemini_api import generate_response # Uses Langchain RAG
from db.db_manager import save_chat_log, get_chat_history

# --- Flask App Initialization ---
app = Flask(__name__)
# Configure static and template folders relative to the app's location
app.static_folder = os.path.join(os.path.dirname(__file__), 'frontend/static')
app.template_folder = os.path.join(os.path.dirname(__file__), 'frontend/templates')
# Optional: Add a secret key for Flask session management if needed later
# app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))


# --- Global variable for the vector store & initialization status ---
vector_store = None
initialization_error = None # Store any critical initialization errors

# --- Application Initialization Function ---
def initialize_app():
    """
    Initializes the application:
    1. Checks if data processing from S3 is needed and runs it.
    2. Loads the vector store.
    Stores any critical errors in 'initialization_error'.
    """
    global vector_store, initialization_error
    print("--- Starting Application Initialization ---")

    # 1. Process data from S3 and populate vector store (if needed)
    # This function now includes the check 'needs_initial_processing()'
    try:
        print("Step 1: Checking/Processing S3 data and populating vector store (if empty)...")
        process_and_load_data_from_s3()
        print("Step 1: S3 data processing check complete.")
    except Exception as e:
        error_msg = f"ERROR during S3 data processing check: {e}\n{traceback.format_exc()}"
        print(error_msg)
        # Store as a non-critical warning for now, maybe store exists
        initialization_error = "Warning: Error during S3 data processing. Vector store might be incomplete or outdated."

    # 2. Load the vector store into memory for querying
    try:
        print("Step 2: Loading vector store from disk...")
        vector_store = get_vector_store() # This function now handles loading from disk
        if vector_store:
            count = vector_store._collection.count()
            print(f"Step 2: Vector store loaded successfully. Contains {count} document chunks.")
            if count == 0 and not initialization_error: # If no previous error, but store is empty
                 initialization_error = "Warning: Vector store loaded but is empty. Check S3 bucket contents or data processing logs."
        else:
            # get_vector_store should have printed errors, but set a critical flag here
            error_msg = "CRITICAL ERROR: Failed to load or initialize vector store instance."
            print(error_msg)
            initialization_error = error_msg # Critical error

    except Exception as e:
        error_msg = f"CRITICAL ERROR loading vector store: {e}\n{traceback.format_exc()}"
        print(error_msg)
        initialization_error = error_msg # Store critical error
        vector_store = None # Ensure vector_store is None if loading fails

    print("--- Application Initialization Complete ---")
    if initialization_error:
        print(f"Initialization completed with issues: {initialization_error}")

# --- Run Initialization ---
# This runs once when the Flask app starts (or per worker in multi-worker setups like Gunicorn).
initialize_app()

# --- Flask Routes ---
@app.route("/")
def index():
    """Serves the main chat page."""
    history = []
    db_error = None
    try:
        # Retrieve limited history for display, show newest first
        history = get_chat_history(limit=15) # Get latest 15 Q&A pairs
    except Exception as e:
        print(f"Error getting chat history from DB: {e}")
        db_error = "Could not load recent chat history from the database."

    # Combine potential DB error with initialization error
    display_error = initialization_error or db_error # Show init error first if it exists
    if initialization_error and db_error:
         display_error = f"{initialization_error} | {db_error}" # Show both if both exist

    return render_template('index.html',
                           chat_history=reversed(history), # Render newest first at bottom
                           initialization_error=display_error)

@app.route("/get_response", methods=['POST'])
def get_chatbot_response():
    """Handles the AJAX request for getting a chatbot response."""
    # --- Critical Initialization Check ---
    if vector_store is None or "CRITICAL ERROR" in (initialization_error or ""):
         print("Error: Cannot process request. Vector store not available due to initialization failure.")
         # Return 503 Service Unavailable
         return jsonify({'response': f'Sorry, the chatbot is temporarily unavailable due to a setup error: {initialization_error}. Please contact the administrator.'}), 503

    # --- Get User Query ---
    user_query = request.form.get('user_query', '').strip()
    if not user_query:
        return jsonify({'response': 'Please enter a question.'}), 400 # Bad Request

    print(f"Received query: \"{user_query}\"")

    # --- Generate Response ---
    try:
        response_text = generate_response(user_query, vector_store)

        # --- Save to DB (Best effort) ---
        try:
            save_chat_log(user_query, response_text)
        except Exception as db_err:
            print(f"Warning: Failed to save chat log to MongoDB: {db_err}")
            # Do not fail the request if DB save fails

        # --- Return Response ---
        return jsonify({'response': response_text})

    # --- Handle Errors during Generation ---
    except Exception as e:
        print(f"Error generating response for query '{user_query}': {e}")
        print(traceback.format_exc())
        # Return 500 Internal Server Error
        return jsonify({'response': 'Sorry, an internal error occurred while processing your request. Please try again later or contact support if the problem persists.'}), 500

# --- Health Check Endpoint (Optional) ---
@app.route("/health")
def health_check():
    """Simple health check endpoint."""
    status = {
        "status": "OK",
        "vector_store_loaded": vector_store is not None,
        "initialization_error": initialization_error or "None",
        "database_connected": db is not None # Check if db object exists from db_manager
    }
    http_status = 200
    if vector_store is None or "CRITICAL" in (initialization_error or "") or db is None:
        status["status"] = "Error"
        http_status = 503 # Service Unavailable

    return jsonify(status), http_status

# --- Main Execution Block ---
if __name__ == '__main__':
    # Runs the Flask development server.
    # For production, use a WSGI server like Gunicorn:
    # Example: gunicorn --workers 2 --bind 0.0.0.0:5000 app:app --log-level debug
    # Debug mode enables auto-reloading and detailed error pages (disable in production)
    use_debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"Running Flask app with debug mode: {use_debug_mode}")
    app.run(debug=use_debug_mode, host='0.0.0.0', port=5000)