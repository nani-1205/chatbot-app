# llm/gemini_api.py
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_NAME = "gemini-1.5-flash-latest" # Or the correct model name you confirmed

# Langchain components for Gemini and Prompt management
llm = ChatGoogleGenerativeAI(model_name=MODEL_NAME, google_api_key=GOOGLE_API_KEY) # Langchain Gemini LLM wrapper

prompt_template_text = """You are a helpful and concise chatbot. Your goal is to answer user questions accurately and directly based ONLY on the information provided in the context below.

**Instructions:**

1.  **Answer concisely and factually.**  Provide direct and to-the-point answers.
2.  **Base answers EXCLUSIVELY on the context provided.** Do not use any external knowledge or information from the internet.
3.  **If the answer is directly stated in the context, try to reference or cite the relevant part of the document in your answer.**
4.  **If the answer cannot be found within the context, respond with the phrase: "I am sorry, but the answer to your question is not in the provided documents."** Do not make up answers or provide information from outside the provided context.

**Context:**
{context}

**Question:**
{question}

**Answer:**
"""
prompt = PromptTemplate.from_template(prompt_template_text) # Langchain prompt template

def generate_response(user_query, vectorstore):
    """Generates a response using Gemini API and Langchain, leveraging semantic search with ChromaDB."""

    # 1. Create RetrievalQA chain using Langchain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff", # "stuff" is a simple chain type, good for smaller contexts. Explore "refine", "map_reduce" for larger ones.
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}), # Retrieve top 3 relevant chunks
        chain_type_kwargs={"prompt": prompt}, # Pass the custom prompt
        return_source_documents=True # Optionally return source documents for citation/reference
    )

    # 2. Run the query and get the Langchain response
    try:
        langchain_response = qa_chain({"query": user_query})
        response_text = langchain_response['result']
        source_documents = langchain_response.get('source_documents', []) # Get source documents if returned

        # Include source document info in response (optional)
        source_documents_info = []
        if source_documents:
            source_documents_info = [{"source": doc.metadata['source'], "content_preview": doc.page_content[:100] + "..."} for doc in source_documents]
            response_text += "\n\n**Source Documents:**\n"
            for doc_info in source_documents_info:
                response_text += f"- Source: {doc_info['source']}, Content Preview: '{doc_info['content_preview']}'\n"

        return response_text

    except Exception as e:
        import traceback
        error_message = f"Error generating response from Gemini API: {e}\n{traceback.format_exc()}"
        print(error_message)
        return "Error processing your query. Please try again."

if __name__ == '__main__':
    # Example usage (for testing - simplified, assumes ChromaDB is already loaded)
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    # Load embedding model (needed for loading ChromaDB)
    embedding_model_example = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")

    # Load ChromaDB from disk (assuming it's persisted in "chroma_db" directory)
    vectorstore_example = Chroma(persist_directory="chroma_db", embedding_function=embedding_model_example)

    sample_query = "What is the capital of France?"
    response = generate_response(sample_query, vectorstore_example)
    print(f"Query: {sample_query}")
    print(f"Response: {response}")

    sample_query_not_in_context = "What is the capital of Germany?"
    response_not_found = generate_response(sample_query_not_in_context, vectorstore_example)
    print(f"\nQuery: {sample_query_not_in_context}")
    print(f"Response: {response_not_found}")