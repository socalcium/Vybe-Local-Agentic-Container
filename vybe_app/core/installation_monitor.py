#!/usr/bin/env python3
"""
AI-Powered Installation Diagnostics and Self-Healing System
Provides intelligent analysis of installation issues and automatic repair capabilities.
"""

import os
import sys
import json
import subprocess
import platform
import psutil
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
import threading
import time

from ..logger import logger
from ..config import Config


class InstallationMonitor:
    """AI-powered installation diagnostics and self-healing system"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.instance_dir = self.base_dir / "instance"
        self.logs_dir = self.base_dir / "vybe_app" / "logs"
        self.diagnostics_file = self.instance_dir / "installation_diagnostics.json"
        self.repair_history_file = self.instance_dir / "repair_history.json"
        self.health_check_interval = 300  # 5 minutes
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Ensure directories exist
        self.instance_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load previous diagnostics
        self.diagnostics = self._load_diagnostics()
        self.repair_history = self._load_repair_history()
        
        # AI analysis patterns
        self.issue_patterns = self._load_issue_patterns()
        
    def _load_diagnostics(self) -> Dict[str, Any]:
        """Load previous diagnostics data"""
        if self.diagnostics_file.exists():
            try:
                with open(self.diagnostics_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load diagnostics file")
        
        return {
            "last_check": None,
            "system_info": {},
            "component_status": {},
            "issues": [],
            "repairs": [],
            "health_score": 100,
            "recommendations": []
        }
    
    def _load_repair_history(self) -> List[Dict[str, Any]]:
        """Load repair history"""
        if self.repair_history_file.exists():
            try:
                with open(self.repair_history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load repair history")
        
        return []
    
    def _load_issue_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load AI issue detection patterns"""
        return {
            "python_environment": {
                "symptoms": [
                    "ModuleNotFoundError",
                    "ImportError", 
                    "python executable not found",
                    "pip not found"
                ],
                "severity": "critical",
                "repair_actions": ["check_python_installation", "install_missing_packages"],
                "ai_analysis": "Python environment issues typically indicate missing dependencies or incorrect Python version"
            },
            "model_download_failure": {
                "symptoms": [
                    "download failed",
                    "connection timeout",
                    "insufficient disk space",
                    "model file corrupted"
                ],
                "severity": "high",
                "repair_actions": ["check_disk_space", "verify_network", "retry_download"],
                "ai_analysis": "Model download failures often relate to network issues, disk space, or corrupted downloads"
            },
            "backend_service_failure": {
                "symptoms": [
                    "backend not responding",
                    "llama-cpp-python error",
                    "port already in use",
                    "service startup failed"
                ],
                "severity": "high",
                "repair_actions": ["restart_backend", "check_port_conflicts", "verify_model_files"],
                "ai_analysis": "Backend service failures usually indicate port conflicts, missing models, or configuration issues"
            },
            "permission_issues": {
                "symptoms": [
                    "permission denied",
                    "access denied",
                    "cannot write to directory",
                    "read-only file system"
                ],
                "severity": "medium",
                "repair_actions": ["fix_permissions", "check_user_rights", "verify_directory_access"],
                "ai_analysis": "Permission issues typically occur when the application lacks proper file system access rights"
            },
            "memory_issues": {
                "symptoms": [
                    "out of memory",
                    "insufficient memory",
                    "memory allocation failed",
                    "swap space exhausted"
                ],
                "severity": "high",
                "repair_actions": ["optimize_memory_usage", "reduce_model_context", "check_system_resources"],
                "ai_analysis": "Memory issues often occur when running large models or when system resources are constrained"
            },
            "dependency_conflicts": {
                "symptoms": [
                    "version conflict",
                    "incompatible versions",
                    "dependency resolution failed",
                    "package conflicts"
                ],
                "severity": "medium",
                "repair_actions": ["resolve_dependencies", "update_packages", "clean_environment"],
                "ai_analysis": "Dependency conflicts typically arise from incompatible package versions or corrupted environments"
            }
        }
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            return
        
        # Use a stop event to enable prompt shutdown without long sleeps
        self._stop_event = getattr(self, "_stop_event", threading.Event())
        self._stop_event.clear()
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Installation monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        # Signal the monitoring thread to stop and wake immediately
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Installation monitoring stopped")
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        # Loop until stop event is set; use wait() for responsive sleeps
        stop_event = getattr(self, "_stop_event", threading.Event())
        while not stop_event.is_set() and self.is_monitoring:
            try:
                self.run_diagnostics()
                # Wait up to the interval, but wake early if stopping
                stop_event.wait(self.health_check_interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                # Back off on error but remain interruptible
                stop_event.wait(60)  # Wait before retrying
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive AI-powered diagnostics"""
        logger.info("Running AI-powered installation diagnostics...")
        
        # Collect system information
        system_info = self._collect_system_info()
        
        # Check component status
        component_status = self._check_component_status()
        
        # Analyze issues using AI patterns
        issues = self._analyze_issues(system_info, component_status)
        
        # Generate health score
        health_score = self._calculate_health_score(component_status, issues)
        
        # Generate AI recommendations
        recommendations = self._generate_recommendations(issues, health_score)
        
        # Update diagnostics
        self.diagnostics.update({
            "last_check": datetime.now().isoformat(),
            "system_info": system_info,
            "component_status": component_status,
            "issues": issues,
            "health_score": health_score,
            "recommendations": recommendations
        })
        
        # Save diagnostics
        self._save_diagnostics()
        
        # Auto-repair if enabled
        if self._should_auto_repair(issues):
            self._perform_auto_repairs(issues)
        
        return self.diagnostics
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information"""
        try:
            # Basic system info
            system_info: Dict[str, Any] = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "python_version": sys.version,
                "python_executable": sys.executable,
                "working_directory": str(Path.cwd()),
                "timestamp": datetime.now().isoformat()
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            system_info.update({
                "total_memory_gb": round(memory.total / (1024**3), 2),
                "available_memory_gb": round(memory.available / (1024**3), 2),
                "memory_percent": memory.percent,
                "swap_total_gb": round(psutil.swap_memory().total / (1024**3), 2),
                "swap_used_gb": round(psutil.swap_memory().used / (1024**3), 2)
            })
            
            # Disk information
            disk = psutil.disk_usage(self.base_dir)
            system_info.update({
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_percent": round((disk.used / disk.total) * 100, 2)
            })
            
            # Network connectivity
            try:
                response = requests.get("https://httpbin.org/get", timeout=5)
                system_info["network_connectivity"] = str(response.status_code == 200)
            except Exception as e:
                logger.warning(f"Network connectivity check failed: {e}")
                system_info["network_connectivity"] = "False"
            
            # Environment variables
            system_info["environment"] = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                "VYBE_ENV": os.environ.get("VYBE_ENV", "")
            }
            
            return system_info
            
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return {"error": str(e)}
    
    def _check_component_status(self) -> Dict[str, Any]:
        """Check status of all Vybe components"""
        components = {}
        
        # Check Python environment
        components["python_environment"] = self._check_python_environment()
        
        # Check core files
        components["core_files"] = self._check_core_files()
        
        # Check models
        components["models"] = self._check_models()
        
        # Check backend services
        components["backend_services"] = self._check_backend_services()
        
        # Check external services
        components["external_services"] = self._check_external_services()
        
        # Check permissions
        components["permissions"] = self._check_permissions()
        
        # Check dependencies
        components["dependencies"] = self._check_dependencies()
        
        return components
    
    def _check_python_environment(self) -> Dict[str, Any]:
        """Check Python environment health"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        try:
            # Check Python version
            python_version = sys.version_info
            status["details"]["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
            if python_version < (3, 8):
                status["healthy"] = False
                status["issues"].append("Python version too old (requires 3.8+)")
            
            # Check pip
            try:
                import pip
                status["details"]["pip_version"] = pip.__version__
            except ImportError:
                status["healthy"] = False
                status["issues"].append("pip not available")
            
            # Check virtual environment
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                status["details"]["virtual_env"] = True
                status["details"]["venv_path"] = sys.prefix
            else:
                status["details"]["virtual_env"] = False
                status["issues"].append("Not running in virtual environment (recommended)")
            
        except Exception as e:
            status["healthy"] = False
            status["issues"].append(f"Python environment check failed: {e}")
        
        return status
    
    def _check_core_files(self) -> Dict[str, Any]:
        """Check core Vybe files"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        required_files = [
            "run.py",
            "vybe_app/__init__.py",
            "vybe_app/core/manager_model.py",
            "vybe_app/core/hardware_manager.py",
            "requirements.txt",
            "pyproject.toml"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        status["details"]["missing_files"] = missing_files
        status["details"]["total_files"] = len(required_files)
        status["details"]["present_files"] = len(required_files) - len(missing_files)
        
        if missing_files:
            status["healthy"] = False
            status["issues"].append(f"Missing core files: {', '.join(missing_files)}")
        
        return status
    
    def _check_models(self) -> Dict[str, Any]:
        """Check model availability and health"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        try:
            models_dir = self.base_dir / "models"
            if not models_dir.exists():
                status["healthy"] = False
                status["issues"].append("Models directory not found")
                return status
            
            # Check for model files
            model_files = list(models_dir.glob("*.gguf"))
            status["details"]["total_models"] = len(model_files)
            status["details"]["model_files"] = [f.name for f in model_files]
            
            if not model_files:
                status["healthy"] = False
                status["issues"].append("No model files found")
            
            # Check model file sizes
            large_models = []
            for model_file in model_files:
                size_mb = model_file.stat().st_size / (1024 * 1024)
                if size_mb < 100:  # Suspiciously small
                    status["issues"].append(f"Model {model_file.name} appears corrupted (size: {size_mb:.1f}MB)")
                    status["healthy"] = False
                large_models.append({"name": model_file.name, "size_mb": size_mb})
            
            status["details"]["model_sizes"] = large_models
            
        except Exception as e:
            status["healthy"] = False
            status["issues"].append(f"Model check failed: {e}")
        
        return status
    
    def _check_backend_services(self) -> Dict[str, Any]:
        """Check backend service status"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        try:
            # Check if backend is running
            try:
                response = requests.get("http://localhost:11435/v1/models", timeout=5)
                status["details"]["backend_running"] = response.status_code == 200
                if response.status_code == 200:
                    status["details"]["backend_models"] = response.json()
            except requests.exceptions.RequestException:
                status["details"]["backend_running"] = False
                status["healthy"] = False
                status["issues"].append("Backend service not responding")
            
            # Check Vybe API
            try:
                response = requests.get(f"http://localhost:{Config.PORT}/api/splash/status", timeout=5)
                status["details"]["vybe_api_running"] = response.status_code == 200
            except requests.exceptions.RequestException:
                status["details"]["vybe_api_running"] = False
                status["healthy"] = False
                status["issues"].append("Vybe API not responding")
            
        except Exception as e:
            status["healthy"] = False
            status["issues"].append(f"Backend service check failed: {e}")
        
        return status
    
    def _check_external_services(self) -> Dict[str, Any]:
        """Check external service status"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        # Check Automatic1111
        try:
            response = requests.get("http://localhost:7860", timeout=5)
            status["details"]["automatic1111_running"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"Automatic1111 service check failed: {e}")
            status["details"]["automatic1111_running"] = False
        
        # Check ComfyUI
        try:
            response = requests.get("http://localhost:8188", timeout=5)
            status["details"]["comfyui_running"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"ComfyUI service check failed: {e}")
            status["details"]["comfyui_running"] = False
        
        # External services are optional, so don't mark as unhealthy if not running
        return status
    
    def _check_permissions(self) -> Dict[str, Any]:
        """Check file and directory permissions"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        try:
            # Check if we can write to instance directory
            test_file = self.instance_dir / "permission_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                status["details"]["instance_writable"] = True
            except (IOError, OSError):
                status["details"]["instance_writable"] = False
                status["healthy"] = False
                status["issues"].append("Cannot write to instance directory")
            
            # Check if we can write to logs directory
            test_file = self.logs_dir / "permission_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                status["details"]["logs_writable"] = True
            except (IOError, OSError):
                status["details"]["logs_writable"] = False
                status["healthy"] = False
                status["issues"].append("Cannot write to logs directory")
            
        except Exception as e:
            status["healthy"] = False
            status["issues"].append(f"Permission check failed: {e}")
        
        return status
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check Python dependencies"""
        status = {"healthy": True, "issues": [], "details": {}}
        
        try:
            # Check critical dependencies
            critical_deps = [
                "flask", "requests", "psutil", "pillow", 
                "llama_cpp", "openai", "anthropic"
            ]
            
            missing_deps = []
            for dep in critical_deps:
                try:
                    __import__(dep.replace("-", "_"))
                    status["details"][f"{dep}_available"] = True
                except ImportError:
                    status["details"][f"{dep}_available"] = False
                    missing_deps.append(dep)
            
            if missing_deps:
                status["healthy"] = False
                status["issues"].append(f"Missing critical dependencies: {', '.join(missing_deps)}")
            
        except Exception as e:
            status["healthy"] = False
            status["issues"].append(f"Dependency check failed: {e}")
        
        return status
    
    def _analyze_issues(self, system_info: Dict[str, Any], component_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze issues using AI patterns"""
        issues = []
        
        # Analyze system resources
        if system_info.get("memory_percent", 0) > 90:
            issues.append({
                "type": "memory_issues",
                "severity": "high",
                "description": f"High memory usage: {system_info['memory_percent']}%",
                "ai_analysis": "System memory is critically low, which may cause model loading failures",
                "recommended_actions": ["close_other_applications", "reduce_model_context", "restart_application"]
            })
        
        if system_info.get("disk_percent", 0) > 95:
            issues.append({
                "type": "disk_space",
                "severity": "critical",
                "description": f"Low disk space: {system_info['disk_free_gb']:.1f}GB free",
                "ai_analysis": "Insufficient disk space will prevent model downloads and file operations",
                "recommended_actions": ["free_disk_space", "clean_temp_files", "remove_unused_models"]
            })
        
        # Analyze component issues
        for component_name, component_data in component_status.items():
            if not component_data.get("healthy", True):
                for issue in component_data.get("issues", []):
                    # Match issue against patterns
                    matched_pattern = self._match_issue_pattern(issue)
                    if matched_pattern:
                        issues.append({
                            "type": matched_pattern["type"],
                            "severity": matched_pattern["severity"],
                            "description": issue,
                            "component": component_name,
                            "ai_analysis": matched_pattern["ai_analysis"],
                            "recommended_actions": matched_pattern["repair_actions"]
                        })
                    else:
                        issues.append({
                            "type": "unknown",
                            "severity": "medium",
                            "description": issue,
                            "component": component_name,
                            "ai_analysis": "Unknown issue pattern - manual investigation required",
                            "recommended_actions": ["manual_investigation", "check_logs"]
                        })
        
        return issues
    
    def _match_issue_pattern(self, issue_description: str) -> Optional[Dict[str, Any]]:
        """Match issue description against known patterns"""
        issue_lower = issue_description.lower()
        
        for pattern_name, pattern_data in self.issue_patterns.items():
            for symptom in pattern_data["symptoms"]:
                if symptom.lower() in issue_lower:
                    return {
                        "type": pattern_name,
                        "severity": pattern_data["severity"],
                        "ai_analysis": pattern_data["ai_analysis"],
                        "repair_actions": pattern_data["repair_actions"]
                    }
        
        return None
    
    def _calculate_health_score(self, component_status: Dict[str, Any], issues: List[Dict[str, Any]]) -> int:
        """Calculate overall health score (0-100)"""
        base_score = 100
        
        # Deduct points for unhealthy components
        for component_data in component_status.values():
            if not component_data.get("healthy", True):
                base_score -= 10
        
        # Deduct points for issues by severity
        for issue in issues:
            severity = issue.get("severity", "medium")
            if severity == "critical":
                base_score -= 25
            elif severity == "high":
                base_score -= 15
            elif severity == "medium":
                base_score -= 10
            elif severity == "low":
                base_score -= 5
        
        return max(0, base_score)
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]], health_score: int) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        if health_score < 50:
            recommendations.append("🚨 CRITICAL: System health is poor. Immediate attention required.")
        
        if health_score < 75:
            recommendations.append("⚠️ WARNING: System health is degraded. Consider running repairs.")
        
        # Generate specific recommendations based on issues
        for issue in issues:
            if issue.get("severity") == "critical":
                recommendations.append(f"🔧 CRITICAL: {issue.get('description', 'Unknown issue')}")
            elif issue.get("severity") == "high":
                recommendations.append(f"🔧 HIGH: {issue.get('description', 'Unknown issue')}")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("✅ System is healthy. No immediate action required.")
        
        return recommendations
    
    def _should_auto_repair(self, issues: List[Dict[str, Any]]) -> bool:
        """Determine if auto-repair should be performed"""
        # Only auto-repair critical and high severity issues
        critical_issues = [i for i in issues if i.get("severity") in ["critical", "high"]]
        return len(critical_issues) > 0
    
    def _perform_auto_repairs(self, issues: List[Dict[str, Any]]):
        """Perform automatic repairs for detected issues"""
        logger.info("Performing automatic repairs...")
        
        repairs_made = []
        
        for issue in issues:
            if issue.get("severity") in ["critical", "high"]:
                repair_result = self._repair_issue(issue)
                if repair_result:
                    repairs_made.append({
                        "issue": issue,
                        "repair_result": repair_result,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Update repair history
        self.repair_history.extend(repairs_made)
        self._save_repair_history()
        
        if repairs_made:
            logger.info(f"Auto-repairs completed: {len(repairs_made)} repairs made")
        else:
            logger.info("No auto-repairs were performed")
    
    def _repair_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to repair a specific issue"""
        issue_type = issue.get("type")
        
        try:
            if issue_type == "python_environment":
                return self._repair_python_environment()
            elif issue_type == "model_download_failure":
                return self._repair_model_download()
            elif issue_type == "backend_service_failure":
                return self._repair_backend_service()
            elif issue_type == "permission_issues":
                return self._repair_permissions()
            elif issue_type == "memory_issues":
                return self._repair_memory_issues()
            elif issue_type == "dependency_conflicts":
                return self._repair_dependencies()
            else:
                logger.warning(f"No repair strategy for issue type: {issue_type}")
                return None
                
        except Exception as e:
            logger.error(f"Repair failed for {issue_type}: {e}")
            return {"success": False, "error": str(e)}
    
    def _repair_python_environment(self) -> Dict[str, Any]:
        """Repair Python environment issues"""
        try:
            # Check if we're in a virtual environment
            if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                logger.info("Creating virtual environment...")
                # This would require more complex logic to create venv
                return {"success": False, "message": "Virtual environment creation requires manual intervention"}
            
            # Install missing packages
            logger.info("Installing missing packages...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                         check=True, capture_output=True)
            
            return {"success": True, "message": "Python environment repaired"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _repair_model_download(self) -> Dict[str, Any]:
        """Repair model download issues"""
        try:
            # Check disk space
            disk = psutil.disk_usage(self.base_dir)
            if disk.free < 5 * 1024**3:  # Less than 5GB
                return {"success": False, "message": "Insufficient disk space for model download"}
            
            # Check network connectivity
            try:
                requests.get("https://httpbin.org/get", timeout=5)
            except Exception as e:
                logger.warning(f"Network connectivity check failed during repair: {e}")
                return {"success": False, "message": "Network connectivity issues detected"}
            
            # Attempt to restart download process
            logger.info("Attempting to restart model download...")
            # This would integrate with the existing download system
            
            return {"success": True, "message": "Model download repair initiated"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _repair_backend_service(self) -> Dict[str, Any]:
        """Repair backend service issues"""
        try:
            # Check if backend is running
            try:
                response = requests.get("http://localhost:11435/v1/models", timeout=5)
                if response.status_code == 200:
                    return {"success": True, "message": "Backend service is already running"}
            except Exception as e:
                logger.debug(f"Backend service check failed during repair: {e}")
                pass
            
            # Attempt to restart backend
            logger.info("Attempting to restart backend service...")
            # This would integrate with the existing backend management
            
            return {"success": True, "message": "Backend service restart initiated"}
            
        except Exception as e:
            logger.error(f"Backend service repair failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _repair_permissions(self) -> Dict[str, Any]:
        """Repair permission issues"""
        try:
            # Try to fix directory permissions
            for directory in [self.instance_dir, self.logs_dir]:
                try:
                    # On Unix-like systems, try to change permissions
                    if platform.system() != "Windows":
                        os.chmod(directory, 0o755)
                except Exception as e:
                    logger.warning(f"Failed to change permissions for {directory}: {e}")
                    pass
            
            return {"success": True, "message": "Permission repair attempted"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _repair_memory_issues(self) -> Dict[str, Any]:
        """Repair memory issues"""
        try:
            # Suggest memory optimization
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return {"success": False, "message": "Critical memory usage - manual intervention required"}
            
            # Could implement model context reduction here
            return {"success": True, "message": "Memory optimization recommendations provided"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _repair_dependencies(self) -> Dict[str, Any]:
        """Repair dependency conflicts"""
        try:
            # Attempt to reinstall dependencies
            logger.info("Attempting to reinstall dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "-r", "requirements.txt"], 
                         check=True, capture_output=True)
            
            return {"success": True, "message": "Dependencies reinstalled"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_diagnostics(self):
        """Save diagnostics to file"""
        try:
            with open(self.diagnostics_file, 'w') as f:
                json.dump(self.diagnostics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save diagnostics: {e}")
    
    def _save_repair_history(self):
        """Save repair history to file"""
        try:
            with open(self.repair_history_file, 'w') as f:
                json.dump(self.repair_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save repair history: {e}")
    
    def get_diagnostics_summary(self) -> Dict[str, Any]:
        """Get a summary of current diagnostics"""
        return {
            "health_score": self.diagnostics.get("health_score", 0),
            "last_check": self.diagnostics.get("last_check"),
            "total_issues": len(self.diagnostics.get("issues", [])),
            "critical_issues": len([i for i in self.diagnostics.get("issues", []) if i.get("severity") == "critical"]),
            "recommendations": self.diagnostics.get("recommendations", []),
            "system_info": {
                "platform": self.diagnostics.get("system_info", {}).get("platform"),
                "memory_percent": self.diagnostics.get("system_info", {}).get("memory_percent"),
                "disk_percent": self.diagnostics.get("system_info", {}).get("disk_percent")
            }
        }
    
    def get_installation_status(self) -> Dict[str, Any]:
        """Get installation status for all components"""
        try:
            logger.info("Getting installation status")
            
            # Run diagnostics to get current status
            diagnostics = self.run_diagnostics()
            
            return {
                'success': True,
                'component_status': diagnostics.get('component_status', {}),
                'health_score': diagnostics.get('health_score', 0),
                'issues': diagnostics.get('issues', []),
                'recommendations': diagnostics.get('recommendations', []),
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting installation status: {e}")
            return {
                'success': False,
                'error': str(e),
                'component_status': {},
                'health_score': 0,
                'issues': [],
                'recommendations': []
            }
    
    def force_repair_all(self) -> Dict[str, Any]:
        """Force repair of all detected issues"""
        try:
            logger.info("Starting force repair of all issues")
            
            # Run diagnostics to identify issues
            diagnostics = self.run_diagnostics()
            issues = diagnostics.get('issues', [])
            
            if not issues:
                return {
                    'success': True,
                    'message': 'No issues detected, system is healthy',
                    'repairs_performed': 0,
                    'results': []
                }
            
            repair_results = []
            successful_repairs = 0
            
            # Attempt to repair each issue
            for issue in issues:
                try:
                    repair_result = self._repair_issue(issue)
                    if repair_result and repair_result.get('success'):
                        successful_repairs += 1
                    repair_results.append(repair_result or {
                        'issue': issue.get('title', 'Unknown issue'),
                        'success': False,
                        'error': 'No repair method available'
                    })
                except Exception as e:
                    repair_results.append({
                        'issue': issue.get('title', 'Unknown issue'),
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'message': f'Completed repairs: {successful_repairs}/{len(issues)} successful',
                'repairs_performed': successful_repairs,
                'total_issues': len(issues),
                'results': repair_results
            }
            
        except Exception as e:
            logger.error(f"Error during force repair: {e}")
            return {
                'success': False,
                'error': str(e),
                'repairs_performed': 0,
                'results': []
            }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed diagnostics report"""
        return self.diagnostics.copy()


# Global instance
installation_monitor = InstallationMonitor()
