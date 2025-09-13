# Example Tool Plugin for Vybe

A sample tool plugin that demonstrates the Vybe plugin system capabilities. This plugin provides various utility functions that can be used within the Vybe application.

## Features

### 1. Text Analyzer
- Analyzes text and provides comprehensive statistics
- Character count, word count, sentence count, paragraph count
- Average word length and sentence length
- Word frequency analysis with most common words

### 2. File Organizer
- Organizes files in a directory by type
- Supports images, documents, videos, audio, archives, and code files
- Provides detailed categorization and statistics

### 3. Data Converter
- Converts data between different formats
- Supports JSON, CSV, and XML formats
- Handles complex data structures

### 4. System Information
- Provides detailed system information
- CPU, memory, disk, and network statistics
- Platform and architecture details

## Installation

1. Copy this plugin directory to the `plugins` folder in your Vybe installation
2. Restart Vybe or use the "Discover Plugins" feature
3. The plugin will be automatically detected and can be loaded

## Usage

### Text Analysis
```python
# Example usage of text analyzer
result = plugin.tools['text_analyzer']['function']("Your text here")
print(result['statistics'])
```

### File Organization
```python
# Example usage of file organizer
result = plugin.tools['file_organizer']['function']("/path/to/directory")
print(result['organized_files'])
```

### Data Conversion
```python
# Example usage of data converter
json_data = '{"name": "John", "age": 30}'
result = plugin.tools['data_converter']['function'](json_data, "json", "csv")
print(result['converted_data'])
```

### System Information
```python
# Example usage of system info
result = plugin.tools['system_info']['function']()
print(result['system'])
```

## Plugin Structure

```
example-tool-plugin/
├── manifest.json          # Plugin metadata and configuration
├── main.py               # Main plugin implementation
└── README.md             # This documentation file
```

## Configuration

The plugin creates a configuration file in `plugin_data/example-tool-plugin/config.json` with the following settings:

- `enabled_tools`: List of available tools
- `max_file_size`: Maximum file size for processing (10MB)
- `supported_formats`: Supported data formats for conversion
- `auto_backup`: Whether to automatically backup data

## Development

This plugin serves as a reference implementation for creating Vybe plugins. Key features demonstrated:

1. **Plugin Base Classes**: Extends `ToolPlugin` for tool-based functionality
2. **Lifecycle Management**: Implements initialize, activate, deactivate, and cleanup methods
3. **Tool Registration**: Registers custom tools with descriptions
4. **Error Handling**: Comprehensive error handling and logging
5. **Configuration Management**: Plugin-specific configuration storage
6. **Data Persistence**: Saves plugin state and configuration

## Requirements

- Vybe 1.0.0 or higher
- Python 3.8+
- psutil (for system information features)

## License

MIT License - see the main Vybe project for details.

## Contributing

This is an example plugin for demonstration purposes. For actual plugin development, refer to the Vybe plugin development documentation.
