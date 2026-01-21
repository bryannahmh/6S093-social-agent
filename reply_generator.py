# from pydantic import BaseModel
# from typing import List
# from llm import call_llm

# class ReplySet(BaseModel):
#     replies: List[str]

# def generate_replies(brand_docs: str, posts: list[str]) -> ReplySet:
#     joined = "\n".join(posts)

#     prompt = f"""
# BRAND DOCUMENTS:
# {brand_docs}

# POSTS:
# {joined}

# TASK:
# Generate a JSON object with exactly 5 thoughtful replies.
# Format:
# {{ "replies": ["...", "..."] }}
# """

#     raw = call_llm(
#         "You generate structured JSON only.",
#         prompt,
#         model="glm-4.5-air"
#     )

#     return ReplySet.model_validate_json(raw)

from pydantic import BaseModel
from typing import List
from llm import call_llm

class Reply(BaseModel):
    post_id: str
    reply_text: str

class ReplySet(BaseModel):
    replies: List[Reply]

def generate_replies(brand_docs: str, posts: list[dict]) -> ReplySet:
    formatted_posts = "\n\n".join(
        f"POST ID: {p['id']}\nCONTENT: {p['content']}"
        for p in posts
    )

    prompt = f"""
BRAND DOCUMENTS:
{brand_docs}

MASTODON POSTS:
{formatted_posts}

TASK:
Generate a reply to EACH post.

Rules:
- Be kind, thoughtful, and non-spammy
- Match the brand voice
- Do NOT repeat marketing language
- Output VALID JSON ONLY

JSON FORMAT:
{{
  "replies": [
    {{ "post_id": "...", "reply_text": "..." }}
  ]
}}
"""

    raw = call_llm(
        system="You generate strictly valid JSON.",
        user=prompt,
    )

    return ReplySet.model_validate_json(raw)
