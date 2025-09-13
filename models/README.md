# Vybe AI Assistant - Models Directory

This directory is where GGUF model files are stored for local AI processing.

## Supported Model Types

- **LLM Models**: GGUF format language models for chat and text generation
- **Image Models**: Stable Diffusion checkpoints (.safetensors, .ckpt)
- **Audio Models**: Whisper models for speech recognition, TTS models for text-to-speech

## Model Sources

You can download models from:
- Hugging Face: https://huggingface.co/
- Ollama: https://ollama.ai/
- Direct model repositories

## Recommended Models

### LLM Models
- `dolphin-2.9-llama3-8b.Q4_K_M.gguf` (~4.8GB) - High quality chat model
- `qwen2-7b-instruct.Q4_K_M.gguf` (~4.2GB) - Good balance of quality and speed
- `llama3.2-3b-instruct.Q4_K_M.gguf` (~2.1GB) - Fast, lightweight model

### Image Models
- Stable Diffusion v1.5 (.safetensors)
- DreamShaper v8 (.safetensors)
- Realistic Vision v6.0 (.safetensors)

### Audio Models
- Whisper models (tiny, base, small, medium)
- XTTS-v2 for voice cloning
- Bark for realistic speech synthesis

## Installation

1. Download model files to this directory
2. Restart Vybe AI Assistant
3. Models will be automatically detected and available

## File Structure

```
models/
├── README.md (this file)
├── *.gguf (LLM models)
├── *.safetensors (image models)
└── *.ckpt (image models)
```

For more information, visit the Vybe AI Assistant documentation.
