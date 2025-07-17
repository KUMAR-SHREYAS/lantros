from sentence_transformers import SentenceTransformer

# Initialize embedding model (you can change the model name)
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def encode_chunks(chunks):
    """Generate embeddings for a list of text chunks."""
    return EMBEDDING_MODEL.encode(chunks, show_progress_bar=True) 