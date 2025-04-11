# llm/gemini_api.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
from data_processing.embeddings import embedding_model, semantic_search

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-2.0-flash" # Or the correct model name you confirmed

def generate_response(user_query, text_chunks, chunk_embeddings):
    """Generates a response using Gemini API based on context data from semantic search."""

    # 1. Generate embedding for the user query
    query_embedding = embedding_model.encode(user_query, convert_to_tensor=False)

    # 2. Perform semantic search to get relevant chunks
    relevant_chunks = semantic_search(query_embedding, chunk_embeddings, text_chunks)
    context_data = "\n\n".join(relevant_chunks) # Join relevant chunks into context

    model = genai.GenerativeModel(MODEL_NAME)
    prompt_content = f"""You are a helpful and concise chatbot. Your goal is to answer user questions accurately and directly based ONLY on the information provided in the "Document Content" below.

    **Instructions:**

    1.  **Answer concisely and factually.**  Provide direct and to-the-point answers.
    2.  **Base answers EXCLUSIVELY on the "Document Content".** Do not use any external knowledge or information from the internet.
    3.  **If the answer is directly stated in the "Document Content", try to reference or cite the relevant part of the document in your answer.** (Optional, if feasible).
    4.  **If the answer cannot be found within the "Document Content", respond with the phrase: "I am sorry, but the answer to your question is not in the provided documents."** Do not make up answers or provide information from outside the provided content.

    **Document Content:**
    {context_data}

    **User Query:**
    {user_query}

    **Answer:**
    """
    try:
        response = model.generate_content(prompt_content)
        return response.text
    except Exception as e:
        import traceback
        error_message = f"Error generating response from Gemini API: {e}\n{traceback.format_exc()}"
        print(error_message) # Print full error with traceback
        return "Error processing your query. Please try again."

if __name__ == '__main__':
    # Example usage (for testing)
    sample_chunks = [
        "The capital of France is Paris. London is the capital of England.",
        "Berlin is the capital of Germany.",
        "Rome is the capital of Italy."
    ]
    sample_embeddings = generate_embeddings(sample_chunks)

    sample_query = "What is the capital of France?"
    response = generate_response(sample_query, sample_chunks, sample_embeddings)
    print(f"Query: {sample_query}")
    print(f"Response: {response}")

    sample_query_not_in_context = "What is the capital of Germany?"
    response_not_found = generate_response(sample_query_not_in_context, sample_chunks, sample_embeddings)
    print(f"\nQuery: {sample_query_not_in_context}")
    print(f"Response: {response_not_found}")