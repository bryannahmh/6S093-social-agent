import os
import requests

def post_status(text: str):
    url = f"{os.environ['MASTODON_BASE_URL']}/api/v1/statuses"
    headers = {
        "Authorization": f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
    }
    data = {
        "status": text + "\n\n(AI-generated)",
        "visibility": "public",
    }
    requests.post(url, headers=headers, data=data)

def search_recent_posts(keyword: str, limit: int = 5):
    url = f"{os.environ['MASTODON_BASE_URL']}/api/v2/search"

    headers = {
        "Authorization": f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
    }

    params = {
        "q": keyword,
        "type": "statuses",
        "limit": limit,
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()

    statuses = res.json()["statuses"]

    return [
        {
            "id": s["id"],
            "content": s["content"],  # HTML
            "url": s["url"],
        }
        for s in statuses
    ]
