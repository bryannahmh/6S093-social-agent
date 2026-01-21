from llm import call_llm

SYSTEM_PROMPT = """
You are the social media manager for Ramos de Bry,
a luxury Mexican-inspired floral brand.
Be bold, emotional, culturally proud.
"""

def generate_post(brand_docs: str) -> str:
    prompt = f"""
BRAND DOCUMENTS:
{brand_docs}

TASK:
Generate one Mastodon-style post (max 300 chars).
Include a dramatic tone.
"""
    return call_llm(SYSTEM_PROMPT, prompt)
