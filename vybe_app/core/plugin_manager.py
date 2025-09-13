"""
Plugin Manager for Vybe
Provides a comprehensive plugin system for extensibility and community contributions
"""

import os
import sys
import json
import importlib
import importlib.util
import inspect
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging
import zipfile
import shutil
import tempfile
import hashlib

from ..logger import log_info, log_error, log_warning
from ..models import db, AppSetting


class PluginType(Enum):
    """Types of plugins supported by the system"""
    TOOL = "tool"
    UI_EXTENSION = "ui_extension"
    API_ENDPOINT = "api_endpoint"
    DATA_PROCESSOR = "data_processor"
    INTEGRATION = "integration"
    THEME = "theme"
    LANGUAGE_MODEL = "language_model"
    CUSTOM = "custom"


class PluginStatus(Enum):
    """Plugin status enumeration"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    UPDATING = "updating"


@dataclass
class PluginMetadata:
    """Plugin metadata structure"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    dependencies: List[str]
    requirements: List[str]
    permissions: List[str]
    tags: List[str]
    icon: Optional[str] = None
    website: Optional[str] = None
    license: Optional[str] = None
    min_vybe_version: Optional[str] = None
    max_vybe_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PluginInstance:
    """Plugin instance with runtime information"""
    metadata: PluginMetadata
    module: Any
    instance: Any
    status: PluginStatus
    error_message: Optional[str] = None
    load_time: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None


class PluginBase:
    """Base class for all Vybe plugins"""
    
    def __init__(self, plugin_id: str, metadata: PluginMetadata):
        self.plugin_id = plugin_id
        self.metadata = metadata
        self.logger = logging.getLogger(f"plugin.{plugin_id}")
        self._hooks: Dict[str, List[Callable]] = {}
        self._api_routes: List[Dict[str, Any]] = []
        self._ui_components: List[Dict[str, Any]] = []
        
    def initialize(self) -> bool:
        """Initialize the plugin - override in subclasses"""
        self.logger.info(f"Initializing plugin {self.plugin_id}")
        return True
        
    def activate(self) -> bool:
        """Activate the plugin - override in subclasses"""
        self.logger.info(f"Activating plugin {self.plugin_id}")
        return True
        
    def deactivate(self) -> bool:
        """Deactivate the plugin - override in subclasses"""
        self.logger.info(f"Deactivating plugin {self.plugin_id}")
        return True
        
    def cleanup(self) -> bool:
        """Cleanup plugin resources - override in subclasses"""
        self.logger.info(f"Cleaning up plugin {self.plugin_id}")
        return True
        
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Get API routes provided by this plugin"""
        return self._api_routes
        
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get UI components provided by this plugin"""
        return self._ui_components
        
    def get_tools(self) -> Dict[str, Any]:
        """Get tools provided by this plugin - override in subclasses"""
        return {}
        
    def get_components(self) -> Dict[str, Dict[str, Any]]:
        """Get UI components provided by this plugin - override in subclasses"""
        return {}
        
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get API routes provided by this plugin - override in subclasses"""
        return self._api_routes
        
    def register_hook(self, hook_name: str, callback: Callable):
        """Register a hook callback"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)
        
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all registered hooks for a given hook name"""
        results = []
        if hook_name in self._hooks:
            for callback in self._hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error executing hook {hook_name}: {e}")
        return results


class ToolPlugin(PluginBase):
    """Base class for tool plugins"""
    
    def __init__(self, plugin_id: str, metadata: PluginMetadata):
        super().__init__(plugin_id, metadata)
        self.tools: Dict[str, Dict[str, Any]] = {}
        
    def register_tool(self, name: str, tool_function: Callable, description: str = ""):
        """Register a tool function"""
        self.tools[name] = {
            'function': tool_function,
            'description': description,
            'plugin_id': self.plugin_id
        }
        
    def get_tools(self) -> Dict[str, Any]:
        """Get all registered tools"""
        return self.tools


class UIExtensionPlugin(PluginBase):
    """Base class for UI extension plugins"""
    
    def __init__(self, plugin_id: str, metadata: PluginMetadata):
        super().__init__(plugin_id, metadata)
        self.components: Dict[str, Dict[str, Any]] = {}
        
    def register_component(self, name: str, component_data: Dict[str, Any]):
        """Register a UI component"""
        self.components[name] = component_data
        self._ui_components.append(component_data)
        
    def get_components(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered UI components"""
        return self.components


class APIPlugin(PluginBase):
    """Base class for API endpoint plugins"""
    
    def __init__(self, plugin_id: str, metadata: PluginMetadata):
        super().__init__(plugin_id, metadata)
        self.routes: List[Dict[str, Any]] = []
        
    def register_route(self, route_data: Dict[str, Any]):
        """Register an API route"""
        self.routes.append(route_data)
        self._api_routes.append(route_data)
        
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all registered API routes"""
        return self.routes


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle"""
    
    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = Path(plugins_dir) if plugins_dir else Path("plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, PluginInstance] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.disabled_plugins: List[str] = []
        self.plugin_hooks: Dict[str, List[Callable]] = {}
        self.plugin_tools: Dict[str, Dict[str, Any]] = {}
        self.plugin_ui_components: Dict[str, List[Dict[str, Any]]] = {}
        self.plugin_api_routes: Dict[str, List[Dict[str, Any]]] = {}
        
        self.discovery_lock = threading.Lock()
        self.loading_lock = threading.Lock()
        
        # Load disabled plugins list
        self._load_disabled_plugins()
        
        # Discover and load plugins
        self.discover_plugins()
        
        # Define allowed permissions for plugins
        self.allowed_permissions = {
            'file_system_read',
            'file_system_write', 
            'network_access',
            'database_read',
            'database_write',
            'ui_modifications',
            'api_endpoints',
            'system_settings',
            'user_data_access',
            'plugin_management',
            'model_access',
            'workspace_access'
        }
    
    def _validate_plugin_metadata(self, manifest_data: Dict[str, Any], plugin_id: str) -> bool:
        """
        Validate plugin metadata from manifest.json
        
        Args:
            manifest_data: The parsed manifest.json data
            plugin_id: The plugin identifier
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ['name', 'version', 'author']
        for field in required_fields:
            if field not in manifest_data:
                log_error(f"Plugin {plugin_id}: Missing required field '{field}' in manifest")
                return False
            
            value = manifest_data[field]
            if not value or (isinstance(value, str) and not value.strip()):
                log_error(f"Plugin {plugin_id}: Required field '{field}' is empty in manifest")
                return False
        
        # Validate permissions
        permissions = manifest_data.get('permissions', [])
        if not isinstance(permissions, list):
            log_error(f"Plugin {plugin_id}: 'permissions' must be a list")
            return False
            
        for permission in permissions:
            if permission not in self.allowed_permissions:
                log_error(f"Plugin {plugin_id}: Unknown permission '{permission}'. Allowed permissions: {sorted(self.allowed_permissions)}")
                return False
        
        # Validate plugin type
        plugin_type = manifest_data.get('type', 'custom')
        valid_types = [ptype.value for ptype in PluginType]
        if plugin_type not in valid_types:
            log_error(f"Plugin {plugin_id}: Invalid plugin type '{plugin_type}'. Valid types: {valid_types}")
            return False
        
        # Validate version format (basic semantic versioning check)
        version = manifest_data.get('version', '')
        import re
        if not re.match(r'^\d+\.\d+\.\d+', version):
            log_error(f"Plugin {plugin_id}: Invalid version format '{version}'. Expected semantic versioning (e.g., 1.0.0)")
            return False
        
        log_info(f"Plugin {plugin_id}: Metadata validation passed")
        return True
        
    def _load_disabled_plugins(self):
        """Load list of disabled plugins from settings"""
        try:
            setting = AppSetting.query.filter_by(key='disabled_plugins').first()
            if setting:
                self.disabled_plugins = json.loads(setting.value)
        except Exception as e:
            log_error(f"Error loading disabled plugins: {e}")
            self.disabled_plugins = []
            
    def _save_disabled_plugins(self):
        """Save list of disabled plugins to settings"""
        try:
            setting = AppSetting.query.filter_by(key='disabled_plugins').first()
            if setting:
                setting.value = json.dumps(self.disabled_plugins)
            else:
                setting = AppSetting()
                setting.key = 'disabled_plugins'
                setting.value = json.dumps(self.disabled_plugins)
                db.session.add(setting)
            db.session.commit()
        except Exception as e:
            log_error(f"Error saving disabled plugins: {e}")
            
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory"""
        discovered_plugins = []
        
        with self.discovery_lock:
            for plugin_dir in self.plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_id = plugin_dir.name
                    
                    # Check for plugin manifest
                    manifest_file = plugin_dir / "manifest.json"
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest_data = json.load(f)
                            
                            # Validate metadata before processing
                            if not self._validate_plugin_metadata(manifest_data, plugin_id):
                                log_error(f"Plugin {plugin_id}: Metadata validation failed, skipping")
                                continue
                                
                            metadata = PluginMetadata(
                                name=manifest_data.get('name', plugin_id),
                                version=manifest_data.get('version', '1.0.0'),
                                description=manifest_data.get('description', ''),
                                author=manifest_data.get('author', 'Unknown'),
                                plugin_type=PluginType(manifest_data.get('type', 'custom')),
                                entry_point=manifest_data.get('entry_point', 'main.py'),
                                dependencies=manifest_data.get('dependencies', []),
                                requirements=manifest_data.get('requirements', []),
                                permissions=manifest_data.get('permissions', []),
                                tags=manifest_data.get('tags', []),
                                icon=manifest_data.get('icon'),
                                website=manifest_data.get('website'),
                                license=manifest_data.get('license'),
                                min_vybe_version=manifest_data.get('min_vybe_version'),
                                max_vybe_version=manifest_data.get('max_vybe_version'),
                                created_at=datetime.fromisoformat(manifest_data.get('created_at')) if manifest_data.get('created_at') else None,
                                updated_at=datetime.fromisoformat(manifest_data.get('updated_at')) if manifest_data.get('updated_at') else None
                            )
                            
                            self.plugin_metadata[plugin_id] = metadata
                            discovered_plugins.append(plugin_id)
                            
                            log_info(f"Discovered plugin: {plugin_id} ({metadata.name})")
                            
                        except Exception as e:
                            log_error(f"Error reading manifest for plugin {plugin_id}: {e}")
                            
        return discovered_plugins
        
    def load_plugin(self, plugin_id: str) -> bool:
        """Load a specific plugin"""
        if plugin_id not in self.plugin_metadata:
            log_error(f"Plugin {plugin_id} not found in metadata")
            return False
            
        if plugin_id in self.plugins:
            log_warning(f"Plugin {plugin_id} already loaded")
            return True
            
        with self.loading_lock:
            try:
                metadata = self.plugin_metadata[plugin_id]
                plugin_dir = self.plugins_dir / plugin_id
                
                # Re-validate metadata during loading for extra security
                manifest_file = plugin_dir / "manifest.json"
                if manifest_file.exists():
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                    if not self._validate_plugin_metadata(manifest_data, plugin_id):
                        log_error(f"Plugin {plugin_id}: Metadata validation failed during loading")
                        return False
                
                # Check if plugin is disabled
                if plugin_id in self.disabled_plugins:
                    log_info(f"Plugin {plugin_id} is disabled, skipping load")
                    return False
                    
                # Load plugin module
                entry_point_path = plugin_dir / metadata.entry_point
                if not entry_point_path.exists():
                    log_error(f"Entry point {metadata.entry_point} not found for plugin {plugin_id}")
                    return False
                    
                # Import plugin module with sandboxing
                spec = importlib.util.spec_from_file_location(f"plugin.{plugin_id}", entry_point_path)
                if spec is None:
                    log_error(f"Failed to create spec for plugin {plugin_id}")
                    return False
                module = importlib.util.module_from_spec(spec)
                
                # Create restricted global scope for plugin execution
                restricted_globals = self._create_restricted_globals()
                
                # Read and execute plugin code in restricted environment
                with open(entry_point_path, 'r', encoding='utf-8') as f:
                    plugin_code = f.read()
                
                try:
                    # Execute plugin code in restricted globals
                    exec(plugin_code, restricted_globals, restricted_globals)
                    
                    # Transfer safe plugin classes to the module
                    for name, obj in restricted_globals.items():
                        if (isinstance(obj, type) and 
                            hasattr(obj, '__bases__') and
                            any(base.__name__ == 'PluginBase' for base in obj.__mro__[1:])):
                            setattr(module, name, obj)
                            
                except Exception as e:
                    log_error(f"Failed to execute plugin {plugin_id} in sandbox: {e}")
                    return False
                    
                sys.modules[f"plugin.{plugin_id}"] = module
                
                # Find plugin class
                plugin_class = None
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginBase) and 
                        obj != PluginBase):
                        plugin_class = obj
                        break
                        
                if not plugin_class:
                    log_error(f"No plugin class found in {plugin_id}")
                    return False
                    
                # Create plugin instance
                plugin_instance = plugin_class(plugin_id, metadata)
                
                # Initialize plugin
                if not plugin_instance.initialize():
                    log_error(f"Failed to initialize plugin {plugin_id}")
                    return False
                    
                # Create plugin instance record
                plugin_record = PluginInstance(
                    metadata=metadata,
                    module=module,
                    instance=plugin_instance,
                    status=PluginStatus.LOADED,
                    load_time=datetime.now()
                )
                
                self.plugins[plugin_id] = plugin_record
                
                # Register plugin tools
                if hasattr(plugin_instance, 'get_tools'):
                    tools = plugin_instance.get_tools()
                    if tools:
                        self.plugin_tools[plugin_id] = tools
                        
                # Register UI components
                if hasattr(plugin_instance, 'get_components'):
                    components = plugin_instance.get_components()
                    if components:
                        self.plugin_ui_components[plugin_id] = list(components.values())
                        
                # Register API routes
                if hasattr(plugin_instance, 'get_routes'):
                    routes = plugin_instance.get_routes()
                    if routes:
                        self.plugin_api_routes[plugin_id] = routes
                        
                log_info(f"Successfully loaded plugin {plugin_id}")
                return True
                
            except Exception as e:
                log_error(f"Error loading plugin {plugin_id}: {e}")
                return False
                
    def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a loaded plugin"""
        if plugin_id not in self.plugins:
            log_error(f"Plugin {plugin_id} not loaded")
            return False
            
        plugin_record = self.plugins[plugin_id]
        
        try:
            if plugin_record.instance.activate():
                plugin_record.status = PluginStatus.ACTIVE
                plugin_record.last_used = datetime.now()
                log_info(f"Activated plugin {plugin_id}")
                return True
            else:
                plugin_record.status = PluginStatus.ERROR
                plugin_record.error_message = "Activation failed"
                log_error(f"Failed to activate plugin {plugin_id}")
                return False
                
        except Exception as e:
            plugin_record.status = PluginStatus.ERROR
            plugin_record.error_message = str(e)
            log_error(f"Error activating plugin {plugin_id}: {e}")
            return False
            
    def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate a plugin"""
        if plugin_id not in self.plugins:
            log_error(f"Plugin {plugin_id} not loaded")
            return False
            
        plugin_record = self.plugins[plugin_id]
        
        try:
            if plugin_record.instance.deactivate():
                plugin_record.status = PluginStatus.LOADED
                log_info(f"Deactivated plugin {plugin_id}")
                return True
            else:
                log_error(f"Failed to deactivate plugin {plugin_id}")
                return False
                
        except Exception as e:
            log_error(f"Error deactivating plugin {plugin_id}: {e}")
            return False
            
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin completely"""
        if plugin_id not in self.plugins:
            log_error(f"Plugin {plugin_id} not loaded")
            return False
            
        plugin_record = self.plugins[plugin_id]
        
        try:
            # Deactivate first if active
            if plugin_record.status == PluginStatus.ACTIVE:
                plugin_record.instance.deactivate()
                
            # Cleanup
            plugin_record.instance.cleanup()
            
            # Remove from registries
            if plugin_id in self.plugin_tools:
                del self.plugin_tools[plugin_id]
            if plugin_id in self.plugin_ui_components:
                del self.plugin_ui_components[plugin_id]
            if plugin_id in self.plugin_api_routes:
                del self.plugin_api_routes[plugin_id]
                
            # Remove from plugins dict
            del self.plugins[plugin_id]
            
            # Remove from sys.modules
            module_name = f"plugin.{plugin_id}"
            if module_name in sys.modules:
                del sys.modules[module_name]
                
            log_info(f"Unloaded plugin {plugin_id}")
            return True
            
        except Exception as e:
            log_error(f"Error unloading plugin {plugin_id}: {e}")
            return False
            
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a disabled plugin"""
        if plugin_id in self.disabled_plugins:
            self.disabled_plugins.remove(plugin_id)
            self._save_disabled_plugins()
            
        # Try to load and activate
        if self.load_plugin(plugin_id):
            return self.activate_plugin(plugin_id)
        return False
        
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        # Deactivate and unload if loaded
        if plugin_id in self.plugins:
            self.deactivate_plugin(plugin_id)
            self.unload_plugin(plugin_id)
            
        # Add to disabled list
        if plugin_id not in self.disabled_plugins:
            self.disabled_plugins.append(plugin_id)
            self._save_disabled_plugins()
            
        log_info(f"Disabled plugin {plugin_id}")
        return True
        
    def get_plugin_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a plugin"""
        if plugin_id not in self.plugin_metadata:
            return None
            
        metadata = self.plugin_metadata[plugin_id]
        plugin_record = self.plugins.get(plugin_id)
        
        status_info = {
            'id': plugin_id,
            'metadata': asdict(metadata),
            'status': 'disabled' if plugin_id in self.disabled_plugins else 'not_loaded'
        }
        
        if plugin_record:
            status_info.update({
                'status': plugin_record.status.value,
                'load_time': plugin_record.load_time.isoformat() if plugin_record.load_time else None,
                'last_used': plugin_record.last_used.isoformat() if plugin_record.last_used else None,
                'usage_count': plugin_record.usage_count,
                'error_message': plugin_record.error_message
            })
            
        return status_info
        
    def get_all_plugins_status(self) -> List[Dict[str, Any]]:
        """Get status of all plugins"""
        status_list = []
        for plugin_id in self.plugin_metadata.keys():
            status = self.get_plugin_status(plugin_id)
            if status is not None:
                status_list.append(status)
        return status_list
        
    def get_available_tools(self) -> Dict[str, Any]:
        """Get all available tools from plugins"""
        tools = {}
        for plugin_id, plugin_tools in self.plugin_tools.items():
            for tool_name, tool_info in plugin_tools.items():
                tools[f"{plugin_id}.{tool_name}"] = {
                    'plugin_id': plugin_id,
                    'name': tool_name,
                    'description': tool_info.get('description', ''),
                    'function': tool_info['function']
                }
        return tools
        
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get all UI components from plugins"""
        components = []
        for plugin_components in self.plugin_ui_components.values():
            components.extend(plugin_components)
        return components
        
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Get all API routes from plugins"""
        routes = []
        for plugin_routes in self.plugin_api_routes.values():
            routes.extend(plugin_routes)
        return routes
        
    def install_plugin(self, plugin_file_path: str) -> bool:
        """Install a plugin from a file (zip or directory)"""
        try:
            plugin_path = Path(plugin_file_path)
            
            if plugin_path.is_file() and plugin_path.suffix == '.zip':
                # Extract zip file
                with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                    # Get plugin name from zip
                    plugin_name = plugin_path.stem
                    extract_path = self.plugins_dir / plugin_name
                    
                    # Remove existing if present
                    if extract_path.exists():
                        shutil.rmtree(extract_path)
                        
                    # Extract
                    zip_ref.extractall(extract_path)
                    
            elif plugin_path.is_dir():
                # Copy directory
                plugin_name = plugin_path.name
                target_path = self.plugins_dir / plugin_name
                
                if target_path.exists():
                    shutil.rmtree(target_path)
                    
                shutil.copytree(plugin_path, target_path)
                
            else:
                log_error(f"Invalid plugin file: {plugin_file_path}")
                return False
                
            # Discover and load the new plugin
            self.discover_plugins()
            
            log_info(f"Installed plugin: {plugin_name}")
            return True
            
        except Exception as e:
            log_error(f"Error installing plugin: {e}")
            return False
            
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin completely"""
        try:
            # Disable and unload if loaded
            self.disable_plugin(plugin_id)
            
            # Remove plugin directory
            plugin_dir = self.plugins_dir / plugin_id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
                
            # Remove from metadata
            if plugin_id in self.plugin_metadata:
                del self.plugin_metadata[plugin_id]
                
            log_info(f"Uninstalled plugin: {plugin_id}")
            return True
            
        except Exception as e:
            log_error(f"Error uninstalling plugin {plugin_id}: {e}")
            return False
            
    def update_plugin(self, plugin_id: str, update_file_path: str) -> bool:
        """Update an existing plugin"""
        try:
            # Backup current plugin
            plugin_dir = self.plugins_dir / plugin_id
            if not plugin_dir.exists():
                log_error(f"Plugin {plugin_id} not found for update")
                return False
                
            backup_dir = self.plugins_dir / f"{plugin_id}_backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(plugin_dir, backup_dir)
            
            # Unload current plugin
            if plugin_id in self.plugins:
                self.unload_plugin(plugin_id)
                
            # Install update
            success = self.install_plugin(update_file_path)
            
            if success:
                # Remove backup
                shutil.rmtree(backup_dir)
                log_info(f"Updated plugin: {plugin_id}")
            else:
                # Restore backup
                shutil.rmtree(plugin_dir)
                shutil.move(backup_dir, plugin_dir)
                log_error(f"Update failed, restored backup for plugin: {plugin_id}")
                
            return success
            
        except Exception as e:
            log_error(f"Error updating plugin {plugin_id}: {e}")
            return False
            
    def _create_restricted_globals(self) -> Dict[str, Any]:
        """Create a restricted global environment for plugin execution"""
        # Safe built-in functions and modules
        safe_builtins = {
            # Basic types and constructors
            'bool', 'int', 'float', 'str', 'list', 'dict', 'tuple', 'set',
            # Safe built-in functions
            'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted',
            'min', 'max', 'sum', 'all', 'any', 'abs', 'round', 'pow',
            # Safe constants
            'True', 'False', 'None',
            # Type checking
            'isinstance', 'type',
            # String operations
            'ord', 'chr', 'bin', 'hex', 'oct',
            # Container operations
            'iter', 'next', 'reversed',
            # Exceptions (needed for plugin error handling)
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
            'AttributeError', 'RuntimeError',
        }
        
        # Create restricted builtins
        restricted_builtins = {}
        import builtins
        for name in safe_builtins:
            if hasattr(builtins, name):
                restricted_builtins[name] = getattr(builtins, name)
        
        # Safe modules that plugins might need
        safe_modules = {
            'json': __import__('json'),
            'datetime': __import__('datetime'),
            'math': __import__('math'),
            'random': __import__('random'),
            're': __import__('re'),
            'base64': __import__('base64'),
            'hashlib': __import__('hashlib'),
            'urllib': __import__('urllib'),
            'logging': __import__('logging'),
            'pathlib': __import__('pathlib'),
            'enum': __import__('enum'),
            'dataclasses': __import__('dataclasses'),
            'typing': __import__('typing'),
        }
        
        # Create the restricted global environment
        restricted_globals = {
            '__builtins__': restricted_builtins,
            # Add safe modules
            **safe_modules,
            # Add our plugin base class for inheritance
            'PluginBase': PluginBase,
            'PluginType': PluginType,
            'PluginMetadata': PluginMetadata,
        }
        
        return restricted_globals


# Global plugin manager instance
plugin_manager = PluginManager()
