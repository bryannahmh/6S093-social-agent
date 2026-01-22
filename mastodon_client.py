import os
import requests
from typing import Optional, List


def upload_media(image_url: str, description: Optional[str] = None) -> str:
    """
    Upload an image to Mastodon from a URL.
    
    Args:
        image_url: URL of the image to upload
        description: Optional alt text description for accessibility
    
    Returns:
        Media ID to attach to status
    """
    # Download the image
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    
    # Determine content type from URL or response headers
    content_type = image_response.headers.get('Content-Type', 'image/jpeg')
    if not content_type.startswith('image/'):
        # Fallback: detect from URL extension
        if image_url.endswith('.webp'):
            content_type = 'image/webp'
        elif image_url.endswith('.png'):
            content_type = 'image/png'
        elif image_url.endswith('.jpg') or image_url.endswith('.jpeg'):
            content_type = 'image/jpeg'
        else:
            content_type = 'image/jpeg'  # Default fallback
    
    # Determine filename extension
    if '.webp' in image_url:
        filename = 'image.webp'
    elif '.png' in image_url:
        filename = 'image.png'
    else:
        filename = 'image.jpg'
    
    # Upload to Mastodon (use v1 endpoint for media)
    upload_url = f"{os.environ['MASTODON_BASE_URL']}/api/v1/media"
    headers = {
        "Authorization": f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
    }
    
    files = {
        "file": (filename, image_response.content, content_type)
    }
    
    data = {}
    if description:
        data["description"] = description
    
    response = requests.post(upload_url, headers=headers, files=files, data=data)
    
    # Better error handling
    if response.status_code == 401:
        try:
            error_msg = response.json().get("error", response.text)
        except:
            error_msg = response.text
        raise requests.exceptions.HTTPError(
            f"401 Unauthorized: {error_msg}. "
            f"Check that your MASTODON_ACCESS_TOKEN is valid and has 'write:media' scope."
        )
    
    response.raise_for_status()
    
    media_data = response.json()
    return media_data["id"]


def post_status(text: str, media_ids: Optional[List[str]] = None):
    """
    Post a status to Mastodon, optionally with images.
    
    Args:
        text: Status text content
        media_ids: Optional list of media IDs to attach (from upload_media)
    """
    url = f"{os.environ['MASTODON_BASE_URL']}/api/v1/statuses"
    headers = {
        "Authorization": f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
    }
    
    # Build form data
    data = [
        ("status", text + "\n\n(AI-generated)"),
        ("visibility", "public"),
    ]
    
    # Add media_ids if provided (Mastodon expects media_ids[] for each ID)
    if media_ids:
        for media_id in media_ids:
            data.append(("media_ids[]", str(media_id)))
    
    response = requests.post(url, headers=headers, data=data)
    
    # Better error handling
    if response.status_code == 401:
        try:
            error_msg = response.json().get("error", response.text)
        except:
            error_msg = response.text
        raise requests.exceptions.HTTPError(
            f"401 Unauthorized: {error_msg}. "
            f"Check that your MASTODON_ACCESS_TOKEN is valid and has 'write:statuses' scope."
        )
    
    response.raise_for_status()

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
