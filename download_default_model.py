#!/usr/bin/env python3
"""
Download default model for Vybe AI Assistant
Downloads TinyLlama 1.1B as a lightweight default model
"""
import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlparse

def download_with_progress(url, filepath, max_retries=3):
    """Download file with progress bar and retry mechanism"""
    import time
    
    for attempt in range(max_retries):
        try:
            print(f"Downloading {filepath.name}... (attempt {attempt + 1}/{max_retries})")
            
            # Check if partial download exists
            temp_filepath = filepath.with_suffix('.tmp')
            resume_header = {}
            initial_pos = 0
            
            if temp_filepath.exists():
                initial_pos = temp_filepath.stat().st_size
                resume_header = {'Range': f'bytes={initial_pos}-'}
                print(f"Resuming download from {initial_pos // 1024 // 1024}MB...")
            
            response = requests.get(url, stream=True, headers=resume_header, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0)) + initial_pos
            downloaded = initial_pos
            
            # Open in append mode if resuming, otherwise write mode
            mode = 'ab' if initial_pos > 0 else 'wb'
            with open(temp_filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)", end='')
            
            # Move temp file to final location on successful completion
            temp_filepath.rename(filepath)
            print(f"\n✅ Downloaded {filepath.name}")
            return
            
        except (requests.RequestException, IOError) as e:
            print(f"\n⚠️ Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # Clean up partial download on final failure
                temp_filepath = filepath.with_suffix('.tmp')
                if temp_filepath.exists():
                    temp_filepath.unlink()
                raise Exception(f"Failed to download after {max_retries} attempts: {e}")

def main():
    """Download default model"""
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Default must meet hard minimum context (>=32k). Prefer Qwen2 7B (32k) small quant; fallback to Dolphin Llama3 8B (32k)
    qwen7_url = "https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q4_k_m.gguf"
    qwen7_file = models_dir / "qwen2-7b-instruct-q4_k_m.gguf"
    dolphin_url = "https://huggingface.co/cognitivecomputations/dolphin-2.9-llama3-8b-gguf/resolve/main/dolphin-2.9-llama3-8b.Q4_K_M.gguf"
    dolphin_file = models_dir / "dolphin-2.9-llama3-8b.Q4_K_M.gguf"
    
    # If any preferred model exists, skip
    for f in [qwen7_file, dolphin_file]:
        if f.exists():
            print(f"✅ Model already exists: {f.name}")
            print(f"Size: {f.stat().st_size // 1024 // 1024}MB")
            return
    
    try:
        try:
            download_with_progress(qwen7_url, qwen7_file)
            print(f"✅ Default model ready: {qwen7_file.name}")
            print(f"Size: {qwen7_file.stat().st_size // 1024 // 1024}MB")
        except Exception as qerr:
            print(f"⚠️  Qwen2 7B download failed or unavailable: {qerr}")
            print("Falling back to Dolphin Llama3 8B...")
            download_with_progress(dolphin_url, dolphin_file)
            print(f"✅ Default model ready: {dolphin_file.name}")
            print(f"Size: {dolphin_file.stat().st_size // 1024 // 1024}MB")
        
    except Exception as e:
        print(f"❌ All model downloads failed: {e}")
        print("💡 You can manually download a GGUF model to the models/ directory")
        print("💡 Recommended models:")
        print(f"   - {qwen7_url}")
        print(f"   - {dolphin_url}")
        print("💡 Or run the application in offline mode with smaller models")
        sys.exit(1)

if __name__ == "__main__":
    main()
