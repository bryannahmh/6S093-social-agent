import sqlite3
import os
from typing import Optional
import json


DB_PATH = os.path.join(os.path.dirname(__file__), "rag.db")


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            notion_page_id TEXT,
            chunk_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chunk embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunk_embeddings (
            chunk_id INTEGER PRIMARY KEY,
            embedding BLOB NOT NULL,
            FOREIGN KEY (chunk_id) REFERENCES chunks(id)
        )
    """)
    
    # FTS5 virtual table for keyword search
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            content_rowid=id
        )
    """)
    
    # Posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            mastodon_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    # Post embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_embeddings (
            post_id INTEGER PRIMARY KEY,
            embedding BLOB NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    
    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_notion_page_id ON chunks(notion_page_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_mastodon_id ON posts(mastodon_id)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")


def store_chunk(content: str, notion_page_id: Optional[str] = None, chunk_index: Optional[int] = None) -> int:
    """Store a chunk and return its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO chunks (content, notion_page_id, chunk_index)
        VALUES (?, ?, ?)
    """, (content, notion_page_id, chunk_index))
    
    chunk_id = cursor.lastrowid
    
    # Also insert into FTS5 table
    cursor.execute("""
        INSERT INTO chunks_fts (rowid, content)
        VALUES (?, ?)
    """, (chunk_id, content))
    
    conn.commit()
    conn.close()
    return chunk_id


def store_chunk_embedding(chunk_id: int, embedding: bytes):
    """Store embedding for a chunk (embedding should be serialized numpy array)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding)
        VALUES (?, ?)
    """, (chunk_id, embedding))
    
    conn.commit()
    conn.close()


def get_chunk(chunk_id: int) -> Optional[dict]:
    """Retrieve a chunk by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_chunk_embedding(chunk_id: int) -> Optional[bytes]:
    """Retrieve embedding for a chunk."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT embedding FROM chunk_embeddings WHERE chunk_id = ?", (chunk_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return None


def store_post(content: str, mastodon_id: str, metadata: Optional[dict] = None) -> int:
    """Store a post and return its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor.execute("""
        INSERT OR REPLACE INTO posts (content, mastodon_id, metadata)
        VALUES (?, ?, ?)
    """, (content, mastodon_id, metadata_json))
    
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def store_post_embedding(post_id: int, embedding: bytes):
    """Store embedding for a post (embedding should be serialized numpy array)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO post_embeddings (post_id, embedding)
        VALUES (?, ?)
    """, (post_id, embedding))
    
    conn.commit()
    conn.close()


def get_all_chunks() -> list[dict]:
    """Retrieve all chunks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM chunks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_chunks_by_page_id(notion_page_id: str) -> list[dict]:
    """Retrieve all chunks for a specific Notion page."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM chunks WHERE notion_page_id = ? ORDER BY chunk_index", (notion_page_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def delete_chunks_by_page_id(notion_page_id: str):
    """Delete all chunks for a specific Notion page (useful for re-syncing)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get chunk IDs to delete
    cursor.execute("SELECT id FROM chunks WHERE notion_page_id = ?", (notion_page_id,))
    chunk_ids = [row[0] for row in cursor.fetchall()]
    
    # Delete from FTS5 table
    for chunk_id in chunk_ids:
        cursor.execute("DELETE FROM chunks_fts WHERE rowid = ?", (chunk_id,))
    
    # Delete embeddings
    cursor.execute("DELETE FROM chunk_embeddings WHERE chunk_id IN ({})".format(
        ",".join("?" * len(chunk_ids))
    ), chunk_ids)
    
    # Delete chunks
    cursor.execute("DELETE FROM chunks WHERE notion_page_id = ?", (notion_page_id,))
    
    conn.commit()
    conn.close()
