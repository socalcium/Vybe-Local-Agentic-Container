"""
Marketplace Manager for Vybe
Provides a foundation for API marketplace with external plugin hosting
"""

import json
import requests
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from urllib.parse import urlparse, urljoin

from ..logger import log_info, log_error, log_warning
from ..models import db, AppSetting

# Import app for Flask application context
try:
    from .. import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("Warning: Flask app not available for marketplace manager")


class PluginSource(Enum):
    """Plugin source types"""
    GITHUB = "github"
    GITLAB = "gitlab"
    DIRECT_URL = "direct_url"
    EXTERNAL_MARKETPLACE = "external_marketplace"
    COMMUNITY_REPO = "community_repo"


class PluginCategory(Enum):
    """Plugin categories for organization"""
    TOOLS = "tools"
    UI_EXTENSIONS = "ui_extensions"
    INTEGRATIONS = "integrations"
    THEMES = "themes"
    LANGUAGE_MODELS = "language_models"
    GAMING = "gaming"
    PRODUCTIVITY = "productivity"
    CREATIVITY = "creativity"
    UTILITIES = "utilities"
    CUSTOM = "custom"


@dataclass
class MarketplacePlugin:
    """Marketplace plugin metadata"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: PluginCategory
    source: PluginSource
    download_url: str
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    website_url: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = []
    icon: Optional[str] = None
    screenshots: List[str] = []
    min_vybe_version: Optional[str] = None
    max_vybe_version: Optional[str] = None
    dependencies: List[str] = []
    requirements: List[str] = []
    permissions: List[str] = []
    rating: Optional[float] = None
    download_count: int = 0
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    verified: bool = False
    featured: bool = False
    price: Optional[float] = None
    currency: str = "USD"
    file_size: Optional[int] = None
    checksum: Optional[str] = None


@dataclass
class MarketplaceCategory:
    """Marketplace category information"""
    id: str
    name: str
    description: str
    icon: str
    plugin_count: int = 0
    featured_plugins: List[str] = []


class MarketplaceManager:
    """Manages the API marketplace for external plugin discovery and installation"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path("instance/marketplace_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, MarketplacePlugin] = {}
        self.categories: Dict[str, MarketplaceCategory] = {}
        self.installed_plugins: List[str] = []
        self.favorite_plugins: List[str] = []
        
        # Cache settings
        self.cache_duration = timedelta(hours=6)  # 6 hours
        self.last_cache_update = None
        
        # External marketplace sources
        self.marketplace_sources = [
            {
                "name": "Vybe Community Repository",
                "url": "https://api.github.com/repos/vybe-team/vybe-plugins/contents",
                "type": PluginSource.GITHUB,
                "enabled": True
            },
            {
                "name": "Community Plugin Hub",
                "url": "https://raw.githubusercontent.com/vybe-community/plugin-hub/main/plugins.json",
                "type": PluginSource.EXTERNAL_MARKETPLACE,
                "enabled": True
            }
        ]
        
        # Load local data
        self._load_local_data()
        
        # Initialize categories
        self._initialize_categories()
        
    def _load_local_data(self):
        """Load local marketplace data"""
        try:
            if not APP_AVAILABLE:
                log_warning("Flask app not available - using default marketplace data")
                return
                
            with app.app_context():
                # Load installed plugins
                setting = AppSetting.query.filter_by(key='installed_marketplace_plugins').first()
                if setting:
                    self.installed_plugins = json.loads(setting.value)
                    
                # Load favorite plugins
                setting = AppSetting.query.filter_by(key='favorite_marketplace_plugins').first()
                if setting:
                    self.favorite_plugins = json.loads(setting.value)
                
        except Exception as e:
            log_error(f"Error loading local marketplace data: {e}")
            
    def _save_local_data(self):
        """Save local marketplace data"""
        try:
            if not APP_AVAILABLE:
                log_warning("Flask app not available - cannot save marketplace data to database")
                return
                
            with app.app_context():
                # Save installed plugins
                setting = AppSetting.query.filter_by(key='installed_marketplace_plugins').first()
                if setting:
                    setting.value = json.dumps(self.installed_plugins)
                else:
                    setting = AppSetting()
                    setting.key = 'installed_marketplace_plugins'
                    setting.value = json.dumps(self.installed_plugins)
                    db.session.add(setting)
                    
                # Save favorite plugins
                setting = AppSetting.query.filter_by(key='favorite_marketplace_plugins').first()
                if setting:
                    setting.value = json.dumps(self.favorite_plugins)
                else:
                    setting = AppSetting()
                    setting.key = 'favorite_marketplace_plugins'
                    setting.value = json.dumps(self.favorite_plugins)
                    db.session.add(setting)
                    
                db.session.commit()
            
        except Exception as e:
            log_error(f"Error saving local marketplace data: {e}")
            
    def _initialize_categories(self):
        """Initialize marketplace categories"""
        categories_data = [
            {
                "id": "tools",
                "name": "Tools & Utilities",
                "description": "Productivity tools and utilities",
                "icon": "bi bi-tools"
            },
            {
                "id": "ui_extensions",
                "name": "UI Extensions",
                "description": "User interface enhancements",
                "icon": "bi bi-window-stack"
            },
            {
                "id": "integrations",
                "name": "Integrations",
                "description": "Third-party service integrations",
                "icon": "bi bi-plug"
            },
            {
                "id": "themes",
                "name": "Themes",
                "description": "Visual themes and styling",
                "icon": "bi bi-palette"
            },
            {
                "id": "language_models",
                "name": "Language Models",
                "description": "AI language model integrations",
                "icon": "bi bi-cpu"
            },
            {
                "id": "gaming",
                "name": "Gaming",
                "description": "Gaming and entertainment plugins",
                "icon": "bi bi-controller"
            },
            {
                "id": "productivity",
                "name": "Productivity",
                "description": "Productivity and workflow tools",
                "icon": "bi bi-lightning"
            },
            {
                "id": "creativity",
                "name": "Creativity",
                "description": "Creative and artistic tools",
                "icon": "bi bi-brush"
            },
            {
                "id": "utilities",
                "name": "Utilities",
                "description": "General utility plugins",
                "icon": "bi bi-gear"
            },
            {
                "id": "custom",
                "name": "Custom",
                "description": "Custom and experimental plugins",
                "icon": "bi bi-code-slash"
            }
        ]
        
        for cat_data in categories_data:
            self.categories[cat_data["id"]] = MarketplaceCategory(
                id=cat_data["id"],
                name=cat_data["name"], 
                description=cat_data["description"],
                icon=cat_data["icon"],
                plugin_count=0,
                featured_plugins=[]
            )
            
    def refresh_marketplace(self, force: bool = False) -> bool:
        """Refresh marketplace data from external sources"""
        try:
            # Check if cache is still valid
            if not force and self.last_cache_update:
                if datetime.now() - self.last_cache_update < self.cache_duration:
                    log_info("Marketplace cache is still valid, skipping refresh")
                    return True
                    
            log_info("Refreshing marketplace data...")
            
            # Clear existing plugins
            self.plugins.clear()
            
            # Fetch from all enabled sources
            for source in self.marketplace_sources:
                if source["enabled"]:
                    self._fetch_from_source(source)
                    
            # Update cache timestamp
            self.last_cache_update = datetime.now()
            
            # Save to cache
            self._save_cache()
            
            # Update category counts
            self._update_category_counts()
            
            log_info(f"Marketplace refreshed successfully. Found {len(self.plugins)} plugins.")
            return True
            
        except Exception as e:
            log_error(f"Error refreshing marketplace: {e}")
            return False
            
    def _fetch_from_source(self, source: Dict[str, Any]):
        """Fetch plugins from a specific source"""
        try:
            if source["type"] == PluginSource.GITHUB:
                self._fetch_from_github(source)
            elif source["type"] == PluginSource.EXTERNAL_MARKETPLACE:
                self._fetch_from_external_marketplace(source)
            elif source["type"] == PluginSource.DIRECT_URL:
                self._fetch_from_direct_url(source)
                
        except Exception as e:
            log_error(f"Error fetching from source {source['name']}: {e}")
            
    def _fetch_from_github(self, source: Dict[str, Any]):
        """Fetch plugins from GitHub repository"""
        try:
            response = requests.get(source["url"], timeout=10)
            if response.status_code == 200:
                contents = response.json()
                
                for item in contents:
                    if item["type"] == "file" and item["name"].endswith(".json"):
                        # Fetch plugin metadata
                        plugin_response = requests.get(item["download_url"], timeout=10)
                        if plugin_response.status_code == 200:
                            plugin_data = plugin_response.json()
                            
                            # Create marketplace plugin
                            plugin = MarketplacePlugin(
                                id=plugin_data.get("id", item["name"].replace(".json", "")),
                                name=plugin_data.get("name", ""),
                                version=plugin_data.get("version", "1.0.0"),
                                description=plugin_data.get("description", ""),
                                author=plugin_data.get("author", "Unknown"),
                                category=PluginCategory(plugin_data.get("category", "custom")),
                                source=PluginSource.GITHUB,
                                download_url=plugin_data.get("download_url", ""),
                                repository_url=plugin_data.get("repository_url", ""),
                                documentation_url=plugin_data.get("documentation_url"),
                                website_url=plugin_data.get("website_url"),
                                license=plugin_data.get("license"),
                                tags=plugin_data.get("tags", []),
                                icon=plugin_data.get("icon"),
                                screenshots=plugin_data.get("screenshots", []),
                                min_vybe_version=plugin_data.get("min_vybe_version"),
                                max_vybe_version=plugin_data.get("max_vybe_version"),
                                dependencies=plugin_data.get("dependencies", []),
                                requirements=plugin_data.get("requirements", []),
                                permissions=plugin_data.get("permissions", []),
                                rating=plugin_data.get("rating"),
                                download_count=plugin_data.get("download_count", 0),
                                last_updated=datetime.fromisoformat(plugin_data.get("last_updated")) if plugin_data.get("last_updated") else None,
                                created_at=datetime.fromisoformat(plugin_data.get("created_at")) if plugin_data.get("created_at") else None,
                                verified=plugin_data.get("verified", False),
                                featured=plugin_data.get("featured", False),
                                price=plugin_data.get("price"),
                                currency=plugin_data.get("currency", "USD"),
                                file_size=plugin_data.get("file_size"),
                                checksum=plugin_data.get("checksum")
                            )
                            
                            self.plugins[plugin.id] = plugin
                            
        except Exception as e:
            log_error(f"Error fetching from GitHub source: {e}")
            
    def _fetch_from_external_marketplace(self, source: Dict[str, Any]):
        """Fetch plugins from external marketplace"""
        try:
            response = requests.get(source["url"], timeout=10)
            if response.status_code == 200:
                plugins_data = response.json()
                
                for plugin_data in plugins_data:
                    plugin = MarketplacePlugin(
                        id=plugin_data.get("id", ""),
                        name=plugin_data.get("name", ""),
                        version=plugin_data.get("version", "1.0.0"),
                        description=plugin_data.get("description", ""),
                        author=plugin_data.get("author", "Unknown"),
                        category=PluginCategory(plugin_data.get("category", "custom")),
                        source=PluginSource.EXTERNAL_MARKETPLACE,
                        download_url=plugin_data.get("download_url", ""),
                        repository_url=plugin_data.get("repository_url"),
                        documentation_url=plugin_data.get("documentation_url"),
                        website_url=plugin_data.get("website_url"),
                        license=plugin_data.get("license"),
                        tags=plugin_data.get("tags", []),
                        icon=plugin_data.get("icon"),
                        screenshots=plugin_data.get("screenshots", []),
                        min_vybe_version=plugin_data.get("min_vybe_version"),
                        max_vybe_version=plugin_data.get("max_vybe_version"),
                        dependencies=plugin_data.get("dependencies", []),
                        requirements=plugin_data.get("requirements", []),
                        permissions=plugin_data.get("permissions", []),
                        rating=plugin_data.get("rating"),
                        download_count=plugin_data.get("download_count", 0),
                        last_updated=datetime.fromisoformat(plugin_data.get("last_updated")) if plugin_data.get("last_updated") else None,
                        created_at=datetime.fromisoformat(plugin_data.get("created_at")) if plugin_data.get("created_at") else None,
                        verified=plugin_data.get("verified", False),
                        featured=plugin_data.get("featured", False),
                        price=plugin_data.get("price"),
                        currency=plugin_data.get("currency", "USD"),
                        file_size=plugin_data.get("file_size"),
                        checksum=plugin_data.get("checksum")
                    )
                    
                    self.plugins[plugin.id] = plugin
                    
        except Exception as e:
            log_error(f"Error fetching from external marketplace: {e}")
            
    def _fetch_from_direct_url(self, source: Dict[str, Any]):
        """Fetch plugins from direct URL"""
        try:
            response = requests.get(source["url"], timeout=10)
            if response.status_code == 200:
                plugin_data = response.json()
                
                plugin = MarketplacePlugin(
                    id=plugin_data.get("id", ""),
                    name=plugin_data.get("name", ""),
                    version=plugin_data.get("version", "1.0.0"),
                    description=plugin_data.get("description", ""),
                    author=plugin_data.get("author", "Unknown"),
                    category=PluginCategory(plugin_data.get("category", "custom")),
                    source=PluginSource.DIRECT_URL,
                    download_url=plugin_data.get("download_url", ""),
                    repository_url=plugin_data.get("repository_url"),
                    documentation_url=plugin_data.get("documentation_url"),
                    website_url=plugin_data.get("website_url"),
                    license=plugin_data.get("license"),
                    tags=plugin_data.get("tags", []),
                    icon=plugin_data.get("icon"),
                    screenshots=plugin_data.get("screenshots", []),
                    min_vybe_version=plugin_data.get("min_vybe_version"),
                    max_vybe_version=plugin_data.get("max_vybe_version"),
                    dependencies=plugin_data.get("dependencies", []),
                    requirements=plugin_data.get("requirements", []),
                    permissions=plugin_data.get("permissions", []),
                    rating=plugin_data.get("rating"),
                    download_count=plugin_data.get("download_count", 0),
                    last_updated=datetime.fromisoformat(plugin_data.get("last_updated")) if plugin_data.get("last_updated") else None,
                    created_at=datetime.fromisoformat(plugin_data.get("created_at")) if plugin_data.get("created_at") else None,
                    verified=plugin_data.get("verified", False),
                    featured=plugin_data.get("featured", False),
                    price=plugin_data.get("price"),
                    currency=plugin_data.get("currency", "USD"),
                    file_size=plugin_data.get("file_size"),
                    checksum=plugin_data.get("checksum")
                )
                
                self.plugins[plugin.id] = plugin
                
        except Exception as e:
            log_error(f"Error fetching from direct URL: {e}")
            
    def _save_cache(self):
        """Save marketplace data to cache"""
        try:
            cache_data = {
                "plugins": {pid: asdict(plugin) for pid, plugin in self.plugins.items()},
                "categories": {cid: asdict(cat) for cid, cat in self.categories.items()},
                "last_update": self.last_cache_update.isoformat() if self.last_cache_update else None
            }
            
            cache_file = self.cache_dir / "marketplace_cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
                
        except Exception as e:
            log_error(f"Error saving marketplace cache: {e}")
            
    def _load_cache(self) -> bool:
        """Load marketplace data from cache"""
        try:
            cache_file = self.cache_dir / "marketplace_cache.json"
            if not cache_file.exists():
                return False
                
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Load plugins
            for pid, plugin_data in cache_data.get("plugins", {}).items():
                # Convert datetime strings back to datetime objects
                if plugin_data.get("last_updated"):
                    plugin_data["last_updated"] = datetime.fromisoformat(plugin_data["last_updated"])
                if plugin_data.get("created_at"):
                    plugin_data["created_at"] = datetime.fromisoformat(plugin_data["created_at"])
                    
                self.plugins[pid] = MarketplacePlugin(**plugin_data)
                
            # Load categories
            for cid, cat_data in cache_data.get("categories", {}).items():
                self.categories[cid] = MarketplaceCategory(**cat_data)
                
            # Load last update time
            if cache_data.get("last_update"):
                self.last_cache_update = datetime.fromisoformat(cache_data["last_update"])
                
            return True
            
        except Exception as e:
            log_error(f"Error loading marketplace cache: {e}")
            return False
            
    def _update_category_counts(self):
        """Update plugin counts for each category"""
        for category in self.categories.values():
            category.plugin_count = len([
                plugin for plugin in self.plugins.values()
                if plugin.category.value == category.id
            ])
            
    def get_plugins(self, category: Optional[str] = None, search: Optional[str] = None, 
                   featured: bool = False, verified: bool = False) -> List[MarketplacePlugin]:
        """Get plugins with optional filtering"""
        plugins = list(self.plugins.values())
        
        # Filter by category
        if category:
            plugins = [p for p in plugins if p.category.value == category]
            
        # Filter by search term
        if search:
            search_lower = search.lower()
            plugins = [p for p in plugins if 
                      search_lower in p.name.lower() or 
                      search_lower in p.description.lower() or 
                      any(search_lower in tag.lower() for tag in p.tags)]
            
        # Filter by featured
        if featured:
            plugins = [p for p in plugins if p.featured]
            
        # Filter by verified
        if verified:
            plugins = [p for p in plugins if p.verified]
            
        # Sort by rating, then by download count
        plugins.sort(key=lambda p: (p.rating or 0, p.download_count), reverse=True)
        
        return plugins
        
    def get_plugin(self, plugin_id: str) -> Optional[MarketplacePlugin]:
        """Get a specific plugin by ID"""
        return self.plugins.get(plugin_id)
        
    def get_categories(self) -> List[MarketplaceCategory]:
        """Get all categories"""
        return list(self.categories.values())
        
    def get_category(self, category_id: str) -> Optional[MarketplaceCategory]:
        """Get a specific category by ID"""
        return self.categories.get(category_id)
        
    def install_plugin(self, plugin_id: str) -> bool:
        """Install a plugin from marketplace"""
        try:
            plugin = self.get_plugin(plugin_id)
            if not plugin:
                log_error(f"Plugin {plugin_id} not found in marketplace")
                return False
                
            # Download plugin file
            if not self._download_plugin(plugin):
                return False
                
            # Add to installed plugins list
            if plugin_id not in self.installed_plugins:
                self.installed_plugins.append(plugin_id)
                self._save_local_data()
                
            log_info(f"Successfully installed plugin: {plugin_id}")
            return True
            
        except Exception as e:
            log_error(f"Error installing plugin {plugin_id}: {e}")
            return False
            
    def _download_plugin(self, plugin: MarketplacePlugin) -> bool:
        """Download plugin file from external source"""
        try:
            # Create temporary directory for download
            temp_dir = self.cache_dir / "downloads" / plugin.id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Download plugin file
            response = requests.get(plugin.download_url, stream=True, timeout=30)
            if response.status_code != 200:
                log_error(f"Failed to download plugin {plugin.id}: HTTP {response.status_code}")
                return False
                
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'zip' in content_type:
                file_ext = '.zip'
            elif 'tar' in content_type:
                file_ext = '.tar.gz'
            else:
                file_ext = '.zip'  # Default
                
            plugin_file = temp_dir / f"{plugin.id}{file_ext}"
            
            # Download file
            with open(plugin_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Verify checksum if provided
            if plugin.checksum:
                if not self._verify_checksum(plugin_file, plugin.checksum):
                    log_error(f"Checksum verification failed for plugin {plugin.id}")
                    return False
                    
            # Install using plugin manager
            from .plugin_manager import plugin_manager
            success = plugin_manager.install_plugin(str(plugin_file))
            
            # Clean up temporary files
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                
            return success
            
        except Exception as e:
            log_error(f"Error downloading plugin {plugin.id}: {e}")
            return False
            
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash == expected_checksum
        except Exception as e:
            log_error(f"Error verifying checksum: {e}")
            return False
            
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a marketplace plugin"""
        try:
            # Remove from installed plugins list
            if plugin_id in self.installed_plugins:
                self.installed_plugins.remove(plugin_id)
                self._save_local_data()
                
            # Uninstall using plugin manager
            from .plugin_manager import plugin_manager
            return plugin_manager.uninstall_plugin(plugin_id)
            
        except Exception as e:
            log_error(f"Error uninstalling plugin {plugin_id}: {e}")
            return False
            
    def add_to_favorites(self, plugin_id: str) -> bool:
        """Add plugin to favorites"""
        try:
            if plugin_id not in self.favorite_plugins:
                self.favorite_plugins.append(plugin_id)
                self._save_local_data()
            return True
        except Exception as e:
            log_error(f"Error adding plugin to favorites: {e}")
            return False
            
    def remove_from_favorites(self, plugin_id: str) -> bool:
        """Remove plugin from favorites"""
        try:
            if plugin_id in self.favorite_plugins:
                self.favorite_plugins.remove(plugin_id)
                self._save_local_data()
            return True
        except Exception as e:
            log_error(f"Error removing plugin from favorites: {e}")
            return False
            
    def get_favorites(self) -> List[MarketplacePlugin]:
        """Get favorite plugins"""
        return [self.plugins[pid] for pid in self.favorite_plugins if pid in self.plugins]
        
    def get_installed_plugins(self) -> List[MarketplacePlugin]:
        """Get installed marketplace plugins"""
        return [self.plugins[pid] for pid in self.installed_plugins if pid in self.plugins]
        
    def search_plugins(self, query: str, category: Optional[str] = None) -> List[MarketplacePlugin]:
        """Search plugins with advanced filtering"""
        return self.get_plugins(category=category, search=query)
        
    def get_featured_plugins(self) -> List[MarketplacePlugin]:
        """Get featured plugins"""
        return self.get_plugins(featured=True)
        
    def get_verified_plugins(self) -> List[MarketplacePlugin]:
        """Get verified plugins"""
        return self.get_plugins(verified=True)
        
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        total_plugins = len(self.plugins)
        installed_count = len(self.installed_plugins)
        favorite_count = len(self.favorite_plugins)
        featured_count = len([p for p in self.plugins.values() if p.featured])
        verified_count = len([p for p in self.plugins.values() if p.verified])
        
        # Category distribution
        category_distribution = {}
        for category in self.categories.values():
            category_distribution[category.name] = category.plugin_count
            
        # Source distribution
        source_distribution = {}
        for plugin in self.plugins.values():
            source = plugin.source.value
            source_distribution[source] = source_distribution.get(source, 0) + 1
            
        return {
            "total_plugins": total_plugins,
            "installed_plugins": installed_count,
            "favorite_plugins": favorite_count,
            "featured_plugins": featured_count,
            "verified_plugins": verified_count,
            "category_distribution": category_distribution,
            "source_distribution": source_distribution,
            "last_update": self.last_cache_update.isoformat() if self.last_cache_update else None
        }


# Global marketplace manager instance
marketplace_manager = MarketplaceManager()
