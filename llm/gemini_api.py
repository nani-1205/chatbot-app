# llm/gemini_api.py

import os # Ensure 'os' is imported for potential future use like os.path.basename() if needed elsewhere
from dotenv import load_dotenv
import traceback

# Langchain & Google GenAI specific imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_core.vectorstores import VectorStore # Type hint for vectorstore parameter

load_dotenv()

# --- Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1024))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", 4))

# --- Initialize LLM ---
llm = None
if GOOGLE_API_KEY:
    try:
        print(f"Initializing Google Generative AI model: {MODEL_NAME}")
        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            convert_system_message_to_human=True # Helps compatibility with some models/prompts
        )
        print("Google Generative AI model initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Google Generative AI for model '{MODEL_NAME}'.")
        print(f"Error details: {e}\n{traceback.format_exc()}")
        llm = None # Ensure llm is None if initialization fails
else:
    print("CRITICAL ERROR: GOOGLE_API_KEY not found in environment variables. LLM is disabled.")

# --- Prompt Template ---
# Updated to discourage adding a separate source list explicitly.
prompt_template_text = """You are an AI assistant designed to answer questions based *only* on the provided document excerpts (context). Follow these instructions carefully:

1.  **Analyze the Context:** Read the following document excerpts thoroughly.
2.  **Answer the Question:** Answer the user's question using *only* the information present in the context.
3.  **Be Concise:** Provide a direct and factual answer. Avoid unnecessary elaboration.
4.  **Cite Sources (If Possible):** If the context includes source information (like filenames or document titles), *try* to mention the source(s) that support your answer *within the main body of the answer* (e.g., "According to 'document.pdf', ..."). Do not add a separate list of sources at the end.
5.  **Handle Missing Information:** If the answer cannot be found *anywhere* within the provided context, respond *exactly* with: "I am sorry, but the answer to your question is not in the provided documents." Do not guess, hallucinate, or use external knowledge.

Context:
---------------------
{context}
---------------------

Question: {question}

Answer:"""

prompt = PromptTemplate(
    template=prompt_template_text, input_variables=["context", "question"]
)

# --- Response Generation Function ---
def generate_response(user_query: str, vectorstore: VectorStore):
    """
    Generates a response using the LLM and RAG pipeline.
    Retrieves relevant documents from the vectorstore, formats the prompt,
    and calls the LLM. It does NOT append source information to the final response.
    """
    if llm is None:
        return "Error: The language model is not available. Please check server configuration and API key."
    if vectorstore is None:
        return "Error: The document vector store is not available. Please check data processing."

    print(f"Generating response for query: '{user_query}' using model {MODEL_NAME}")

    try:
        # Create the retriever from the vector store
        retriever = vectorstore.as_retriever(
            search_type="similarity", # Or "mmr"
            search_kwargs={"k": RETRIEVER_K} # Retrieve top K chunks
        )

        # Create the RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" puts all retrieved chunks into the context
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True # Still retrieve sources for potential logging
        )

        # Run the chain to get the response
        print(f"Running QA chain with k={RETRIEVER_K}...")
        langchain_response = qa_chain.invoke({"query": user_query})

        # Extract the core answer text from the LLM response
        response_text = langchain_response.get('result', '').strip()
        # Get the source documents (primarily for logging now)
        source_documents = langchain_response.get('source_documents', [])

        # Log the raw response from the LLM for debugging
        print(f"LLM Raw Response: '{response_text[:200]}...'")


        # --- BLOCK COMMENTED OUT: Ensure source info is NOT appended to user response ---
        # if source_documents and "not in the provided documents" not in response_text:
        #     if "\n\n**Retrieved Sources:**" not in response_text:
        #          # response_text += "\n\n**Retrieved Sources:**\n" # DO NOT ADD LABEL
        #          unique_source_paths = set()
        #          source_details = []
        #          max_sources_to_show = 2
        #          count = 0
        #          for doc in source_documents:
        #              source_path = doc.metadata.get('source', 'Unknown Source')
        #              if source_path not in unique_source_paths and count < max_sources_to_show:
        #                  unique_source_paths.add(source_path)
        #                  filename = os.path.basename(source_path) # Example: If you wanted filename only
        #                  # source_details.append(f"- {filename}") # DO NOT ADD FILENAME/PATH
        #                  count += 1
        #          # response_text += "\n".join(source_details) # DO NOT JOIN AND APPEND
        # --- END OF COMMENTED OUT BLOCK ---


        # Log full source paths internally for debugging/verification (Optional)
        if source_documents:
            print(f"Retrieved sources (for server logging only):")
            for i, doc in enumerate(source_documents):
                print(f"  Source {i+1}: {doc.metadata.get('source', 'N/A')}")

        # Return *only* the text generated by the LLM based on the prompt instructions
        return response_text

    except Exception as e:
        # Log detailed error information
        error_message = f"Error during response generation pipeline: {e}\n{traceback.format_exc()}"
        print(error_message)
        # Return a generic error message to the user
        return "Sorry, an error occurred while processing your query. The technical details have been logged."

# --- Test Block (Optional) ---
# This code runs only when the script is executed directly (e.g., python llm/gemini_api.py)
if __name__ == '__main__':
    print("\n--- Testing gemini_api with Langchain RAG ---")
    # Requires data_processing.vector_store_manager to be runnable and Chroma DB populated
    try:
        # Attempt to import the necessary function to get the vector store
        from data_processing.vector_store_manager import get_vector_store
        vectorstore_example = get_vector_store()

        # Check if the vector store loaded and contains data
        if vectorstore_example and vectorstore_example._collection.count() > 0:
            print("Successfully loaded vector store for testing.")

            # Test Query 1 (Replace with something likely in your specific documents)
            sample_query_present = "What is the policy regarding sustainable development?" # Example
            response_present = generate_response(sample_query_present, vectorstore_example)
            print(f"\nQuery: {sample_query_present}")
            print(f"Response:\n{response_present}") # Should NOT include "Retrieved Sources"

            # Test Query 2 (Something unlikely to be in your documents)
            sample_query_absent = "What are the mission goals for Artemis III?"
            response_absent = generate_response(sample_query_absent, vectorstore_example)
            print(f"\nQuery: {sample_query_absent}")
            print(f"Response:\n{response_absent}") # Should be "I am sorry..."

        else:
            # Handle cases where vector store isn't ready
            print("WARNING: Vector store is empty or unavailable. Test queries cannot be run meaningfully.")
            print("Suggestion: Run the main app (app.py) first to allow it to populate the vector store from S3.")

    except ImportError:
        print("Error: Could not import 'get_vector_store'. Ensure data_processing/vector_store_manager.py exists and is correct.")
    except Exception as e:
        print(f"An error occurred during testing setup or execution: {e}\n{traceback.format_exc()}")

    print("\n--- gemini_api Test Complete ---")