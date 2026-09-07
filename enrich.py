"""
Enriches a scraped business with a quick, lightweight audit of its own
website -- no paid APIs needed. This is what feeds the scoring logic in
scorer.py.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT, ONLINE_ORDERING_KEYWORDS


def analyze_website(url: str) -> dict:
    """
    Returns a dict describing the state of a business's website.
    If url is None/empty, returns has_website=False and nothing else checked.
    """
    result = {
        "has_website": False,
        "reachable": False,
        "is_https": False,
        "mobile_friendly": False,
        "has_meta_description": False,
        "has_schema_markup": False,
        "has_ordering_keywords": False,
        "load_time_seconds": None,
        "title": None,
        "error": None,
    }

    if not url:
        return result

    result["has_website"] = True
    if not url.startswith("http"):
        url = "https://" + url
    result["is_https"] = urlparse(url).scheme == "https"

    headers = {"User-Agent": USER_AGENT}
    try:
        start = time.time()
        resp = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True
        )
        result["load_time_seconds"] = round(time.time() - start, 2)
        result["reachable"] = resp.status_code < 400

        if not result["reachable"]:
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        viewport = soup.find("meta", attrs={"name": "viewport"})
        result["mobile_friendly"] = viewport is not None

        meta_desc = soup.find("meta", attrs={"name": "description"})
        result["has_meta_description"] = bool(meta_desc and meta_desc.get("content"))

        result["has_schema_markup"] = bool(soup.find("script", attrs={"type": "application/ld+json"}))

        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else None

        page_text = soup.get_text(separator=" ").lower()
        result["has_ordering_keywords"] = any(kw in page_text for kw in ONLINE_ORDERING_KEYWORDS)

    except requests.RequestException as e:
        result["error"] = str(e)
        result["reachable"] = False

    return result
