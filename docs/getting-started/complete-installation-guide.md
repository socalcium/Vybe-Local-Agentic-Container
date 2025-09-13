# 🚀 Vybe AI Desktop - Complete Installation Guide

*Comprehensive installation and setup guide for all deployment methods*

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [First Launch Setup](#first-launch-setup)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Setup](#advanced-setup)

---

## 🎯 Quick Start

### **Option A: Desktop Installer (Recommended)**
1. Download `Vybe-AI-Desktop-Setup.exe`
2. Run as Administrator
3. Follow the wizard
4. Launch from Start Menu

### **Option B: Development Setup**
```bash
setup_python_env.bat
launch_vybe.bat
# Open http://127.0.0.1:8000
```

---

## 📋 System Requirements

### **Minimum Requirements**
- **OS**: Windows 10 (1903+) or newer
- **RAM**: 8 GB (16 GB recommended)
- **CPU**: 4‑core processor
- **Storage**: 6+ GB free disk space (models add more)
- **Network**: Internet connection for model downloads

### **Recommended Tiers**

| Hardware Tier | Specifications | AI Model | Performance |
|---------------|----------------|----------|-------------|
| **Entry Level** | GTX 1060 6GB, 12GB RAM | Mistral-7B | Good response times |
| **Performance** | GTX 1080 8GB, 16GB RAM | Dolphin-Llama3-8B | Excellent performance |
| **Enthusiast** | RTX 3080+ 12GB, 32GB RAM | Hermes-2-Pro-13B | Maximum capabilities |

---

## 🚀 Installation Methods

### **Method 1: Desktop Application (Recommended)**

#### **Step 1: Download**
- Navigate to [Releases](https://github.com/socalcium/Vybe-Local-Agentic-Container/releases)
- Download `Vybe-AI-Desktop-Setup.exe`

#### **Step 2: Install**
- Right-click installer → "Run as Administrator"
- Follow the installation wizard
- Choose installation directory (default: `C:\Program Files\Vybe AI`)

#### **Step 3: Launch**
- Start Menu → "Vybe AI Assistant"
- Desktop shortcut (if selected during install)

#### **Step 4: First Run Setup**
- Hardware analysis runs automatically
- Optimal AI model downloads based on your system
- Progress shown with real-time status updates

### **Method 2: Manual Development Setup**

#### **Prerequisites**
- **Windows 10** (1903) or newer
- **Python 3.11+** installed
- **Git** for cloning the repository
- **4GB+ RAM** available
- **2GB+ storage** for the application and models

#### **Step-by-Step Installation**

1. **Clone Repository**:
   ```bash
   git clone https://github.com/socalcium/Vybe-Local-Agentic-Container.git
   cd vybe
   ```

2. **Setup Python Environment**:
   ```bash
   # Run the automated setup script
   setup_python_env.bat
   
   # This script will:
   # - Create a Python 3.11 virtual environment
   # - Install all required dependencies
   # - Configure the environment for optimal performance
   ```

3. **Verify Installation**:
   ```bash
   # Test the environment
   vybe-env-311\Scripts\activate
   python -c "from vybe_app import create_app; print('✅ Installation successful!')"
   ```

4. **Launch Application**:
   ```bash
   # Start the application
   launch_vybe.bat
   
   # Then open http://127.0.0.1:8000
   ```

---

## 🌟 First Launch Setup

### **Automatic Hardware Detection**
- GPU detection and optimization
- RAM analysis for model selection
- Storage space verification
- Network connectivity check

### **Model Installation**
- Recommended model selection based on hardware
- Automatic download with progress tracking
- Model optimization for your system
- Backup model configuration

### **Service Initialization**
- Core services startup
- Health check verification
- Ready state confirmation
- Dashboard accessibility

---

## ⚙️ Configuration

### **Basic Configuration**
- Model preferences
- Hardware utilization settings
- Privacy and security options
- Interface customization

### **Advanced Configuration**
- Custom model integration
- Plugin management
- Performance tuning
- Developer options

---

## 🔍 Troubleshooting

### **Common Installation Issues**
- Python environment conflicts
- Permission and administrator access
- Antivirus interference
- Network and firewall issues

### **First Launch Problems**
- Hardware detection failures
- Model download issues
- Service startup problems
- Port conflicts and accessibility

---

## 🛠️ Advanced Setup

### **Custom Deployment**
- Server deployment options
- Container deployment
- Cloud hosting setup
- Multi-user configuration

### **Enterprise Setup**
- Security hardening
- Monitoring and logging
- Backup and recovery
- Maintenance procedures

---

*Complete installation guide for Vybe AI Desktop - from quick setup to enterprise deployment*
