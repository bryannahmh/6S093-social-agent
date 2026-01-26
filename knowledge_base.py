from dotenv import load_dotenv
load_dotenv()

from notion_client import fetch_all_docs_structured
from chunking import chunk_documents, Chunk
from embeddings import generate_embeddings, serialize_embedding
from rag_database import (
    init_database,
    store_chunk,
    store_chunk_embedding,
    delete_chunks_by_page_id,
    get_chunks_by_page_id
)
from typing import List, Optional


def sync_notion_to_database(force_resync: bool = False):
    """
    Full sync operation: fetch all documents from Notion, chunk them,
    generate embeddings, and store in SQLite.
    
    Args:
        force_resync: If True, delete existing chunks before syncing
    """
    print("Starting Notion → SQLite sync...")
    
    # Initialize database if needed
    init_database()
    
    # Fetch documents from Notion
    print("Fetching documents from Notion...")
    docs = fetch_all_docs_structured()
    
    if not docs:
        print("No documents found in Notion")
        return
    
    print(f"Found {len(docs)} documents")
    
    # Extract page IDs and contents
    page_ids = [doc["page_id"] for doc in docs]
    contents = [doc["content"] for doc in docs]
    
    # Delete existing chunks if force_resync
    if force_resync:
        print("Deleting existing chunks...")
        for page_id in page_ids:
            delete_chunks_by_page_id(page_id)
    
    # Chunk documents
    print("Chunking documents...")
    chunks = chunk_documents(contents, page_ids)
    print(f"Created {len(chunks)} chunks")
    
    # Generate embeddings in batches
    print("Generating embeddings...")
    batch_size = 32
    chunk_contents = [chunk.content for chunk in chunks]
    
    for i in range(0, len(chunk_contents), batch_size):
        batch = chunk_contents[i:i + batch_size]
        print(f"Processing batch {i // batch_size + 1}/{(len(chunk_contents) + batch_size - 1) // batch_size}")
        
        # Generate embeddings for batch
        embeddings = generate_embeddings(batch)
        
        # Store chunks and embeddings
        for j, chunk in enumerate(chunks[i:i + batch_size]):
            chunk_id = store_chunk(
                content=chunk.content,
                notion_page_id=chunk.notion_page_id,
                chunk_index=chunk.chunk_index
            )
            
            # Serialize and store embedding
            embedding_bytes = serialize_embedding(embeddings[j])
            store_chunk_embedding(chunk_id, embedding_bytes)
    
    print("Sync completed successfully!")


def add_document(page_id: str, content: str):
    """
    Incrementally add a single document to the knowledge base.
    
    Args:
        page_id: Notion page ID
        content: Document content
    """
    print(f"Adding document {page_id}...")
    
    # Initialize database if needed
    init_database()
    
    # Delete existing chunks for this page (in case of update)
    delete_chunks_by_page_id(page_id)
    
    # Chunk document
    chunks = chunk_documents([content], [page_id])
    print(f"Created {len(chunks)} chunks")
    
    # Generate embeddings
    chunk_contents = [chunk.content for chunk in chunks]
    embeddings = generate_embeddings(chunk_contents)
    
    # Store chunks and embeddings
    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = store_chunk(
            content=chunk.content,
            notion_page_id=chunk.notion_page_id,
            chunk_index=chunk.chunk_index
        )
        
        embedding_bytes = serialize_embedding(embedding)
        store_chunk_embedding(chunk_id, embedding_bytes)
    
    print(f"Document {page_id} added successfully!")


def update_document(page_id: str, content: str):
    """
    Update an existing document (same as add_document, but clearer naming).
    
    Args:
        page_id: Notion page ID
        content: Updated document content
    """
    add_document(page_id, content)


def get_document_chunks(page_id: str) -> List[dict]:
    """
    Get all chunks for a specific document.
    
    Args:
        page_id: Notion page ID
    
    Returns:
        List of chunk dictionaries
    """
    return get_chunks_by_page_id(page_id)


if __name__ == "__main__":
    # Run sync when executed directly
    sync_notion_to_database(force_resync=True)
