from typing import List
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    content: str
    notion_page_id: str
    chunk_index: int


def chunk_documents(
    docs: List[str],
    page_ids: List[str],
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Chunk]:
    """
    Split documents into overlapping chunks.
    
    Args:
        docs: List of document contents
        page_ids: List of Notion page IDs corresponding to each document
        chunk_size: Target size of each chunk (in characters, approximate)
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of Chunk objects with content and metadata
    """
    if len(docs) != len(page_ids):
        raise ValueError("Number of documents must match number of page IDs")
    
    all_chunks = []
    
    for doc, page_id in zip(docs, page_ids):
        if not doc.strip():
            continue
        
        # Simple character-based chunking with overlap
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(doc):
            # Calculate end position
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence boundary
            if end < len(doc):
                # Look for sentence endings within the last 100 chars
                search_start = max(start + chunk_size - 100, start)
                for i in range(end - 1, search_start, -1):
                    if doc[i] in '.!?\n':
                        end = i + 1
                        break
                # If no sentence boundary found, break at word boundary
                if end == start + chunk_size:
                    for i in range(end - 1, max(start, end - 50), -1):
                        if doc[i] in ' \t\n':
                            end = i + 1
                            break
            
            chunk_content = doc[start:end].strip()
            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    notion_page_id=page_id,
                    chunk_index=chunk_index
                ))
                chunk_index += 1
            
            # Move start position forward, accounting for overlap
            start = max(start + 1, end - chunk_overlap)
        
        all_chunks.extend(chunks)
    
    return all_chunks


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[str]:
    """
    Simple text chunking without metadata (for general use).
    
    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of chunk strings
    """
    if not text.strip():
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            search_start = max(start + chunk_size - 100, start)
            for i in range(end - 1, search_start, -1):
                if text[i] in '.!?\n':
                    end = i + 1
                    break
            # If no sentence boundary, try word boundary
            if end == start + chunk_size:
                for i in range(end - 1, max(start, end - 50), -1):
                    if text[i] in ' \t\n':
                        end = i + 1
                        break
        
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(chunk_content)
        
        start = max(start + 1, end - chunk_overlap)
    
    return chunks
