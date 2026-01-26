import time
import os
import requests
from typing import Callable, List, Dict, Optional
from reply_generator import generate_replies, ReplySet
from rag_retriever import hybrid_search


class MastodonListener:
    """
    Listens for Mastodon notifications (mentions/replies) and triggers callbacks.
    Uses polling to check for new notifications.
    """
    
    def __init__(self, poll_interval: int = 60):
        """
        Initialize the Mastodon listener.
        
        Args:
            poll_interval: Time in seconds between polls (default: 1 minute)
        """
        self.poll_interval = poll_interval
        self.processed_notification_ids = set()
        self.running = False
        self.base_url = os.environ.get('MASTODON_BASE_URL')
        self.access_token = os.environ.get('MASTODON_ACCESS_TOKEN')
    
    def _get_notifications(self, limit: int = 20) -> List[Dict]:
        """
        Fetch notifications from Mastodon API.
        
        Args:
            limit: Maximum number of notifications to fetch
        
        Returns:
            List of notification dictionaries
        """
        if not self.base_url or not self.access_token:
            raise ValueError("MASTODON_BASE_URL and MASTODON_ACCESS_TOKEN must be set")
        
        url = f"{self.base_url}/api/v1/notifications"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "limit": limit,
            "exclude_types": ["follow", "favourite", "reblog"]  # Only get mentions and replies
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return []
    
    def _get_status(self, status_id: str) -> Optional[Dict]:
        """Get a status/post by ID."""
        if not self.base_url or not self.access_token:
            return None
        
        url = f"{self.base_url}/api/v1/statuses/{status_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching status {status_id}: {e}")
            return None
    
    def _post_reply(self, status_id: str, reply_text: str, in_reply_to_id: str) -> bool:
        """
        Post a reply to a Mastodon status.
        
        Args:
            status_id: ID of the status being replied to
            reply_text: Text of the reply
            in_reply_to_id: ID of the status to reply to
        
        Returns:
            True if successful, False otherwise
        """
        if not self.base_url or not self.access_token:
            return False
        
        url = f"{self.base_url}/api/v1/statuses"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        data = {
            "status": reply_text,
            "in_reply_to_id": in_reply_to_id,
            "visibility": "public"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error posting reply: {e}")
            return False
    
    def _check_for_new_notifications(self) -> List[Dict]:
        """
        Check for new notifications that haven't been processed.
        
        Returns:
            List of new notification dictionaries
        """
        notifications = self._get_notifications()
        new_notifications = []
        
        for notification in notifications:
            notification_id = notification.get("id")
            notification_type = notification.get("type")
            
            # Only process mentions and replies
            if notification_type not in ["mention", "status"]:
                continue
            
            # Skip if already processed
            if notification_id in self.processed_notification_ids:
                continue
            
            # Get the status/post content
            status = notification.get("status")
            if not status:
                continue
            
            new_notifications.append({
                "notification_id": notification_id,
                "type": notification_type,
                "status_id": status.get("id"),
                "status_content": status.get("content", ""),
                "account": status.get("account", {}).get("acct", "unknown"),
                "status_url": status.get("url", "")
            })
            
            # Mark as processed
            self.processed_notification_ids.add(notification_id)
        
        return new_notifications
    
    def watch_mastodon_notifications(self, callback: Callable[[Dict], None], auto_reply: bool = False):
        """
        Watch for Mastodon notifications and call the callback when new ones are detected.
        
        Args:
            callback: Function to call with notification information
            auto_reply: If True, automatically generate and post replies
        """
        print(f"Starting Mastodon listener (polling every {self.poll_interval} seconds)...")
        
        self.running = True
        
        while self.running:
            try:
                new_notifications = self._check_for_new_notifications()
                
                if new_notifications:
                    print(f"Detected {len(new_notifications)} new notification(s)")
                    for notification in new_notifications:
                        print(f"  - {notification['type']} from @{notification['account']}")
                        callback(notification)
                        
                        if auto_reply:
                            self._handle_notification_auto_reply(notification)
                
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                print("\nStopping Mastodon listener...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in Mastodon listener loop: {e}")
                time.sleep(self.poll_interval)
    
    def _handle_notification_auto_reply(self, notification: Dict):
        """
        Automatically generate and post a reply to a notification.
        
        Args:
            notification: Notification dictionary
        """
        status_content = notification.get("status_content", "")
        status_id = notification.get("status_id")
        
        if not status_content or not status_id:
            return
        
        print(f"Generating reply for status {status_id}...")
        
        # Use RAG to retrieve relevant context
        # Extract query from the notification content (first 100 chars)
        query = status_content[:100] if len(status_content) > 100 else status_content
        
        # Retrieve relevant context using hybrid search
        retrieved_chunks = hybrid_search(query, top_k=5, include_posts=True)
        
        # Format context
        if retrieved_chunks:
            context_parts = [chunk.content for chunk in retrieved_chunks]
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "Ramos de Bry is a luxury Mexican-inspired floral brand."
        
        # Generate reply using RAG context
        posts = [{
            "id": status_id,
            "content": status_content
        }]
        
        try:
            replies = generate_replies(context, posts)
            
            if replies.replies:
                reply_text = replies.replies[0].reply_text
                print(f"Generated reply: {reply_text[:100]}...")
                
                # Post the reply
                if self._post_reply(status_id, reply_text, status_id):
                    print(f"Reply posted successfully!")
                else:
                    print(f"Failed to post reply")
        except Exception as e:
            print(f"Error generating reply: {e}")
    
    def stop(self):
        """Stop the listener."""
        self.running = False


def watch_mastodon_notifications(callback: Callable[[Dict], None], poll_interval: int = 60, auto_reply: bool = False):
    """
    Convenience function to watch for Mastodon notifications.
    
    Args:
        callback: Function to call when notifications are detected
        poll_interval: Time in seconds between polls
        auto_reply: If True, automatically generate and post replies
    """
    listener = MastodonListener(poll_interval=poll_interval)
    listener.watch_mastodon_notifications(callback, auto_reply=auto_reply)


def handle_mastodon_notification(notification: Dict):
    """
    Default handler for Mastodon notifications: logs the notification.
    
    Args:
        notification: Dict with notification information
    """
    print(f"Received {notification['type']} notification:")
    print(f"  From: @{notification['account']}")
    print(f"  Content: {notification['status_content'][:100]}...")
    print(f"  URL: {notification['status_url']}")


if __name__ == "__main__":
    # Example usage
    print("Starting Mastodon listener...")
    watch_mastodon_notifications(handle_mastodon_notification, poll_interval=30, auto_reply=True)
