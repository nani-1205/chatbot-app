# app.py
from flask import Flask, render_template, request, jsonify
from data_processing.data_loader import load_data_from_s3
from llm.gemini_api import generate_response
from db.db_manager import save_chat_log, get_chat_history

app = Flask(__name__)
app.static_folder = 'frontend/static' # For static files (CSS, JS)
app.template_folder = 'frontend/templates' # For HTML templates

# Load data from S3 and generate embeddings when the app starts
document_chunks, chunk_embeddings = load_data_from_s3() # Load chunks AND embeddings
print("Document data and embeddings loaded.") # Log when data loading is complete

@app.route("/")
def index():
    history = get_chat_history()
    return render_template('index.html', chat_history=history)

@app.route("/get_response", methods=['POST'])
def get_chatbot_response():
    user_query = request.form['user_query']
    response_text = generate_response(user_query, document_chunks, chunk_embeddings) # Pass chunks and embeddings
    save_chat_log(user_query, response_text) # Save to DB
    return jsonify({'response': response_text})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Run in debug mode for development