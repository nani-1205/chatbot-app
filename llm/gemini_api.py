# llm/gemini_api.py
import os
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
# Ensure MODEL_NAME matches available Gemini models via API (e.g., "gemini-1.5-flash-latest")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1)) # Lower for more factual Q&A
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1024))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", 4)) # Number of chunks to retrieve

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
# Tailored for RAG, instructing the model to use ONLY the provided context.
prompt_template_text = """You are an AI assistant designed to answer questions based *only* on the provided document excerpts (context). Follow these instructions carefully:

1.  **Analyze the Context:** Read the following document excerpts thoroughly.
2.  **Answer the Question:** Answer the user's question using *only* the information present in the context.
3.  **Be Concise:** Provide a direct and factual answer. Avoid unnecessary elaboration.
4.  **Cite Sources (If Possible):** If the context includes source information (like filenames or document titles), mention the source(s) that support your answer (e.g., "According to 's3://bucket/doc.pdf', ...").
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
    and calls the LLM.
    """
    if llm is None:
        return "Error: The language model is not available. Please check server configuration and API key."
    if vectorstore is None:
        return "Error: The document vector store is not available. Please check data processing."

    print(f"Generating response for query: '{user_query}' using model {MODEL_NAME}")

    try:
        # Create the retriever
        retriever = vectorstore.as_retriever(
            search_type="similarity", # Or "mmr"
            search_kwargs={"k": RETRIEVER_K} # Retrieve top K chunks
        )

        # Create the RetrievalQA chain
        # Chain type "stuff" is good for models with large context windows
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True # Return the chunks used for context
        )

        # Run the chain
        print(f"Running QA chain with k={RETRIEVER_K}...")
        langchain_response = qa_chain.invoke({"query": user_query}) # Use invoke for newer Langchain versions

        response_text = langchain_response.get('result', '').strip()
        source_documents = langchain_response.get('source_documents', [])

        print(f"LLM Raw Response: '{response_text[:200]}...'")

        # Optional: Append source info if not already included by the LLM and answer was found
        if source_documents and "not in the provided documents" not in response_text:
            if "\n\n**Retrieved Sources:**" not in response_text: # Avoid duplication
                 response_text += "\n\n**Retrieved Sources:**\n"
                 unique_sources = set()
                 source_details = []
                 max_sources_to_show = 2 # Limit display for brevity
                 count = 0
                 for doc in source_documents:
                     source_name = doc.metadata.get('source', 'Unknown Source')
                     if source_name not in unique_sources and count < max_sources_to_show:
                         unique_sources.add(source_name)
                         # Preview first few words of the relevant chunk
                         content_preview = doc.page_content[:80].replace('\n', ' ') + "..."
                         source_details.append(f"- {source_name}") # Just list source name
                         # source_details.append(f"- {source_name} (Preview: '{content_preview}')") # More detail
                         count += 1
                 response_text += "\n".join(source_details)

        return response_text

    except Exception as e:
        error_message = f"Error during response generation pipeline: {e}\n{traceback.format_exc()}"
        print(error_message)
        return "Sorry, an error occurred while processing your query. The technical details have been logged."

# Example usage for testing (optional)
if __name__ == '__main__':
    print("\n--- Testing gemini_api with Langchain RAG ---")
    # Requires data_processing.vector_store_manager to be runnable and Chroma DB populated
    try:
        from data_processing.vector_store_manager import get_vector_store
        vectorstore_example = get_vector_store()

        if vectorstore_example and vectorstore_example._collection.count() > 0:
            print("Successfully loaded vector store for testing.")

            # Test Query 1 (Replace with something likely in your docs)
            sample_query_present = "What is mentioned about [specific topic in your docs]?"
            response_present = generate_response(sample_query_present, vectorstore_example)
            print(f"\nQuery: {sample_query_present}")
            print(f"Response:\n{response_present}")

            # Test Query 2 (Something unlikely to be in your docs)
            sample_query_absent = "What is the chemical formula for water?"
            response_absent = generate_response(sample_query_absent, vectorstore_example)
            print(f"\nQuery: {sample_query_absent}")
            print(f"Response:\n{response_absent}")

        else:
            print("WARNING: Vector store is empty or unavailable. Test queries cannot be run meaningfully.")
            print("Run the main app (app.py) first to populate the vector store from S3.")

    except ImportError:
        print("Could not import 'get_vector_store'. Ensure vector_store_manager.py is correct.")
    except Exception as e:
        print(f"An error occurred during testing setup or execution: {e}\n{traceback.format_exc()}")

    print("\n--- gemini_api Test Complete ---")