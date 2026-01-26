import sqlite3
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from rag_database import get_db_connection, get_chunk, get_chunk_embedding
from embeddings import generate_embeddings, deserialize_embedding, cosine_similarity_batch


@dataclass
class RetrievedChunk:
    """Represents a retrieved chunk with relevance score."""
    chunk_id: int
    content: str
    notion_page_id: Optional[str]
    chunk_index: Optional[int]
    score: float
    bm25_score: float
    semantic_score: float


def hybrid_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.5,
    include_posts: bool = False
) -> List[RetrievedChunk]:
    """
    Perform hybrid search combining BM25 (FTS5) and semantic (embedding) search.
    
    Args:
        query: Search query string
        top_k: Number of results to return
        alpha: Weight between semantic (alpha) and BM25 (1-alpha)
              - alpha=0.0: pure BM25
              - alpha=0.5: equal weight
              - alpha=1.0: pure semantic
        include_posts: Whether to include stored posts in search
    
    Returns:
        List of RetrievedChunk objects sorted by relevance score (highest first)
    """
    # Step 1: BM25 search using FTS5
    bm25_results = _bm25_search(query, top_k * 2)  # Get more candidates
    
    # Step 2: Semantic search
    semantic_results = _semantic_search(query, top_k * 2, include_posts)
    
    # Step 3: Combine results
    combined = _combine_results(bm25_results, semantic_results, alpha)
    
    # Step 4: Sort by combined score and return top_k
    combined.sort(key=lambda x: x.score, reverse=True)
    return combined[:top_k]


def _bm25_search(query: str, limit: int = 10) -> Dict[int, float]:
    """
    Perform BM25 keyword search using SQLite FTS5.
    
    Returns:
        Dictionary mapping chunk_id to BM25 score
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # FTS5 search - using match() function
    # Escape special characters in query for FTS5
    query_escaped = query.replace('"', '""')
    
    cursor.execute("""
        SELECT 
            chunks.id,
            chunks.content,
            chunks.notion_page_id,
            chunks.chunk_index,
            rank
        FROM chunks_fts
        JOIN chunks ON chunks_fts.rowid = chunks.id
        WHERE chunks_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query_escaped, limit))
    
    results = {}
    rows = cursor.fetchall()
    
    # FTS5 rank is lower for better matches, so we'll invert it
    # Normalize scores to 0-1 range
    if rows:
        max_rank = max(row[4] for row in rows) if rows else 1
        min_rank = min(row[4] for row in rows) if rows else 0
        
        for row in rows:
            chunk_id = row[0]
            rank = row[4]
            # Invert and normalize: better matches (lower rank) get higher score
            if max_rank > min_rank:
                normalized_score = 1.0 - ((rank - min_rank) / (max_rank - min_rank))
            else:
                normalized_score = 1.0
            results[chunk_id] = normalized_score
    
    conn.close()
    return results


def _semantic_search(query: str, limit: int = 10, include_posts: bool = False) -> Dict[int, float]:
    """
    Perform semantic search using embeddings.
    
    Returns:
        Dictionary mapping chunk_id/post_id to semantic similarity score
    """
    # Generate query embedding
    query_embedding = generate_embeddings(query)[0]  # Get first (and only) embedding
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    results = {}
    
    # Search chunks
    cursor.execute("SELECT chunk_id, embedding FROM chunk_embeddings")
    chunk_rows = cursor.fetchall()
    
    if chunk_rows:
        chunk_ids = []
        embeddings = []
        
        for row in chunk_rows:
            chunk_id = row[0]
            embedding_bytes = row[1]
            embedding = deserialize_embedding(embedding_bytes)
            
            chunk_ids.append(chunk_id)
            embeddings.append(embedding)
        
        # Calculate similarities
        embeddings_array = np.array(embeddings)
        similarities = cosine_similarity_batch(query_embedding, embeddings_array)
        
        # Store results
        for chunk_id, similarity in zip(chunk_ids, similarities):
            results[chunk_id] = float(similarity)
    
    # Search posts if requested
    if include_posts:
        cursor.execute("SELECT post_id, embedding FROM post_embeddings")
        post_rows = cursor.fetchall()
        
        if post_rows:
            post_ids = []
            embeddings = []
            
            for row in post_rows:
                post_id = row[0]
                embedding_bytes = row[1]
                embedding = deserialize_embedding(embedding_bytes)
                
                post_ids.append(post_id)
                embeddings.append(embedding)
            
            # Calculate similarities
            if embeddings:
                embeddings_array = np.array(embeddings)
                similarities = cosine_similarity_batch(query_embedding, embeddings_array)
                
                # Store results with negative IDs to distinguish from chunks
                for post_id, similarity in zip(post_ids, similarities):
                    results[-post_id] = float(similarity)  # Negative ID for posts
    
    conn.close()
    return results


def _combine_results(
    bm25_results: Dict[int, float],
    semantic_results: Dict[int, float],
    alpha: float
) -> List[RetrievedChunk]:
    """
    Combine BM25 and semantic search results.
    
    Args:
        bm25_results: Dictionary of chunk_id -> BM25 score
        semantic_results: Dictionary of chunk_id -> semantic score
        alpha: Weight for semantic search (0-1)
    
    Returns:
        List of RetrievedChunk objects
    """
    # Get all unique chunk IDs
    all_ids = set(bm25_results.keys()) | set(semantic_results.keys())
    
    combined = []
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for chunk_id in all_ids:
        bm25_score = bm25_results.get(chunk_id, 0.0)
        semantic_score = semantic_results.get(chunk_id, 0.0)
        
        # Combine scores
        combined_score = alpha * semantic_score + (1 - alpha) * bm25_score
        
        # Get chunk/post details
        if chunk_id < 0:
            # This is a post (negative ID used to distinguish from chunks)
            post_id = abs(chunk_id)  # Convert back to positive
            cursor.execute("SELECT content, mastodon_id FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if row:
                combined.append(RetrievedChunk(
                    chunk_id=chunk_id,  # Keep negative to indicate it's a post
                    content=row[0],
                    notion_page_id=None,
                    chunk_index=None,
                    score=combined_score,
                    bm25_score=0.0,  # Posts don't have BM25 scores
                    semantic_score=semantic_score
                ))
        else:
            # This is a chunk
            chunk = get_chunk(chunk_id)
            if chunk:
                combined.append(RetrievedChunk(
                    chunk_id=chunk_id,
                    content=chunk['content'],
                    notion_page_id=chunk.get('notion_page_id'),
                    chunk_index=chunk.get('chunk_index'),
                    score=combined_score,
                    bm25_score=bm25_score,
                    semantic_score=semantic_score
                ))
    
    conn.close()
    return combined


def search_chunks(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    """Convenience function for searching only chunks (not posts)."""
    return hybrid_search(query, top_k=top_k, include_posts=False)


def search_all(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    """Convenience function for searching both chunks and posts."""
    return hybrid_search(query, top_k=top_k, include_posts=True)
