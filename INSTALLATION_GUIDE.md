# Vybe AI Assistant v0.8 ALPHA - Installation Guide

## Quick Start

1. **Download the installer**: `Vybe_Setup_v0.8_ALPHA.exe`
2. **Run as administrator** (required for Python installation)
3. **Follow the setup wizard** - it will automatically:
   - Download the latest application files from GitHub
   - Install Python 3.11 (if not present)
   - Set up the Python environment
   - Download the default AI model (optional)
   - Create desktop shortcuts

## System Requirements

- **OS**: Windows 10 or later (64-bit)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 5GB free space (10GB with AI models)
- **Internet**: Required for installation and AI model downloads

## Installation Options

### Full Installation (Recommended)
- Core application files
- Desktop application (Tauri)
- Default AI model (637MB)
- Documentation and guides
- Desktop and Start Menu shortcuts

### Minimal Installation
- Core application files only
- No desktop app or shortcuts
- Models downloaded manually later

### Custom Installation
- Choose which components to install

## Post-Installation

1. **First Launch**: The application will complete setup automatically
2. **Web Interface**: Access at `http://localhost:5000`
3. **Desktop App**: Use the desktop shortcut for the native app experience

## Manual Installation (Advanced Users)

If you prefer to install manually:

1. Clone this repository
2. Run `setup_python_env.bat`
3. Run `python download_default_model.py` (optional)
4. Run `python run.py` to start the application

## Troubleshooting

- **Python Issues**: The installer includes Python 3.11 for Windows
- **Permission Errors**: Run installer as administrator
- **Firewall**: Allow Python/Vybe through Windows Firewall
- **Port Conflicts**: Default port is 5000, configurable in settings

## Support

- **Issues**: [GitHub Issues](https://github.com/socalcium/Vybe-Local-Agentic-Container/issues)
- **Documentation**: [GitHub Wiki](https://github.com/socalcium/Vybe-Local-Agentic-Container/wiki)