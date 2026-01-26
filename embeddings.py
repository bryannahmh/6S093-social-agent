import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
import pickle


# Global model instance (lazy loaded)
_model = None


def get_model() -> SentenceTransformer:
    """Get or load the MiniLM-L6-v2 model (lazy loading)."""
    global _model
    if _model is None:
        print("Loading MiniLM-L6-v2 model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model loaded successfully")
    return _model


def generate_embeddings(texts: Union[str, List[str]]) -> np.ndarray:
    """
    Generate embeddings for text(s) using MiniLM-L6-v2.
    
    Args:
        texts: Single string or list of strings to embed
    
    Returns:
        numpy array of embeddings (shape: (n_texts, embedding_dim))
    """
    model = get_model()
    
    # Handle single string input
    if isinstance(texts, str):
        texts = [texts]
    
    # Generate embeddings
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    
    return embeddings


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """
    Serialize a numpy embedding array to bytes for storage in SQLite.
    
    Args:
        embedding: numpy array (can be 1D or 2D)
    
    Returns:
        Serialized bytes
    """
    return pickle.dumps(embedding)


def deserialize_embedding(embedding_bytes: bytes) -> np.ndarray:
    """
    Deserialize embedding bytes back to numpy array.
    
    Args:
        embedding_bytes: Serialized embedding bytes
    
    Returns:
        numpy array
    """
    return pickle.loads(embedding_bytes)


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding (1D array)
        embedding2: Second embedding (1D array)
    
    Returns:
        Cosine similarity score (0-1)
    """
    # Normalize embeddings if not already normalized
    embedding1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
    embedding2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
    
    return float(np.dot(embedding1, embedding2))


def cosine_similarity_batch(query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """
    Calculate cosine similarity between a query embedding and a batch of embeddings.
    
    Args:
        query_embedding: Query embedding (1D array)
        embeddings: Batch of embeddings (2D array, shape: (n, embedding_dim))
    
    Returns:
        Array of similarity scores (shape: (n,))
    """
    # Normalize query embedding
    query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
    
    # Normalize all embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings_normalized = embeddings / (norms + 1e-8)
    
    # Compute cosine similarity
    similarities = np.dot(embeddings_normalized, query_embedding)
    
    return similarities
