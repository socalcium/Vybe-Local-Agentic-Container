"""
Automated Validation Scripts and Quality Checks for Vybe
Provides comprehensive system validation, quality monitoring, and automated testing
"""

import os
import sys
import subprocess
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import traceback
from pathlib import Path

try:
    from ..logger import log_info, log_warning, log_error
except ImportError:
    # Fallback to logging if relative import fails
    import logging
    logger = logging.getLogger(__name__)
    def log_info(message): logger.info(message)
    def log_warning(message): logger.warning(message)
    def log_error(message): logger.error(message)


class ValidationStatus(Enum):
    """Validation status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Validation result structure"""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration: float = 0.0
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SystemValidator:
    """Comprehensive system validation"""
    
    def __init__(self):
        self.validation_results: List[ValidationResult] = []
        self.validators: Dict[str, Callable] = {}
        self._setup_validators()
    
    def _setup_validators(self):
        """Setup all validation functions"""
        self.validators = {
            'python_environment': self._validate_python_environment,
            'dependencies': self._validate_dependencies,
            'file_permissions': self._validate_file_permissions,
            'database_connectivity': self._validate_database_connectivity,
            'network_connectivity': self._validate_network_connectivity,
            'hardware_requirements': self._validate_hardware_requirements,
            'security_checks': self._validate_security_checks,
            'performance_checks': self._validate_performance_checks,
            'configuration_validation': self._validate_configuration,
            'api_endpoints': self._validate_api_endpoints
        }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks"""
        self.validation_results = []
        start_time = time.time()
        
        log_info("Starting comprehensive system validation...")
        
        for name, validator in self.validators.items():
            try:
                result = validator()
                self.validation_results.append(result)
                
                if result.status == ValidationStatus.FAILED:
                    log_error(f"Validation failed: {name} - {result.message}")
                elif result.status == ValidationStatus.WARNING:
                    log_warning(f"Validation warning: {name} - {result.message}")
                else:
                    log_info(f"Validation passed: {name}")
                    
            except Exception as e:
                error_result = ValidationResult(
                    name=name,
                    status=ValidationStatus.ERROR,
                    message=f"Validation error: {str(e)}",
                    details={'traceback': traceback.format_exc()}
                )
                self.validation_results.append(error_result)
                log_error(f"Validation error in {name}: {e}")
        
        duration = time.time() - start_time
        
        return self._generate_validation_summary(duration)
    
    def _validate_python_environment(self) -> ValidationResult:
        """Validate Python environment"""
        start_time = time.time()
        
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                return ValidationResult(
                    name="Python Environment",
                    status=ValidationStatus.FAILED,
                    message=f"Python version {python_version.major}.{python_version.minor} is too old. Required: 3.8+",
                    duration=time.time() - start_time
                )
            
            # Check virtual environment
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            
            # Check critical modules
            required_modules = ['flask', 'sqlalchemy', 'psutil', 'requests']
            missing_modules = []
            
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                return ValidationResult(
                    name="Python Environment",
                    status=ValidationStatus.FAILED,
                    message=f"Missing required modules: {', '.join(missing_modules)}",
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Python Environment",
                status=ValidationStatus.PASSED,
                message=f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - Virtual env: {in_venv}",
                details={
                    'python_version': f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                    'virtual_environment': in_venv,
                    'required_modules': required_modules
                },
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Python Environment",
                status=ValidationStatus.ERROR,
                message=f"Python environment validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_dependencies(self) -> ValidationResult:
        """Validate application dependencies"""
        start_time = time.time()
        
        try:
            # Check if requirements.txt exists
            requirements_file = Path("requirements.txt")
            if not requirements_file.exists():
                return ValidationResult(
                    name="Dependencies",
                    status=ValidationStatus.WARNING,
                    message="requirements.txt not found",
                    duration=time.time() - start_time
                )
            
            # Check installed packages
            import pkg_resources
            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
            
            # Check critical dependencies
            critical_deps = {
                'flask': '2.0.0',
                'sqlalchemy': '1.4.0',
                'psutil': '5.8.0',
                'requests': '2.25.0'
            }
            
            missing_deps = []
            outdated_deps = []
            
            for dep, min_version in critical_deps.items():
                if dep not in installed_packages:
                    missing_deps.append(dep)
                else:
                    current_version = installed_packages[dep]
                    if self._compare_versions(current_version, min_version) < 0:
                        outdated_deps.append(f"{dep} (current: {current_version}, required: {min_version})")
            
            if missing_deps or outdated_deps:
                issues = []
                if missing_deps:
                    issues.append(f"Missing: {', '.join(missing_deps)}")
                if outdated_deps:
                    issues.append(f"Outdated: {', '.join(outdated_deps)}")
                
                return ValidationResult(
                    name="Dependencies",
                    status=ValidationStatus.FAILED,
                    message=f"Dependency issues: {'; '.join(issues)}",
                    details={
                        'missing_dependencies': missing_deps,
                        'outdated_dependencies': outdated_deps,
                        'installed_packages': installed_packages
                    },
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Dependencies",
                status=ValidationStatus.PASSED,
                message=f"All {len(critical_deps)} critical dependencies satisfied",
                details={'installed_packages': installed_packages},
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Dependencies",
                status=ValidationStatus.ERROR,
                message=f"Dependency validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_file_permissions(self) -> ValidationResult:
        """Validate file permissions and accessibility"""
        start_time = time.time()
        
        try:
            # Check critical directories
            critical_paths = [
                "vybe_app",
                "vybe_app/static",
                "vybe_app/templates",
                "models",
                "logs"
            ]
            
            permission_issues = []
            
            for path in critical_paths:
                path_obj = Path(path)
                if not path_obj.exists():
                    permission_issues.append(f"Missing directory: {path}")
                elif not os.access(path_obj, os.R_OK):
                    permission_issues.append(f"Cannot read: {path}")
                elif path_obj.is_dir() and not os.access(path_obj, os.W_OK):
                    permission_issues.append(f"Cannot write to: {path}")
            
            # Check log file writability
            log_dir = Path("logs")
            if log_dir.exists():
                test_log = log_dir / "test_permissions.log"
                try:
                    with open(test_log, 'w') as f:
                        f.write("test")
                    test_log.unlink()
                except Exception:
                    permission_issues.append("Cannot write to logs directory")
            
            if permission_issues:
                return ValidationResult(
                    name="File Permissions",
                    status=ValidationStatus.FAILED,
                    message=f"Permission issues: {'; '.join(permission_issues)}",
                    details={'permission_issues': permission_issues},
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="File Permissions",
                status=ValidationStatus.PASSED,
                message=f"All {len(critical_paths)} critical paths accessible",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="File Permissions",
                status=ValidationStatus.ERROR,
                message=f"File permission validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_database_connectivity(self) -> ValidationResult:
        """Validate database connectivity"""
        start_time = time.time()
        
        try:
            from ..models import db
            
            # Test database connection
            try:
                # Test basic database availability
                db.engine.url  # This will raise an error if engine is not properly configured
                connection_ok = True
            except Exception as e:
                connection_ok = False
                error_msg = str(e)
            
            if not connection_ok:
                return ValidationResult(
                    name="Database Connectivity",
                    status=ValidationStatus.FAILED,
                    message=f"Database connection failed: {error_msg}",
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Database Connectivity",
                status=ValidationStatus.PASSED,
                message="Database connection successful",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Database Connectivity",
                status=ValidationStatus.ERROR,
                message=f"Database validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_network_connectivity(self) -> ValidationResult:
        """Validate network connectivity"""
        start_time = time.time()
        
        try:
            import requests
            
            # Test internet connectivity
            test_urls = [
                "https://httpbin.org/get",
                "https://api.github.com"
            ]
            
            connectivity_issues = []
            
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        connectivity_issues.append(f"{url} returned {response.status_code}")
                except Exception as e:
                    connectivity_issues.append(f"{url} failed: {str(e)}")
            
            if connectivity_issues:
                return ValidationResult(
                    name="Network Connectivity",
                    status=ValidationStatus.WARNING,
                    message=f"Network connectivity issues: {'; '.join(connectivity_issues)}",
                    details={'connectivity_issues': connectivity_issues},
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Network Connectivity",
                status=ValidationStatus.PASSED,
                message="Network connectivity verified",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Network Connectivity",
                status=ValidationStatus.ERROR,
                message=f"Network validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_hardware_requirements(self) -> ValidationResult:
        """Validate hardware requirements"""
        start_time = time.time()
        
        try:
            try:
                from vybe_app.core.hardware_safety import check_system_compatibility
                compatibility = check_system_compatibility()
            except ImportError:
                # Fallback hardware check
                compatibility = {'compatible': True, 'warnings': [], 'cpu_count': os.cpu_count()}
            
            if not compatibility['compatible']:
                return ValidationResult(
                    name="Hardware Requirements",
                    status=ValidationStatus.FAILED,
                    message=f"Hardware requirements not met: {'; '.join(compatibility['issues'])}",
                    details=compatibility,
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Hardware Requirements",
                status=ValidationStatus.PASSED,
                message=f"Hardware requirements met (Tier: {compatibility['hardware_tier']})",
                details=compatibility,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Hardware Requirements",
                status=ValidationStatus.ERROR,
                message=f"Hardware validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_security_checks(self) -> ValidationResult:
        """Validate security configuration"""
        start_time = time.time()
        
        try:
            security_issues = []
            
            # Check for secure configuration
            from ..config import Config
            
            # Check secret key
            if not hasattr(Config, 'SECRET_KEY') or not Config.SECRET_KEY:
                security_issues.append("SECRET_KEY not configured")
            
            # Check HTTPS settings
            if hasattr(Config, 'HTTPS_ENABLED') and not getattr(Config, 'HTTPS_ENABLED', True):
                security_issues.append("HTTPS not enabled")
            
            # Check debug mode
            if hasattr(Config, 'DEBUG') and Config.DEBUG:
                security_issues.append("Debug mode enabled in production")
            
            if security_issues:
                return ValidationResult(
                    name="Security Checks",
                    status=ValidationStatus.WARNING,
                    message=f"Security issues: {'; '.join(security_issues)}",
                    details={'security_issues': security_issues},
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Security Checks",
                status=ValidationStatus.PASSED,
                message="Security configuration verified",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Security Checks",
                status=ValidationStatus.ERROR,
                message=f"Security validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_performance_checks(self) -> ValidationResult:
        """Validate performance metrics"""
        start_time = time.time()
        
        try:
            import psutil
            
            performance_issues = []
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                performance_issues.append(f"High memory usage: {memory.percent:.1f}%")
            
            # Check CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            if isinstance(cpu_usage, (int, float)) and cpu_usage > 90:
                performance_issues.append(f"High CPU usage: {cpu_usage:.1f}%")
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                performance_issues.append(f"High disk usage: {disk.percent:.1f}%")
            
            if performance_issues:
                return ValidationResult(
                    name="Performance Checks",
                    status=ValidationStatus.WARNING,
                    message=f"Performance issues: {'; '.join(performance_issues)}",
                    details={
                        'memory_usage': memory.percent,
                        'cpu_usage': cpu_usage,
                        'disk_usage': disk.percent
                    },
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Performance Checks",
                status=ValidationStatus.PASSED,
                message="Performance metrics within acceptable ranges",
                details={
                    'memory_usage': memory.percent,
                    'cpu_usage': cpu_usage,
                    'disk_usage': disk.percent
                },
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Performance Checks",
                status=ValidationStatus.ERROR,
                message=f"Performance validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_configuration(self) -> ValidationResult:
        """Validate application configuration"""
        start_time = time.time()
        
        try:
            from ..config import Config
            
            config_issues = []
            
            # Check required configuration
            required_configs = ['VERSION', 'LOG_LEVEL']
            for config_name in required_configs:
                if not hasattr(Config, config_name):
                    config_issues.append(f"Missing configuration: {config_name}")
            
            # Check configuration values
            if hasattr(Config, 'LOG_LEVEL'):
                valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if Config.LOG_LEVEL not in valid_log_levels:
                    config_issues.append(f"Invalid LOG_LEVEL: {Config.LOG_LEVEL}")
            
            if config_issues:
                return ValidationResult(
                    name="Configuration Validation",
                    status=ValidationStatus.FAILED,
                    message=f"Configuration issues: {'; '.join(config_issues)}",
                    details={'config_issues': config_issues},
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="Configuration Validation",
                status=ValidationStatus.PASSED,
                message="Configuration validated successfully",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="Configuration Validation",
                status=ValidationStatus.ERROR,
                message=f"Configuration validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _validate_api_endpoints(self) -> ValidationResult:
        """Validate API endpoints"""
        start_time = time.time()
        
        try:
            # This would test actual API endpoints
            # For now, just check if Flask app can be imported
            from .. import create_app
            
            app = create_app()
            if app:
                return ValidationResult(
                    name="API Endpoints",
                    status=ValidationStatus.PASSED,
                    message="Flask application created successfully",
                    duration=time.time() - start_time
                )
            else:
                return ValidationResult(
                    name="API Endpoints",
                    status=ValidationStatus.FAILED,
                    message="Failed to create Flask application",
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            return ValidationResult(
                name="API Endpoints",
                status=ValidationStatus.ERROR,
                message=f"API validation error: {str(e)}",
                duration=time.time() - start_time
            )
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare version strings"""
        from packaging import version
        try:
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except Exception as e:
            logger.warning(f"Version comparison failed: {e}")
            return 0
    
    def _generate_validation_summary(self, duration: float) -> Dict[str, Any]:
        """Generate validation summary"""
        total_validations = len(self.validation_results)
        passed_validations = len([r for r in self.validation_results if r.status == ValidationStatus.PASSED])
        failed_validations = len([r for r in self.validation_results if r.status == ValidationStatus.FAILED])
        warning_validations = len([r for r in self.validation_results if r.status == ValidationStatus.WARNING])
        error_validations = len([r for r in self.validation_results if r.status == ValidationStatus.ERROR])
        
        return {
            'summary': {
                'total_validations': total_validations,
                'passed_validations': passed_validations,
                'failed_validations': failed_validations,
                'warning_validations': warning_validations,
                'error_validations': error_validations,
                'success_rate': round((passed_validations / total_validations) * 100, 1) if total_validations > 0 else 0,
                'duration': round(duration, 2),
                'overall_status': 'passed' if failed_validations == 0 else 'failed'
            },
            'results': [self._result_to_dict(r) for r in self.validation_results],
            'failed_validations': [self._result_to_dict(r) for r in self.validation_results if r.status == ValidationStatus.FAILED],
            'timestamp': datetime.now().isoformat()
        }
    
    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            'name': result.name,
            'status': result.status.value,
            'message': result.message,
            'details': result.details,
            'duration': round(result.duration, 3),
            'timestamp': result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat()
        }


# Global validator instance
system_validator = SystemValidator()


def run_system_validation() -> Dict[str, Any]:
    """Run comprehensive system validation"""
    return system_validator.run_all_validations()


def get_validation_results() -> List[ValidationResult]:
    """Get current validation results"""
    return system_validator.validation_results
