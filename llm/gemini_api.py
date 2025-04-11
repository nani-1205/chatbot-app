# llm/gemini_api.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-1.5-flash-latest"  # <--- UPDATED MODEL NAME

def generate_response(user_query, context_data):
    """Generates a response using Gemini API based on context data."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt_content = f"""You are a chatbot that answers questions based ONLY on the provided document content.
    Do not use any external knowledge. If the answer is not found in the document, say "I am sorry, but the answer to your question is not in the provided documents."

    Document Content:
    {context_data}

    User Query:
    {user_query}

    Answer:
    """
    try:
        response = model.generate_content(prompt_content)
        return response.text
    except Exception as e:
        print(f"Error generating response from Gemini API: {e}")
        return "Error processing your query. Please try again."

if __name__ == '__main__':
    # Example usage (for testing)
    sample_context = "The capital of France is Paris. London is the capital of England."
    sample_query = "What is the capital of France?"
    response = generate_response(sample_query, sample_context)
    print(f"Query: {sample_query}")
    print(f"Response: {response}")

    sample_query_not_in_context = "What is the capital of Germany?"
    response_not_found = generate_response(sample_query_not_in_context, sample_context)
    print(f"\nQuery: {sample_query_not_in_context}")
    print(f"Response: {response_not_found}")