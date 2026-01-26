import asyncio
from dotenv import load_dotenv
load_dotenv()
from notion_client import fetch_all_docs
from post_generator import generate_post
from mastodon_client import post_status, upload_media
from mastodon_client import search_recent_posts
from reply_generator import generate_replies
from image_generator import ImageGenerator
from telegram_client import wait_for_approval
from knowledge_base import sync_notion_to_database
from rag_database import init_database


async def main(generate_image: bool = True, require_approval: bool = True, query: str = None):
    """
    Main function to generate and post content to Mastodon with Telegram HITL.
    
    Args:
        generate_image: Whether to generate and attach an image to the post
        require_approval: Whether to require Telegram approval before posting
        query: Optional query for RAG retrieval (if None, uses general brand theme)
    """
    # Initialize database and ensure knowledge base is synced
    init_database()
    # Note: In production, you might want to check if sync is needed
    # For now, we'll assume the knowledge base is already synced
    # Uncomment the line below to force a sync on each run:
    # sync_notion_to_database(force_resync=False)
    
    # Generate post using RAG
    post = generate_post(query=query)
    print("Generated Post:\n", post)
    
    image_url = None
    if generate_image:
        try:
            print("\nGenerating image...")
            generator = ImageGenerator()
            image_url = generator.generate_bouquet_image(
                description="extravagant rose bouquets",
                letter="B",  # You can make this dynamic based on post content
            )
            print(f"Generated image URL: {image_url}")
        except Exception as e:
            print(f"Warning: Could not generate image: {e}")
            print("Continuing without image...")
    
    # Human-in-the-loop approval via Telegram
    if require_approval:
        print("\n📱 Sending to Telegram for approval...")
        decision, rejection_reason = await wait_for_approval(
            post_text=post,
            image_url=image_url,
            collect_feedback=True,
            timeout=300.0,  # 5 minute timeout
        )
        
        if decision == "reject":
            print(f"\n❌ Post rejected by human reviewer.")
            if rejection_reason:
                print(f"📝 Feedback: {rejection_reason}")
            print("Post will not be published.")
            return
        else:
            print("\n✅ Post approved! Publishing to Mastodon...")
    
    # Upload image to Mastodon if we have one
    media_ids = None
    if image_url:
        try:
            media_id = upload_media(image_url, description="Mexican-style extravagant rose bouquet")
            media_ids = [media_id]
            print("Image uploaded to Mastodon successfully")
        except Exception as e:
            print(f"Warning: Could not upload image to Mastodon: {e}")
            print("Posting without image...")
    
    # Post to Mastodon
    post_status(post, media_ids=media_ids)
    print("\n✅ Post published to Mastodon!")


def run_goal_4():
    """
    Generate replies to recent Mastodon posts using RAG.
    """
    from rag_retriever import hybrid_search
    
    posts = search_recent_posts(
        keyword="flowers",
        limit=5,
    )
    
    if not posts:
        print("No posts found to reply to.")
        return
    
    # Use RAG to retrieve relevant context for each post
    # For simplicity, we'll use the first post's content as query
    # In a more sophisticated implementation, you could generate queries per post
    query = posts[0].get("content", "flowers")[:100] if posts else "flowers"
    
    # Retrieve relevant context using hybrid search (including stored posts)
    retrieved_chunks = hybrid_search(query, top_k=5, include_posts=True)
    
    # Format context
    if retrieved_chunks:
        context_parts = [chunk.content for chunk in retrieved_chunks]
        context = "\n\n---\n\n".join(context_parts)
    else:
        # Fallback to fetching all docs if no chunks found
        context = fetch_all_docs()
    
    replies = generate_replies(context, posts)

    print("\n=== GENERATED REPLIES ===\n")
    for r in replies.replies:
        print(f"Post ID: {r.post_id}")
        print(f"Reply: {r.reply_text}\n")


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
    # Uncomment to also run goal 4:
    # run_goal_4()
