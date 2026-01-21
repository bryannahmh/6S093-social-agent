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

NOTION_API = "https://api.notion.com/v1"

def fetch_page_text(page_id: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
        "Notion-Version": "2022-06-28",
    }

    url = f"{NOTION_API}/blocks/{page_id}/children"
    res = requests.get(url, headers=headers).json()

    lines = []
    for block in res["results"]:
        if "rich_text" in block.get(block["type"], {}):
            for rt in block[block["type"]]["rich_text"]:
                lines.append(rt["plain_text"])

    return "\n".join(lines)

def fetch_all_docs() -> str:
    page_ids = os.environ["NOTION_PAGE_IDS"].split(",")
    docs = [fetch_page_text(pid) for pid in page_ids]
    return "\n\n---\n\n".join(docs)
