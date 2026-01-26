# import os
# import requests

# NOTION_API = "https://api.notion.com/v1"
# HEADERS = {
#     "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
#     "Notion-Version": "2022-06-28",
# }

# def fetch_page_text(page_id: str) -> str:
#     url = f"{NOTION_API}/blocks/{page_id}/children"
#     res = requests.get(url, headers=HEADERS).json()

#     lines = []
#     for block in res["results"]:
#         if "rich_text" in block.get(block["type"], {}):
#             for rt in block[block["type"]]["rich_text"]:
#                 lines.append(rt["plain_text"])

#     return "\n".join(lines)

# def fetch_all_docs() -> str:
#     page_ids = os.environ["NOTION_PAGE_IDS"].split(",")
#     docs = [fetch_page_text(pid) for pid in page_ids]
#     return "\n\n---\n\n".join(docs)

import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()

NOTION_API = "https://api.notion.com/v1"

def format_notion_id(page_id: str) -> str:
    """
    Convert Notion page ID to UUID format if needed.
    Notion IDs can be provided with or without dashes, but API requires UUID format.
    """
    # Remove any existing dashes and whitespace
    page_id = page_id.strip().replace("-", "")
    
    # If it's already 32 characters, format it as UUID
    if len(page_id) == 32:
        return f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
    
    # If it's already in UUID format (has dashes), return as is
    if "-" in page_id:
        return page_id.strip()
    
    # Otherwise, return as-is (will likely fail, but let API handle the error)
    return page_id

def fetch_page_text(page_id: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
        "Notion-Version": "2022-06-28",
    }

    # Format page ID to UUID format
    formatted_page_id = format_notion_id(page_id)
    url = f"{NOTION_API}/blocks/{formatted_page_id}/children"
    res = requests.get(url, headers=headers)
    
    # Check for errors
    if res.status_code != 200:
        error_msg = res.text
        try:
            error_json = res.json()
            error_msg = error_json.get("message", str(error_json))
        except:
            pass
        raise Exception(f"Notion API error (status {res.status_code}): {error_msg}")
    
    data = res.json()
    
    # Check if response has results key
    if "results" not in data:
        raise Exception(f"Unexpected Notion API response format: {data}")
    
    lines = []
    for block in data["results"]:
        if "rich_text" in block.get(block["type"], {}):
            for rt in block[block["type"]]["rich_text"]:
                lines.append(rt["plain_text"])

    return "\n".join(lines)

def fetch_all_docs() -> str:
    """Fetch all documents and return as concatenated string (legacy function)."""
    structured = fetch_all_docs_structured()
    return "\n\n---\n\n".join([doc["content"] for doc in structured])


def fetch_all_docs_structured() -> list[dict]:
    """
    Fetch all documents and return as structured list.
    
    Returns:
        List of dictionaries with 'page_id' and 'content' keys
    """
    page_ids = [pid.strip() for pid in os.environ["NOTION_PAGE_IDS"].split(",")]
    docs = []
    for page_id in page_ids:
        try:
            content = fetch_page_text(page_id)
            docs.append({
                "page_id": page_id,
                "content": content
            })
        except Exception as e:
            print(f"Warning: Failed to fetch page {page_id}: {e}")
            continue
    return docs
