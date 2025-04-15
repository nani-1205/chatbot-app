# llm/gemini_api.py
# --- Your provided code using Langchain, ChatGoogleGenerativeAI, RetrievalQA ---
# Ensure imports are correct and dependencies are installed.
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
import traceback # Import traceback for detailed error logging

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Model and Prompt Configuration ---
# Ensure MODEL_NAME matches available Gemini models via API
# Check Google AI documentation for latest model names.
# "gemini-1.5-flash-latest" is often available via Vertex AI or AI Studio API.
MODEL_NAME = "gemini-1.5-flash-latest"
try:
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GOOGLE_API_KEY,
                                 convert_system_message_to_human=True) # Helps with some models
    print(f"Google Generative AI model '{MODEL_NAME}' initialized.")
except Exception as e:
    print(f"ERROR: Failed to initialize Google Generative AI for model '{MODEL_NAME}'. Check API Key and model name.")
    print(f"Error details: {e}")
    llm = None # Set llm to None if initialization fails

prompt_template_text = """You are a helpful and concise chatbot. Your goal is to answer user questions accurately and directly based ONLY on the information provided in the context below.

Instructions:
- Answer concisely and factually. Provide direct and to-the-point answers.
- Base answers EXCLUSIVELY on the context provided. Do not use any external knowledge or information from the internet.
- If the answer is directly stated in the context, try to reference or cite the relevant part of the document in your answer (e.g., "According to document X...").
- If the answer cannot be found within the context, respond with the phrase: "I am sorry, but the answer to your question is not in the provided documents." Do not make up answers or provide information from outside the provided context.

Context:
{context}

Question:
{question}

Answer:
"""
prompt = PromptTemplate.from_template(prompt_template_text)

def generate_response(user_query, vectorstore):
    """Generates a response using Gemini API and Langchain, leveraging semantic search with the vector store."""
    if llm is None:
        return "Error: The language model is not available. Please check configuration."
    if vectorstore is None:
        return "Error: The vector store is not available. Please check data processing."

    try:
        # 1. Create RetrievalQA chain using Langchain
        #    search_type="similarity" is default. Can also use "mmr" (Max Marginal Relevance)
        #    k=3 retrieves top 3 most similar chunks. Adjust as needed.
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" puts all retrieved chunks into the context. Good for models with large context windows like Gemini 1.5 Flash.
                               # Consider "map_reduce" or "refine" if context exceeds limits.
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True # Return the source chunks used for the answer
        )

        # 2. Run the query and get the Langchain response
        print(f"Running query against vector store: '{user_query}'")
        langchain_response = qa_chain({"query": user_query})
        response_text = langchain_response['result']

        # 3. Optionally add source document info to the response
        source_documents = langchain_response.get('source_documents', [])
        if source_documents:
            # Check if the model already included source info or if we need to add it
            if "Source Documents:**" not in response_text and "not in the provided documents" not in response_text:
                response_text += "\n\n**Retrieved Sources:**\n"
                unique_sources = set()
                source_details = []
                 # Limit the number of sources displayed for brevity
                max_sources_to_show = 2
                count = 0
                for doc in source_documents:
                    source_name = doc.metadata.get('source', 'Unknown')
                    if source_name not in unique_sources and count < max_sources_to_show:
                        unique_sources.add(source_name)
                        # Preview first few words of the relevant chunk
                        content_preview = doc.page_content[:100].replace('\n', ' ') + "..."
                        source_details.append(f"- {source_name} (Preview: '{content_preview}')")
                        count += 1
                response_text += "\n".join(source_details)

        print(f"Generated response: {response_text[:200]}...") # Log snippet of response
        return response_text

    except Exception as e:
        error_message = f"Error generating response: {e}\n{traceback.format_exc()}"
        print(error_message)
        return "Sorry, an error occurred while processing your query. Please check the logs or try again later."

if __name__ == '__main__':
    # Example usage (for testing - assumes ChromaDB is populated)
    print("\n--- Testing gemini_api with Langchain RAG ---")
    # Make sure embedding model and vector store can be loaded
    try:
        from data_processing.vector_store_manager import get_vector_store
        vectorstore_example = get_vector_store()
        print("Successfully loaded vector store for testing.")

        if vectorstore_example._collection.count() == 0:
             print("WARNING: Vector store is empty. Test queries will likely fail or return 'not found'.")
             print("Run data_loader.py first to populate the vector store.")

        # Test Query 1 (Assuming relevant info exists in your processed docs)
        sample_query_present = "What is the main topic of document X?" # Replace with a relevant query
        response_present = generate_response(sample_query_present, vectorstore_example)
        print(f"\nQuery: {sample_query_present}")
        print(f"Response:\n{response_present}")

        # Test Query 2 (Assuming this info DOES NOT exist)
        sample_query_absent = "What is the airspeed velocity of an unladen swallow?"
        response_absent = generate_response(sample_query_absent, vectorstore_example)
        print(f"\nQuery: {sample_query_absent}")
        print(f"Response:\n{response_absent}")

    except ImportError:
        print("Could not import 'get_vector_store'. Make sure 'vector_store_manager.py' is runnable.")
    except Exception as e:
        print(f"An error occurred during testing setup or execution: {e}")
        print(traceback.format_exc())

    print("\n--- Test Complete ---")