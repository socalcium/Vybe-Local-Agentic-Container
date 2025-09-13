"""
Example Tool Plugin for Vybe
Demonstrates how to create a tool plugin with custom functionality
"""

import os
import json
from datetime import datetime
from pathlib import Path

from vybe_app.core.plugin_manager import ToolPlugin, PluginMetadata


class ExampleToolPlugin(ToolPlugin):
    """Example tool plugin that provides various utility functions"""
    
    def __init__(self, plugin_id: str, metadata: PluginMetadata):
        super().__init__(plugin_id, metadata)
        
        # Register tools
        self.register_tool(
            name="text_analyzer",
            tool_function=self.analyze_text,
            description="Analyze text and provide statistics"
        )
        
        self.register_tool(
            name="file_organizer",
            tool_function=self.organize_files,
            description="Organize files in a directory by type"
        )
        
        self.register_tool(
            name="data_converter",
            tool_function=self.convert_data,
            description="Convert data between different formats"
        )
        
        self.register_tool(
            name="system_info",
            tool_function=self.get_system_info,
            description="Get detailed system information"
        )
        
        self.logger.info(f"Example Tool Plugin initialized with {len(self.tools)} tools")
    
    def initialize(self) -> bool:
        """Initialize the plugin"""
        try:
            self.logger.info("Initializing Example Tool Plugin")
            
            # Create plugin data directory
            data_dir = Path("plugin_data") / self.plugin_id
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample configuration
            config = {
                "enabled_tools": list(self.tools.keys()),
                "settings": {
                    "max_file_size": 10 * 1024 * 1024,  # 10MB
                    "supported_formats": ["txt", "json", "csv", "xml"],
                    "auto_backup": True
                },
                "created_at": datetime.now().isoformat()
            }
            
            config_file = data_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info("Example Tool Plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Example Tool Plugin: {e}")
            return False
    
    def activate(self) -> bool:
        """Activate the plugin"""
        try:
            self.logger.info("Activating Example Tool Plugin")
            
            # Load configuration
            data_dir = Path("plugin_data") / self.plugin_id
            config_file = data_dir / "config.json"
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                self.logger.info(f"Loaded configuration: {config}")
            
            self.logger.info("Example Tool Plugin activated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to activate Example Tool Plugin: {e}")
            return False
    
    def deactivate(self) -> bool:
        """Deactivate the plugin"""
        try:
            self.logger.info("Deactivating Example Tool Plugin")
            
            # Save any pending data
            data_dir = Path("plugin_data") / self.plugin_id
            data_dir.mkdir(parents=True, exist_ok=True)
            
            deactivation_info = {
                "deactivated_at": datetime.now().isoformat(),
                "tools_used": list(self.tools.keys())
            }
            
            info_file = data_dir / "deactivation_info.json"
            with open(info_file, 'w') as f:
                json.dump(deactivation_info, f, indent=2)
            
            self.logger.info("Example Tool Plugin deactivated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deactivate Example Tool Plugin: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Cleanup plugin resources"""
        try:
            self.logger.info("Cleaning up Example Tool Plugin")
            
            # Cleanup temporary files if any
            data_dir = Path("plugin_data") / self.plugin_id
            if data_dir.exists():
                # Keep configuration files, remove temporary files
                for temp_file in data_dir.glob("temp_*"):
                    temp_file.unlink()
            
            self.logger.info("Example Tool Plugin cleanup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup Example Tool Plugin: {e}")
            return False
    
    def analyze_text(self, text: str) -> dict:
        """Analyze text and provide statistics"""
        try:
            if not text:
                return {"error": "No text provided"}
            
            # Basic text analysis
            words = text.split()
            sentences = text.split('.')
            paragraphs = text.split('\n\n')
            
            # Character analysis
            char_count = len(text)
            word_count = len(words)
            sentence_count = len([s for s in sentences if s.strip()])
            paragraph_count = len([p for p in paragraphs if p.strip()])
            
            # Word frequency analysis
            word_freq = {}
            for word in words:
                clean_word = word.lower().strip('.,!?;:')
                if clean_word:
                    word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
            
            # Most common words
            most_common = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "success": True,
                "statistics": {
                    "character_count": char_count,
                    "word_count": word_count,
                    "sentence_count": sentence_count,
                    "paragraph_count": paragraph_count,
                    "average_word_length": sum(len(word) for word in words) / word_count if word_count > 0 else 0,
                    "average_sentence_length": word_count / sentence_count if sentence_count > 0 else 0
                },
                "most_common_words": most_common,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing text: {e}")
            return {"error": f"Text analysis failed: {str(e)}"}
    
    def organize_files(self, directory_path: str) -> dict:
        """Organize files in a directory by type"""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return {"error": f"Directory {directory_path} does not exist"}
            
            if not directory.is_dir():
                return {"error": f"{directory_path} is not a directory"}
            
            # File type mappings
            file_types = {
                "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
                "videos": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"],
                "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php"]
            }
            
            organized_files = {}
            unorganized_files = []
            
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_extension = file_path.suffix.lower()
                    file_organized = False
                    
                    for category, extensions in file_types.items():
                        if file_extension in extensions:
                            if category not in organized_files:
                                organized_files[category] = []
                            organized_files[category].append(str(file_path.name))
                            file_organized = True
                            break
                    
                    if not file_organized:
                        unorganized_files.append(str(file_path.name))
            
            return {
                "success": True,
                "directory": str(directory),
                "organized_files": organized_files,
                "unorganized_files": unorganized_files,
                "total_files": sum(len(files) for files in organized_files.values()) + len(unorganized_files),
                "organization_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error organizing files: {e}")
            return {"error": f"File organization failed: {str(e)}"}
    
    def convert_data(self, data: str, from_format: str, to_format: str) -> dict:
        """Convert data between different formats"""
        try:
            if not data:
                return {"error": "No data provided"}
            
            from_format = from_format.lower()
            to_format = to_format.lower()
            
            # Parse input data
            parsed_data = None
            
            if from_format == "json":
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON data"}
            
            elif from_format == "csv":
                # Simple CSV parsing (assumes comma-separated values)
                lines = data.strip().split('\n')
                if lines:
                    headers = lines[0].split(',')
                    rows = []
                    for line in lines[1:]:
                        values = line.split(',')
                        if len(values) == len(headers):
                            row = dict(zip(headers, values))
                            rows.append(row)
                    parsed_data = {"headers": headers, "rows": rows}
            
            elif from_format == "xml":
                # Simple XML parsing (basic implementation)
                import re
                tags = re.findall(r'<(\w+)>(.*?)</\1>', data, re.DOTALL)
                parsed_data = dict(tags)
            
            else:
                return {"error": f"Unsupported input format: {from_format}"}
            
            # Convert to output format
            if to_format == "json":
                output_data = json.dumps(parsed_data, indent=2)
            
            elif to_format == "csv":
                if isinstance(parsed_data, dict) and "rows" in parsed_data:
                    headers = parsed_data["headers"]
                    rows = parsed_data["rows"]
                    output_data = ",".join(headers) + "\n"
                    for row in rows:
                        output_data += ",".join(str(row.get(h, "")) for h in headers) + "\n"
                else:
                    return {"error": "Cannot convert to CSV: data structure not supported"}
            
            elif to_format == "xml":
                if isinstance(parsed_data, dict):
                    output_data = "<?xml version='1.0' encoding='UTF-8'?>\n<root>\n"
                    for key, value in parsed_data.items():
                        output_data += f"  <{key}>{value}</{key}>\n"
                    output_data += "</root>"
                else:
                    return {"error": "Cannot convert to XML: data structure not supported"}
            
            else:
                return {"error": f"Unsupported output format: {to_format}"}
            
            return {
                "success": True,
                "from_format": from_format,
                "to_format": to_format,
                "converted_data": output_data,
                "conversion_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error converting data: {e}")
            return {"error": f"Data conversion failed: {str(e)}"}
    
    def get_system_info(self) -> dict:
        """Get detailed system information"""
        try:
            import platform
            import psutil
            
            # Basic system info
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version()
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            }
            
            # Disk information
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
            
            # CPU information
            cpu_info = {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
            
            # Network information
            network_info = {}
            try:
                network = psutil.net_io_counters()
                network_info = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            except Exception as e:
                network_info = {"error": f"Network information not available: {e}"}
            
            return {
                "success": True,
                "system": system_info,
                "memory": memory_info,
                "disk": disk_info,
                "cpu": cpu_info,
                "network": network_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {"error": f"System info collection failed: {str(e)}"}


# Plugin instance (this will be created by the plugin manager)
plugin_instance = None
