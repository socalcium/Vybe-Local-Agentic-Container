"""
Notion Connector
Connects to Notion workspaces to sync pages and their content
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_connector import BaseConnector, SyncResult, ConnectorError

class NotionConnector(BaseConnector):
    """Connector for Notion workspaces"""
    
    @property
    def display_name(self) -> str:
        return "Notion"
    
    @property
    def description(self) -> str:
        return "Sync pages and content from Notion workspaces"
    
    @property
    def icon(self) -> str:
        return "bi bi-journal-text"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["api_key"]
    
    @property
    def default_collection_name(self) -> str:
        return "notion_pages"
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to Notion using API key"""
        try:
            api_key = credentials.get("api_key")
            
            if not api_key:
                raise ConnectorError("Notion API key is required")
            
            # Test the connection by getting the bot user info
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://api.notion.com/v1/users/me"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        
                        # Store credentials with user metadata
                        self.store_credentials({
                            "api_key": api_key,
                            "bot_id": user_data.get("id"),
                            "bot_name": user_data.get("name"),
                            "workspace_name": user_data.get("workspace_name")
                        })
                        
                        self.logger.info(f"Connected to Notion as: {user_data.get('name')}")
                        return True
                    elif response.status == 401:
                        raise ConnectorError("Invalid Notion API key")
                    else:
                        raise ConnectorError(f"Notion API error: {response.status}")
                        
        except aiohttp.ClientError as e:
            raise ConnectorError(f"Network error connecting to Notion: {e}")
        except Exception as e:
            self.logger.error(f"Notion connection failed: {e}")
            raise ConnectorError(f"Failed to connect to Notion: {e}")
    
    async def test_connection(self) -> bool:
        """Test if the current Notion connection is valid"""
        try:
            if not self.credentials or not self.credentials.credentials:
                return False
            
            api_key = self.credentials.credentials.get("api_key")
            
            if not api_key:
                return False
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://api.notion.com/v1/users/me"
                async with session.get(url, headers=headers) as response:
                    self._update_last_used()
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Notion connection test failed: {e}")
            return False
    
    async def sync(self) -> SyncResult:
        """Sync pages from Notion workspace"""
        start_time = datetime.now()
        result = SyncResult(success=False, collection_name=self.default_collection_name)
        
        try:
            if not self.credentials or not self.credentials.credentials:
                raise ConnectorError("No Notion credentials available")
            
            api_key = self.credentials.credentials.get("api_key")
            
            if not api_key:
                raise ConnectorError("Missing Notion API key in credentials")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Search for all pages accessible by the integration
                pages_to_process = await self._search_pages(session, headers)
                result.items_processed = len(pages_to_process)
                
                # Process each page
                for page_info in pages_to_process:
                    try:
                        success = await self._process_page(session, page_info, headers)
                        
                        if success:
                            result.items_added += 1
                        else:
                            result.items_failed += 1
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process page {page_info.get('id')}: {e}")
                        result.items_failed += 1
                
                result.success = result.items_failed < result.items_processed
                self._update_last_used()
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Notion sync failed: {e}")
        
        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _search_pages(self, session: aiohttp.ClientSession, 
                           headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Search for all accessible pages in Notion"""
        pages = []
        
        search_data = {
            "filter": {
                "value": "page",
                "property": "object"
            },
            "page_size": 100
        }
        
        url = "https://api.notion.com/v1/search"
        
        async with session.post(url, headers=headers, json=search_data) as response:
            if response.status != 200:
                raise ConnectorError(f"Failed to search Notion pages: {response.status}")
            
            search_results = await response.json()
            pages.extend(search_results.get("results", []))
            
            # Handle pagination if needed
            has_more = search_results.get("has_more", False)
            next_cursor = search_results.get("next_cursor")
            
            while has_more and next_cursor:
                search_data["start_cursor"] = next_cursor
                
                async with session.post(url, headers=headers, json=search_data) as response:
                    if response.status != 200:
                        break
                    
                    search_results = await response.json()
                    pages.extend(search_results.get("results", []))
                    has_more = search_results.get("has_more", False)
                    next_cursor = search_results.get("next_cursor")
        
        self.logger.info(f"Found {len(pages)} pages in Notion workspace")
        return pages
    
    async def _process_page(self, session: aiohttp.ClientSession, 
                           page_info: Dict[str, Any], 
                           headers: Dict[str, str]) -> bool:
        """Process a single page from Notion"""
        try:
            page_id = page_info["id"]
            page_url = page_info.get("url", "")
            
            # Get page title
            properties = page_info.get("properties", {})
            title_property = properties.get("title") or properties.get("Name")
            
            if title_property and title_property.get("title"):
                page_title = title_property["title"][0]["plain_text"] if title_property["title"] else "Untitled"
            else:
                page_title = "Untitled"
            
            # Get page content by fetching blocks
            content = await self._get_page_content(session, page_id, headers)
            
            if not content.strip():
                return False  # Skip empty pages
            
            # Create unique content ID
            content_id = f"notion_{page_id}_{page_title.replace(' ', '_')}"
            
            # Prepare metadata
            metadata = {
                "source": "notion",
                "page_id": page_id,
                "page_title": page_title,
                "page_url": page_url,
                "created_time": page_info.get("created_time"),
                "last_edited_time": page_info.get("last_edited_time"),
                "object_type": page_info.get("object")
            }
            
            # Ingest into RAG
            return await self._ingest_content_to_rag(
                content=content,
                content_id=content_id,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error processing page {page_info.get('id')}: {e}")
            return False
    
    async def _get_page_content(self, session: aiohttp.ClientSession, 
                               page_id: str, headers: Dict[str, str]) -> str:
        """Get the text content of a Notion page"""
        try:
            content_parts = []
            
            # Get page blocks
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get page blocks for {page_id}: {response.status}")
                    return ""
                
                blocks_data = await response.json()
                blocks = blocks_data.get("results", [])
                
                # Extract text from blocks
                for block in blocks:
                    block_text = self._extract_text_from_block(block)
                    if block_text:
                        content_parts.append(block_text)
            
            return "\n".join(content_parts)
            
        except Exception as e:
            self.logger.error(f"Error getting page content for {page_id}: {e}")
            return ""
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> str:
        """Extract plain text from a Notion block"""
        try:
            block_type = block.get("type")
            
            if not block_type:
                return ""
            
            block_data = block.get(block_type, {})
            
            # Handle different block types
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
                rich_text = block_data.get("rich_text", [])
                return "".join([text.get("plain_text", "") for text in rich_text])
            
            elif block_type == "code":
                rich_text = block_data.get("rich_text", [])
                code_text = "".join([text.get("plain_text", "") for text in rich_text])
                language = block_data.get("language", "")
                return f"```{language}\n{code_text}\n```"
            
            elif block_type == "quote":
                rich_text = block_data.get("rich_text", [])
                quote_text = "".join([text.get("plain_text", "") for text in rich_text])
                return f"> {quote_text}"
            
            elif block_type == "callout":
                rich_text = block_data.get("rich_text", [])
                return "".join([text.get("plain_text", "") for text in rich_text])
            
            # Add more block types as needed
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting text from block: {e}")
            return ""
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get a summary of the connector for display"""
        if not self.credentials or not self.credentials.credentials:
            return {
                "status": "not_connected",
                "bot_name": None,
                "last_sync": None
            }
        
        return {
            "status": self.get_status().value,
            "bot_name": self.credentials.credentials.get("bot_name"),
            "workspace_name": self.credentials.credentials.get("workspace_name"),
            "last_sync": self.credentials.last_used.isoformat() if self.credentials.last_used else None
        }
