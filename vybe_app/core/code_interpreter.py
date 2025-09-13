"""
Secure Code Interpreter System
Provides a sandboxed Python code execution environment using Jupyter kernel.
"""

import os
import sys
import time
import json
import tempfile
import subprocess
import logging
import threading
import ast
import shutil
import uuid
import secrets
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CodeExecutionResult:
    """Result of code execution"""
    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    plots: List[str] = field(default_factory=list)  # Base64 encoded plot images
    files_created: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    variables_changed: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "plots": self.plots,
            "files_created": self.files_created,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "variables_changed": self.variables_changed
        }

@dataclass
class SecuritySettings:
    """Security configuration for code execution"""
    allow_file_io: bool = True
    allow_network: bool = False
    allow_subprocess: bool = False
    max_execution_time: float = 30.0
    max_memory_mb: int = 512
    allowed_imports: List[str] = field(default_factory=lambda: [
        "numpy", "pandas", "matplotlib", "seaborn", "plotly", "scipy",
        "sklearn", "requests", "json", "csv", "sqlite3", "math", "random",
        "datetime", "os", "sys", "pathlib", "itertools", "collections",
        "functools", "re", "string", "base64", "hashlib", "urllib",
        "xml", "html", "io", "typing", "dataclasses", "enum"
    ])
    blocked_imports: List[str] = field(default_factory=lambda: [
        "subprocess", "multiprocessing", "threading", "asyncio",
        "socket", "ftplib", "smtplib", "telnetlib", "paramiko"
    ])
    workspace_dir: Optional[str] = None

class SecureCodeInterpreter:
    """Secure Python code interpreter using subprocess with safety measures"""
    
    def __init__(self, security_settings: Optional[SecuritySettings] = None):
        self.security_settings = security_settings or SecuritySettings()
        self.workspace_dir = self._setup_workspace()
        self.session_id = f"code_session_{int(time.time())}"
        self._active_process: Optional[subprocess.Popen] = None
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging for the code interpreter"""
        self.logger = logging.getLogger(f"code_interpreter.{self.session_id}")
        
    def _setup_workspace(self) -> str:
        """Setup isolated workspace directory with unique random name"""
        if self.security_settings.workspace_dir:
            base_workspace = Path(self.security_settings.workspace_dir)
        else:
            # Create in the main workspace directory
            base_workspace = Path("workspace") / "code_interpreter"
        
        # Create unique, randomly named subdirectory for this session
        unique_id = secrets.token_hex(16)  # 32 character hex string
        workspace = base_workspace / f"session_{unique_id}"
        
        # Ensure the unique workspace doesn't already exist (extremely unlikely)
        while workspace.exists():
            unique_id = secrets.token_hex(16)
            workspace = base_workspace / f"session_{unique_id}"
        
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (workspace / "outputs").mkdir(exist_ok=True)
        (workspace / "plots").mkdir(exist_ok=True)
        (workspace / "data").mkdir(exist_ok=True)
        (workspace / "temp").mkdir(exist_ok=True)  # For temporary files
        
        logger.info(f"Created unique workspace: {workspace}")
        return str(workspace)
    
    def execute_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> CodeExecutionResult:
        """Execute Python code in a secure environment"""
        start_time = time.time()
        
        try:
            # Validate the code
            security_check = self._validate_code_security(code)
            if not security_check["allowed"]:
                return CodeExecutionResult(
                    success=False,
                    error=f"Security violation: {security_check['reason']}",
                    execution_time=time.time() - start_time
                )
            
            # Prepare execution environment
            execution_script = self._prepare_execution_script(code, context)
            
            # Execute the code
            result = self._execute_in_subprocess(execution_script)
            
            # Process results
            result.execution_time = time.time() - start_time
            result.files_created = self._scan_created_files()
            result.plots = self._collect_plot_outputs()
            
            self.logger.info(f"Code execution completed: success={result.success}, time={result.execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Code execution failed: {e}")
            return CodeExecutionResult(
                success=False,
                error=f"Execution failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _validate_code_security(self, code: str) -> Dict[str, Any]:
        """Validate code against security policies using AST analysis"""
        
        try:
            # Parse code into AST
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "allowed": False,
                "reason": f"Syntax error in code: {str(e)}"
            }
        
        # Define dangerous AST node types and patterns
        dangerous_nodes = []
        
        # Walk through the AST and check for dangerous patterns
        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_names = []
                if isinstance(node, ast.Import):
                    module_names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_names.append(node.module)
                
                for module_name in module_names:
                    if module_name in self.security_settings.blocked_imports:
                        return {
                            "allowed": False,
                            "reason": f"Blocked import detected: {module_name}"
                        }
                    
                    # Check for dangerous system modules
                    dangerous_modules = [
                        'subprocess', 'multiprocessing', 'threading', 'asyncio',
                        'socket', 'ftplib', 'smtplib', 'telnetlib', 'paramiko',
                        'ctypes', 'cffi', 'imp', 'importlib'
                    ]
                    if module_name in dangerous_modules:
                        return {
                            "allowed": False,
                            "reason": f"Dangerous module import detected: {module_name}"
                        }
            
            # Check for dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    dangerous_functions = [
                        'eval', 'exec', 'compile', '__import__',
                        'globals', 'locals', 'vars', 'dir'
                    ]
                    if func_name in dangerous_functions:
                        return {
                            "allowed": False,
                            "reason": f"Dangerous function call detected: {func_name}"
                        }
                    
                    # Check file operations if not allowed
                    if not self.security_settings.allow_file_io:
                        file_functions = ['open', 'file']
                        if func_name in file_functions:
                            return {
                                "allowed": False,
                                "reason": f"File I/O not allowed: {func_name}"
                            }
                
                elif isinstance(node.func, ast.Attribute):
                    # Check for os.system, os.popen, etc.
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == 'os':
                            dangerous_os_methods = [
                                'system', 'popen', 'spawn', 'exec', 'fork', 
                                'kill', 'wait', 'environ', 'getenv', 'putenv'
                            ]
                            if node.func.attr in dangerous_os_methods:
                                return {
                                    "allowed": False,
                                    "reason": f"Dangerous os method detected: os.{node.func.attr}"
                                }
                        
                        # Check for subprocess calls
                        elif node.func.value.id == 'subprocess':
                            return {
                                "allowed": False,
                                "reason": "subprocess module usage detected"
                            }
            
            # Check for attribute access to dangerous objects
            elif isinstance(node, ast.Attribute):
                dangerous_attributes = [
                    '__builtins__', '__import__', '__globals__', '__locals__'
                ]
                if node.attr in dangerous_attributes:
                    return {
                        "allowed": False,
                        "reason": f"Access to dangerous attribute detected: {node.attr}"
                    }
            
            # Check for dangerous name access
            elif isinstance(node, ast.Name):
                dangerous_names = [
                    '__builtins__', '__import__', 'builtins'
                ]
                if node.id in dangerous_names:
                    return {
                        "allowed": False,
                        "reason": f"Access to dangerous name detected: {node.id}"
                    }
        
        return {"allowed": True, "reason": "Code passed AST security validation"}
    
    def _prepare_execution_script(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Prepare the execution script with safety wrappers"""
        
        script_lines = [
            "import sys",
            "import os",
            "import json",
            "import traceback",
            "import matplotlib",
            "matplotlib.use('Agg')  # Use non-interactive backend",
            "import matplotlib.pyplot as plt",
            "",
            "# Set working directory",
            f"os.chdir(r'{self.workspace_dir}')",
            "",
            "# Initialize output capture",
            "import io",
            "from contextlib import redirect_stdout, redirect_stderr",
            "",
            "stdout_buffer = io.StringIO()",
            "stderr_buffer = io.StringIO()",
            "",
            "execution_result = {",
            "    'success': False,",
            "    'output': '',",
            "    'error': '',",
            "    'stdout': '',",
            "    'stderr': '',",
            "    'variables_changed': {}",
            "}",
            "",
            "try:",
            "    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):",
        ]
        
        # Add context variables if provided
        if context:
            script_lines.append("        # Context variables")
            for key, value in context.items():
                if isinstance(value, str):
                    script_lines.append(f"        {key} = {repr(value)}")
                else:
                    script_lines.append(f"        {key} = {value}")
            script_lines.append("")
        
        # Add the actual code with proper indentation
        script_lines.append("        # User code")
        for line in code.split('\n'):
            script_lines.append(f"        {line}")
        
        script_lines.extend([
            "",
            "    execution_result['success'] = True",
            "    execution_result['output'] = 'Code executed successfully'",
            "",
            "except Exception as e:",
            "    execution_result['error'] = str(e)",
            "    execution_result['output'] = traceback.format_exc()",
            "",
            "finally:",
            "    execution_result['stdout'] = stdout_buffer.getvalue()",
            "    execution_result['stderr'] = stderr_buffer.getvalue()",
            "    ",
            "    # Save plots if any",
            "    plt.savefig('plots/output.png', dpi=150, bbox_inches='tight')",
            "    plt.close('all')",
            "    ",
            "    # Output result as JSON",
            "    print('__EXECUTION_RESULT__')",
            "    print(json.dumps(execution_result))",
            "    print('__END_EXECUTION_RESULT__')",
        ])
        
        return '\n'.join(script_lines)
    
    def _execute_in_subprocess(self, script: str) -> CodeExecutionResult:
        """Execute script in a subprocess with timeouts and limits"""
        
        # Create temporary script file
        script_file = Path(self.workspace_dir) / f"execution_script_{int(time.time())}.py"
        
        try:
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script)
            
            # Execute with timeout
            self._active_process = subprocess.Popen(
                [sys.executable, str(script_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.workspace_dir,
                env=self._get_restricted_env()
            )
            
            try:
                stdout, stderr = self._active_process.communicate(
                    timeout=self.security_settings.max_execution_time
                )
                exit_code = self._active_process.returncode
                
                # Parse the execution result
                result = self._parse_execution_output(stdout, stderr, exit_code)
                
                return result
                
            except subprocess.TimeoutExpired:
                self._active_process.kill()
                return CodeExecutionResult(
                    success=False,
                    error="Code execution timed out",
                    exit_code=-1
                )
                
        finally:
            # Cleanup
            if script_file.exists():
                script_file.unlink()
            self._active_process = None
    
    def _get_restricted_env(self) -> Dict[str, str]:
        """Get environment variables for restricted execution - ENHANCED SECURITY"""
        # Start with minimal environment for security
        env = {
            'PATH': os.environ.get('PATH', ''),
            'PYTHONPATH': '',
            'PYTHONHOME': '',
            'PYTHONEXECUTABLE': sys.executable,
            'HOME': str(Path.home()),
            'TEMP': str(Path(self.workspace_dir) / 'temp'),
            'TMP': str(Path(self.workspace_dir) / 'temp'),
        }
        
        # Limit network access
        if not self.security_settings.allow_network:
            env.update({
                'http_proxy': 'http://127.0.0.1:1',
                'https_proxy': 'http://127.0.0.1:1',
                'HTTP_PROXY': 'http://127.0.0.1:1',
                'HTTPS_PROXY': 'http://127.0.0.1:1',
                'no_proxy': '*',
                'NO_PROXY': '*'
            })
        
        # Remove potentially dangerous environment variables
        dangerous_vars = [
            'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP',
            'PYTHONUSERBASE', 'PYTHONEXECUTABLE',
            'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH',
            'LD_PRELOAD', 'DYLD_INSERT_LIBRARIES'
        ]
        
        for var in dangerous_vars:
            if var in env:
                del env[var]
        
        return env
    
    def _parse_execution_output(self, stdout: str, stderr: str, exit_code: int) -> CodeExecutionResult:
        """Parse the output from code execution"""
        
        result = CodeExecutionResult(
            success=exit_code == 0,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code
        )
        
        # Extract execution result JSON
        try:
            if '__EXECUTION_RESULT__' in stdout:
                start_marker = stdout.find('__EXECUTION_RESULT__') + len('__EXECUTION_RESULT__\n')
                end_marker = stdout.find('__END_EXECUTION_RESULT__')
                
                if start_marker != -1 and end_marker != -1:
                    json_result = stdout[start_marker:end_marker].strip()
                    parsed_result = json.loads(json_result)
                    
                    result.success = parsed_result.get('success', False)
                    result.output = parsed_result.get('output', '')
                    result.error = parsed_result.get('error', '')
                    result.variables_changed = parsed_result.get('variables_changed', {})
                    
        except Exception as e:
            self.logger.warning(f"Failed to parse execution result: {e}")
            result.error = stderr or str(e)
            result.output = stdout
        
        return result
    
    def _scan_created_files(self) -> List[str]:
        """Scan for files created during execution"""
        created_files = []
        
        try:
            workspace_path = Path(self.workspace_dir)
            for file_path in workspace_path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    relative_path = file_path.relative_to(workspace_path)
                    created_files.append(str(relative_path))
                    
        except Exception as e:
            self.logger.warning(f"Failed to scan created files: {e}")
        
        return created_files
    
    def _collect_plot_outputs(self) -> List[str]:
        """Collect generated plots as base64 encoded images"""
        plots = []
        
        try:
            plots_dir = Path(self.workspace_dir) / "plots"
            for plot_file in plots_dir.glob("*.png"):
                with open(plot_file, "rb") as f:
                    import base64
                    plot_data = base64.b64encode(f.read()).decode('utf-8')
                    plots.append(plot_data)
                    
        except Exception as e:
            self.logger.warning(f"Failed to collect plots: {e}")
        
        return plots
    
    def stop_execution(self):
        """Stop any running code execution"""
        if self._active_process:
            try:
                self._active_process.terminate()
                self._active_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._active_process.kill()
            except Exception as e:
                self.logger.error(f"Failed to stop execution: {e}")
            finally:
                self._active_process = None
    
    def cleanup(self):
        """Cleanup interpreter resources and workspace"""
        self.stop_execution()
        
        # Cleanup unique workspace directory completely
        try:
            workspace_path = Path(self.workspace_dir)
            if workspace_path.exists():
                logger.info(f"Cleaning up workspace: {workspace_path}")
                
                # Force cleanup - handle read-only files and permissions
                def handle_remove_readonly(func, path, exc):
                    """Handle removal of read-only files"""
                    import stat
                    if os.path.exists(path):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                
                # Recursively delete the unique workspace directory
                shutil.rmtree(workspace_path, onerror=handle_remove_readonly)
                
                logger.info(f"Successfully cleaned up workspace: {workspace_path}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup workspace {self.workspace_dir}: {e}")
            # Try alternative cleanup method
            try:
                import subprocess
                if os.name == 'nt':  # Windows
                    subprocess.run(['rmdir', '/s', '/q', str(workspace_path)], 
                                 shell=True, check=False)
                else:  # Unix/Linux
                    subprocess.run(['rm', '-rf', str(workspace_path)], 
                                 check=False)
            except Exception as e2:
                logger.error(f"Alternative cleanup also failed: {e2}")
    
    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        try:
            self.cleanup()
        except Exception:
            pass  # Avoid exceptions in destructor
    
    def get_workspace_files(self) -> List[Dict[str, Any]]:
        """Get list of files in the workspace"""
        files = []
        
        try:
            workspace_path = Path(self.workspace_dir)
            for file_path in workspace_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(workspace_path)
                    stat = file_path.stat()
                    
                    files.append({
                        "name": file_path.name,
                        "path": str(relative_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": file_path.suffix.lower()
                    })
                    
        except Exception as e:
            self.logger.error(f"Failed to list workspace files: {e}")
        
        return files
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a file in the workspace"""
        try:
            full_path = Path(self.workspace_dir) / file_path
            
            # Security check: ensure file is within workspace
            if not str(full_path.resolve()).startswith(str(Path(self.workspace_dir).resolve())):
                raise ValueError("File access outside workspace not allowed")
            
            if full_path.exists() and full_path.is_file():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
        
        return None

# Global interpreter instances
_interpreters: Dict[str, SecureCodeInterpreter] = {}

def get_code_interpreter(session_id: Optional[str] = None, 
                        security_settings: Optional[SecuritySettings] = None) -> SecureCodeInterpreter:
    """Get or create a code interpreter instance"""
    global _interpreters
    
    if session_id is None:
        session_id = f"default_{int(time.time())}"
    
    if session_id not in _interpreters:
        _interpreters[session_id] = SecureCodeInterpreter(security_settings)
    
    return _interpreters[session_id]

def cleanup_interpreter(session_id: str):
    """Cleanup and remove interpreter instance"""
    global _interpreters
    
    if session_id in _interpreters:
        _interpreters[session_id].cleanup()
        del _interpreters[session_id]

def cleanup_all_interpreters():
    """Cleanup all interpreter instances"""
    global _interpreters
    
    for session_id in list(_interpreters.keys()):
        cleanup_interpreter(session_id)
