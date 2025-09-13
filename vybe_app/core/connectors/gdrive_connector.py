"""
Google Drive Connector
Connects to Google Drive to sync Google Docs and text files
"""

import aiohttp
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlencode

from .base_connector import BaseConnector, SyncResult, ConnectorError

class GoogleDriveConnector(BaseConnector):
    """Connector for Google Drive"""
    
    @property
    def display_name(self) -> str:
        return "Google Drive"
    
    @property
    def description(self) -> str:
        return "Sync Google Docs and text files from Google Drive"
    
    @property
    def icon(self) -> str:
        return "bi bi-google"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["client_id", "client_secret", "refresh_token"]
    
    @property
    def default_collection_name(self) -> str:
        return "gdrive_docs"
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to Google Drive using OAuth2"""
        try:
            client_id = credentials.get("client_id")
            client_secret = credentials.get("client_secret")
            refresh_token = credentials.get("refresh_token")
            
            if not all([client_id, client_secret, refresh_token]):
                raise ConnectorError("Google Drive requires client_id, client_secret, and refresh_token")
            
            # Type assertion since we've checked they're not None
            client_id = str(client_id)
            client_secret = str(client_secret)
            refresh_token = str(refresh_token)
            
            # Get access token using refresh token
            access_token = await self._get_access_token(client_id, client_secret, refresh_token)
            
            if not access_token:
                raise ConnectorError("Failed to obtain Google Drive access token")
            
            # Test the connection by getting user info
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/drive/v3/about?fields=user"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        user_info = user_data.get("user", {})
                        
                        # Store credentials with user metadata
                        self.store_credentials({
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "refresh_token": refresh_token,
                            "access_token": access_token,
                            "user_email": user_info.get("emailAddress"),
                            "user_name": user_info.get("displayName")
                        })
                        
                        self.logger.info(f"Connected to Google Drive for user: {user_info.get('emailAddress')}")
                        return True
                    else:
                        raise ConnectorError(f"Google Drive API error: {response.status}")
                        
        except aiohttp.ClientError as e:
            raise ConnectorError(f"Network error connecting to Google Drive: {e}")
        except Exception as e:
            self.logger.error(f"Google Drive connection failed: {e}")
            raise ConnectorError(f"Failed to connect to Google Drive: {e}")
    
    async def test_connection(self) -> bool:
        """Test if the current Google Drive connection is valid"""
        try:
            if not self.credentials or not self.credentials.credentials:
                return False
            
            access_token = self.credentials.credentials.get("access_token")
            
            if not access_token:
                # Try to refresh token
                access_token = await self._refresh_access_token()
                if not access_token:
                    return False
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/drive/v3/about?fields=user"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        self._update_last_used()
                        return True
                    elif response.status == 401:
                        # Token expired, try to refresh
                        access_token = await self._refresh_access_token()
                        return access_token is not None
                    else:
                        return False
                    
        except Exception as e:
            self.logger.error(f"Google Drive connection test failed: {e}")
            return False
    
    async def sync(self) -> SyncResult:
        """Sync Google Docs and text files from Google Drive"""
        start_time = datetime.now()
        result = SyncResult(success=False, collection_name=self.default_collection_name)
        
        try:
            if not self.credentials or not self.credentials.credentials:
                raise ConnectorError("No Google Drive credentials available")
            
            access_token = await self._ensure_valid_access_token()
            if not access_token:
                raise ConnectorError("Failed to obtain valid access token")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Get all supported files
                files_to_process = await self._get_drive_files(session, headers)
                result.items_processed = len(files_to_process)
                
                # Process each file
                for file_info in files_to_process:
                    try:
                        success = await self._process_file(session, file_info, headers)
                        
                        if success:
                            result.items_added += 1
                        else:
                            result.items_failed += 1
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process file {file_info.get('name')}: {e}")
                        result.items_failed += 1
                
                result.success = result.items_failed < result.items_processed
                self._update_last_used()
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Google Drive sync failed: {e}")
        
        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _get_access_token(self, client_id: str, client_secret: str, refresh_token: str) -> Optional[str]:
        """Get access token using refresh token"""
        try:
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://oauth2.googleapis.com/token"
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data.get("access_token")
                    else:
                        self.logger.error(f"Failed to get access token: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
            return None
    
    async def _refresh_access_token(self) -> Optional[str]:
        """Refresh the stored access token"""
        try:
            if not self.credentials or not self.credentials.credentials:
                return None
            
            client_id = self.credentials.credentials.get("client_id")
            client_secret = self.credentials.credentials.get("client_secret")
            refresh_token = self.credentials.credentials.get("refresh_token")
            
            if not all([client_id, client_secret, refresh_token]):
                return None
            
            # Type assertion since we've checked they're not None
            client_id = str(client_id)
            client_secret = str(client_secret)
            refresh_token = str(refresh_token)
            
            access_token = await self._get_access_token(client_id, client_secret, refresh_token)
            
            if access_token:
                # Update stored credentials
                self.credentials.credentials["access_token"] = access_token
                self._save_credentials()
            
            return access_token
            
        except Exception as e:
            self.logger.error(f"Error refreshing access token: {e}")
            return None
    
    async def _ensure_valid_access_token(self) -> Optional[str]:
        """Ensure we have a valid access token"""
        if not self.credentials or not self.credentials.credentials:
            return None
        
        access_token = self.credentials.credentials.get("access_token")
        
        if not access_token:
            access_token = await self._refresh_access_token()
        
        return access_token
    
    async def _get_drive_files(self, session: aiohttp.ClientSession, 
                              headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get all Google Docs and text files from Drive"""
        files_to_process = []
        
        # Query for Google Docs and text files
        query = "mimeType='application/vnd.google-apps.document' or mimeType='text/plain' or mimeType='text/markdown'"
        params = {
            "q": query,
            "fields": "files(id,name,mimeType,modifiedTime,size)",
            "pageSize": 100
        }
        
        url = f"https://www.googleapis.com/drive/v3/files?{urlencode(params)}"
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ConnectorError(f"Failed to list Drive files: {response.status}")
            
            files_data = await response.json()
            files_to_process.extend(files_data.get("files", []))
        
        self.logger.info(f"Found {len(files_to_process)} files in Google Drive")
        return files_to_process
    
    async def _process_file(self, session: aiohttp.ClientSession, 
                           file_info: Dict[str, Any], 
                           headers: Dict[str, str]) -> bool:
        """Process a single file from Google Drive"""
        try:
            file_id = file_info["id"]
            file_name = file_info["name"]
            mime_type = file_info["mimeType"]
            
            # Get file content based on type
            if mime_type == "application/vnd.google-apps.document":
                # Export Google Doc as plain text
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
            else:
                # Download regular text file
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get content for {file_name}: {response.status}")
                    return False
                
                content = await response.text()
                
                # Skip empty files
                if not content.strip():
                    return False
                
                # Create unique content ID
                content_id = f"gdrive_{file_id}_{file_name.replace(' ', '_')}"
                
                # Prepare metadata
                metadata = {
                    "source": "google_drive",
                    "file_id": file_id,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "modified_time": file_info.get("modifiedTime"),
                    "file_size": file_info.get("size")
                }
                
                # Ingest into RAG
                return await self._ingest_content_to_rag(
                    content=content,
                    content_id=content_id,
                    metadata=metadata
                )
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_info.get('name')}: {e}")
            return False
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get a summary of the connector for display"""
        if not self.credentials or not self.credentials.credentials:
            return {
                "status": "not_connected",
                "user_email": None,
                "last_sync": None
            }
        
        return {
            "status": self.get_status().value,
            "user_email": self.credentials.credentials.get("user_email"),
            "user_name": self.credentials.credentials.get("user_name"),
            "last_sync": self.credentials.last_used.isoformat() if self.credentials.last_used else None
        }
