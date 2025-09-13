"""
Web search and content retrieval functionality for RAG.
"""

import re
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import quote
from typing import List, Dict, Optional

def perform_web_search(query: str) -> List[Dict[str, str]]:
    """
    Performs a web search using DuckDuckGo by scraping the HTML results page.
    Returns a list of dicts: {title, link, snippet}.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f"https://duckduckgo.com/html/?q={quote(query)}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        result_divs = soup.find_all('div', class_='result')
        for result in result_divs:
            if isinstance(result, Tag):
                link_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet') or result.find('div', class_='result__snippet')
                if link_tag and snippet_tag and isinstance(link_tag, Tag) and isinstance(snippet_tag, Tag):
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get('href')
                    snippet = snippet_tag.get_text(strip=True)
                    # Basic filtering for non-http links from DDG
                    if link and isinstance(link, str) and link.startswith('http'):
                        results.append({'title': title, 'link': link, 'snippet': snippet})
        return results
    except requests.exceptions.RequestException as e:
        print(f"DuckDuckGo web search request error: {e}")
        return []
    except Exception as e:
        print(f"DuckDuckGo web search parsing error: {e}")
        return []

def apply_post_retrieval_filtering(text_content: str) -> str:
    """
    Removes common ad-like, social media, and trash content from retrieved text.
    """
    if not text_content:
        return text_content
    trash_patterns = [
        r"subscribe(\s+to\s+our)?", r"follow\s+us", r"ad[s]?:", r"sponsored",
        r"like\s+and\s+share", r"click\s+here", r"sign\s+up\s+now", r"buy\s+now",
        r"limited\s+time\s+offer", r"giveaway", r"contest", r"promo\s+code",
        r"discount\s+code", r"share\s+this\s+post", r"follow\s+me\s+on",
        r"find\s+us\s+on", r"visit\s+our\s+website", r"download\s+our\s+app",
        r"join\s+our\s+newsletter", r"support\s+us\s+on", r"patreon",
        r"instagram|facebook|twitter|tiktok|youtube",
    ]
    lines = text_content.splitlines()
    filtered_lines = [
        line for line in lines if not any(re.search(pattern, line.strip().lower()) for pattern in trash_patterns)
    ]
    return "\n".join(filtered_lines)

def scrape_url_content(url: str) -> Optional[str]:
    """
    Fetches HTML content from a URL and extracts visible text from <p> tags.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = [p.get_text() for p in soup.find_all('p')]
        return "\n".join(paragraphs)
    except requests.exceptions.RequestException as e:
        print(f"Error scraping URL {url}: {e}")
        return None
