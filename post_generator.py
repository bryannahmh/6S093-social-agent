from llm import call_llm
from typing import Optional
from rag_retriever import hybrid_search

SYSTEM_PROMPT = """
You are the social media manager for Ramos de Bry,
a luxury Mexican-inspired floral brand.
Be bold, emotional, culturally proud.
"""

def generate_post(query: Optional[str] = None, top_k: int = 5) -> str:
    """
    Generate a post using RAG context from hybrid search.
    
    Args:
        query: Optional query to retrieve relevant context. If None, uses a general brand theme.
        top_k: Number of relevant chunks to retrieve
    
    Returns:
        Generated post text
    """
    # If no query provided, use a general brand-related query
    if query is None:
        query = "luxury Mexican floral brand Ramos de Bry"
    
    # Retrieve relevant context using hybrid search
    retrieved_chunks = hybrid_search(query, top_k=top_k, include_posts=False)
    
    # Format retrieved context
    if retrieved_chunks:
        context_parts = []
        for chunk in retrieved_chunks:
            context_parts.append(chunk.content)
        context = "\n\n---\n\n".join(context_parts)
    else:
        # Fallback if no chunks found
        context = "Ramos de Bry is a luxury Mexican-inspired floral brand."
    
    prompt = f"""
RELEVANT BRAND CONTEXT (from knowledge base):
{context}

TASK:
Generate one Mastodon-style post (max 300 chars) based on the context above.
Include a dramatic tone and stay true to the brand voice.
Use the retrieved context to inform your post, but don't quote it verbatim.
"""
    return call_llm(SYSTEM_PROMPT, prompt)
