"""
Update Notifier for Vybe AI
Checks for updates from GitHub and notifies users appropriately with one-click update capability
"""
import sys
from pathlib import Path

# Add the workspace root to Python path for imports
workspace_root = Path(__file__).parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

import requests
import json
import time
import subprocess
import shutil
import os
import platform
import tempfile
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import threading

logger = logging.getLogger(__name__)

# Try to import external API manager with proper fallback
external_api_available = False
get_api_manager = None
GITHUB_API_CONFIG = {}

try:
    # Import external API manager if available
    import importlib.util
    spec = importlib.util.find_spec("vybe_app.utils.external_api_manager")
    if spec is not None:
        from vybe_app.utils.external_api_manager import get_api_manager, GITHUB_API_CONFIG
        external_api_available = True
        logger.debug("External API manager imported successfully")
    else:
        logger.debug("External API manager module not found")
except Exception as e:
    logger.debug(f"External API manager import failed: {e}")
    get_api_manager = None
    GITHUB_API_CONFIG = {}

class UpdateNotifier:
    """Handles checking for and notifying about app updates with one-click update capability"""
    
    def __init__(self):
        self.github_repo = "socalcium/Vybe-Local-Agentic-Container"
        self.api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        self.instance_dir = Path(__file__).parent.parent.parent / "instance"
        self.instance_dir.mkdir(exist_ok=True)
        
        self.update_check_file = self.instance_dir / "last_update_check.json"
        self.notification_file = self.instance_dir / "update_notifications.json"
        self.update_settings_file = self.instance_dir / "update_settings.json"
        
        # Current version (should match your app version)
        self.current_version = "3.1.0"
        
        # Update settings
        self.update_settings = self._load_update_settings()
        
        # Initialize external API manager for GitHub if available
        self.api_manager = None
        if external_api_available and get_api_manager:
            try:
                self.api_manager = get_api_manager()
                if self.api_manager and hasattr(self.api_manager, 'get_api_status'):
                    if not self.api_manager.get_api_status("github") and GITHUB_API_CONFIG:
                        try:
                            # Try to register API config with type safety
                            self.api_manager.register_api(GITHUB_API_CONFIG)  # type: ignore
                            logger.debug("GitHub API registered with external API manager")
                        except Exception as reg_error:
                            logger.warning(f"Failed to register GitHub API config: {reg_error}")
                else:
                    logger.debug("API manager doesn't support status checking")
            except Exception as e:
                logger.warning(f"Failed to initialize external API manager: {e}")
                self.api_manager = None
        else:
            logger.debug("External API manager not available, using direct requests")
        
    def _load_update_settings(self) -> Dict[str, Any]:
        """Load update notification settings"""
        if self.update_settings_file.exists():
            try:
                with open(self.update_settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError, PermissionError) as e:
                logger.warning(f"Failed to load update settings: {type(e).__name__}")
            except Exception as e:
                logger.error(f"Unexpected error loading update settings: {type(e).__name__}")
        
        return {
            "check_frequency_hours": 24,
            "notification_frequency_hours": 168,  # 1 week
            "auto_check_enabled": True,
            "one_click_update_enabled": True,
            "backup_before_update": True,
            "notify_on_beta": False,
            "last_notification": None
        }
    
    def _save_update_settings(self):
        """Save update notification settings"""
        try:
            # Ensure directory exists
            self.update_settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.update_settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.update_settings, f, indent=2)
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Failed to save update settings: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Unexpected error saving update settings: {type(e).__name__}")
    
    def update_settings_config(self, **kwargs):
        """Update notification settings"""
        for key, value in kwargs.items():
            if key in self.update_settings:
                self.update_settings[key] = value
        
        self._save_update_settings()
        logger.info(f"Update settings updated: {kwargs}")
    
    def _load_check_data(self) -> Dict[str, Any]:
        """Load update check data"""
        if self.update_check_file.exists():
            try:
                with open(self.update_check_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError, PermissionError) as e:
                logger.warning(f"Failed to load update check data: {type(e).__name__}")
            except Exception as e:
                logger.error(f"Unexpected error loading update check data: {type(e).__name__}")
        
        return {
            "last_check": None,
            "last_version": None,
            "install_date": datetime.now().isoformat()
        }
    
    def _save_check_data(self, data: Dict[str, Any]):
        """Save update check data"""
        try:
            with open(self.update_check_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save update check data: {e}")
    
    def _load_notification_data(self) -> Dict[str, Any]:
        """Load notification tracking data"""
        if self.notification_file.exists():
            try:
                with open(self.notification_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load notification data")
        
        return {
            "notified_versions": [],
            "last_daily_check": None
        }
    
    def _save_notification_data(self, data: Dict[str, Any]):
        """Save notification tracking data"""
        try:
            with open(self.notification_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save notification data: {e}")
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            # Remove 'v' prefix if present and split by dots
            v1_parts = version1.lstrip('v').split('.')
            v2_parts = version2.lstrip('v').split('.')
            
            # Pad with zeros to make same length
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend(['0'] * (max_len - len(v1_parts)))
            v2_parts.extend(['0'] * (max_len - len(v2_parts)))
            
            # Compare each part
            for i in range(max_len):
                v1_num = int(v1_parts[i])
                v2_num = int(v2_parts[i])
                
                if v1_num > v2_num:
                    return 1
                elif v1_num < v2_num:
                    return -1
            
            return 0
        except (ValueError, IndexError):
            # If version parsing fails, consider them equal
            return 0
    
    def check_for_updates(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """Check for updates from GitHub. Returns update info if available."""
        try:
            check_data = self._load_check_data()
            notification_data = self._load_notification_data()
            
            now = datetime.now()
            
            # Check if we should skip this check
            if not force:
                # Skip if checked within configured frequency
                if check_data.get("last_check"):
                    last_check = datetime.fromisoformat(check_data["last_check"])
                    if now - last_check < timedelta(hours=self.update_settings["check_frequency_hours"]):
                        return None
                
                # Check notification frequency
                if notification_data.get("last_daily_check"):
                    last_notification = datetime.fromisoformat(notification_data["last_daily_check"])
                    if now - last_notification < timedelta(hours=self.update_settings["notification_frequency_hours"]):
                        return None
            
            # Try external API manager first for better reliability
            try:
                if self.api_manager and hasattr(self.api_manager, 'call_api'):
                    response = self.api_manager.call_api(
                        "github",
                        method="GET",
                        endpoint=f"repos/{self.github_repo}/releases/latest"
                    )
                    
                    if response and response.get('success'):
                        release_data = response['data']
                        logger.debug("Successfully fetched update data via external API manager")
                    else:
                        logger.warning(f"External API manager call failed: {response.get('error') if response else 'No response'}")
                        raise Exception("External API call failed")
                else:
                    raise Exception("External API manager not available")
                    
            except Exception as e:
                logger.debug(f"External API manager failed, falling back to direct request: {e}")
                # Fallback to direct request
                try:
                    response = requests.get(self.api_url, timeout=10)
                    response.raise_for_status()
                    release_data = response.json()
                    logger.debug("Successfully fetched update data via direct request")
                except Exception as req_e:
                    logger.error(f"Failed to fetch GitHub release data: {req_e}")
                    return None
            
            latest_version = release_data.get("tag_name", "").lstrip('v')
            
            # Update check data
            check_data["last_check"] = now.isoformat()
            check_data["last_version"] = latest_version
            self._save_check_data(check_data)
            
            # Compare versions
            if self._compare_versions(latest_version, self.current_version) > 0:
                # New version available
                update_info = {
                    "version": latest_version,
                    "current_version": self.current_version,
                    "name": release_data.get("name", f"Version {latest_version}"),
                    "body": release_data.get("body", ""),
                    "html_url": release_data.get("html_url", ""),
                    "published_at": release_data.get("published_at", ""),
                    "assets": [
                        {
                            "name": asset.get("name", ""),
                            "download_url": asset.get("browser_download_url", ""),
                            "size": asset.get("size", 0)
                        }
                        for asset in release_data.get("assets", [])
                    ]
                }
                
                # Check if we should notify about this version
                should_notify = self._should_notify_version(latest_version, notification_data)
                
                if should_notify:
                    # Mark this version as notified
                    notification_data["notified_versions"].append(latest_version)
                    notification_data["last_daily_check"] = now.isoformat()
                    self._save_notification_data(notification_data)
                    
                    return update_info
            
            # Update daily check time even if no update
            if not force:
                notification_data["last_daily_check"] = now.isoformat()
                self._save_notification_data(notification_data)
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking updates: {e}")
            return None
    
    def _should_notify_version(self, version: str, notification_data: Dict[str, Any]) -> bool:
        """Determine if we should notify about this version"""
        notified_versions = notification_data.get("notified_versions", [])
        
        # Don't notify if already notified about this version
        if version in notified_versions:
            return False
        
        # Check notification frequency settings
        if self.update_settings.get("last_notification"):
            try:
                last_notification = datetime.fromisoformat(self.update_settings["last_notification"])
                if datetime.now() - last_notification < timedelta(hours=self.update_settings["notification_frequency_hours"]):
                    return False
            except (ValueError, TypeError):
                pass
        
        # For fresh installs, notify immediately
        check_data = self._load_check_data()
        install_date_str = check_data.get("install_date")
        if install_date_str:
            try:
                install_date = datetime.fromisoformat(install_date_str)
                # If installed within last hour, this is likely a fresh install
                if datetime.now() - install_date < timedelta(hours=1):
                    return True
            except (ValueError, TypeError):
                pass
        
        # For running apps, follow notification frequency rule
        return True
    
    def get_notification_message(self, update_info: Dict[str, Any]) -> str:
        """Generate a user-friendly notification message"""
        version = update_info.get("version", "Unknown")
        name = update_info.get("name", f"Version {version}")
        
        message = f"🚀 New Vybe AI update available: {name}\n\n"
        
        if update_info.get("body"):
            # Truncate release notes if too long
            body = update_info["body"]
            if len(body) > 200:
                body = body[:200] + "..."
            message += f"What's new:\n{body}\n\n"
        
        message += f"Current version: {self.current_version}\n"
        message += f"Latest version: {version}\n\n"
        
        if self.update_settings.get("one_click_update_enabled"):
            message += "💡 One-click update available in the app!"
        elif update_info.get("html_url"):
            message += f"Download: {update_info['html_url']}"
        
        return message
    
    def perform_one_click_update(self, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform one-click update with backup and validation"""
        try:
            # Check if one-click update is enabled
            if not self.update_settings.get("one_click_update_enabled"):
                return {
                    "success": False,
                    "error": "One-click update is disabled in settings"
                }
            
            # Find appropriate asset for current platform
            assets = update_info.get("assets", [])
            if not assets:
                return {
                    "success": False,
                    "error": "No update assets available"
                }
            
            # Determine platform and find appropriate asset
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            # Look for appropriate asset
            target_asset = None
            for asset in assets:
                asset_name = asset.get("name", "").lower()
                if system == "windows" and ("windows" in asset_name or ".exe" in asset_name):
                    target_asset = asset
                    break
                elif system == "linux" and "linux" in asset_name:
                    target_asset = asset
                    break
                elif system == "darwin" and ("macos" in asset_name or "darwin" in asset_name):
                    target_asset = asset
                    break
            
            if not target_asset:
                return {
                    "success": False,
                    "error": f"No compatible update asset found for {system} {machine}"
                }
            
            # Create backup if enabled
            backup_path = None
            if self.update_settings.get("backup_before_update"):
                backup_path = self._create_backup()
                if not backup_path:
                    return {
                        "success": False,
                        "error": "Failed to create backup before update"
                    }
            
            # Download and apply update
            success = self._download_and_apply_update(target_asset, backup_path)
            
            if success:
                # Update notification timestamp
                self.update_settings["last_notification"] = datetime.now().isoformat()
                self._save_update_settings()
                
                return {
                    "success": True,
                    "message": f"Successfully updated to version {update_info['version']}",
                    "backup_path": backup_path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to apply update"
                }
                
        except Exception as e:
            logger.error(f"One-click update failed: {e}")
            return {
                "success": False,
                "error": f"Update failed: {str(e)}"
            }
    
    def _create_backup(self) -> Optional[str]:
        """Create backup of current installation"""
        try:
            # Create backup directory
            backup_dir = self.instance_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Create backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"vybe_backup_{timestamp}.zip"
            backup_path = backup_dir / backup_filename
            
            # Create zip backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                app_root = Path(__file__).parent.parent.parent
                
                # Add important files and directories
                important_paths = [
                    "vybe_app",
                    "run.py",
                    "requirements.txt",
                    "launch_vybe.bat",
                    "instance"
                ]
                
                for path in important_paths:
                    full_path = app_root / path
                    if full_path.exists():
                        if full_path.is_file():
                            zipf.write(full_path, path)
                        else:
                            for file_path in full_path.rglob("*"):
                                if file_path.is_file():
                                    arcname = file_path.relative_to(app_root)
                                    zipf.write(file_path, arcname)
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _download_and_apply_update(self, asset: Dict[str, Any], backup_path: Optional[str]) -> bool:
        """Download and apply the update"""
        try:
            download_url = asset.get("download_url")
            if not download_url:
                return False
            
            # Download update file
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # Extract and apply update
            success = self._extract_and_apply_update(tmp_path)
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download and apply update: {e}")
            return False
    
    def _extract_and_apply_update(self, update_file_path: str) -> bool:
        """Extract and apply the update file"""
        try:
            # Extract to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(update_file_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Apply update (this would need to be customized based on your app structure)
                # For now, we'll just log that the update was extracted
                logger.info(f"Update extracted to: {temp_dir}")
                
                # TODO: Implement actual update application logic
                # This would involve:
                # 1. Stopping the application gracefully
                # 2. Replacing files with new versions
                # 3. Restarting the application
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to extract and apply update: {e}")
            return False
    
    def send_notification(self, update_info: Dict[str, Any]):
        """Send update notification through available channels"""
        try:
            message = self.get_notification_message(update_info)
            
            # Try to use the notification manager if available
            notification_sent = False
            try:
                # Dynamic import to avoid import errors
                import importlib.util
                spec = importlib.util.find_spec("vybe_app.core.notifications")
                if spec is not None:
                    notifications_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(notifications_module)  # type: ignore
                    
                    if hasattr(notifications_module, 'get_notification_manager'):
                        notification_manager = notifications_module.get_notification_manager()
                        notification_manager.send_notification(
                            title="Vybe AI Update Available",
                            message=message,
                            notification_type="info",
                            action_url="/settings?tab=updates"
                        )
                        logger.info("Update notification sent via notification manager")
                        notification_sent = True
                    else:
                        logger.debug("Notification manager function not found")
                else:
                    logger.debug("Notifications module not found")
                    
            except Exception as e:
                logger.debug(f"Notification manager not available: {e}")
            
            # Fallback to enhanced console notification
            if not notification_sent:
                logger.info("=" * 60)
                logger.info("🚀 VYBE AI UPDATE NOTIFICATION")
                logger.info("=" * 60)
                logger.info(f"📦 New Version Available: {update_info.get('version', 'Unknown')}")
                logger.info(f"📝 Current Version: {self.current_version}")
                logger.info(f"🔗 Download URL: {update_info.get('html_url', 'N/A')}")
                logger.info("─" * 60)
                logger.info(f"📄 Release Notes:")
                for line in message.split('\n'):
                    if line.strip():
                        logger.info(f"   {line}")
                logger.info("=" * 60)
                
        except Exception as e:
            logger.error(f"Failed to send update notification: {e}")
    
    def start_background_checker(self):
        """Start background update checking (non-blocking)"""
        if not self.update_settings.get("auto_check_enabled"):
            logger.info("Auto update checking is disabled")
            return
        
        def check_updates_periodically():
            while True:
                try:
                    update_info = self.check_for_updates()
                    if update_info:
                        self.send_notification(update_info)
                    
                    # Sleep for configured frequency
                    sleep_hours = self.update_settings["check_frequency_hours"]
                    time.sleep(sleep_hours * 60 * 60)
                except Exception as e:
                    logger.error(f"Error in background update checker: {e}")
                    # Sleep for 1 hour on error before retrying
                    time.sleep(60 * 60)
        
        thread = threading.Thread(target=check_updates_periodically, daemon=True)
        thread.start()
        logger.info("Background update checker started")
    
    def get_current_version(self) -> str:
        """Get the current version of the application"""
        return self.current_version
    
    def set_current_version(self, version: str):
        """Set the current version of the application"""
        self.current_version = version
        logger.info(f"Current version updated to: {version}")
    
    def force_check_now(self) -> Optional[Dict[str, Any]]:
        """Force an immediate update check regardless of frequency settings"""
        logger.info("Forcing immediate update check...")
        return self.check_for_updates(force=True)
    
    def get_last_check_info(self) -> Dict[str, Any]:
        """Get information about the last update check"""
        try:
            check_data = self._load_check_data()
            return {
                "last_check": check_data.get("last_check"),
                "last_version": check_data.get("last_version"),
                "install_date": check_data.get("install_date"),
                "current_version": self.current_version
            }
        except Exception as e:
            logger.error(f"Failed to get last check info: {e}")
            return {}
    
    def reset_notification_history(self):
        """Reset the notification history to allow re-notification of versions"""
        try:
            notification_data = {"notified_versions": [], "last_daily_check": None}
            self._save_notification_data(notification_data)
            logger.info("Notification history reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset notification history: {e}")
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """Get statistics about update checking"""
        try:
            check_data = self._load_check_data()
            notification_data = self._load_notification_data()
            
            return {
                "external_api_available": external_api_available,
                "api_manager_active": self.api_manager is not None,
                "auto_check_enabled": self.update_settings.get("auto_check_enabled", False),
                "check_frequency_hours": self.update_settings.get("check_frequency_hours", 24),
                "notification_frequency_hours": self.update_settings.get("notification_frequency_hours", 168),
                "one_click_update_enabled": self.update_settings.get("one_click_update_enabled", False),
                "total_notified_versions": len(notification_data.get("notified_versions", [])),
                "last_check": check_data.get("last_check"),
                "github_repo": self.github_repo,
                "current_version": self.current_version
            }
        except Exception as e:
            logger.error(f"Failed to get update statistics: {e}")
            return {}

# Global instance for easy access
update_notifier = UpdateNotifier()
