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


async def main(generate_image: bool = True, require_approval: bool = True):
    """
    Main function to generate and post content to Mastodon with Telegram HITL.
    
    Args:
        generate_image: Whether to generate and attach an image to the post
        require_approval: Whether to require Telegram approval before posting
    """
    docs = fetch_all_docs()
    post = generate_post(docs)
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
    docs = fetch_all_docs()

    posts = search_recent_posts(
        keyword="flowers",
        limit=5,
    )

    replies = generate_replies(docs, posts)

    print("\n=== GENERATED REPLIES ===\n")
    for r in replies.replies:
        print(f"Post ID: {r.post_id}")
        print(f"Reply: {r.reply_text}\n")


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
    # Uncomment to also run goal 4:
    # run_goal_4()
