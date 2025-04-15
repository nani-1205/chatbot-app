# app.py
from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
import traceback # For detailed error logging

# Load environment variables early, before other imports that might need them
load_dotenv()

# --- Import custom modules AFTER loading .env ---
# Data processing and vector store
from data_processing.data_loader import process_and_load_data_from_s3
from data_processing.vector_store_manager import get_vector_store, needs_initial_processing

# LLM interaction (using the Langchain RAG approach)
from llm.gemini_api import generate_response

# Database interaction
from db.db_manager import save_chat_log, get_chat_history

# --- Flask App Initialization ---
app = Flask(__name__)
# Configure static and template folders relative to the app's location
app.static_folder = os.path.join(os.path.dirname(__file__), 'frontend/static')
app.template_folder = os.path.join(os.path.dirname(__file__), 'frontend/templates')

# --- Global variable for the vector store ---
# This will hold the loaded ChromaDB instance
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
    # process_and_load_data_from_s3() internally calls needs_initial_processing()
    try:
        print("Checking and processing S3 data if necessary...")
        process_and_load_data_from_s3()
        print("S3 data processing check complete.")
    except Exception as e:
        error_msg = f"ERROR during initial data processing: {e}\n{traceback.format_exc()}"
        print(error_msg)
        # Depending on severity, you might set initialization_error here
        # For now, we'll try loading the vector store anyway, maybe it exists from a previous run.
        initialization_error = "Warning: Error during S3 data processing check. Vector store might be incomplete or outdated."


    # 2. Load the vector store into memory for querying
    try:
        print("Loading vector store...")
        vector_store = get_vector_store() # This function now handles loading from disk
        if vector_store:
            # Perform a simple check to confirm it's usable
            count = vector_store._collection.count()
            print(f"Vector store loaded successfully. Contains {count} document chunks.")
            if count == 0 and not initialization_error:
                 initialization_error = "Warning: Vector store loaded but is empty. Check S3 processing and data."
        else:
            # This case shouldn't happen if get_vector_store raises errors, but check anyway
            error_msg = "ERROR: Failed to get a vector store instance from get_vector_store()."
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
# Run this when the script is executed.
# Note on Gunicorn/multiple workers: This might run per worker.
# For heavy initial processing, consider a separate setup script or lazy loading.
initialize_app()

# --- Flask Routes ---
@app.route("/")
def index():
    """Serves the main chat page."""
    # Retrieve limited history for display, show newest first
    try:
        history = get_chat_history(limit=15) # Get latest 15 Q&A pairs
        # Pass any initialization warnings/errors to the template if needed
        init_error_display = initialization_error if initialization_error else ""
    except Exception as e:
        print(f"Error getting chat history: {e}")
        history = []
        init_error_display = initialization_error if initialization_error else "Error loading chat history."

    # Render the template, passing history (reversed) and potential init errors
    return render_template('index.html', chat_history=reversed(history), initialization_error=init_error_display)

@app.route("/get_response", methods=['POST'])
def get_chatbot_response():
    """Handles the AJAX request for getting a chatbot response."""
    # Check if initialization failed critically
    if vector_store is None or "CRITICAL ERROR" in (initialization_error or ""):
         print("Error: Vector store not available due to initialization failure.")
         return jsonify({'response': f'Sorry, the chatbot is not available due to an initialization error: {initialization_error}. Please check the server logs.'}), 503 # Service Unavailable

    user_query = request.form.get('user_query', '').strip()
    if not user_query:
        return jsonify({'response': 'Please enter a question.'}), 400 # Bad Request

    print(f"Received query: \"{user_query}\"")
    try:
        # Generate response using the Langchain RAG pipeline
        response_text = generate_response(user_query, vector_store)

        # Save interaction to MongoDB
        try:
            save_chat_log(user_query, response_text)
        except Exception as db_err:
            print(f"Error saving chat log to MongoDB: {db_err}")
            # Continue serving the response even if DB save fails

        return jsonify({'response': response_text})

    except Exception as e:
        # Log the full error for debugging
        print(f"Error generating response for query '{user_query}': {e}")
        print(traceback.format_exc())
        # Return a generic error to the user
        return jsonify({'response': 'Sorry, an internal error occurred while processing your request. Please try again later.'}), 500 # Internal Server Error

# --- Main Execution Block ---
if __name__ == '__main__':
    # Runs the Flask development server.
    # For production, use a WSGI server like Gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 app:app
    # Debug mode enables auto-reloading which can be useful in development,
    # but be aware it might re-trigger initialization.
    app.run(debug=True, host='0.0.0.0', port=5000)