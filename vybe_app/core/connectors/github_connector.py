"""
GitHub Connector
Connects to GitHub repositories to sync markdown and text files
"""

import aiohttp
import asyncio
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_connector import BaseConnector, SyncResult, ConnectorError

class GitHubConnector(BaseConnector):
    """Connector for GitHub repositories"""
    
    @property
    def display_name(self) -> str:
        return "GitHub"
    
    @property
    def description(self) -> str:
        return "Sync markdown and text files from GitHub repositories"
    
    @property
    def icon(self) -> str:
        return "bi bi-github"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["token", "repository"]
    
    @property
    def default_collection_name(self) -> str:
        return "github_docs"
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to GitHub using Personal Access Token"""
        try:
            token = credentials.get("token")
            repository = credentials.get("repository")
            
            if not token or not repository:
                raise ConnectorError("GitHub token and repository are required")
            
            # Test the connection by getting repository info
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Vybe-AI-Assistant"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/repos/{repository}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        
                        # Store credentials with repository metadata
                        self.store_credentials({
                            "token": token,
                            "repository": repository,
                            "repo_name": repo_data.get("name"),
                            "repo_description": repo_data.get("description"),
                            "default_branch": repo_data.get("default_branch", "main")
                        })
                        
                        self.logger.info(f"Connected to GitHub repository: {repository}")
                        return True
                    elif response.status == 404:
                        raise ConnectorError("Repository not found or not accessible")
                    elif response.status == 401:
                        raise ConnectorError("Invalid GitHub token")
                    else:
                        raise ConnectorError(f"GitHub API error: {response.status}")
                        
        except aiohttp.ClientError as e:
            raise ConnectorError(f"Network error connecting to GitHub: {e}")
        except Exception as e:
            self.logger.error(f"GitHub connection failed: {e}")
            raise ConnectorError(f"Failed to connect to GitHub: {e}")
    
    async def test_connection(self) -> bool:
        """Test if the current GitHub connection is valid"""
        try:
            if not self.credentials or not self.credentials.credentials:
                return False
            
            token = self.credentials.credentials.get("token")
            repository = self.credentials.credentials.get("repository")
            
            if not token or not repository:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Vybe-AI-Assistant"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/repos/{repository}"
                async with session.get(url, headers=headers) as response:
                    self._update_last_used()
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"GitHub connection test failed: {e}")
            return False
    
    async def sync(self) -> SyncResult:
        """Sync markdown and text files from GitHub repository"""
        start_time = datetime.now()
        result = SyncResult(success=False, collection_name=self.default_collection_name)
        
        try:
            if not self.credentials or not self.credentials.credentials:
                raise ConnectorError("No GitHub credentials available")
            
            token = self.credentials.credentials.get("token")
            repository = self.credentials.credentials.get("repository")
            default_branch = self.credentials.credentials.get("default_branch", "main")
            
            if not token or not repository:
                raise ConnectorError("Missing GitHub token or repository in credentials")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Vybe-AI-Assistant"
            }
            
            async with aiohttp.ClientSession() as session:
                # Get all files in the repository
                files_to_process = await self._get_repository_files(
                    session, repository, default_branch, headers
                )
                
                result.items_processed = len(files_to_process)
                
                # Process each file
                for file_info in files_to_process:
                    try:
                        success = await self._process_file(
                            session, repository, file_info, headers
                        )
                        
                        if success:
                            result.items_added += 1
                        else:
                            result.items_failed += 1
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process file {file_info.get('path')}: {e}")
                        result.items_failed += 1
                
                result.success = result.items_failed < result.items_processed
                self._update_last_used()
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"GitHub sync failed: {e}")
        
        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _get_repository_files(self, session: aiohttp.ClientSession, 
                                   repository: str, branch: str, 
                                   headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get all markdown and text files from the repository"""
        files_to_process = []
        
        # Get repository tree recursively
        url = f"https://api.github.com/repos/{repository}/git/trees/{branch}?recursive=1"
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ConnectorError(f"Failed to get repository tree: {response.status}")
            
            tree_data = await response.json()
            
            for item in tree_data.get("tree", []):
                if item.get("type") == "blob":  # It's a file
                    path = item.get("path", "")
                    
                    # Check if it's a markdown or text file
                    if any(path.lower().endswith(ext) for ext in ['.md', '.txt', '.markdown', '.rst']):
                        files_to_process.append({
                            "path": path,
                            "sha": item.get("sha"),
                            "url": item.get("url")
                        })
        
        self.logger.info(f"Found {len(files_to_process)} text files in {repository}")
        return files_to_process
    
    async def _process_file(self, session: aiohttp.ClientSession, 
                           repository: str, file_info: Dict[str, Any], 
                           headers: Dict[str, str]) -> bool:
        """Process a single file from GitHub"""
        try:
            path = file_info["path"]
            sha = file_info["sha"]
            
            # Get file content
            url = f"https://api.github.com/repos/{repository}/git/blobs/{sha}"
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get file content for {path}: {response.status}")
                    return False
                
                blob_data = await response.json()
                
                # Decode base64 content
                if blob_data.get("encoding") == "base64":
                    content_bytes = base64.b64decode(blob_data["content"])
                    try:
                        content = content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        # Try with different encoding
                        content = content_bytes.decode('utf-8', errors='ignore')
                else:
                    content = blob_data.get("content", "")
                
                # Skip empty files
                if not content.strip():
                    return False
                
                # Create unique content ID
                content_id = f"github_{repository.replace('/', '_')}_{path.replace('/', '_')}"
                
                # Prepare metadata
                metadata = {
                    "source": "github",
                    "repository": repository,
                    "file_path": path,
                    "file_sha": sha,
                    "file_type": path.split('.')[-1].lower() if '.' in path else "unknown"
                }
                
                # Ingest into RAG
                return await self._ingest_content_to_rag(
                    content=content,
                    content_id=content_id,
                    metadata=metadata
                )
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_info.get('path')}: {e}")
            return False
    
    def get_repository_url(self) -> Optional[str]:
        """Get the GitHub repository URL"""
        if not self.credentials or not self.credentials.credentials:
            return None
        
        repository = self.credentials.credentials.get("repository")
        if repository:
            return f"https://github.com/{repository}"
        
        return None
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get a summary of the connector for display"""
        if not self.credentials or not self.credentials.credentials:
            return {
                "status": "not_connected",
                "repository": None,
                "last_sync": None
            }
        
        return {
            "status": self.get_status().value,
            "repository": self.credentials.credentials.get("repository"),
            "repo_name": self.credentials.credentials.get("repo_name"),
            "last_sync": self.credentials.last_used.isoformat() if self.credentials.last_used else None,
            "repository_url": self.get_repository_url()
        }
