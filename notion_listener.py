import time
import os
from typing import Callable, Optional
from notion_client import fetch_all_docs_structured, fetch_page_text
from knowledge_base import sync_notion_to_database, add_document
from rag_database import get_chunks_by_page_id
import hashlib


class NotionListener:
    """
    Listens for changes in Notion pages and triggers callbacks.
    Uses polling to check for updates.
    """
    
    def __init__(self, poll_interval: int = 300):
        """
        Initialize the Notion listener.
        
        Args:
            poll_interval: Time in seconds between polls (default: 5 minutes)
        """
        self.poll_interval = poll_interval
        self.page_hashes = {}  # Store content hashes to detect changes
        self.running = False
    
    def _get_page_hash(self, page_id: str, content: str) -> str:
        """Generate a hash for page content to detect changes."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _check_for_changes(self) -> list[dict]:
        """
        Check for changes in Notion pages.
        
        Returns:
            List of changed pages with 'page_id' and 'action' ('new' or 'updated')
        """
        changed_pages = []
        
        try:
            docs = fetch_all_docs_structured()
            
            for doc in docs:
                page_id = doc["page_id"]
                content = doc["content"]
                content_hash = self._get_page_hash(page_id, content)
                
                if page_id not in self.page_hashes:
                    # New page
                    self.page_hashes[page_id] = content_hash
                    changed_pages.append({
                        "page_id": page_id,
                        "action": "new",
                        "content": content
                    })
                elif self.page_hashes[page_id] != content_hash:
                    # Updated page
                    self.page_hashes[page_id] = content_hash
                    changed_pages.append({
                        "page_id": page_id,
                        "action": "updated",
                        "content": content
                    })
        except Exception as e:
            print(f"Error checking for Notion changes: {e}")
        
        return changed_pages
    
    def watch_notion_changes(self, callback: Callable[[dict], None]):
        """
        Watch for Notion changes and call the callback when changes are detected.
        
        Args:
            callback: Function to call with change information
                     Receives dict with 'page_id', 'action', and 'content'
        """
        print(f"Starting Notion listener (polling every {self.poll_interval} seconds)...")
        
        # Initialize page hashes
        try:
            docs = fetch_all_docs_structured()
            for doc in docs:
                page_id = doc["page_id"]
                content = doc["content"]
                self.page_hashes[page_id] = self._get_page_hash(page_id, content)
            print(f"Initialized {len(self.page_hashes)} pages")
        except Exception as e:
            print(f"Error initializing Notion listener: {e}")
            return
        
        self.running = True
        
        while self.running:
            try:
                changed_pages = self._check_for_changes()
                
                if changed_pages:
                    print(f"Detected {len(changed_pages)} changed page(s)")
                    for change in changed_pages:
                        print(f"  - {change['action']}: {change['page_id']}")
                        callback(change)
                
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                print("\nStopping Notion listener...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in Notion listener loop: {e}")
                time.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the listener."""
        self.running = False


def watch_notion_changes(callback: Callable[[dict], None], poll_interval: int = 300):
    """
    Convenience function to watch for Notion changes.
    
    Args:
        callback: Function to call when changes are detected
        poll_interval: Time in seconds between polls
    """
    listener = NotionListener(poll_interval=poll_interval)
    listener.watch_notion_changes(callback)


def handle_notion_change(change: dict):
    """
    Default handler for Notion changes: updates knowledge base and triggers post generation.
    
    Args:
        change: Dict with 'page_id', 'action', and 'content'
    """
    page_id = change["page_id"]
    action = change["action"]
    content = change["content"]
    
    print(f"Handling {action} page: {page_id}")
    
    # Update knowledge base
    try:
        add_document(page_id, content)
        print(f"Knowledge base updated for page {page_id}")
    except Exception as e:
        print(f"Error updating knowledge base: {e}")
        return
    
    # Trigger post generation (import here to avoid circular imports)
    try:
        import asyncio
        from main import main as generate_and_post
        
        # Generate a query based on the page content (first 100 chars)
        query = content[:100] if len(content) > 100 else content
        
        print(f"Triggering post generation with query: {query[:50]}...")
        asyncio.run(generate_and_post(query=query, require_approval=False))
    except Exception as e:
        print(f"Error triggering post generation: {e}")


if __name__ == "__main__":
    # Example usage
    print("Starting Notion listener...")
    watch_notion_changes(handle_notion_change, poll_interval=60)  # Poll every minute for testing
