#!/usr/bin/env python3
"""
Vybe Installer Status Window
Provides real-time feedback during installation with copy-able error text
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import sys
import subprocess
import time
import os
import json
import traceback
from pathlib import Path
from datetime import datetime

class InstallerStatusWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vybe AI Assistant - Installation Progress")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            icon_path = Path(__file__).parent / "assets" / "VybeLight.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        self.is_running = True
        self.has_errors = False
        self.installation_complete = False
        
        # Create GUI elements
        self.setup_gui()
        
        # Start message processor
        self.process_messages()
        
    def setup_gui(self):
        """Setup the GUI elements"""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Vybe AI Assistant Installation", 
                             font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Progress section
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(progress_frame, text="Initializing installation...", 
                                   font=("Arial", 10))
        self.status_label.pack(anchor=tk.W)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                              maximum=100, length=760)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Log section
        log_label = tk.Label(main_frame, text="Installation Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Log text area with scrollbar
        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, 
                                                 font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        
        # Buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.copy_button = tk.Button(button_frame, text="Copy Log", command=self.copy_log,
                                   state=tk.NORMAL)
        self.copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = tk.Button(button_frame, text="Save Log", command=self.save_log)
        self.save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.close_button = tk.Button(button_frame, text="Cancel", command=self.cancel_installation,
                                    bg="#ff4444", fg="white")
        self.close_button.pack(side=tk.RIGHT)
        
    def log(self, message, level="info"):
        """Add a log message to the queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_queue.put(("log", f"[{timestamp}] {message}", level))
        
    def update_status(self, status):
        """Update the status label"""
        self.message_queue.put(("status", status))
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.message_queue.put(("progress", value))
        
    def process_messages(self):
        """Process messages from the queue"""
        try:
            while not self.message_queue.empty():
                msg_type, *args = self.message_queue.get_nowait()
                
                if msg_type == "log":
                    message, level = args
                    self.log_text.insert(tk.END, message + "\n", level)
                    self.log_text.see(tk.END)
                    if level == "error":
                        self.has_errors = True
                        
                elif msg_type == "status":
                    self.status_label.config(text=args[0])
                    
                elif msg_type == "progress":
                    self.progress_var.set(args[0])
                    
                elif msg_type == "complete":
                    self.installation_complete = True
                    self.close_button.config(text="Close", bg="#44ff44", fg="black",
                                           command=self.close_installation)
                    # Enable window close button
                    self.root.protocol("WM_DELETE_WINDOW", self.close_installation)
                    
                    if self.has_errors:
                        messagebox.showwarning("Installation Complete", 
                                             "Installation completed with warnings. Please check the log.")
                    else:
                        messagebox.showinfo("Installation Complete", 
                                          "Vybe AI Assistant has been successfully installed!")
                        
        except queue.Empty:
            pass
            
        if self.is_running:
            self.root.after(100, self.process_messages)
            
    def copy_log(self):
        """Copy log contents to clipboard"""
        log_content = self.log_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(log_content)
        self.log("Log copied to clipboard", "success")
        
    def save_log(self):
        """Save log to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"vybe_install_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.log(f"Log saved to {filename}", "success")
            
    def cancel_installation(self):
        """Cancel the installation"""
        if not self.installation_complete:
            if messagebox.askyesno("Cancel Installation", 
                                 "Are you sure you want to cancel the installation?"):
                self.is_running = False
                self.log("Installation cancelled by user", "warning")
                sys.exit(1)
        else:
            self.close_installation()
            
    def close_installation(self):
        """Close the installation window after completion"""
        if self.installation_complete:
            self.is_running = False
            self.root.quit()
            self.root.destroy()
        else:
            self.cancel_installation()
            
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


class VybeInstaller:
    def __init__(self, status_window):
        self.status_window = status_window
        self.install_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
        self.temp_path = Path(os.environ.get('TEMP', '/tmp')) / 'vybe_install'
        self.temp_path.mkdir(exist_ok=True)
        
    def run_command(self, command, description, show_output=True):
        """Run a command and capture output"""
        self.status_window.log(f"Executing: {description}", "info")
        
        try:
            if isinstance(command, str):
                # For shell commands
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                # For list commands
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            
            output_lines = []
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line = line.strip()
                        if show_output and line:
                            self.status_window.log(f"  > {line}", "info")
                        output_lines.append(line)
                        
            process.wait()
            
            if process.returncode == 0:
                self.status_window.log(f"✓ {description} completed successfully", "success")
                return True, '\n'.join(output_lines)
            else:
                self.status_window.log(f"✗ {description} failed with code {process.returncode}", "error")
                return False, '\n'.join(output_lines)
                
        except Exception as e:
            self.status_window.log(f"✗ Exception during {description}: {str(e)}", "error")
            return False, str(e)
            
    def download_file(self, url, destination, description):
        """Download a file with progress tracking"""
        self.status_window.update_status(f"Downloading {description}...")
        self.status_window.log(f"Downloading from: {url}", "info")
        
        # Try requests first, then fall back to PowerShell
        try:
            import requests
            
            # Configure session for GitHub
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Vybe-Installer/1.0'
            })
            
            response = session.get(url, stream=True, timeout=60, allow_redirects=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            self.status_window.log(f"Download size: {total_size // 1024 // 1024}MB", "info")
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.status_window.update_progress(progress)
                            
            # Verify file was actually downloaded
            if destination.exists() and destination.stat().st_size > 0:
                self.status_window.log(f"✓ Downloaded {description} ({downloaded // 1024 // 1024}MB)", "success")
                return True
            else:
                raise Exception("Downloaded file is empty or missing")
                
        except Exception as e:
            self.status_window.log(f"Requests download failed: {str(e)}", "warning")
            self.status_window.log("Trying PowerShell download method...", "info")
            
            # Fallback to PowerShell
            try:
                # Clean up failed download
                if destination.exists():
                    destination.unlink()
                    
                ps_script = f"""
                $ProgressPreference = 'SilentlyContinue'
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                try {{
                    Invoke-WebRequest -Uri '{url}' -OutFile '{destination}' -UseBasicParsing
                    exit 0
                }} catch {{
                    Write-Host $_.Exception.Message
                    exit 1
                }}
                """
                
                success, output = self.run_command(
                    ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                    f"PowerShell download of {description}",
                    show_output=False
                )
                
                if success and destination.exists() and destination.stat().st_size > 0:
                    size_mb = destination.stat().st_size // 1024 // 1024
                    self.status_window.log(f"✓ Downloaded {description} via PowerShell ({size_mb}MB)", "success")
                    return True
                else:
                    self.status_window.log(f"✗ PowerShell download failed: {output}", "error")
                    return False
                    
            except Exception as ps_error:
                self.status_window.log(f"✗ All download methods failed: {str(ps_error)}", "error")
                return False
                
    def should_download_models(self):
        """Check if models should be downloaded based on command line args or user selection"""
        # Check command line arguments for model download flag
        if len(sys.argv) > 2 and '--download-models' in sys.argv:
            return True
        elif len(sys.argv) > 2 and '--no-models' in sys.argv:
            return False
        else:
            # Default behavior - try to download models
            return True
            
    def detect_hardware_tier(self) -> int:
        """Detect hardware capabilities and recommend appropriate model tier"""
        try:
            import psutil
            
            # Get system info
            memory_gb = psutil.virtual_memory().total / (1024**3)
            cpu_cores = psutil.cpu_count(logical=True)
            
            self.status_window.log(f"System detected: {memory_gb:.1f}GB RAM, {cpu_cores} CPU cores", "info")
            
            # Try to detect GPU VRAM (basic detection)
            gpu_vram_gb = self.detect_gpu_vram()
            
            # Determine tier based on GPU VRAM (primary factor for orchestrator models)
            if gpu_vram_gb >= 16:
                tier = 3
                self.status_window.log(f"Hardware Tier 3 detected: {gpu_vram_gb}GB VRAM (16GB+ GPU)", "success")
            elif gpu_vram_gb >= 10:
                tier = 2
                self.status_window.log(f"Hardware Tier 2 detected: {gpu_vram_gb}GB VRAM (10GB+ GPU)", "success")
            elif gpu_vram_gb >= 8:
                tier = 1
                self.status_window.log(f"Hardware Tier 1 detected: {gpu_vram_gb}GB VRAM (8GB+ GPU)", "success")
            elif memory_gb >= 16:
                tier = 1  # Default to Tier 1 for decent systems without clear GPU info
                self.status_window.log(f"Hardware Tier 1 (fallback): {memory_gb:.1f}GB RAM, GPU detection unclear", "info")
            else:
                tier = 1  # Conservative fallback
                self.status_window.log(f"Hardware Tier 1 (conservative): Limited system resources detected", "warning")
                
            return tier
            
        except Exception as e:
            self.status_window.log(f"Hardware detection failed: {str(e)}, defaulting to Tier 1", "warning")
            return 1
            
    def detect_gpu_vram(self) -> float:
        """Detect GPU VRAM in GB"""
        try:
            # Try different methods to detect GPU VRAM
            import subprocess
            
            # Method 1: Try nvidia-smi for NVIDIA GPUs
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    vram_mb = int(result.stdout.strip())
                    vram_gb = vram_mb / 1024
                    self.status_window.log(f"NVIDIA GPU detected: {vram_gb:.1f}GB VRAM", "success")
                    return vram_gb
            except:
                pass
                
            # Method 2: Try wmic for Windows
            if sys.platform == 'win32':
                try:
                    result = subprocess.run(
                        ['wmic', 'path', 'win32_VideoController', 'get', 'AdapterRAM'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[1:]:  # Skip header
                            if line.strip() and line.strip().isdigit():
                                vram_bytes = int(line.strip())
                                vram_gb = vram_bytes / (1024**3)
                                if vram_gb > 1:  # Filter out integrated graphics
                                    self.status_window.log(f"GPU detected via wmic: {vram_gb:.1f}GB VRAM", "success")
                                    return vram_gb
                except:
                    pass
                    
            self.status_window.log("GPU VRAM detection failed, using conservative estimates", "warning")
            return 0  # Unknown
            
        except Exception as e:
            self.status_window.log(f"GPU detection error: {str(e)}", "warning")
            return 0
        
    def download_large_file_with_progress(self, url, destination, description):
        """Download large files (like models) with detailed progress tracking"""
        self.status_window.log(f"Starting download: {description}", "info")
        self.status_window.log(f"URL: {url}", "info")
        self.status_window.log(f"Destination: {destination}", "info")
        
        try:
            import requests
            import time
            
            # Configure session for large file downloads
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Vybe-Installer/1.0'
            })
            
            # Start the download with streaming
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()
            
            self.status_window.log(f"File size: {total_size // 1024 // 1024:.1f} MB", "info")
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):  # 32KB chunks for large files
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every 1MB or so
                        if downloaded % 1048576 < 32768:  # ~1MB
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                elapsed = time.time() - start_time
                                if elapsed > 0:
                                    speed = downloaded / elapsed / 1024 / 1024  # MB/s
                                    eta_seconds = (total_size - downloaded) / (downloaded / elapsed) if downloaded > 0 else 0
                                    eta_mins = int(eta_seconds / 60)
                                    eta_secs = int(eta_seconds % 60)
                                    
                                    self.status_window.log(
                                        f"Progress: {percent}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB) "
                                        f"Speed: {speed:.1f} MB/s ETA: {eta_mins:02d}:{eta_secs:02d}", 
                                        "info"
                                    )
                                    
            # Verify download
            if destination.exists() and destination.stat().st_size > 0:
                final_size = destination.stat().st_size
                elapsed = time.time() - start_time
                avg_speed = final_size / elapsed / 1024 / 1024 if elapsed > 0 else 0
                
                self.status_window.log(
                    f"✓ Download completed: {description} ({final_size // 1024 // 1024}MB) "
                    f"Average speed: {avg_speed:.1f} MB/s", 
                    "success"
                )
                return True
            else:
                raise Exception("Downloaded file is empty or missing")
                
        except Exception as e:
            self.status_window.log(f"✗ Download failed: {str(e)}", "error")
            
            # Try PowerShell as fallback for large files
            self.status_window.log("Trying PowerShell download method for large file...", "info")
            
            try:
                # Clean up failed download
                if destination.exists():
                    destination.unlink()
                    
                ps_script = f"""
                $ProgressPreference = 'SilentlyContinue'
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                try {{
                    $webClient = New-Object System.Net.WebClient
                    $webClient.DownloadFile('{url}', '{destination}')
                    exit 0
                }} catch {{
                    Write-Host $_.Exception.Message
                    exit 1
                }}
                """
                
                success, output = self.run_command(
                    ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                    f"PowerShell download of {description}",
                    show_output=False
                )
                
                if success and destination.exists() and destination.stat().st_size > 0:
                    size_mb = destination.stat().st_size // 1024 // 1024
                    self.status_window.log(f"✓ Downloaded {description} via PowerShell ({size_mb}MB)", "success")
                    return True
                else:
                    self.status_window.log(f"✗ PowerShell download failed: {output}", "error")
                    return False
                    
            except Exception as ps_error:
                self.status_window.log(f"✗ All download methods failed for large file: {str(ps_error)}", "error")
                return False
                
    def download_default_models(self):
        """Download default AI models with progress tracking in the status window"""
        models_dir = self.install_path / "models"
        models_dir.mkdir(exist_ok=True)
        
        # Orchestrator models based on hardware tiers (from app's manager_model.py)
        models_to_try = [
            # Tier 1: 8GB GPU (most common - GTX 1070, RTX 3060 8GB)
            {
                'name': 'Dolphin Phi-2 2.7B Backend',
                'url': 'https://huggingface.co/cognitivecomputations/dolphin-2.6-phi-2-gguf/resolve/main/dolphin-2.6-phi-2.Q4_K_M.gguf',
                'filename': 'dolphin-2.6-phi-2.Q4_K_M.gguf',
                'description': 'Tier 1: 8GB GPU Compatible (1.6GB)',
                'tier': 1,
                'vram_requirement': '8GB',
                'size_mb': 1600,
                'gpu_requirement': 'GTX 1070 / RTX 3060 8GB'
            },
            # Tier 2: 10GB GPU (RTX 3080, RTX 4060 Ti)
            {
                'name': 'Dolphin Mistral 7B Backend',
                'url': 'https://huggingface.co/cognitivecomputations/dolphin-2.8-mistral-7b-v02-gguf/resolve/main/dolphin-2.8-mistral-7b-v02.Q4_K_M.gguf',
                'filename': 'dolphin-2.8-mistral-7b-v02.Q4_K_M.gguf',
                'description': 'Tier 2: 10GB GPU Optimized (4.1GB)',
                'tier': 2,
                'vram_requirement': '10GB',
                'size_mb': 4100,
                'gpu_requirement': 'RTX 3080 10GB / RTX 4060 Ti'
            },
            # Tier 3: 16GB GPU (RTX 4070 Ti, RTX 3090, RTX 4080)
            {
                'name': 'Hermes 2 Pro Llama3 8B Backend',
                'url': 'https://huggingface.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF/resolve/main/Hermes-2-Pro-Llama-3-8B.Q4_K_M.gguf',
                'filename': 'Hermes-2-Pro-Llama-3-8B.Q4_K_M.gguf',
                'description': 'Tier 3: 16GB GPU Performance (4.8GB)',
                'tier': 3,
                'vram_requirement': '16GB',
                'size_mb': 4800,
                'gpu_requirement': 'RTX 4070 Ti / RTX 3090 / RTX 4080'
            }
        ]
        
        # Check if any model already exists
        existing_models = []
        for model in models_to_try:
            model_path = models_dir / model['filename']
            if model_path.exists() and model_path.stat().st_size > 100 * 1024 * 1024:  # At least 100MB
                existing_models.append(model)
                size_mb = model_path.stat().st_size // 1024 // 1024
                self.status_window.log(f"✓ Model already exists: {model['name']} ({size_mb}MB)", "success")
                
        if existing_models:
            self.status_window.log("Skipping model download - suitable models already present", "info")
            return True
            
        # Detect hardware and select appropriate model
        self.status_window.log("Analyzing system capabilities for optimal model selection...", "info")
        detected_tier = self.detect_hardware_tier()
        
        # Select model based on detected tier, with fallbacks
        selected_models = []
        
        # Add the recommended model for detected tier
        for model in models_to_try:
            if model['tier'] == detected_tier:
                selected_models.append(model)
                self.status_window.log(f"Selected primary model: {model['name']} (Tier {detected_tier})", "success")
                break
                
        # Add fallback models (lower tiers)
        for tier in range(detected_tier - 1, 0, -1):
            for model in models_to_try:
                if model['tier'] == tier:
                    selected_models.append(model)
                    self.status_window.log(f"Added fallback model: {model['name']} (Tier {tier})", "info")
                    break
        
        if not selected_models:
            # Safety fallback - use Tier 1 model
            for model in models_to_try:
                if model['tier'] == 1:
                    selected_models.append(model)
                    break
        
        # Try to download models starting with the best match
        self.status_window.log("Starting orchestrator model download...", "info")
        self.status_window.log("This may take 5-30 minutes depending on your internet speed and model size", "warning")
        
        for i, model in enumerate(selected_models):
            try:
                model_path = models_dir / model['filename']
                self.status_window.log(f"Attempting to download: {model['name']}", "info")
                self.status_window.log(f"Model specs: {model['description']} - {model['gpu_requirement']}", "info")
                
                if self.download_large_file_with_progress(model['url'], model_path, model['description']):
                    # Verify the downloaded model
                    expected_size = model['size_mb'] * 1024 * 1024
                    actual_size = model_path.stat().st_size if model_path.exists() else 0
                    
                    if actual_size > expected_size * 0.8:  # Allow 20% variance
                        size_mb = actual_size // 1024 // 1024
                        self.status_window.log(f"✓ Orchestrator model ready: {model['name']} ({size_mb}MB)", "success")
                        self.status_window.log(f"✓ This model is optimized for your {model['gpu_requirement']} hardware", "success")
                        self.status_window.log("✓ The app will use this as the backend orchestrator model", "success")
                        return True
                    else:
                        self.status_window.log(f"✗ Downloaded model appears corrupted (expected ~{model['size_mb']}MB, got {actual_size // 1024 // 1024}MB)", "error")
                        if model_path.exists():
                            model_path.unlink()
                        continue
                else:
                    self.status_window.log(f"✗ Failed to download {model['name']}", "error")
                    if i < len(selected_models) - 1:
                        self.status_window.log(f"Trying fallback model...", "info")
                    continue
                    
            except Exception as e:
                self.status_window.log(f"✗ Exception downloading {model['name']}: {str(e)}", "error")
                continue
                
        # If we get here, all downloads failed
        self.status_window.log("⚠️ All model downloads failed", "warning")
        self.status_window.log("You can manually download models later:", "info")
        self.status_window.log("1. Go to the models/ folder in your installation", "info")
        self.status_window.log("2. Download any GGUF model file", "info")
        self.status_window.log("3. Restart Vybe AI Assistant", "info")
        self.status_window.log("Recommended models:", "info")
        for model in models_to_try:
            self.status_window.log(f"   - {model['url']}", "info")
            
        # Don't fail the installation just because model download failed
        return False
            
    def install(self):
        """Main installation process"""
        try:
            steps = [
                ("Preparing installation", 5),
                ("Downloading application files", 20),
                ("Extracting files", 30),
                ("Installing Python", 50),
                ("Creating virtual environment", 60),
                ("Installing dependencies", 80),
                ("Configuring application", 90),
                ("Finalizing installation", 100)
            ]
            
            total_steps = len(steps)
            
            # Step 1: Prepare installation
            self.status_window.update_status(steps[0][0])
            self.status_window.update_progress(steps[0][1])
            self.status_window.log("Vybe AI Assistant Installation Started", "info")
            self.status_window.log(f"Installation directory: {self.install_path}", "info")
            
            # Create installation directory
            self.install_path.mkdir(parents=True, exist_ok=True)
            
            # Step 2: Download application files
            self.status_window.update_status(steps[1][0])
            self.status_window.update_progress(steps[1][1])
            
            zip_path = self.temp_path / 'vybe-master.zip'
            if not self.download_file(
                'https://github.com/socalcium/Vybe-Local-Agentic-Container/archive/refs/heads/master.zip',
                zip_path,
                'application files'
            ):
                raise Exception("Failed to download application files")
                
            # Step 3: Extract files
            self.status_window.update_status(steps[2][0])
            self.status_window.update_progress(steps[2][1])
            
            import zipfile
            import shutil
            
            self.status_window.log("Extracting downloaded archive...", "info")
            
            # First, let's verify the ZIP file
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                raise Exception(f"Downloaded file is missing or empty: {zip_path}")
                
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the archive for debugging
                file_list = zip_ref.namelist()
                self.status_window.log(f"Archive contains {len(file_list)} files", "info")
                
                # Extract all files
                self.status_window.log("Extracting files to temporary directory...", "info")
                zip_ref.extractall(self.temp_path)
                
            # Find the extracted directory (GitHub adds a suffix)
            extracted_dirs = [d for d in self.temp_path.iterdir() if d.is_dir() and 'Vybe' in d.name]
            if not extracted_dirs:
                # List what we got for debugging
                self.status_window.log("Contents of temp directory:", "warning")
                for item in self.temp_path.iterdir():
                    self.status_window.log(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})", "warning")
                raise Exception("Could not find extracted Vybe directory")
                
            extracted_dir = extracted_dirs[0]
            self.status_window.log(f"Found extracted directory: {extracted_dir.name}", "info")
            
            # Verify the extracted directory has content
            extracted_items = list(extracted_dir.iterdir())
            if not extracted_items:
                raise Exception(f"Extracted directory is empty: {extracted_dir}")
                
            self.status_window.log(f"Copying {len(extracted_items)} items to installation directory...", "info")
            
            # Copy files to installation directory with progress
            total_items = len(extracted_items)
            copied = 0
            
            for item in extracted_items:
                dest = self.install_path / item.name
                try:
                    if item.is_dir():
                        # Remove existing directory if it exists
                        if dest.exists():
                            shutil.rmtree(dest)
                        # Copy entire directory tree
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                        # Count files in directory for logging
                        file_count = sum(1 for _ in dest.rglob('*') if _.is_file())
                        self.status_window.log(f"  ✓ Copied directory: {item.name} ({file_count} files)", "info")
                    else:
                        # Copy single file
                        shutil.copy2(item, dest)
                        self.status_window.log(f"  ✓ Copied file: {item.name}", "info")
                    
                    copied += 1
                    progress = steps[2][1] + int((copied / total_items) * 10)
                    self.status_window.update_progress(progress)
                    
                except Exception as e:
                    self.status_window.log(f"  ✗ Failed to copy {item.name}: {str(e)}", "error")
                    
            # Verify critical files exist
            critical_files = ['run.py', 'requirements.txt', 'launch_vybe_master.bat']
            missing_files = []
            
            for file_name in critical_files:
                if not (self.install_path / file_name).exists():
                    missing_files.append(file_name)
                    
            if missing_files:
                self.status_window.log(f"Warning: Missing critical files: {', '.join(missing_files)}", "warning")
                # List what we actually have
                self.status_window.log("Installed files:", "info")
                for item in self.install_path.iterdir():
                    self.status_window.log(f"  - {item.name}", "info")
            else:
                self.status_window.log("✓ All critical files verified", "success")
                
            self.status_window.log(f"✓ Files extracted and copied successfully ({copied} items)", "success")
                
            # Step 4: Check/Install Python
            self.status_window.update_status(steps[3][0])
            self.status_window.update_progress(steps[3][1])
            
            # Check if Python is installed
            python_installed = False
            python_exe = None
            
            for python_cmd in ['python', 'python3', 'py -3.11', 'py -3.10', 'py -3.9']:
                success, output = self.run_command(
                    f"{python_cmd} --version",
                    f"Checking for Python ({python_cmd})",
                    show_output=False
                )
                if success and 'Python 3.' in output:
                    python_exe = python_cmd
                    python_installed = True
                    self.status_window.log(f"Found Python: {output.strip()}", "success")
                    break
                    
            if not python_installed:
                self.status_window.log("Python not found, downloading installer...", "warning")
                python_installer = self.temp_path / 'python-installer.exe'
                if self.download_file(
                    'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe',
                    python_installer,
                    'Python 3.11.9'
                ):
                    # Install Python silently
                    success, _ = self.run_command(
                        f'"{python_installer}" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0',
                        "Installing Python 3.11.9"
                    )
                    if success:
                        python_exe = 'python'
                    else:
                        raise Exception("Failed to install Python")
                        
            # Step 5: Create virtual environment
            self.status_window.update_status(steps[4][0])
            self.status_window.update_progress(steps[4][1])
            
            venv_path = self.install_path / 'vybe-env'
            success, _ = self.run_command(
                f'{python_exe} -m venv "{venv_path}"',
                "Creating virtual environment"
            )
            if not success:
                raise Exception("Failed to create virtual environment")
                
            # Step 6: Install dependencies
            self.status_window.update_status(steps[5][0])
            self.status_window.update_progress(steps[5][1])
            
            if sys.platform == 'win32':
                pip_exe = venv_path / 'Scripts' / 'pip.exe'
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                pip_exe = venv_path / 'bin' / 'pip'
                venv_python = venv_path / 'bin' / 'python'
                
            # Upgrade pip first
            success, _ = self.run_command(
                f'"{venv_python}" -m pip install --upgrade pip',
                "Upgrading pip"
            )
            
            # Install requirements
            requirements_file = self.install_path / 'requirements.txt'
            if requirements_file.exists():
                success, output = self.run_command(
                    f'"{pip_exe}" install -r "{requirements_file}"',
                    "Installing Python packages"
                )
                if not success:
                    self.status_window.log("Some packages failed to install, continuing...", "warning")
                    
            # Step 7: Configure application
            self.status_window.update_status(steps[6][0])
            self.status_window.update_progress(steps[6][1])
            
            # Create necessary directories
            dirs_to_create = [
                self.install_path / 'instance',
                self.install_path / 'logs',
                self.install_path / 'models',
                self.install_path / 'rag_data' / 'chroma_db',
                self.install_path / 'rag_data' / 'knowledge_base'
            ]
            
            for dir_path in dirs_to_create:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.status_window.log(f"Created directory: {dir_path.name}", "info")
                
            # Create .env file if needed
            env_example = self.install_path / '.env.example'
            env_file = self.install_path / '.env'
            if env_example.exists() and not env_file.exists():
                import shutil
                shutil.copy2(env_example, env_file)
                self.status_window.log("Created .env configuration file", "success")
                
            # Step 8: Download AI Models (if selected)
            if self.should_download_models():
                self.status_window.update_status("Downloading AI Models...")
                self.status_window.update_progress(85)
                self.download_default_models()
            
            # Step 9: Finalize installation
            self.status_window.update_status(steps[7][0])
            self.status_window.update_progress(steps[7][1])
            
            # Create completion flag
            flag_file = self.install_path / 'instance' / 'setup_complete.flag'
            flag_file.touch()
            
            self.status_window.log("=" * 60, "info")
            self.status_window.log("Installation completed successfully!", "success")
            self.status_window.log(f"Installation path: {self.install_path}", "info")
            self.status_window.log("You can now launch Vybe AI Assistant from the Start Menu or Desktop", "info")
            self.status_window.log("=" * 60, "info")
            
            self.status_window.message_queue.put(("complete",))
            
        except Exception as e:
            self.status_window.log(f"CRITICAL ERROR: {str(e)}", "error")
            self.status_window.log(traceback.format_exc(), "error")
            self.status_window.update_status("Installation failed")
            messagebox.showerror("Installation Failed", 
                               f"Installation failed with error:\n\n{str(e)}\n\nPlease check the log for details.")
            

def main():
    """Main entry point"""
    # Create and show status window
    status_window = InstallerStatusWindow()
    
    # Run installer in separate thread
    installer = VybeInstaller(status_window)
    installer_thread = threading.Thread(target=installer.install)
    installer_thread.daemon = True
    installer_thread.start()
    
    # Start GUI
    status_window.run()
    

if __name__ == "__main__":
    main()
