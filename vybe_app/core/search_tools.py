"""
Search Tools for Vybe Application
Implements web search functionality using the Brave Search API
"""

import requests
import json
from typing import List, Dict, Any, Optional
from ..config import Config
from ..logger import logger


def search_brave(query: str, count: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Perform a web search using the Brave Search API
    
    Args:
        query (str): The search query
        count (int, optional): Number of results to return. Defaults to Config.WEB_SEARCH_MAX_RESULTS
    
    Returns:
        List[Dict[str, Any]]: List of search results with title, link, and snippet
    """
    if not Config.BRAVE_SEARCH_API_KEY:
        logger.warning("Brave Search API key not configured")
        return [{
            'title': 'Search API Not Configured',
            'link': '#',
            'snippet': 'Please configure BRAVE_SEARCH_API_KEY in your environment variables to enable web search functionality.'
        }]
    
    if count is None:
        count = Config.WEB_SEARCH_MAX_RESULTS
    
    # Brave Search API endpoint
    url = "https://api.search.brave.com/res/v1/web/search"
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": Config.BRAVE_SEARCH_API_KEY
    }
    
    params = {
        "q": query,
        "count": min(count, 20),  # Brave API limits to 20 results per request
        "safesearch": "moderate",
        "search_lang": "en",
        "country": "US",
        "text_decorations": "false",
        "spellcheck": "true"
    }
    
    try:
        logger.info(f"Performing Brave search for query: {query}")
        response = requests.get(
            url, 
            headers=headers, 
            params=params, 
            timeout=Config.WEB_SEARCH_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # Extract web results
        web_results = data.get("web", {}).get("results", [])
        
        for result in web_results:
            # Clean and format the result
            clean_result = {
                'title': result.get('title', 'No Title'),
                'link': result.get('url', '#'),
                'snippet': result.get('description', 'No description available')
            }
            results.append(clean_result)
        
        logger.info(f"Retrieved {len(results)} search results")
        return results
    
    except requests.exceptions.Timeout:
        logger.error(f"Search request timed out after {Config.WEB_SEARCH_TIMEOUT} seconds")
        return [{
            'title': 'Search Timeout',
            'link': '#',
            'snippet': f'The search request timed out after {Config.WEB_SEARCH_TIMEOUT} seconds. Please try again.'
        }]
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error performing Brave search: {str(e)}")
        return [{
            'title': 'Search Error',
            'link': '#',
            'snippet': f'An error occurred while searching: {str(e)}'
        }]
    
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing Brave search response: {str(e)}")
        return [{
            'title': 'Search Response Error',
            'link': '#',
            'snippet': 'An error occurred while processing the search results. Please try again.'
        }]


def search_web_fallback(query: str) -> List[Dict[str, Any]]:
    """
    Fallback search function when Brave API is not available
    Returns mock results to maintain functionality
    
    Args:
        query (str): The search query
    
    Returns:
        List[Dict[str, Any]]: List of mock search results
    """
    logger.warning("Using fallback search - no real search performed")
    return [
        {
            'title': f'Mock Search Result for: "{query}"',
            'link': 'https://example.com',
            'snippet': f'This is a mock search result for the query "{query}". Configure BRAVE_SEARCH_API_KEY to enable real web search.'
        },
        {
            'title': 'Configure Web Search',
            'link': 'https://brave.com/search/api/',
            'snippet': 'Visit the Brave Search API documentation to get your API key and enable real web search functionality.'
        }
    ]
