# # data_processing/embeddings.py
# from sentence_transformers import SentenceTransformer
# import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity

# # Choose a pre-trained sentence transformer model
# EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2' # Good balance of speed and quality
# embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# def generate_embeddings(text_chunks):
#     """Generates embeddings for a list of text chunks."""
#     embeddings = embedding_model.encode(text_chunks, convert_to_tensor=False)
#     return embeddings

# def semantic_search(query_embedding, chunk_embeddings, text_chunks, top_k=3):
#     """Performs semantic search to find top_k most similar text chunks to the query."""
#     similarities = cosine_similarity([query_embedding], chunk_embeddings)[0]
#     top_indices = np.argsort(similarities)[::-1][0:top_k] # Get top k indices
#     relevant_chunks = [text_chunks[index] for index in top_indices]
#     return relevant_chunks

# if __name__ == '__main__':
#     # Example Usage
#     sample_chunks = [
#         "The capital of France is Paris.",
#         "London is the capital of England.",
#         "Berlin is the capital of Germany.",
#         "Rome is the capital of Italy."
#     ]
#     sample_embeddings = generate_embeddings(sample_chunks)

#     query = "What is the capital of France?"
#     query_embedding = embedding_model.encode(query, convert_to_tensor=False)

#     relevant_chunks = semantic_search(query_embedding, sample_embeddings, sample_chunks)
#     print(f"Query: {query}")
#     print("\nRelevant Chunks:")
#     for chunk in relevant_chunks:
#         print(f"- {chunk}")