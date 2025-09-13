"""
System Tray Manager for Vybe AI Desktop Application
Provides cross-platform system tray functionality with modern methodologies
"""

import os
import sys
import threading
import time
import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Platform detection
PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_MACOS = PLATFORM == "darwin"
IS_LINUX = PLATFORM == "linux"

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray not available - system tray functionality disabled")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - process management limited")

# Platform-specific imports
if IS_WINDOWS:
    try:
        import win32api
        import win32con
        import win32gui
        WINDOWS_API_AVAILABLE = True
    except ImportError:
        WINDOWS_API_AVAILABLE = False
        logger.warning("win32api not available - Windows-specific features disabled")

if IS_MACOS:
    try:
        import subprocess
        MACOS_AVAILABLE = True
    except ImportError:
        MACOS_AVAILABLE = False

if IS_LINUX:
    try:
        import subprocess
        LINUX_AVAILABLE = True
    except ImportError:
        LINUX_AVAILABLE = False


class SystemTrayManager:
    """Manages cross-platform system tray functionality for Vybe AI desktop application"""
    
    def __init__(self):
        self.icon = None
        self.is_running = False
        self.is_minimized = False
        self.callbacks = {}
        self.settings = self._load_settings()
        self.app_process = None
        self.tray_thread = None
        self.platform_features = self._detect_platform_features()
        self.health_check_interval = 30  # seconds
        self.health_check_thread = None
        
        # Initialize tray icon with platform-specific optimizations
        self._create_tray_icon()
        
        # Start health monitoring
        self._start_health_monitoring()
    
    def _detect_platform_features(self) -> Dict[str, bool]:
        """Detect available platform-specific features"""
        features = {
            "windows_api": IS_WINDOWS and WINDOWS_API_AVAILABLE,
            "macos_native": IS_MACOS and MACOS_AVAILABLE,
            "linux_native": IS_LINUX and LINUX_AVAILABLE,
            "pystray": PYSTRAY_AVAILABLE,
            "psutil": PSUTIL_AVAILABLE
        }
        
        logger.info(f"Platform features detected: {features}")
        return features
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load system tray settings"""
        settings_file = Path(__file__).parent.parent.parent / "instance" / "system_tray_settings.json"
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load system tray settings")
        
        return {
            "start_minimized": False,
            "minimize_to_tray": True,
            "show_notifications": True,
            "auto_start": False,
            "close_to_tray": True,
            "tray_icon_theme": "dark",
            "platform_optimizations": True,
            "health_monitoring": True,
            "notification_sound": True,
            "context_menu_enhanced": True,
            "auto_restore_on_click": True,
            "minimize_animation": True
        }
    
    def _save_settings(self):
        """Save system tray settings"""
        try:
            settings_file = Path(__file__).parent.parent.parent / "instance" / "system_tray_settings.json"
            settings_file.parent.mkdir(exist_ok=True)
            
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save system tray settings: {e}")
    
    def update_settings(self, **kwargs):
        """Update system tray settings"""
        for key, value in kwargs.items():
            if key in self.settings:
                self.settings[key] = value
        
        self._save_settings()
        logger.info(f"System tray settings updated: {kwargs}")
    
    def _create_tray_icon(self):
        """Create system tray icon with platform-specific optimizations"""
        if not PYSTRAY_AVAILABLE:
            logger.warning("Cannot create system tray icon - pystray not available")
            return
        
        try:
            # Create platform-optimized icon
            icon_image = self._create_platform_icon()
            
            # Create enhanced menu items
            menu_items = self._create_enhanced_menu_items()
            
            # Create tray icon with platform-specific settings
            icon_name = "vybe_ai"
            icon_title = "Vybe AI - Local AI Assistant"
            
            # Platform-specific icon configuration
            if IS_WINDOWS and self.platform_features["windows_api"]:
                icon_name = "VybeAI"
                icon_title = "Vybe AI Desktop Application"
            elif IS_MACOS and self.platform_features["macos_native"]:
                icon_name = "com.vybe.ai.desktop"
                icon_title = "Vybe AI"
            elif IS_LINUX and self.platform_features["linux_native"]:
                icon_name = "vybe-ai"
                icon_title = "Vybe AI Desktop"
            
            self.icon = pystray.Icon(
                icon_name,
                icon_image,
                icon_title,
                menu_items
            )
            
            logger.info(f"System tray icon created successfully for {PLATFORM}")
            
        except Exception as e:
            logger.error(f"Failed to create system tray icon: {e}")
    
    def _create_platform_icon(self):
        """Create platform-optimized icon image"""
        if not PYSTRAY_AVAILABLE:
            return None
        
        # Platform-specific icon sizes
        if IS_WINDOWS:
            size = 32  # Windows prefers smaller icons
        elif IS_MACOS:
            size = 128  # macOS prefers larger, high-DPI icons
        else:
            size = 64  # Linux default
        
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Platform-specific color schemes
        if IS_WINDOWS:
            primary_color = (0, 120, 215, 255)  # Windows blue
            secondary_color = (255, 255, 255, 255)  # White
        elif IS_MACOS:
            primary_color = (0, 122, 255, 255)  # macOS blue
            secondary_color = (255, 255, 255, 255)  # White
        else:
            primary_color = (52, 152, 219, 255)  # Linux blue
            secondary_color = (255, 255, 255, 255)  # White
        
        # Theme override
        if self.settings.get("tray_icon_theme") == "light":
            primary_color = (255, 255, 255, 255)
            secondary_color = (0, 0, 0, 255)
        elif self.settings.get("tray_icon_theme") == "dark":
            primary_color = (0, 0, 0, 255)
            secondary_color = (255, 255, 255, 255)
        
        # Draw enhanced "V" shape with platform-specific styling
        self._draw_enhanced_icon(draw, size, primary_color, secondary_color)
        
        return image
    
    def _draw_enhanced_icon(self, draw, size: int, primary_color: tuple, secondary_color: tuple):
        """Draw enhanced icon with platform-specific styling"""
        # Main V shape
        points = [
            (size * 0.2, size * 0.2),  # Top left
            (size * 0.5, size * 0.7),  # Bottom middle
            (size * 0.8, size * 0.2),  # Top right
        ]
        
        # Draw the V shape with platform-specific line width
        line_width = 3 if IS_WINDOWS else 4 if IS_MACOS else 3
        draw.line([points[0], points[1]], fill=primary_color, width=line_width)
        draw.line([points[1], points[2]], fill=primary_color, width=line_width)
        
        # Add AI circle with platform-specific styling
        center = (size * 0.5, size * 0.5)
        radius = size * 0.12 if IS_MACOS else size * 0.1
        
        # Draw outer circle
        draw.ellipse([
            center[0] - radius, center[1] - radius,
            center[0] + radius, center[1] + radius
        ], outline=secondary_color, width=2)
        
        # Draw inner AI indicator
        inner_radius = radius * 0.6
        draw.ellipse([
            center[0] - inner_radius, center[1] - inner_radius,
            center[0] + inner_radius, center[1] + inner_radius
        ], fill=primary_color)
        
        # Add small accent dots for visual appeal
        accent_radius = size * 0.03
        accent_positions = [
            (size * 0.3, size * 0.3),
            (size * 0.7, size * 0.3),
            (size * 0.5, size * 0.8)
        ]
        
        for pos in accent_positions:
            draw.ellipse([
                pos[0] - accent_radius, pos[1] - accent_radius,
                pos[0] + accent_radius, pos[1] + accent_radius
            ], fill=secondary_color)
    
    def _create_icon_image(self):
        """Create icon image for system tray"""
        if not PYSTRAY_AVAILABLE:
            return None
            
        # Create a simple 64x64 icon
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a simple "V" shape for Vybe
        if self.settings.get("tray_icon_theme") == "light":
            color = (255, 255, 255, 255)  # White
        else:
            color = (0, 0, 0, 255)  # Black
        
        # Draw a stylized "V"
        points = [
            (size * 0.2, size * 0.2),  # Top left
            (size * 0.5, size * 0.7),  # Bottom middle
            (size * 0.8, size * 0.2),  # Top right
        ]
        
        # Draw the V shape
        draw.line([points[0], points[1]], fill=color, width=3)
        draw.line([points[1], points[2]], fill=color, width=3)
        
        # Add a small circle for the AI aspect
        center = (size * 0.5, size * 0.5)
        radius = size * 0.1
        draw.ellipse([
            center[0] - radius, center[1] - radius,
            center[0] + radius, center[1] + radius
        ], outline=color, width=2)
        
        return image
    
    def _create_enhanced_menu_items(self):
        """Create enhanced system tray menu items with platform-specific features"""
        if not PYSTRAY_AVAILABLE:
            return None
        
        # Platform-specific menu items
        platform_items = []
        
        if IS_WINDOWS and self.platform_features["windows_api"]:
            platform_items.extend([
                pystray.MenuItem("Pin to Taskbar", self._pin_to_taskbar),
                pystray.MenuItem("Start with Windows", self._toggle_auto_start),
            ])
        elif IS_MACOS and self.platform_features["macos_native"]:
            platform_items.extend([
                pystray.MenuItem("Open in Finder", self._open_in_finder),
                pystray.MenuItem("Add to Dock", self._add_to_dock),
            ])
        elif IS_LINUX and self.platform_features["linux_native"]:
            platform_items.extend([
                pystray.MenuItem("Add to Startup", self._add_to_startup),
                pystray.MenuItem("Desktop Shortcut", self._create_desktop_shortcut),
            ])
        
        # Enhanced menu structure
        menu_items = [
            pystray.MenuItem("Show Vybe AI", self._show_app, default=True),
            pystray.MenuItem("Minimize to Tray", self._toggle_minimize),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quick Actions", self._create_quick_actions_submenu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("System", self._create_system_submenu()),
            pystray.Menu.SEPARATOR,
        ]
        
        # Add platform-specific items
        if platform_items:
            menu_items.extend(platform_items)
            menu_items.append(pystray.Menu.SEPARATOR)
        
        # Add settings and quit
        menu_items.extend([
            pystray.MenuItem("Settings", self._open_settings),
            pystray.MenuItem("About", self._show_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit_app)
        ])
        
        return pystray.Menu(*menu_items)
    
    def _create_quick_actions_submenu(self):
        """Create quick actions submenu"""
        return pystray.Menu(
            pystray.MenuItem("New Chat", self._new_chat),
            pystray.MenuItem("Voice Recording", self._start_voice_recording),
            pystray.MenuItem("Screenshot", self._take_screenshot),
            pystray.MenuItem("Quick Note", self._quick_note),
        )
    
    def _create_system_submenu(self):
        """Create system submenu"""
        return pystray.Menu(
            pystray.MenuItem("Check for Updates", self._check_updates),
            pystray.MenuItem("System Status", self._show_status),
            pystray.MenuItem("Performance Dashboard", self._open_dashboard),
            pystray.MenuItem("Health Check", self._run_health_check),
            pystray.MenuItem("Optimize System", self._optimize_system),
        )
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for system tray events"""
        self.callbacks[event] = callback
        logger.info(f"Registered callback for event: {event}")
    
    def start(self):
        """Start the system tray manager"""
        if not PYSTRAY_AVAILABLE:
            logger.warning("Cannot start system tray - pystray not available")
            return False
        
        if self.is_running:
            logger.warning("System tray manager already running")
            return True
        
        try:
            self.is_running = True
            
            # Start tray icon in separate thread
            self.tray_thread = threading.Thread(target=self._run_tray_icon, daemon=True)
            self.tray_thread.start()
            
            logger.info("System tray manager started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system tray manager: {e}")
            self.is_running = False
            return False
    
    def stop(self):
        """Stop the system tray manager"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            if self.icon:
                self.icon.stop()
                self.icon = None
            
            logger.info("System tray manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping system tray manager: {e}")
    
    def _run_tray_icon(self):
        """Run the system tray icon"""
        try:
            if self.icon:
                self.icon.run()
        except Exception as e:
            logger.error(f"Error running system tray icon: {e}")
    
    def show_notification(self, title: str, message: str, duration: int = 5):
        """Show system tray notification"""
        if not self.is_running or not self.settings.get("show_notifications"):
            return
        
        try:
            if self.icon:
                self.icon.notify(title, message)
                logger.info(f"System tray notification: {title} - {message}")
        except Exception as e:
            logger.error(f"Failed to show system tray notification: {e}")
    
    def minimize_to_tray(self):
        """Minimize application to system tray"""
        if not self.settings.get("minimize_to_tray"):
            return
        
        try:
            self.is_minimized = True
            
            # Call minimize callback if registered
            if "minimize" in self.callbacks:
                self.callbacks["minimize"]()
            
            # Show notification
            self.show_notification(
                "Vybe AI",
                "Application minimized to system tray",
                3
            )
            
            logger.info("Application minimized to system tray")
            
        except Exception as e:
            logger.error(f"Failed to minimize to tray: {e}")
    
    def restore_from_tray(self):
        """Restore application from system tray"""
        try:
            self.is_minimized = False
            
            # Call restore callback if registered
            if "restore" in self.callbacks:
                self.callbacks["restore"]()
            
            logger.info("Application restored from system tray")
            
        except Exception as e:
            logger.error(f"Failed to restore from tray: {e}")
    
    def _show_app(self, icon, item):
        """Show application window"""
        self.restore_from_tray()
    
    def _toggle_minimize(self, icon, item):
        """Toggle minimize state"""
        if self.is_minimized:
            self.restore_from_tray()
        else:
            self.minimize_to_tray()
    
    def _check_updates(self, icon, item):
        """Check for application updates"""
        try:
            from .update_notifier import update_notifier
            update_info = update_notifier.check_for_updates(force=True)
            
            if update_info:
                self.show_notification(
                    "Update Available",
                    f"Vybe AI {update_info['version']} is available",
                    10
                )
            else:
                self.show_notification(
                    "No Updates",
                    "Vybe AI is up to date",
                    3
                )
                
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            self.show_notification(
                "Update Check Failed",
                "Could not check for updates",
                3
            )
    
    def _show_status(self, icon, item):
        """Show system status"""
        try:
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                status_message = f"CPU: {cpu_percent:.1f}% | RAM: {memory.percent:.1f}%"
                self.show_notification("System Status", status_message, 5)
            else:
                self.show_notification("System Status", "Status monitoring unavailable", 3)
                
        except Exception as e:
            logger.error(f"Failed to show system status: {e}")
    
    def _open_settings(self, icon, item):
        """Open application settings"""
        try:
            # Call settings callback if registered
            if "settings" in self.callbacks:
                self.callbacks["settings"]()
            else:
                self.show_notification("Settings", "Settings window not available", 3)
                
        except Exception as e:
            logger.error(f"Failed to open settings: {e}")
    
    def _show_about(self, icon, item):
        """Show about dialog"""
        try:
            about_message = "Vybe AI Desktop v3.1.0\nLocal AI Assistant"
            self.show_notification("About Vybe AI", about_message, 5)
            
        except Exception as e:
            logger.error(f"Failed to show about dialog: {e}")
    
    def _quit_app(self, icon, item):
        """Quit application"""
        try:
            # Call quit callback if registered
            if "quit" in self.callbacks:
                self.callbacks["quit"]()
            else:
                # Default quit behavior
                self.stop()
                os._exit(0)
                
        except Exception as e:
            logger.error(f"Failed to quit application: {e}")
    
    def is_available(self) -> bool:
        """Check if system tray is available"""
        return PYSTRAY_AVAILABLE
    
    def get_status(self) -> Dict[str, Any]:
        """Get system tray status"""
        return {
            "available": self.is_available(),
            "running": self.is_running,
            "minimized": self.is_minimized,
            "settings": self.settings.copy(),
            "callbacks_registered": list(self.callbacks.keys()),
            "platform_features": self.platform_features,
            "platform": PLATFORM
        }
    
    def _start_health_monitoring(self):
        """Start health monitoring"""
        if self.settings.get("health_monitoring", True):
            self.health_check_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
            self.health_check_thread.start()
            logger.info("Health monitoring started")
    
    def _health_monitor_loop(self):
        """Health monitoring loop"""
        while self.is_running:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _perform_health_check(self):
        """Perform system health check"""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # Check system resources
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Alert if resources are high
            if isinstance(cpu_percent, (int, float)) and cpu_percent > 80:
                self.show_notification(
                    "High CPU Usage",
                    f"CPU usage is {cpu_percent:.1f}%",
                    5
                )
            
            if hasattr(memory, 'percent') and isinstance(memory.percent, (int, float)) and memory.percent > 85:
                self.show_notification(
                    "High Memory Usage",
                    f"Memory usage is {memory.percent:.1f}%",
                    5
                )
            
            # Check if main application is still running
            if self.app_process and not self.app_process.is_running():
                logger.warning("Main application process not found")
                self.show_notification(
                    "Application Status",
                    "Main application may have stopped",
                    10
                )
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def _pin_to_taskbar(self, icon, item):
        """Pin application to Windows taskbar"""
        if IS_WINDOWS and self.platform_features["windows_api"]:
            try:
                # Implementation would require Windows API calls
                self.show_notification("Taskbar", "Pin to taskbar feature not yet implemented", 3)
            except Exception as e:
                logger.error(f"Failed to pin to taskbar: {e}")
    
    def _toggle_auto_start(self, icon, item):
        """Toggle Windows auto-start"""
        if IS_WINDOWS and self.platform_features["windows_api"]:
            try:
                # Implementation would require registry modification
                self.show_notification("Auto-start", "Auto-start feature not yet implemented", 3)
            except Exception as e:
                logger.error(f"Failed to toggle auto-start: {e}")
    
    def _open_in_finder(self, icon, item):
        """Open application folder in macOS Finder"""
        if IS_MACOS and self.platform_features["macos_native"]:
            try:
                app_path = Path(__file__).parent.parent.parent
                subprocess.run(["open", str(app_path)])
                self.show_notification("Finder", "Opened in Finder", 3)
            except Exception as e:
                logger.error(f"Failed to open in Finder: {e}")
    
    def _add_to_dock(self, icon, item):
        """Add application to macOS dock"""
        if IS_MACOS and self.platform_features["macos_native"]:
            try:
                # Implementation would require macOS-specific commands
                self.show_notification("Dock", "Add to dock feature not yet implemented", 3)
            except Exception as e:
                logger.error(f"Failed to add to dock: {e}")
    
    def _add_to_startup(self, icon, item):
        """Add application to Linux startup"""
        if IS_LINUX and self.platform_features["linux_native"]:
            try:
                # Implementation would require desktop entry creation
                self.show_notification("Startup", "Add to startup feature not yet implemented", 3)
            except Exception as e:
                logger.error(f"Failed to add to startup: {e}")
    
    def _create_desktop_shortcut(self, icon, item):
        """Create Linux desktop shortcut"""
        if IS_LINUX and self.platform_features["linux_native"]:
            try:
                # Implementation would require .desktop file creation
                self.show_notification("Shortcut", "Desktop shortcut feature not yet implemented", 3)
            except Exception as e:
                logger.error(f"Failed to create desktop shortcut: {e}")
    
    def _new_chat(self, icon, item):
        """Start new chat session"""
        try:
            if "new_chat" in self.callbacks:
                self.callbacks["new_chat"]()
            else:
                self.show_notification("New Chat", "New chat feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to start new chat: {e}")
    
    def _start_voice_recording(self, icon, item):
        """Start voice recording"""
        try:
            if "voice_recording" in self.callbacks:
                self.callbacks["voice_recording"]()
            else:
                self.show_notification("Voice Recording", "Voice recording feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to start voice recording: {e}")
    
    def _take_screenshot(self, icon, item):
        """Take screenshot"""
        try:
            if "screenshot" in self.callbacks:
                self.callbacks["screenshot"]()
            else:
                self.show_notification("Screenshot", "Screenshot feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
    
    def _quick_note(self, icon, item):
        """Open quick note"""
        try:
            if "quick_note" in self.callbacks:
                self.callbacks["quick_note"]()
            else:
                self.show_notification("Quick Note", "Quick note feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to open quick note: {e}")
    
    def _open_dashboard(self, icon, item):
        """Open performance dashboard"""
        try:
            if "dashboard" in self.callbacks:
                self.callbacks["dashboard"]()
            else:
                self.show_notification("Dashboard", "Dashboard feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to open dashboard: {e}")
    
    def _run_health_check(self, icon, item):
        """Run manual health check"""
        try:
            self._perform_health_check()
            self.show_notification("Health Check", "System health check completed", 3)
        except Exception as e:
            logger.error(f"Failed to run health check: {e}")
    
    def _optimize_system(self, icon, item):
        """Optimize system performance"""
        try:
            if "optimize" in self.callbacks:
                self.callbacks["optimize"]()
            else:
                self.show_notification("Optimize", "System optimization feature not available", 3)
        except Exception as e:
            logger.error(f"Failed to optimize system: {e}")


# Global system tray manager instance
system_tray_manager = SystemTrayManager()


def get_system_tray_manager() -> SystemTrayManager:
    """Get the global system tray manager instance"""
    return system_tray_manager


def initialize_system_tray():
    """Initialize system tray functionality"""
    if system_tray_manager.is_available():
        success = system_tray_manager.start()
        if success:
            logger.info("System tray initialized successfully")
        else:
            logger.warning("Failed to initialize system tray")
    else:
        logger.warning("System tray not available - pystray not installed")


def cleanup_system_tray():
    """Cleanup system tray on application exit"""
    if system_tray_manager.is_running:
        system_tray_manager.stop()
        logger.info("System tray cleaned up")
