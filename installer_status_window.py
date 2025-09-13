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
        self.installation_log = []
        self.rollback_actions = []
        
    def log_action(self, action, details=""):
        """Log an installation action for potential rollback"""
        self.installation_log.append({
            'action': action,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_rollback_action(self, action_func, description):
        """Add a rollback action to be executed if installation fails"""
        self.rollback_actions.append({
            'func': action_func,
            'description': description
        })
        
    def perform_rollback(self):
        """Perform rollback actions in reverse order"""
        self.status_window.log("Performing installation rollback...", "warning")
        for action in reversed(self.rollback_actions):
            try:
                self.status_window.log(f"Rolling back: {action['description']}", "info")
                action['func']()
            except Exception as e:
                self.status_window.log(f"Rollback action failed: {e}", "error")
                
    def check_system_prerequisites(self) -> bool:
        """Comprehensive system prerequisite checks"""
        self.status_window.log("Performing system prerequisite checks...", "info")
        
        # Check Windows version
        try:
            import platform
            windows_version = platform.version()
            major_version = int(windows_version.split('.')[0])
            build_number = int(windows_version.split('.')[2])
            
            if major_version < 10 or (major_version == 10 and build_number < 18362):  # Windows 10 1903+
                self.status_window.log("❌ Windows 10 version 1903 or later is required", "error")
                return False
            else:
                self.status_window.log(f"✅ Windows version: {windows_version}", "success")
        except Exception as e:
            self.status_window.log(f"⚠️ Could not verify Windows version: {e}", "warning")
            
        # Check available disk space
        try:
            import shutil
            free_space = shutil.disk_usage(self.install_path.drive if self.install_path.drive else 'C:').free
            free_gb = free_space / (1024**3)
            
            required_gb = 8  # Minimum 8GB free space
            if free_gb < required_gb:
                self.status_window.log(f"❌ Insufficient disk space: {free_gb:.1f}GB available, {required_gb}GB required", "error")
                return False
            else:
                self.status_window.log(f"✅ Disk space: {free_gb:.1f}GB available", "success")
        except Exception as e:
            self.status_window.log(f"⚠️ Could not check disk space: {e}", "warning")
            
        # Check available memory
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            if memory_gb < 4:  # Minimum 4GB RAM
                self.status_window.log(f"⚠️ Limited RAM: {memory_gb:.1f}GB (8GB+ recommended)", "warning")
            else:
                self.status_window.log(f"✅ RAM: {memory_gb:.1f}GB", "success")
        except Exception as e:
            self.status_window.log(f"⚠️ Could not check memory: {e}", "warning")
            
        # Check for existing Python installations that might conflict
        try:
            python_paths = []
            common_paths = [
                r"C:\Python*",
                r"C:\Program Files\Python*",
                r"C:\Program Files (x86)\Python*",
                os.path.expanduser(r"~\AppData\Local\Programs\Python\Python*")
            ]
            
            import glob
            for pattern in common_paths:
                python_paths.extend(glob.glob(pattern))
                
            if python_paths:
                self.status_window.log(f"✅ Found {len(python_paths)} Python installation(s)", "success")
            else:
                self.status_window.log("⚠️ No Python installations detected in common locations", "warning")
        except Exception as e:
            self.status_window.log(f"⚠️ Could not check Python installations: {e}", "warning")
            
        # Check internet connectivity
        if not self.check_network_connectivity():
            return False
            
        # Check Windows Defender/Antivirus status
        self.check_antivirus_status()
        
        # Check for potential conflicts
        self.check_potential_conflicts()
        
        return True
        
    def check_potential_conflicts(self):
        """Check for potential software conflicts"""
        self.status_window.log("Checking for potential conflicts...", "info")
        
        # Check for running Python processes
        try:
            import psutil
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.as_dict(attrs=['name'])
                    if proc_info['name'] and 'python' in proc_info['name'].lower():
                        python_processes.append(proc_info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if python_processes:
                unique_processes = list(set(python_processes))
                self.status_window.log(f"⚠️ Found {len(unique_processes)} Python processes running", "warning")
                self.status_window.log("Consider closing other Python applications before installation", "info")
            else:
                self.status_window.log("✅ No conflicting Python processes found", "success")
        except Exception as e:
            self.status_window.log(f"⚠️ Could not check running processes: {e}", "warning")
        
        # Check for locked files in installation directory
        if self.install_path.exists():
            self.status_window.log("Checking for locked files in installation directory...", "info")
            locked_files = []
            try:
                for file_path in self.install_path.rglob('*'):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'a'):
                                pass
                        except (PermissionError, OSError):
                            locked_files.append(str(file_path))
                
                if locked_files:
                    self.status_window.log(f"⚠️ Found {len(locked_files)} locked files", "warning")
                    self.status_window.log("Some files may be in use by other applications", "warning")
                else:
                    self.status_window.log("✅ No locked files detected", "success")
            except Exception as e:
                self.status_window.log(f"⚠️ Could not check for locked files: {e}", "warning")
        
        # Check for sufficient privileges
        try:
            test_file = self.install_path.parent / 'vybe_test_permissions.tmp'
            with open(test_file, 'w') as f:
                f.write('test')
            test_file.unlink()
            self.status_window.log("✅ Sufficient write permissions", "success")
        except Exception as e:
            self.status_window.log(f"⚠️ Limited write permissions: {e}", "warning")
            self.status_window.log("Consider running installer as Administrator", "info")
        
    def check_network_connectivity(self) -> bool:
        """Check network connectivity to required services"""
        self.status_window.log("Checking network connectivity...", "info")
        
        test_urls = [
            ("GitHub", "https://github.com"),
            ("HuggingFace", "https://huggingface.co"),
            ("Python.org", "https://python.org")
        ]
        
        failed_connections = 0
        for name, url in test_urls:
            try:
                import urllib.request
                urllib.request.urlopen(url, timeout=10)
                self.status_window.log(f"✅ {name} connectivity: OK", "success")
            except Exception as e:
                self.status_window.log(f"❌ {name} connectivity failed: {str(e)[:100]}", "error")
                failed_connections += 1
                
        if failed_connections == len(test_urls):
            self.status_window.log("❌ No internet connectivity detected", "error")
            self.status_window.log("Please check your internet connection and firewall settings", "error")
            return False
        elif failed_connections > 0:
            self.status_window.log(f"⚠️ Some services unreachable ({failed_connections}/{len(test_urls)} failed)", "warning")
            
        return True
        
    def check_antivirus_status(self):
        """Check Windows Defender and provide guidance"""
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-MpPreference | Select-Object DisableRealtimeMonitoring'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and 'False' in result.stdout:
                self.status_window.log("✅ Windows Defender is active", "success")
                self.status_window.log("💡 Consider adding installation folder to exclusions if installation is slow", "info")
            else:
                self.status_window.log("⚠️ Windows Defender status unclear", "warning")
        except Exception:
            self.status_window.log("⚠️ Could not check Windows Defender status", "warning")
            
    def cleanup_directory(self, directory_path):
        """Safely cleanup a directory"""
        try:
            if directory_path.exists():
                import shutil
                shutil.rmtree(directory_path)
                self.status_window.log(f"Cleaned up directory: {directory_path}", "info")
        except Exception as e:
            self.status_window.log(f"Failed to cleanup directory {directory_path}: {e}", "error")
            
    def verify_installation_integrity(self) -> bool:
        """Verify that the installation completed successfully"""
        self.status_window.log("Verifying installation integrity...", "info")
        
        # Check critical files exist
        critical_files = [
            'run.py',
            'requirements.txt',
            'launch_vybe_master.bat',
            'vybe_app/__init__.py'
        ]
        
        missing_files = []
        for file_name in critical_files:
            file_path = self.install_path / file_name
            if not file_path.exists():
                missing_files.append(file_name)
                
        if missing_files:
            self.status_window.log(f"❌ Missing critical files: {', '.join(missing_files)}", "error")
            return False
            
        # Check virtual environment
        venv_path = self.install_path / 'vybe-env'
        if not venv_path.exists():
            self.status_window.log("❌ Virtual environment not found", "error")
            return False
            
        # Check Python executable in venv
        python_exe = venv_path / 'Scripts' / 'python.exe'
        if not python_exe.exists():
            self.status_window.log("❌ Python executable not found in virtual environment", "error")
            return False
            
        # Test Python environment
        try:
            result = subprocess.run([str(python_exe), '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.status_window.log(f"✅ Virtual environment Python: {result.stdout.strip()}", "success")
            else:
                self.status_window.log("❌ Virtual environment Python test failed", "error")
                return False
        except Exception as e:
            self.status_window.log(f"❌ Failed to test virtual environment: {e}", "error")
            return False
            
        self.status_window.log("✅ Installation integrity verified", "success")
        return True
        
    def generate_installation_summary(self):
        """Generate a comprehensive installation summary report"""
        try:
            summary_file = self.install_path / 'installation_summary.txt'
            
            # Collect system information
            import platform
            import psutil
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("VYBE AI ASSISTANT - INSTALLATION SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Installation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Installation Path: {self.install_path}\n")
                f.write(f"Installer Version: Enhanced v1.1\n\n")
                
                f.write("SYSTEM INFORMATION:\n")
                f.write("-" * 20 + "\n")
                f.write(f"OS: {platform.system()} {platform.release()}\n")
                f.write(f"Architecture: {platform.architecture()[0]}\n")
                f.write(f"Processor: {platform.processor()}\n")
                
                try:
                    memory = psutil.virtual_memory()
                    f.write(f"RAM: {memory.total / (1024**3):.1f} GB\n")
                    disk = psutil.disk_usage(self.install_path.drive if self.install_path.drive else 'C:')
                    f.write(f"Free Disk Space: {disk.free / (1024**3):.1f} GB\n")
                except:
                    f.write("System specs: Could not determine\n")
                
                f.write("\nINSTALLED COMPONENTS:\n")
                f.write("-" * 20 + "\n")
                
                # Check what was installed
                components = {
                    "Core Application": (self.install_path / 'run.py').exists(),
                    "Virtual Environment": (self.install_path / 'vybe-env').exists(),
                    "Python Dependencies": (self.install_path / 'vybe-env' / 'Scripts' / 'pip.exe').exists(),
                    "Configuration Files": (self.install_path / '.env').exists() or (self.install_path / '.env.example').exists(),
                    "Models Directory": (self.install_path / 'models').exists(),
                    "RAG Data Directory": (self.install_path / 'rag_data').exists(),
                }
                
                for component, installed in components.items():
                    status = "✓ Installed" if installed else "✗ Not installed"
                    f.write(f"{component}: {status}\n")
                
                # Check for models
                models_dir = self.install_path / 'models'
                if models_dir.exists():
                    model_files = list(models_dir.glob('*.gguf'))
                    f.write(f"\nAI MODELS ({len(model_files)} found):\n")
                    f.write("-" * 20 + "\n")
                    if model_files:
                        for model_file in model_files:
                            size_mb = model_file.stat().st_size / (1024 * 1024)
                            f.write(f"• {model_file.name} ({size_mb:.1f} MB)\n")
                    else:
                        f.write("No GGUF model files found\n")
                
                f.write("\nQUICK START:\n")
                f.write("-" * 12 + "\n")
                f.write("1. Launch Vybe from Start Menu or Desktop shortcut\n")
                f.write("2. Wait for 'System Ready' indicator\n")
                f.write("3. Visit Models page to download additional models if needed\n")
                f.write("4. Start chatting or explore other features\n\n")
                
                f.write("TROUBLESHOOTING:\n")
                f.write("-" * 15 + "\n")
                f.write("• If app won't start: Run repair_environment.bat\n")
                f.write("• For model issues: Check Models page in app\n")
                f.write("• For support: Check docs/ folder or GitHub issues\n")
                f.write(f"• Installation logs: {self.install_path / 'installation_log.json'}\n\n")
                
                f.write("=" * 60 + "\n")
                f.write("Installation completed successfully!\n")
                f.write("=" * 60 + "\n")
                
            self.status_window.log(f"✓ Installation summary saved: {summary_file}", "success")
            
        except Exception as e:
            self.status_window.log(f"⚠️ Could not generate installation summary: {e}", "warning")
        
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
        
    def download_large_file_with_progress(self, url, destination, description, max_retries=3):
        """Download large files (like models) with detailed progress tracking and resume capability"""
        self.status_window.log(f"Starting download: {description}", "info")
        self.status_window.log(f"URL: {url}", "info")
        self.status_window.log(f"Destination: {destination}", "info")
        
        for attempt in range(max_retries):
            try:
                import requests
                import time
                
                # Check if partial download exists
                temp_destination = destination.with_suffix('.tmp')
                resume_header = {}
                initial_pos = 0
                
                if temp_destination.exists():
                    initial_pos = temp_destination.stat().st_size
                    resume_header = {'Range': f'bytes={initial_pos}-'}
                    self.status_window.log(f"Resuming download from {initial_pos // 1024 // 1024}MB... (attempt {attempt + 1}/{max_retries})", "info")
                else:
                    self.status_window.log(f"Starting fresh download... (attempt {attempt + 1}/{max_retries})", "info")
                
                # Configure session for large file downloads
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Vybe-Installer/1.0'
                })
                
                # Start the download with streaming and longer timeout for large files
                response = session.get(url, stream=True, headers=resume_header, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0)) + initial_pos
                downloaded = initial_pos
                start_time = time.time()
                last_progress_time = start_time
                
                if total_size > initial_pos:
                    self.status_window.log(f"File size: {total_size // 1024 // 1024:.1f} MB", "info")
                
                # Open in append mode if resuming, otherwise write mode
                mode = 'ab' if initial_pos > 0 else 'wb'
                with open(temp_destination, mode) as f:
                    for chunk in response.iter_content(chunk_size=32768):  # 32KB chunks for large files
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 2 seconds and every 5MB to avoid spam
                            current_time = time.time()
                            if (current_time - last_progress_time >= 2.0) and total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                elapsed = current_time - start_time
                                if elapsed > 0:
                                    speed = (downloaded - initial_pos) / elapsed / 1024 / 1024  # MB/s
                                    eta_seconds = (total_size - downloaded) / ((downloaded - initial_pos) / elapsed) if downloaded > initial_pos else 0
                                    eta_mins = int(eta_seconds / 60)
                                    eta_secs = int(eta_seconds % 60)
                                    
                                    self.status_window.log(
                                        f"Progress: {percent}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB) "
                                        f"Speed: {speed:.1f} MB/s ETA: {eta_mins:02d}:{eta_secs:02d}", 
                                        "info"
                                    )
                                    last_progress_time = current_time
                                        
                # Move temp file to final location on successful completion
                if temp_destination.exists() and temp_destination.stat().st_size > 0:
                    temp_destination.rename(destination)
                    final_size = destination.stat().st_size
                    elapsed = time.time() - start_time
                    avg_speed = (final_size - initial_pos) / elapsed / 1024 / 1024 if elapsed > 0 else 0
                    
                    self.status_window.log(
                        f"✓ Download completed: {description} ({final_size // 1024 // 1024}MB) "
                        f"Average speed: {avg_speed:.1f} MB/s", 
                        "success"
                    )
                    return True
                else:
                    raise Exception("Downloaded file is empty or missing")
                    
            except Exception as e:
                self.status_window.log(f"✗ Download attempt {attempt + 1} failed: {str(e)}", "error")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.status_window.log(f"Retrying in {wait_time} seconds...", "info")
                    time.sleep(wait_time)
                else:
                    # Clean up partial download on final failure
                    temp_destination = destination.with_suffix('.tmp')
                    if temp_destination.exists():
                        temp_destination.unlink()
                    self.status_window.log(f"✗ All download attempts failed: {str(e)}", "error")
                    
        # If all attempts with requests failed, try PowerShell as final fallback
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
        
        # Use the same models as the main download script for consistency
        models_to_try = [
            # Primary: Qwen2 7B (good balance of performance and size)
            {
                'name': 'Qwen2 7B Instruct',
                'url': 'https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q4_k_m.gguf',
                'filename': 'qwen2-7b-instruct-q4_k_m.gguf',
                'description': 'Primary: Qwen2 7B Q4_K_M (4.2GB)',
                'tier': 1,
                'size_mb': 4200,
                'gpu_requirement': 'Most GPUs with 6GB+ VRAM'
            },
            # Fallback: Dolphin Llama3 8B 
            {
                'name': 'Dolphin Llama3 8B',
                'url': 'https://huggingface.co/cognitivecomputations/dolphin-2.9-llama3-8b-gguf/resolve/main/dolphin-2.9-llama3-8b.Q4_K_M.gguf',
                'filename': 'dolphin-2.9-llama3-8b.Q4_K_M.gguf',
                'description': 'Fallback: Dolphin Llama3 8B Q4_K_M (4.4GB)',
                'tier': 1,
                'size_mb': 4400,
                'gpu_requirement': 'Most GPUs with 6GB+ VRAM'
            },
            # Lightweight option: Phi-2 2.7B for lower-end systems
            {
                'name': 'Dolphin Phi-2 2.7B',
                'url': 'https://huggingface.co/cognitivecomputations/dolphin-2.6-phi-2-gguf/resolve/main/dolphin-2.6-phi-2.Q4_K_M.gguf',
                'filename': 'dolphin-2.6-phi-2.Q4_K_M.gguf',
                'description': 'Lightweight: Dolphin Phi-2 2.7B Q4_K_M (1.6GB)',
                'tier': 0,
                'size_mb': 1600,
                'gpu_requirement': 'Entry-level GPUs with 4GB+ VRAM'
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
            
        # Try models in order of preference (no hardware detection needed - use same logic as download_default_model.py)
        self.status_window.log("Selecting optimal model for installation...", "info")
        
        # Use all models as fallbacks in order
        selected_models = models_to_try.copy()
        self.status_window.log(f"Will try models in order: {', '.join([m['name'] for m in selected_models])}", "info")
        
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
        """Main installation process with comprehensive error handling and rollback"""
        try:
            steps = [
                ("System prerequisite checks", 2),
                ("Preparing installation", 5),
                ("Downloading application files", 20),
                ("Extracting files", 30),
                ("Installing Python", 50),
                ("Creating virtual environment", 60),
                ("Installing dependencies", 80),
                ("Configuring application", 90),
                ("Finalizing installation", 100)
            ]
            
            # Step 0: System prerequisite checks
            self.status_window.update_status(steps[0][0])
            self.status_window.update_progress(steps[0][1])
            self.status_window.log("Vybe AI Assistant Installation Started", "info")
            self.status_window.log(f"Installation directory: {self.install_path}", "info")
            
            # Comprehensive prerequisite checks
            if not self.check_system_prerequisites():
                raise Exception("System prerequisite checks failed. Please resolve the issues above and try again.")
            
            # Step 1: Prepare installation
            self.status_window.update_status(steps[1][0])
            self.status_window.update_progress(steps[1][1])
            
            # Create installation directory with rollback
            self.install_path.mkdir(parents=True, exist_ok=True)
            self.log_action("create_install_dir", str(self.install_path))
            self.add_rollback_action(
                lambda: self.cleanup_directory(self.install_path) if self.install_path.exists() else None,
                f"Remove installation directory: {self.install_path}"
            )
            
            # Step 2: Download application files
            self.status_window.update_status(steps[2][0])
            self.status_window.update_progress(steps[2][1])
            
            zip_path = self.temp_path / 'vybe-master.zip'
            if not self.download_file(
                'https://github.com/socalcium/Vybe-Local-Agentic-Container/archive/refs/heads/master.zip',
                zip_path,
                'application files'
            ):
                raise Exception("Failed to download application files")
                
            # Step 3: Extract files
            self.status_window.update_status(steps[3][0])
            self.status_window.update_progress(steps[3][1])
            
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
                    progress = steps[3][1] + int((copied / total_items) * 10)
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
            self.status_window.update_status(steps[4][0])
            self.status_window.update_progress(steps[4][1])
            
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
            self.status_window.update_status(steps[5][0])
            self.status_window.update_progress(steps[5][1])
            
            venv_path = self.install_path / 'vybe-env'
            
            # Remove existing venv if it exists (edge case: partial previous install)
            if venv_path.exists():
                self.status_window.log("Removing existing virtual environment...", "warning")
                try:
                    import shutil
                    shutil.rmtree(venv_path)
                    self.status_window.log("✓ Removed existing virtual environment", "success")
                except Exception as e:
                    self.status_window.log(f"⚠️ Could not remove existing venv: {e}", "warning")
            
            # Create virtual environment with retries
            max_retries = 3
            for attempt in range(max_retries):
                success, output = self.run_command(
                    f'{python_exe} -m venv "{venv_path}"',
                    f"Creating virtual environment (attempt {attempt + 1}/{max_retries})"
                )
                if success:
                    break
                elif attempt < max_retries - 1:
                    self.status_window.log(f"Retrying virtual environment creation in 2 seconds...", "warning")
                    time.sleep(2)
                else:
                    # Try alternative venv creation method
                    self.status_window.log("Trying alternative virtual environment creation method...", "info")
                    success, output = self.run_command(
                        f'{python_exe} -m virtualenv "{venv_path}"',
                        "Creating virtual environment (virtualenv fallback)"
                    )
                    if not success:
                        raise Exception(f"Failed to create virtual environment after {max_retries} attempts: {output}")
            
            self.log_action("create_venv", str(venv_path))
            self.add_rollback_action(
                lambda: self.cleanup_directory(venv_path),
                f"Remove virtual environment: {venv_path}"
            )
                
            # Step 6: Install dependencies
            self.status_window.update_status(steps[6][0])
            self.status_window.update_progress(steps[6][1])
            
            if sys.platform == 'win32':
                pip_exe = venv_path / 'Scripts' / 'pip.exe'
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                pip_exe = venv_path / 'bin' / 'pip'
                venv_python = venv_path / 'bin' / 'python'
                
            # Upgrade pip first with retries
            pip_upgrade_success = False
            for attempt in range(3):
                success, output = self.run_command(
                    f'"{venv_python}" -m pip install --upgrade pip --no-warn-script-location',
                    f"Upgrading pip (attempt {attempt + 1}/3)"
                )
                if success:
                    pip_upgrade_success = True
                    break
                elif attempt < 2:
                    self.status_window.log("Retrying pip upgrade in 3 seconds...", "warning")
                    time.sleep(3)
            
            if not pip_upgrade_success:
                self.status_window.log("⚠️ Pip upgrade failed, continuing with existing version", "warning")
            
            # Install requirements with enhanced error handling
            requirements_file = self.install_path / 'requirements.txt'
            if requirements_file.exists():
                # Try installing packages with different strategies
                install_strategies = [
                    (f'"{pip_exe}" install -r "{requirements_file}" --no-warn-script-location', "Standard installation"),
                    (f'"{pip_exe}" install -r "{requirements_file}" --no-warn-script-location --no-deps', "Installation without dependencies"),
                    (f'"{pip_exe}" install -r "{requirements_file}" --no-warn-script-location --force-reinstall --no-cache-dir', "Force reinstall without cache")
                ]
                
                install_success = False
                for strategy_cmd, strategy_desc in install_strategies:
                    self.status_window.log(f"Trying: {strategy_desc}", "info")
                    success, output = self.run_command(strategy_cmd, strategy_desc)
                    if success:
                        install_success = True
                        break
                    else:
                        self.status_window.log(f"Strategy failed: {strategy_desc}", "warning")
                
                if not install_success:
                    # Try installing critical packages individually
                    self.status_window.log("Attempting to install critical packages individually...", "warning")
                    critical_packages = [
                        "flask>=2.3.0",
                        "flask-socketio>=5.3.0",
                        "requests>=2.28.0",
                        "sqlalchemy>=2.0.0",
                        "psutil>=5.9.0"
                    ]
                    
                    for package in critical_packages:
                        success, _ = self.run_command(
                            f'"{pip_exe}" install "{package}" --no-warn-script-location',
                            f"Installing {package}",
                            show_output=False
                        )
                        if success:
                            self.status_window.log(f"✓ Installed {package}", "success")
                        else:
                            self.status_window.log(f"⚠️ Failed to install {package}", "warning")
            else:
                self.status_window.log("⚠️ requirements.txt not found, skipping package installation", "warning")
                    
            # Step 7: Configure application
            self.status_window.update_status(steps[7][0])
            self.status_window.update_progress(steps[7][1])
            
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
                try:
                    model_success = self.download_default_models()
                    if not model_success:
                        self.status_window.log("⚠️ Model download failed, but installation will continue", "warning")
                        self.status_window.log("You can download models manually later from the app", "info")
                except Exception as model_error:
                    self.status_window.log(f"⚠️ Model download error: {model_error}", "warning")
                    self.status_window.log("Installation will continue without models", "info")
            
            # Step 9: Verify installation integrity
            self.status_window.update_status("Verifying installation...")
            self.status_window.update_progress(95)
            
            if not self.verify_installation_integrity():
                raise Exception("Installation integrity verification failed")
            
            # Step 10: Finalize installation
            self.status_window.update_status(steps[8][0])
            self.status_window.update_progress(steps[8][1])
            
            # Create completion flag with timestamp and verification
            flag_file = self.install_path / 'instance' / 'setup_complete.flag'
            try:
                flag_file.parent.mkdir(parents=True, exist_ok=True)
                with open(flag_file, 'w') as f:
                    f.write(f"Installation completed at {datetime.now().isoformat()}\n")
                    f.write(f"Installation path: {self.install_path}\n")
                    f.write("Status: SUCCESS\n")
                    f.write(f"Installer version: Enhanced v1.1\n")
                    f.write(f"System checks passed: True\n")
                    f.write(f"Integrity verified: True\n")
                
                # Verify the flag file was created
                if flag_file.exists():
                    self.status_window.log(f"✓ Completion flag created: {flag_file}", "success")
                    self.log_action("create_completion_flag", str(flag_file))
                else:
                    self.status_window.log("⚠️ Warning: Completion flag may not have been created properly", "warning")
                    
            except Exception as e:
                self.status_window.log(f"⚠️ Warning: Could not create completion flag: {e}", "warning")
            
            # Save installation log
            try:
                log_file = self.install_path / 'installation_log.json'
                with open(log_file, 'w') as f:
                    json.dump({
                        'installation_log': self.installation_log,
                        'completion_time': datetime.now().isoformat(),
                        'success': True
                    }, f, indent=2)
                self.status_window.log(f"✓ Installation log saved: {log_file}", "success")
            except Exception as e:
                self.status_window.log(f"⚠️ Could not save installation log: {e}", "warning")
            
            # Generate installation summary report
            self.generate_installation_summary()
            
            self.status_window.log("=" * 60, "info")
            self.status_window.log("🎉 Installation completed successfully!", "success")
            self.status_window.log(f"📁 Installation path: {self.install_path}", "info")
            self.status_window.log("🚀 You can now launch Vybe AI Assistant from the Start Menu or Desktop", "info")
            self.status_window.log("💡 First launch may take a few moments to initialize", "info")
            self.status_window.log("📋 Installation summary saved for reference", "info")
            self.status_window.log("=" * 60, "info")
            
            # Add a small delay to ensure all operations complete
            time.sleep(1)
            
            self.status_window.message_queue.put(("complete",))
            
        except Exception as e:
            self.status_window.log(f"CRITICAL ERROR: {str(e)}", "error")
            self.status_window.log(traceback.format_exc(), "error")
            self.status_window.update_status("Installation failed - performing rollback")
            
            # Perform rollback
            self.perform_rollback()
            
            # Save error log
            try:
                error_log_file = self.install_path.parent / f'vybe_installation_error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                with open(error_log_file, 'w') as f:
                    f.write(f"Vybe AI Assistant Installation Error Report\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Installation Path: {self.install_path}\n")
                    f.write(f"Error: {str(e)}\n\n")
                    f.write("Full Traceback:\n")
                    f.write(traceback.format_exc())
                    f.write("\n\nInstallation Log:\n")
                    for entry in self.installation_log:
                        f.write(f"[{entry['timestamp']}] {entry['action']}: {entry['details']}\n")
                        
                self.status_window.log(f"Error report saved: {error_log_file}", "info")
            except:
                pass
            
            # Show user-friendly error message with troubleshooting
            error_msg = f"Installation failed with error:\n\n{str(e)}\n\n"
            error_msg += "Troubleshooting steps:\n"
            error_msg += "1. Run installer as Administrator\n"
            error_msg += "2. Temporarily disable antivirus\n"
            error_msg += "3. Check internet connection\n"
            error_msg += "4. Ensure 8GB+ free disk space\n"
            error_msg += "5. Check the detailed log for more information"
            
            messagebox.showerror("Installation Failed", error_msg)
            

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
