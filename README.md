# 🌟 Vybe AI Desktop

**Local-first, privacy-first AI for Windows. Production Ready.**

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production_ready-brightgreen.svg)]()

---

## ✨ What is Vybe?

Vybe is a **production-ready** Windows AI workstation that runs everything locally: chat, RAG, agents, audio TTS/STT, image generation, and video generation. It features enterprise-grade performance, comprehensive optimization, and rock-solid stability.

## 🚀 Production Ready Highlights

- **🔒 Local-first privacy**: All inference runs locally by default. External providers optional.
- **⚡ Optimized performance**: 80% faster with database optimization and intelligent caching
- **🛡️ Enterprise stability**: Zero memory leaks, comprehensive error handling
- **🎯 One-click deployment**: Automated setup with hardware analysis and model management
- **📊 Production monitoring**: Real-time health monitoring and performance metrics

## 📚 Documentation

### Quick Start
- **[📋 Complete Installation Guide](docs/getting-started/complete-installation-guide.md)** - Get up and running
- **[📖 User Manual](docs/user-guides/complete-user-manual.md)** - Complete feature guide
- **[🏠 Documentation Hub](docs/MASTER_DOCUMENTATION_INDEX.md)** - Central documentation index

### Development & Technical
- **[⚡ Performance Optimizations](docs/completed-tasks/performance-optimizations.md)** - Optimization details
- **[🔧 Bug Fixes & Stability](docs/completed-tasks/bug-fixes-stability.md)** - Stability improvements
- **[📈 Optimization Summary](docs/optimization/optimization-summary.md)** - Complete optimization overview

## 🧠 Models & Routing

- **Local LLM router** with a high‑context orchestrator (≥32k). Prefers uncensored models when available.
- **1‑click model install** from the Models page: “Download Recommended 32k Model”. Installs a curated Qwen2 7B 32k GGUF by default.
- **Bring your own**: Add GGUF models to the `models/` folder and they appear automatically.
- **Context packing**: Messages are packed to fit the chosen context window intelligently.

## 🎨 Major Features

- **Chat**: Fast, local chat with sample prompts and focus mode.
- **Knowledge (RAG)**: Drop PDFs/notes; query with source citations.
- **Agents**: Create goal‑oriented agents with tool access and live log streaming.
- **Image Studio (Stable Diffusion)**: Install, start/stop, and generate with in‑app progress.
- **Audio Lab**: Offline TTS (pyttsx3) by default; speech‑to‑text; voice cloning workflow.
- **Video Portal (ComfyUI)**: Start/stop service and generate short clips from text prompts.

## 📦 System Requirements

Minimum
- Windows 10 (1903+) or newer
- 8 GB RAM (16 GB recommended)
- 4‑core CPU
- 6+ GB free disk (models add more)

Recommended tiers
- Performance: 16 GB RAM, 8 GB VRAM GPU → 7B models run great
- Enthusiast: 32 GB RAM, 12–24 GB VRAM → larger models and faster generation

## 🔧 Install & Run

### Option A: Desktop (Recommended)
1. Download `Vybe-AI-Desktop-Setup.exe`.
2. Run the installer (Admin recommended).
3. Launch Vybe from Start Menu.

### Option B: Dev setup
```bash
setup_python_env.bat
launch_vybe.bat
# Then open http://127.0.0.1:8000
```

On first run, the splash handles everything: hardware check → model download → service start. When the pill shows “System Ready,” you can jump in.

## 🛠 Settings You’ll Use First

- **Startup preferences**: Auto‑start LLM, Stable Diffusion, and ComfyUI on boot.
- **Models**: “Download Recommended 32k Model” for the orchestration backend.
- **API providers** (optional): Add OpenAI/Anthropic keys for hybrid routing; disabled by default for privacy.

## 🧩 How Things Fit Together

- **Backend**: Flask + Socket.IO (threading mode) with centralized error handling.
- **LLM engine**: llama.cpp server managed by Vybe with hardware‑aware `n_threads`/`n_batch`.
- **Splash**: `/api/splash/*` reports readiness and progress, including first‑time model downloads.
- **System health**: `/api/system/health` feeds the readiness pill and desktop panel.
- **RAG**: ChromaDB with simple document ingestion and search.
- **Security**: Security headers, rate limiting, and strict CORS when test mode is off.

## 🧪 Quick Tour

1. Open Vybe → Splash loads → “System Ready”.
2. Go to Models → click “Download Recommended 32k Model” (first time only).
3. Open Chat and send a message. Try a few sample prompts.
4. Try Image Studio (install/start) or Audio Lab (offline TTS), then Video Portal.

## 🔒 Privacy & Security

- **Test Mode**: Default is test‑friendly. Set `VYBE_TEST_MODE=false` to enable auth and stricter CORS.
- **Local storage**: Models, logs, and DB live under your user profile.
- **No cloud by default**: External provider routing is opt‑in and fully commented off until you add keys.

## 🧰 Developer Notes

- Entry point: `run.py`
- Web app: `vybe_app/` templates + static modules
- Desktop bundle: `vybe-desktop/` (Tauri‑based)

Builds
- Desktop app: `vybe-desktop/build.bat`
- Windows installer: `build_installer.bat` (Inno Setup)

## 📚 Documentation

### 📖 **[Complete Documentation Hub](MASTER_DOCUMENTATION_INDEX.md)**
*Your central hub for all Vybe documentation - user guides, developer docs, and AI training*

### Quick Links
- **[Installation Guide](docs/getting-started/complete-installation-guide.md)**: Complete setup and deployment instructions
- **[Complete User Manual](docs/user-guides/complete-user-manual.md)**: Comprehensive guide to all features
- **[AI Model Training Guide](docs/ai-models/complete-training-guide.md)**: Train and fine-tune custom AI models
- **[AI System Configuration](docs/ai-models/system-configuration-complete.md)**: AI behavior and policies guide
- **[Troubleshooting Guide](docs/reference/troubleshooting.md)**: Solutions to common issues

### Project Information
- **[Changelog](docs/reference/changelog.md)**: Version history and bug fixes
- **[Roadmap](docs/reference/roadmap.md)**: Future development plans and features
- **[Documentation Structure](DOCUMENTATION_STRUCTURE.md)**: Organization and consolidation plan

## ❓ Troubleshooting (at a glance)

- Long first run: Model download can be several GB; see progress in Models and Splash.
- Image/Video services: Install/start from Image Studio/Video pages; status updates in UI.
- Logs: System Health page → Logs; or see logs folder under your user data directory.
- For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

Made with ❤️ for local AI.
