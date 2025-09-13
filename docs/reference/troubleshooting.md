# 🚨 Vybe AI Desktop - Troubleshooting Guide

## 🎯 Quick Troubleshooting

### **Most Common Issues**
1. **App won't start** → Check antivirus exclusions
2. **Slow responses** → Enable GPU acceleration
3. **Model download fails** → Check internet connection
4. **Audio not working** → Check Windows audio settings
5. **Memory errors** → Switch to smaller model

---

## 🔧 Installation Issues

### **Python Environment Problems**

#### **Issue**: "Python not found" or "pip not recognized"
```
Solution:
1. Install Python 3.11+ from python.org
2. During installation, check "Add Python to PATH"
3. Restart Command Prompt/PowerShell
4. Verify: python --version
```

#### **Issue**: "Permission denied" during setup_python_env.bat
```
Solution:
1. Run Command Prompt as Administrator
2. Navigate to Vybe directory
3. Run: setup_python_env.bat
4. If still failing, check antivirus blocking
```

#### **Issue**: Virtual environment creation fails
```
Solution:
1. Delete existing vybe-env-311 folder
2. Run: python -m venv vybe-env-311 --clear
3. Activate: vybe-env-311\Scripts\activate
4. Install: pip install -r requirements.txt
```

### **Desktop App Issues**

#### **Issue**: App won't start after installation
```
Diagnosis:
1. Check Windows Event Viewer → Application logs
2. Look for Vybe-related errors

Common Fixes:
- Install Visual C++ Redistributable (latest)
- Update Windows to latest version
- Run as Administrator once
- Check antivirus exclusions
```

#### **Issue**: White screen on launch
```
Solution:
1. Wait 30-60 seconds for backend startup
2. Check if Python process is running in Task Manager
3. Try closing and restarting the app
4. Check Windows Firewall settings
```

---

## ⚡ Performance Issues

### **Slow AI Responses**

#### **Issue**: Very slow model responses (>30 seconds)
```
Diagnosis:
- Check GPU utilization in Task Manager
- Monitor RAM usage (should be <80%)
- Verify model size matches your hardware

Solutions:
1. Enable GPU acceleration in Settings
2. Switch to smaller model if RAM limited
3. Close other applications
4. Restart Vybe to clear memory
```

#### **Issue**: High CPU usage when idle
```
Solution:
1. Check background processes in Task Manager
2. Disable unnecessary model preloading
3. Reduce context window size in Settings
4. Update to latest version
```

### **Memory Issues**

#### **Issue**: "Out of memory" errors
```
Immediate Fix:
1. Restart Vybe completely
2. Close other applications
3. Switch to smaller model

Long-term Solutions:
- Upgrade RAM (16GB+ recommended)
- Use CPU-only models if GPU VRAM limited
- Reduce batch sizes in Settings
```

---

## 🌐 Network & Download Issues

### **Model Download Problems**

#### **Issue**: "Failed to download model" errors
```
Solution:
1. Check internet connection
2. Verify sufficient disk space (models are 4-13GB)
3. Try downloading during off-peak hours
4. Disable VPN if active
5. Check firewall settings
```

#### **Issue**: Download speeds very slow
```
Solution:
1. Close bandwidth-heavy applications
2. Use wired connection instead of WiFi
3. Try different model mirror in Settings
4. Download during off-peak hours
```

#### **Issue**: "Connection refused" or timeout errors
```
Solution:
1. Check Windows Firewall
2. Verify antivirus isn't blocking
3. Try different DNS servers (8.8.8.8, 1.1.1.1)
4. Restart router/modem
```

---

## 🎵 Audio Issues

### **Text-to-Speech Problems**

#### **Issue**: No audio output from TTS
```
Solution:
1. Check Windows audio settings
2. Set correct default audio device
3. Verify volume levels
4. Restart Windows Audio service
5. Try different voice in Settings
```

#### **Issue**: Poor TTS quality or robotic voice
```
Solution:
1. Update to latest Windows version
2. Install additional Windows voice packs
3. Adjust speech rate in Settings
4. Try different voice engine
```

### **Speech Recognition Issues**

#### **Issue**: Microphone not detected
```
Solution:
1. Check Windows Privacy Settings → Microphone
2. Allow desktop apps to access microphone
3. Verify microphone permissions for Vybe
4. Test microphone in Windows Settings
```

#### **Issue**: Poor speech recognition accuracy
```
Solution:
1. Use headset/quality microphone
2. Reduce background noise
3. Speak clearly and at normal pace
4. Train Windows speech recognition
5. Check microphone levels (not too low/high)
```

---

## 🎨 Image Generation Issues

### **Stable Diffusion Problems**

#### **Issue**: "CUDA out of memory" during image generation
```
Solution:
1. Reduce image resolution in Settings
2. Lower batch size to 1
3. Close other GPU-intensive applications
4. Switch to CPU generation (slower but works)
```

#### **Issue**: Generated images are poor quality
```
Solution:
1. Increase steps (20-50 recommended)
2. Adjust guidance scale (7-12 typical)
3. Use more descriptive prompts
4. Try different model variants
5. Check GPU temperature (may be throttling)
```

#### **Issue**: Image generation fails to start
```
Solution:
1. Verify GPU has 6GB+ VRAM
2. Update GPU drivers
3. Check CUDA installation
4. Try CPU fallback mode
```

---

## 📚 Knowledge Base Issues

### **Document Processing Problems**

#### **Issue**: PDF upload fails or corrupts
```
Solution:
1. Try different PDF (test with simple text PDF)
2. Ensure PDF isn't password protected
3. Check file size (<100MB recommended)
4. Update to latest version
5. Try converting PDF to text first
```

#### **Issue**: Search results are irrelevant
```
Solution:
1. Use more specific search terms
2. Rebuild knowledge base index
3. Check document quality (clear text)
4. Verify proper document chunking
```

---

## 🔐 Security & Privacy Issues

### **Antivirus Conflicts**

#### **Issue**: Antivirus blocking Vybe
```
Solution:
1. Add Vybe folder to antivirus exclusions
2. Whitelist Python processes
3. Temporarily disable real-time protection during install
4. Use Windows Defender instead of third-party (often more compatible)
```

#### **Issue**: Windows SmartScreen warnings
```
Solution:
1. Click "More info" → "Run anyway"
2. This is normal for new software
3. Vybe is open-source and safe
4. Report false positive to Microsoft if persistent
```

---

## 🛠️ Advanced Diagnostics

### **Debug Mode**

Enable detailed logging for troubleshooting:

1. **Create debug.env file**:
   ```env
   VYBE_DEBUG=true
   VYBE_LOG_LEVEL=DEBUG
   VYBE_VERBOSE=true
   ```

2. **Start with logging**:
   ```bash
   launch_vybe.bat > debug.log 2>&1
   ```

3. **Check logs**:
   - Application logs in `logs/` folder
   - System logs in Windows Event Viewer
   - Browser console (F12) for frontend issues

### **System Information Collection**

For bug reports, collect this information:

```bash
# System specs
systeminfo | findstr /C:"OS" /C:"Total Physical Memory" /C:"Processor"

# Python environment
python --version
pip list | findstr vybe

# GPU information
nvidia-smi  # For NVIDIA GPUs
dxdiag      # For general GPU info
```

### **Testing Procedures**

#### **Pre-Testing Setup**
```cmd
# Verify Python installation
python --version
# Should show Python 3.11+

# Verify packages are installed
python -c "import flask, requests, llama_cpp; print('Core packages OK')"
```

#### **Application Import Test**
```cmd
# Test core imports
python -c "import vybe_app; print('✅ App imports successfully')"

# Test new modules
python -c "from vybe_app.api import external_api; from vybe_app.core import model_router; print('✅ New modules work')"
```

#### **Basic Application Start**
```cmd
# Start the application
python run.py
```
**Expected Output:**
- No fatal errors
- Server starts on `http://localhost:8000`
- Hardware manager initializes (may show warnings - this is normal)

#### **API Health Checks**
```cmd
# In a new terminal, test API endpoints
curl http://localhost:8000/api/health
# Expected: {"status":"ok","service":"vybe-api","timestamp":...}

curl http://localhost:8000/api/external/providers
# Expected: List of AI providers (OpenAI, Anthropic, etc.)

curl http://localhost:8000/api/models/recommended
# Expected: Hardware-appropriate model recommendations
```

#### **Web Interface Tests**
1. **Navigate to:** `http://localhost:8000`
2. **Test Pages:**
   - Chat interface
   - Models manager
   - Settings page
   - System health dashboard

3. **Key Features to Test:**
   - Model selection works
   - External API configuration (in settings)
   - Hardware detection displays correctly

#### **Hardware Detection Tests**
```cmd
# Test hardware manager
python -c "from vybe_app.core.hardware_manager import hardware_manager; print(hardware_manager.classify_performance_tier())"
# Expected: 'entry_level', 'mid_range', or 'high_end'
```

---

## 🔍 Common Error Messages

### **Import Errors**
```
Error: "Import 'flask' could not be resolved"
Solution: pip install -r requirements.txt
```

### **Hardware Manager Errors**
```
Error: "Hardware manager failed to initialize"
Note: This is normal on first run
Solution: Hardware detection will work when app context is available
```

### **Model Errors**
```
Error: "No models found"
Solution: python -c "from vybe_app.core.first_launch_manager import first_launch_manager; first_launch_manager.download_model()"
```

### **Desktop App Errors**
```
Error: Desktop app won't start
Solution: 
cd vybe-desktop
npm audit fix
cargo check
```

---

## 📊 Performance Benchmarks

### **API Response Times (Expected)**
- Health check: < 100ms
- Model recommendations: < 500ms
- Hardware detection: < 1s
- Model router selection: < 200ms

### **Memory Usage (Typical)**
- Base application: ~100MB
- With local LLM loaded: ~2-8GB (depending on model)
- Desktop wrapper: ~50MB additional

---

## 🔧 Advanced Testing

### **Load Testing**
```cmd
# Test concurrent requests
for i in {1..10}; do curl http://localhost:8000/api/health & done
wait
```

### **Model Router Intelligence**
```cmd
# Test different request types
curl -X POST http://localhost:8000/api/external/route \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Write Python code"}],"request_type":"code"}'

curl -X POST http://localhost:8000/api/external/route \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Analyze this data"}],"request_type":"reasoning"}'
```

### **Hardware Adaptation**
```cmd
# Verify recommendations match hardware
python -c "
from vybe_app.core.hardware_manager import hardware_manager;
from vybe_app.api.models_api import api_recommended_models;
print('Hardware tier:', hardware_manager.classify_performance_tier())
"
```

---

## ✅ Success Criteria

### **Core Functionality**
- [ ] Application starts without fatal errors
- [ ] All API endpoints respond correctly
- [ ] Model router selects appropriate models
- [ ] Hardware detection works
- [ ] External API integration ready

### **Web Interface**
- [ ] All pages load without errors
- [ ] Navigation works correctly
- [ ] Settings can be saved
- [ ] Model management functional

### **Desktop App**
- [ ] Builds successfully
- [ ] Launches without errors
- [ ] Connects to backend
- [ ] All web features work

---

## 📞 Getting Help

### **Self-Help Resources**
1. **Documentation**: Check all guides in `docs/` folder
2. **Search**: Look through existing GitHub issues
3. **Community**: Join Discord for real-time help
4. **Video Tutorials**: YouTube channel with walkthroughs

### **Reporting Issues**
When reporting bugs, include:
- **System Information**: OS version, RAM, GPU
- **Error Messages**: Exact text of any errors
- **Steps to Reproduce**: What you did before the issue
- **Log Files**: Debug logs if available
- **Screenshots**: Visual evidence of the problem

### **Contact Options**
- **GitHub Issues**: Technical bugs and feature requests
- **Discord**: Real-time community support
- **Email**: contact@vybe-ai.com for urgent issues
- **Documentation**: This guide and others in `docs/`

---

## 🔧 Quick Fixes

### **Reset Application**
```bash
# Clear all data and start fresh
rm -rf instance/
rm -rf models/cache/
python run.py
```

### **Reinstall Dependencies**
```bash
# Clean reinstall
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### **Clear Browser Cache**
- Press Ctrl+Shift+Delete
- Clear all browser data
- Restart browser

### **Check System Resources**
```bash
# Monitor system resources
tasklist | findstr python
tasklist | findstr vybe
```

---

## 🚨 Emergency Procedures

### **Application Won't Start**
1. Check Task Manager for stuck processes
2. Restart computer
3. Run as Administrator
4. Check antivirus exclusions

### **Data Loss Prevention**
1. Backup `instance/` folder regularly
2. Export important conversations
3. Save model configurations
4. Document custom settings

### **Complete Reset**
```bash
# Nuclear option - complete reset
rm -rf vybe-env-311/
rm -rf instance/
rm -rf models/
setup_python_env.bat
```

---

*Troubleshooting guide for Vybe AI Assistant v1.4.0 - Production Ready Release*
