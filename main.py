from dotenv import load_dotenv
load_dotenv()
from notion_client import fetch_all_docs
from post_generator import generate_post
from mastodon_client import post_status, upload_media
from mastodon_client import search_recent_posts
from reply_generator import generate_replies
from image_generator import ImageGenerator


def main(generate_image: bool = True):
    """
    Main function to generate and post content to Mastodon.
    
    Args:
        generate_image: Whether to generate and attach an image to the post
    """
    docs = fetch_all_docs()
    post = generate_post(docs)
    print("Generated Post:\n", post)
    
    media_ids = None
    if generate_image:
        try:
            print("\nGenerating image...")
            generator = ImageGenerator()
            image_url = generator.generate_bouquet_image(
                description="extravagant rose bouquets",
                letter="B",  # You can make this dynamic based on post content
            )
            print(f"Generated image URL: {image_url}")
            
            # Upload image to Mastodon
            media_id = upload_media(image_url, description="Mexican-style extravagant rose bouquet")
            media_ids = [media_id]
            print("Image uploaded successfully")
        except Exception as e:
            print(f"Warning: Could not generate/upload image: {e}")
            print("Posting without image...")
    
    post_status(post, media_ids=media_ids)


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
    main()
    run_goal_4()
