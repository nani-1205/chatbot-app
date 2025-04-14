# llm/gemini_api.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from data_processing.embeddings import embedding_model # Keep this import for test example

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_NAME = "gemini-1.5-flash-latest" # Or the correct model name you confirmed

# Langchain components for Gemini and Prompt management
llm = ChatGoogleGenerativeAI(model_name=MODEL_NAME, google_api_key=GOOGLE_API_KEY) # Langchain Gemini LLM wrapper

prompt_template_text = """You are a helpful and concise chatbot. Your goal is to answer user questions accurately and directly based ONLY on the information provided in the "Document Content" below.

**Instructions:**

1.  **Answer concisely and factually.**  Provide direct and to-the-point answers.
2.  **Base answers EXCLUSIVELY on the "Document Content".** Do not use any external knowledge or information from the internet.
3.  **If the answer is directly stated in the "Document Content", try to reference or cite the relevant part of the document in your answer.** (Optional, if feasible).
4.  **If the answer cannot be found within the "Document Content", respond with the phrase: "I am sorry, but the answer to your question is not in the provided documents."** Do not make up answers or provide information from outside the provided content.

**Document Content:**
{context}

**User Query:**
{query}

**Answer:**
"""
prompt = PromptTemplate.from_template(prompt_template_text) # Langchain prompt template
llm_chain = LLMChain(llm=llm, prompt=prompt) # Langchain LLM chain

def generate_response(user_query, vectorstore):
    """Generates a response using Gemini API and Langchain, leveraging semantic search with ChromaDB."""

    # 1. Perform semantic search using Langchain's VectorStoreRetriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # Retrieve top 3 relevant chunks
    relevant_documents = retriever.get_relevant_documents(user_query)

    context_data = ""
    source_documents_info = []
    if relevant_documents:
        context_data = "\n\n".join([doc.page_content for doc in relevant_documents]) # Extract page content
        source_documents_info = [{"source": doc.metadata['source'], "content_start": doc.page_content[:50] + "..."} for doc in relevant_documents] # Example source info

    # 2. Use Langchain LLMChain to generate response with Gemini and retrieved context
    try:
        response_text = llm_chain.run(context=context_data, query=user_query)

        # Include source document info in response (optional)
        if source_documents_info:
            response_text += "\n\n**Source Documents:**\n"
            for doc_info in source_documents_info:
                response_text += f"- Source: {doc_info['source']}, Content Preview: '{doc_info['content_start']}'\n"
        return response_text

    except Exception as e:
        import traceback
        error_message = f"Error generating response from Gemini API: {e}\n{traceback.format_exc()}"
        print(error_message)
        return "Error processing your query. Please try again."

if __name__ == '__main__':
    # Example usage (for testing - simplified, assumes ChromaDB is already loaded)
    from langchain.vectorstores import Chroma
    # Load ChromaDB from disk (assuming it's persisted in "chroma_db" directory)
    vectorstore_example = Chroma(persist_directory="chroma_db", embedding_function=embedding_model)

    sample_query = "What is the capital of France?"
    response = generate_response(sample_query, vectorstore_example)
    print(f"Query: {sample_query}")
    print(f"Response: {response}")

    sample_query_not_in_context = "What is the capital of Germany?"
    response_not_found = generate_response(sample_query_not_in_context, vectorstore_example)
    print(f"\nQuery: {sample_query_not_in_context}")
    print(f"Response: {response_not_found}")