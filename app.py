# app.py
from flask import Flask, render_template, request, jsonify
from data_processing.data_loader import load_data_from_s3
from llm.gemini_api import generate_response
from db.db_manager import save_chat_log, get_chat_history
import os

app = Flask(__name__)
app.static_folder = 'frontend/static'
app.template_folder = 'frontend/templates'

# Global variable to hold the vector database
vector_db = None

def initialize_chatbot():
    global vector_db
    vector_db = load_data_from_s3() # Load and get ChromaDB vectorstore
    print("Document data and embeddings loaded into ChromaDB.")

@app.route("/")
def index():
    history = get_chat_history()
    return render_template('index.html', chat_history=history)

@app.route("/get_response", methods=['POST'])
def get_chatbot_response():
    user_query = request.form['user_query']
    if vector_db is None: # Check if vector_db is loaded
        initialize_chatbot() # Load it if not loaded yet (in case of delayed loading)
    response_text = generate_response(user_query, vector_db) # Pass vector_db to generate_response
    save_chat_log(user_query, response_text)
    return jsonify({'response': response_text})

if __name__ == '__main__':
    with app.app_context(): # Create application context for initialization
        initialize_chatbot() # Initialize chatbot and load data on startup
    app.run(debug=True, host='0.0.0.0')