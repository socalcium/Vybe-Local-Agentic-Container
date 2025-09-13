"""
Web Content Loader for RAG Integration
Fetches and processes web content for ingestion into RAG collections
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import re

class WebContentLoader:
    """Loads and processes web content for RAG ingestion"""
    
    def __init__(self, timeout=10, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set user agent to appear as a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def __del__(self):
        """Cleanup session on object destruction"""
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
        except Exception:
            pass  # Ignore cleanup errors
    
    def fetch_url(self, url):
        """
        Fetch content from a single URL with enhanced validation and error handling
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            dict: Processed content with metadata or None if failed
        """
        try:
            # Enhanced URL validation
            if not url or not isinstance(url, str):
                raise ValueError("URL must be a non-empty string")
            
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format - missing scheme or domain")
            
            # Security checks
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Only HTTP and HTTPS URLs are supported")
            
            # Check for potentially malicious URLs
            if self._is_suspicious_url(url):
                raise ValueError("URL appears to be suspicious or potentially malicious")
            
            # Fetch content with enhanced retries
            response = None
            last_error = None
            
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise e
            
            # Ensure we have a valid response
            if response is None:
                raise RuntimeError("Failed to get response after all retry attempts")
            
            # Validate response size
            content_length = len(response.content)
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError(f"Content too large: {content_length} bytes")
            
            # Process content based on type
            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                return self._process_html(response.text, url)
            elif 'text/plain' in content_type:
                return self._process_text(response.text, url)
            elif 'application/json' in content_type:
                return self._process_json(response.text, url)
            else:
                # Try to process as HTML anyway
                return self._process_html(response.text, url)
                
        except Exception as e:
            print(f"Error fetching URL {url}: {str(e)}")
            return None
    
    def _is_suspicious_url(self, url):
        """Check if URL appears suspicious or potentially malicious"""
        suspicious_patterns = [
            r'javascript:', r'data:', r'file:', r'ftp:', r'gopher:',
            r'localhost', r'127\.0\.0\.1', r'0\.0\.0\.0',
            r'\.(exe|bat|cmd|com|pif|scr|vbs|js)$',
            r'[<>"\']',  # HTML injection attempts
        ]
        
        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                return True
        return False
    
    def _process_html(self, html_content, url):
        """Process HTML content and extract meaningful text"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Extract metadata
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            
            # Extract main content
            text_content = self._extract_main_text(soup)
            
            # Clean and normalize text
            cleaned_text = self._clean_text(text_content)
            
            if not cleaned_text.strip():
                return None
            
            return {
                'url': url,
                'title': title,
                'description': description,
                'content': cleaned_text,
                'content_type': 'html',
                'word_count': len(cleaned_text.split()),
                'char_count': len(cleaned_text)
            }
            
        except Exception as e:
            print(f"Error processing HTML from {url}: {str(e)}")
            return None
    
    def _process_text(self, text_content, url):
        """Process plain text content"""
        try:
            cleaned_text = self._clean_text(text_content)
            
            if not cleaned_text.strip():
                return None
            
            # Try to extract a title from the first line
            lines = cleaned_text.split('\n')
            title = lines[0][:100] + '...' if len(lines[0]) > 100 else lines[0]
            
            return {
                'url': url,
                'title': title,
                'description': '',
                'content': cleaned_text,
                'content_type': 'text',
                'word_count': len(cleaned_text.split()),
                'char_count': len(cleaned_text)
            }
            
        except Exception as e:
            print(f"Error processing text from {url}: {str(e)}")
            return None
    
    def _extract_title(self, soup):
        """Extract page title"""
        # Try title tag first
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1 as fallback
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        return "Untitled"
    
    def _extract_description(self, soup):
        """Extract page description"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        return ""
    
    def _extract_main_text(self, soup):
        """Extract main text content from HTML"""
        # Try to find main content areas
        main_selectors = [
            'main', 'article', '[role="main"]', 
            '.content', '.main-content', '.post-content',
            '.entry-content', '.article-content'
        ]
        
        main_content = None
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text
        text_content = main_content.get_text(separator='\n', strip=True)
        return text_content
    
    def _clean_text(self, text):
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Reduce multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces and tabs
        
        # Remove common noise patterns
        noise_patterns = [
            r'Cookie Policy.*?(?=\n|$)',
            r'Privacy Policy.*?(?=\n|$)',
            r'Terms of Service.*?(?=\n|$)',
            r'Subscribe to.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Trim and normalize
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        return text.strip()
    
    def _process_json(self, json_content, url):
        """Process JSON content and extract meaningful text"""
        try:
            import json
            data = json.loads(json_content)
            
            # Extract text from common JSON structures
            text_parts = []
            
            if isinstance(data, dict):
                # Common fields that might contain text
                text_fields = ['title', 'name', 'description', 'content', 'text', 'body', 'summary']
                for field in text_fields:
                    if field in data and isinstance(data[field], str):
                        text_parts.append(data[field])
                
                # Recursively extract text from nested structures
                text_parts.extend(self._extract_text_from_dict(data))
            elif isinstance(data, list):
                # Extract text from list items
                for item in data[:10]:  # Limit to first 10 items
                    if isinstance(item, dict):
                        text_parts.extend(self._extract_text_from_dict(item))
                    elif isinstance(item, str):
                        text_parts.append(item)
            
            content = ' '.join(text_parts)
            if not content.strip():
                content = str(data)[:1000]  # Fallback to string representation
            
            return {
                'url': url,
                'title': url,
                'description': 'JSON content',
                'content': content,
                'content_type': 'json',
                'word_count': len(content.split()),
                'timestamp': time.time()
            }
            
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as text
            return self._process_text(json_content, url)
    
    def _extract_text_from_dict(self, data, max_depth=3, current_depth=0):
        """Recursively extract text from dictionary structures"""
        if current_depth >= max_depth:
            return []
        
        text_parts = []
        for key, value in data.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                text_parts.extend(self._extract_text_from_dict(value, max_depth, current_depth + 1))
            elif isinstance(value, list):
                for item in value[:5]:  # Limit nested lists
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        text_parts.extend(self._extract_text_from_dict(item, max_depth, current_depth + 1))
        
        return text_parts
    
    def fetch_multiple_urls(self, urls, delay=1):
        """
        Fetch content from multiple URLs with optional delay
        
        Args:
            urls (list): List of URLs to fetch
            delay (float): Delay between requests in seconds
            
        Returns:
            list: List of processed content dictionaries
        """
        results = []
        
        for i, url in enumerate(urls):
            if i > 0 and delay > 0:
                time.sleep(delay)
            
            content = self.fetch_url(url)
            if content:
                results.append(content)
        
        return results

# Helper function for easy use
def load_web_content(url):
    """
    Simple helper function to load content from a URL
    
    Args:
        url (str): The URL to load
        
    Returns:
        str: The extracted text content or None if failed
    """
    try:
        loader = WebContentLoader()
        result = loader.fetch_url(url)
        if result and 'content' in result:
            return result['content']
        return None
    except Exception as e:
        print(f"Error loading web content from {url}: {str(e)}")
        return None
