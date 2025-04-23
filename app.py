# app.py

# <<< --- SQLITE PATCH SHOULD BE AT THE VERY TOP --- >>>
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("Successfully patched sqlite3 with pysqlite3-binary.")
except ImportError:
    print("pysqlite3-binary not found or import failed, falling back to system sqlite3.")
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
from data_processing.data_loader import process_and_load_data_from_s3
from data_processing.vector_store_manager import get_vector_store
# --- MODIFIED: Import the constant from gemini_api ---
from llm.gemini_api import generate_response, RAG_REFUSAL_MESSAGE
# --- MODIFIED: Import the updated save_chat_log ---
from db.db_manager import save_chat_log, get_chat_history

# --- Flask App Initialization ---
app = Flask(__name__)
app.static_folder = os.path.join(os.path.dirname(__file__), 'frontend/static')
app.template_folder = os.path.join(os.path.dirname(__file__), 'frontend/templates')

# --- Global variable for the vector store & initialization status ---
vector_store = None
initialization_error = None # Store any critical initialization errors

# --- Application Initialization Function ---
def initialize_app():
    """Initializes the application state (vector store, DB connection etc.)."""
    global vector_store, initialization_error
    print("--- Starting Application Initialization ---")
    # --- Step 1: Data Processing & Vector Store ---
    try:
        print("Step 1: Checking/Processing S3 data and populating vector store (if empty)...")
        process_and_load_data_from_s3() # Checks internally if needed
        print("Step 1a: Loading vector store from disk...")
        vector_store = get_vector_store() # Load or get existing store
        if vector_store:
            count = vector_store._collection.count()
            print(f"Step 1b: Vector store loaded successfully. Contains {count} document chunks.")
            if count == 0: initialization_error = "Warning: Vector store is empty."
        else:
            error_msg = "CRITICAL ERROR: Failed to load vector store."
            print(error_msg)
            initialization_error = error_msg
    except Exception as e:
        error_msg = f"CRITICAL ERROR during vector store initialization: {e}\n{traceback.format_exc()}"
        print(error_msg)
        initialization_error = error_msg
        vector_store = None

    # --- Step 2: Database connection (handled within db_manager.py) ---
    # db_manager attempts connection upon import/initialization. We just check its status later.
    print("Step 2: Database connection attempted during db_manager initialization.")

    print("--- Application Initialization Complete ---")
    if initialization_error:
        print(f"Initialization completed with issues: {initialization_error}")

# --- Run Initialization ---
initialize_app()

# --- Flask Routes ---
@app.route("/")
def index():
    """Serves the main chat page."""
    history = []
    db_error = None
    try:
        history = get_chat_history(limit=15)
    except Exception as e:
        print(f"Error getting chat history from DB: {e}")
        db_error = "Could not load recent chat history."

    display_error = initialization_error or db_error
    if initialization_error and db_error:
         display_error = f"{initialization_error} | {db_error}"

    return render_template('index.html',
                           chat_history=reversed(history),
                           initialization_error=display_error)

@app.route("/get_response", methods=['POST'])
def get_chatbot_response():
    """Handles the AJAX request for getting a chatbot response."""
    # --- Critical Initialization Check ---
    if vector_store is None or "CRITICAL ERROR" in (initialization_error or ""):
         print("Error: Cannot process request. Vector store not available.")
         return jsonify({'response': f'Sorry, the chatbot is temporarily unavailable due to a setup error: {initialization_error}. Please contact the administrator.'}), 503

    # --- Get User Query ---
    user_query = request.form.get('user_query', '').strip()
    if not user_query:
        return jsonify({'response': 'Please enter a question.'}), 400

    print(f"Received query: \"{user_query}\"")

    # --- Initialize flags ---
    response_text = ""
    violation_type = None
    severity = None

    # --- Generate Response using RAG ---
    try:
        response_text = generate_response(user_query, vector_store)

        # --- MODIFIED: Check for RAG Refusal ---
        # Use .strip() for robust comparison
        if response_text.strip() == RAG_REFUSAL_MESSAGE.strip():
            print(f"Query classified as OUT_OF_CONTEXT: '{user_query[:50]}...'")
            violation_type = "OUT_OF_CONTEXT"
            # Define severity level - 'INFO' seems appropriate as it's not malicious
            severity = "INFO"
            # For this implementation, we still return the refusal message.
            # A future enhancement could trigger a general LLM call here.

        # --- Save to DB (including potential flags) ---
        try:
            # Call the updated save_chat_log with potential flags
            save_chat_log(
                question=user_query,
                response=response_text,
                violation_type=violation_type, # Will be None if not out-of-context
                severity=severity             # Will be None if not out-of-context
            )
        except Exception as db_err:
            # Log DB error but don't fail the user response if generation worked
            print(f"Warning: Failed to save chat log to MongoDB: {db_err}")

        # --- Return Response ---
        return jsonify({'response': response_text})

    # --- Handle Errors during Generation ---
    except Exception as e:
        print(f"Error generating response for query '{user_query}': {e}")
        print(traceback.format_exc())
        # Attempt to save the error occurrence to DB
        try:
             save_chat_log(
                 question=user_query,
                 response=f"ERROR during generation: Check server logs.", # Keep user message clean
                 violation_type="GENERATION_ERROR",
                 severity="ERROR" # Clearly mark this as an error
             )
        except Exception as db_save_err:
             print(f"Additionally failed to save generation error log to DB: {db_save_err}")

        # Return 500 Internal Server Error to the user
        return jsonify({'response': 'Sorry, an internal error occurred while processing your request. Please try again later or contact support if the problem persists.'}), 500

# --- Health Check Endpoint (Optional but Recommended) ---
@app.route("/health")
def health_check():
    """Simple health check endpoint."""
    # Check DB connection status via the global db object from db_manager
    from db.db_manager import db as db_conn_status # Import locally to avoid circular dependency issues at top level
    status = {
        "status": "OK",
        "vector_store_loaded": vector_store is not None,
        "initialization_error": initialization_error or "None",
        "database_connected": db_conn_status is not None
    }
    http_status = 200
    if vector_store is None or "CRITICAL" in (initialization_error or "") or db_conn_status is None:
        status["status"] = "Error"
        http_status = 503 # Service Unavailable

    return jsonify(status), http_status

# --- Main Execution Block ---
if __name__ == '__main__':
    # Runs the Flask development server.
    use_debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"Running Flask app with debug mode: {use_debug_mode}")
    # Use host='0.0.0.0' to make it accessible externally (e.g., on EC2)
    # Use port 5000 or another preferred port
    app.run(debug=use_debug_mode, host='0.0.0.0', port=5000)