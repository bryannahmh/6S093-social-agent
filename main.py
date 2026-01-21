from dotenv import load_dotenv
load_dotenv()
from notion_client import fetch_all_docs
from post_generator import generate_post
from mastodon_client import post_status
from mastodon_client import search_recent_posts
from reply_generator import generate_replies


def main():
    docs = fetch_all_docs()
    post = generate_post(docs)
    print("Generated Post:\n", post)
    post_status(post)


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
