"""
Linter Manager
Comprehensive linting and code quality management for Vybe AI Desktop
"""

import os
import re
import ast
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class LintSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class LintIssue:
    file_path: str
    line_number: int
    column: int
    message: str
    severity: LintSeverity
    rule_id: str
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False

class LinterManager:
    """Comprehensive linter manager for Vybe AI Desktop"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
        self.issues = []
        self.fixed_issues = []
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load linter configuration"""
        try:
            config_path = os.path.join(self.project_root, 'pyrightconfig.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load linter config: {e}, using defaults")
        
        return {
            "include": ["vybe_app"],
            "exclude": ["**/node_modules", "**/__pycache__", "**/*.pyc"],
            "ignore": [],
            "defineConstant": {},
            "typeCheckingMode": "basic",
            "useLibraryCodeForTypes": True,
            "reportMissingImports": True,
            "reportMissingTypeStubs": False,
            "reportUnusedImport": True,
            "reportUnusedClass": True,
            "reportUnusedFunction": True,
            "reportUnusedVariable": True,
            "reportDuplicateImport": True,
            "reportOptionalSubscript": True,
            "reportOptionalMemberAccess": True,
            "reportOptionalCall": True,
            "reportOptionalIterable": True,
            "reportOptionalContextManager": True,
            "reportOptionalOperand": True,
            "reportUntypedFunctionDecorator": True,
            "reportUntypedClassDecorator": True,
            "reportUntypedBaseClass": True,
            "reportUntypedNamedTuple": True,
            "reportPrivateUsage": True,
            "reportConstantRedefinition": True,
            "reportIncompatibleMethodOverride": True,
            "reportIncompatibleVariableOverride": True,
            "reportInconsistentConstructor": True,
            "reportOverlappingOverloads": True,
            "reportMissingSuperCall": True,
            "reportUninitializedInstanceVariable": True,
            "reportInvalidStringEscapeSequence": True,
            "reportUnknownParameterType": True,
            "reportUnknownArgumentType": True,
            "reportUnknownLambdaType": True,
            "reportUnknownVariableType": True,
            "reportUnknownMemberType": True,
            "reportMissingTypeArgument": True,
            "reportInvalidTypeVarUse": True,
            "reportCallInDefaultInitializer": True,
            "reportUnnecessaryIsInstance": True,
            "reportUnnecessaryCast": True,
            "reportUnnecessaryComparison": True,
            "reportAssertAlwaysTrue": True,
            "reportSelfClsParameterName": True,
            "reportImplicitStringConcatenation": True,
            "reportUndefinedVariable": True,
            "reportUnboundVariable": True,
            "reportInvalidName": True,
            "reportMissingParameterType": True,
            "reportMissingReturnType": True,
            "reportMissingTypeStub": True,
            "reportUnusedExpression": True,
            "reportUnusedCallResult": True,
            "reportUnusedCoroutine": True,
            "reportUnusedAwaitable": True,
            "reportUnusedException": True,
            "reportUnusedImport": True,
            "reportUnusedVariable": True,
            "reportUnusedClass": True,
            "reportUnusedFunction": True,
            "reportUnusedModule": True,
            "reportUnusedTypeAlias": True,
            "reportUnusedTypeVar": True,
            "reportUnusedProtocol": True,
            "reportUnusedTypedDict": True,
            "reportUnusedLiteral": True,
            "reportUnusedEnum": True,
            "reportUnusedEnumMember": True,
            "reportUnusedClassVar": True,
            "reportUnusedInstanceVar": True,
            "reportUnusedProperty": True,
            "reportUnusedMethod": True,
            "reportUnusedStaticMethod": True,
            "reportUnusedClassMethod": True,
            "reportUnusedAbstractMethod": True,
            "reportUnusedAbstractProperty": True,
            "reportUnusedAbstractClass": True,
            "reportUnusedAbstractModule": True,
            "reportUnusedAbstractTypeAlias": True,
            "reportUnusedAbstractTypeVar": True,
            "reportUnusedAbstractProtocol": True,
            "reportUnusedAbstractTypedDict": True,
            "reportUnusedAbstractLiteral": True,
            "reportUnusedAbstractEnum": True,
            "reportUnusedAbstractEnumMember": True,
            "reportUnusedAbstractClassVar": True,
            "reportUnusedAbstractInstanceVar": True,
            "reportUnusedAbstractProperty": True,
            "reportUnusedAbstractMethod": True,
            "reportUnusedAbstractStaticMethod": True,
            "reportUnusedAbstractClassMethod": True
        }
    
    def should_skip_file(self, file_path: str) -> bool:
        """Check if a file should be skipped during linting"""
        try:
            # Skip files in excluded patterns
            for pattern in self.config.get('exclude', []):
                if pattern.replace('**/', '') in file_path or pattern.replace('*', '') in file_path:
                    return True
            
            # Skip binary files and common exclusions
            skip_patterns = [
                '__pycache__',
                '.pyc',
                '.pyo',
                '.pyd',
                '.so',
                '.dll',
                'node_modules',
                '.git',
                '.venv',
                'venv',
                'env',
                '.env'
            ]
            
            for pattern in skip_patterns:
                if pattern in file_path:
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if file should be skipped: {e}")
            return False
    
    def run_full_lint(self) -> List[LintIssue]:
        """Run comprehensive linting across the entire codebase"""
        logger.info("Starting comprehensive linting...")
        
        self.issues = []
        
        # Run different types of linting
        self.run_pyright_lint()
        self.run_flake8_lint()
        self.run_black_check()
        self.run_isort_check()
        self.run_bandit_security_check()
        self.run_custom_checks()
        
        logger.info(f"Linting complete. Found {len(self.issues)} issues.")
        return self.issues
    
    def run_pyright_lint(self):
        """Run Pyright type checking and linting"""
        try:
            result = subprocess.run(
                ['pyright', '--outputformat=json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout:
                try:
                    pyright_output = json.loads(result.stdout)
                    for diagnostic in pyright_output.get('diagnostics', []):
                        issue = LintIssue(
                            file_path=diagnostic['file'],
                            line_number=diagnostic['range']['start']['line'] + 1,
                            column=diagnostic['range']['start']['character'] + 1,
                            message=diagnostic['message'],
                            severity=LintSeverity(diagnostic['category']),
                            rule_id=diagnostic.get('rule', 'pyright'),
                            auto_fixable=False
                        )
                        self.issues.append(issue)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Pyright JSON output")
                    
        except FileNotFoundError:
            logger.warning("Pyright not found. Install with: pip install pyright")
        except Exception as e:
            logger.error(f"Error running Pyright: {e}")
    
    def run_flake8_lint(self):
        """Run Flake8 linting"""
        try:
            result = subprocess.run(
                ['flake8', '--format=json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout:
                try:
                    flake8_output = json.loads(result.stdout)
                    for file_path, file_issues in flake8_output.items():
                        for issue_data in file_issues:
                            issue = LintIssue(
                                file_path=file_path,
                                line_number=issue_data['line_number'],
                                column=issue_data['column_number'],
                                message=issue_data['text'],
                                severity=LintSeverity.ERROR if issue_data['code'].startswith('E') else LintSeverity.WARNING,
                                rule_id=issue_data['code'],
                                auto_fixable=self.is_flake8_fixable(issue_data['code'])
                            )
                            self.issues.append(issue)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Flake8 JSON output")
                    
        except FileNotFoundError:
            logger.warning("Flake8 not found. Install with: pip install flake8")
        except Exception as e:
            logger.error(f"Error running Flake8: {e}")
    
    def run_black_check(self):
        """Check code formatting with Black"""
        try:
            result = subprocess.run(
                ['black', '--check', '--diff', '--quiet'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                # Parse Black output to extract file information
                for line in result.stdout.split('\n'):
                    if line.startswith('would reformat'):
                        file_path = line.split('would reformat ')[1]
                        issue = LintIssue(
                            file_path=file_path,
                            line_number=1,
                            column=1,
                            message="Code formatting issues detected by Black",
                            severity=LintSeverity.WARNING,
                            rule_id="black",
                            auto_fixable=True,
                            fix_suggestion="Run 'black .' to auto-format"
                        )
                        self.issues.append(issue)
                        
        except FileNotFoundError:
            logger.warning("Black not found. Install with: pip install black")
        except Exception as e:
            logger.error(f"Error running Black: {e}")
    
    def run_isort_check(self):
        """Check import sorting with isort"""
        try:
            result = subprocess.run(
                ['isort', '--check-only', '--diff'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                # Parse isort output
                for line in result.stdout.split('\n'):
                    if line.startswith('ERROR: '):
                        file_path = line.split('ERROR: ')[1].split(' Imports are incorrectly sorted')[0]
                        issue = LintIssue(
                            file_path=file_path,
                            line_number=1,
                            column=1,
                            message="Import sorting issues detected by isort",
                            severity=LintSeverity.WARNING,
                            rule_id="isort",
                            auto_fixable=True,
                            fix_suggestion="Run 'isort .' to auto-sort imports"
                        )
                        self.issues.append(issue)
                        
        except FileNotFoundError:
            logger.warning("isort not found. Install with: pip install isort")
        except Exception as e:
            logger.error(f"Error running isort: {e}")
    
    def run_bandit_security_check(self):
        """Run security checks with Bandit"""
        try:
            result = subprocess.run(
                ['bandit', '-r', 'vybe_app', '-f', 'json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout:
                try:
                    bandit_output = json.loads(result.stdout)
                    for issue_data in bandit_output.get('results', []):
                        issue = LintIssue(
                            file_path=issue_data['filename'],
                            line_number=issue_data['line_number'],
                            column=1,
                            message=issue_data['issue_text'],
                            severity=LintSeverity.ERROR if issue_data['issue_severity'] == 'HIGH' else LintSeverity.WARNING,
                            rule_id=f"bandit_{issue_data['test_id']}",
                            auto_fixable=False
                        )
                        self.issues.append(issue)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Bandit JSON output")
                    
        except FileNotFoundError:
            logger.warning("Bandit not found. Install with: pip install bandit")
        except Exception as e:
            logger.error(f"Error running Bandit: {e}")
    
    def run_custom_checks(self):
        """Run custom linting checks"""
        self.check_bare_except_clauses()
        self.check_missing_docstrings()
        self.check_unused_imports()
        self.check_long_functions()
        self.check_complex_functions()
        self.check_duplicate_code()
        self.check_hardcoded_values()
        self.check_error_handling()
    
    def check_bare_except_clauses(self):
        """Check for bare except clauses"""
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find bare except clauses
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(r'except\s*:', line):
                        issue = LintIssue(
                            file_path=file_path,
                            line_number=i,
                            column=line.find('except') + 1,
                            message="Bare except clause detected. Use specific exception types.",
                            severity=LintSeverity.WARNING,
                            rule_id="bare_except",
                            auto_fixable=False,
                            fix_suggestion="Replace with 'except Exception as e:' or specific exception type"
                        )
                        self.issues.append(issue)
                        
            except Exception as e:
                logger.error(f"Error checking file {file_path}: {e}")
    
    def check_missing_docstrings(self):
        """Check for missing docstrings in functions and classes"""
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not ast.get_docstring(node):
                            issue = LintIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset + 1,
                                message=f"Missing docstring for {node.__class__.__name__.lower()} '{node.name}'",
                                severity=LintSeverity.INFO,
                                rule_id="missing_docstring",
                                auto_fixable=False
                            )
                            self.issues.append(issue)
                            
            except Exception as e:
                logger.error(f"Error checking docstrings in {file_path}: {e}")
    
    def check_unused_imports(self):
        """Check for unused imports"""
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                # Get all imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append((alias.name, node.lineno, node.col_offset))
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            imports.append((alias.name, node.lineno, node.col_offset))
                
                # Check if imports are used
                for import_name, lineno, col_offset in imports:
                    if not self.is_import_used(tree, import_name):
                        issue = LintIssue(
                            file_path=file_path,
                            line_number=lineno,
                            column=col_offset + 1,
                            message=f"Unused import '{import_name}'",
                            severity=LintSeverity.WARNING,
                            rule_id="unused_import",
                            auto_fixable=True,
                            fix_suggestion=f"Remove unused import '{import_name}'"
                        )
                        self.issues.append(issue)
                        
            except Exception as e:
                logger.error(f"Error checking unused imports in {file_path}: {e}")
    
    def check_long_functions(self):
        """Check for functions that are too long"""
        max_lines = 50
        
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if hasattr(node, 'end_lineno') and node.end_lineno:
                            function_length = node.end_lineno - node.lineno
                            if function_length > max_lines:
                                issue = LintIssue(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    column=node.col_offset + 1,
                                    message=f"Function '{node.name}' is too long ({function_length} lines, max {max_lines})",
                                    severity=LintSeverity.WARNING,
                                    rule_id="long_function",
                                    auto_fixable=False,
                                    fix_suggestion="Consider breaking the function into smaller functions"
                                )
                                self.issues.append(issue)
                                
            except Exception as e:
                logger.error(f"Error checking function length in {file_path}: {e}")
    
    def check_complex_functions(self):
        """Check for functions with high cyclomatic complexity"""
        max_complexity = 10
        
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self.calculate_complexity(node)
                        if complexity > max_complexity:
                            issue = LintIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset + 1,
                                message=f"Function '{node.name}' has high complexity ({complexity}, max {max_complexity})",
                                severity=LintSeverity.WARNING,
                                rule_id="high_complexity",
                                auto_fixable=False,
                                fix_suggestion="Consider simplifying the function logic"
                            )
                            self.issues.append(issue)
                            
            except Exception as e:
                logger.error(f"Error checking complexity in {file_path}: {e}")
    
    def check_duplicate_code(self):
        """Check for duplicate code patterns"""
        try:
            # This is a simplified version. In practice, you'd use tools like jscpd or similar
            # For now, we'll implement basic duplicate function detection
            function_signatures = {}
            
            for file_path in Path(self.project_root).rglob("*.py"):
                if self.should_skip_file(str(file_path)):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Create a simple signature based on function structure
                            func_lines = content.split('\n')[node.lineno-1:node.end_lineno]
                            func_body = '\n'.join(func_lines)
                            func_hash = hash(func_body.strip())
                            
                            if func_hash in function_signatures:
                                # Found potential duplicate
                                original_file, original_line = function_signatures[func_hash]
                                issue = LintIssue(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    column=node.col_offset,
                                    message=f"Potential duplicate function found. Similar to {original_file}:{original_line}",
                                    severity=LintSeverity.WARNING,
                                    rule_id="duplicate_code",
                                    auto_fixable=False
                                )
                                self.issues.append(issue)
                            else:
                                function_signatures[func_hash] = (str(file_path), node.lineno)
                                
                except (SyntaxError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not parse {file_path} for duplicate code check: {e}")
                    
        except Exception as e:
            logger.error(f"Error in duplicate code check: {e}")
    
    def check_hardcoded_values(self):
        """Check for hardcoded values that should be constants"""
        hardcoded_patterns = [
            (r'\b\d{4,}\b', "Large number should be a named constant"),
            (r'"[^"]{50,}"', "Long string should be a constant"),
            (r"'[^']{50,}'", "Long string should be a constant"),
        ]
        
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    for pattern, message in hardcoded_patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            issue = LintIssue(
                                file_path=file_path,
                                line_number=i,
                                column=match.start() + 1,
                                message=message,
                                severity=LintSeverity.INFO,
                                rule_id="hardcoded_value",
                                auto_fixable=False
                            )
                            self.issues.append(issue)
                            
            except Exception as e:
                logger.error(f"Error checking hardcoded values in {file_path}: {e}")
    
    def check_error_handling(self):
        """Check for proper error handling patterns"""
        for file_path in self.get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Check for print statements in production code
                    if 'print(' in line and 'debug' not in line.lower():
                        issue = LintIssue(
                            file_path=file_path,
                            line_number=i,
                            column=line.find('print(') + 1,
                            message="Print statement detected. Use proper logging instead.",
                            severity=LintSeverity.WARNING,
                            rule_id="print_statement",
                            auto_fixable=False,
                            fix_suggestion="Replace with logger.info() or logger.debug()"
                        )
                        self.issues.append(issue)
                        
            except Exception as e:
                logger.error(f"Error checking error handling in {file_path}: {e}")
    
    def auto_fix_issues(self) -> List[LintIssue]:
        """Automatically fix issues that can be fixed"""
        logger.info("Starting auto-fix process...")
        
        self.fixed_issues = []
        
        # Group issues by file
        issues_by_file = {}
        for issue in self.issues:
            if issue.auto_fixable:
                if issue.file_path not in issues_by_file:
                    issues_by_file[issue.file_path] = []
                issues_by_file[issue.file_path].append(issue)
        
        # Fix issues in each file
        for file_path, file_issues in issues_by_file.items():
            self.fix_issues_in_file(file_path, file_issues)
        
        logger.info(f"Auto-fix complete. Fixed {len(self.fixed_issues)} issues.")
        return self.fixed_issues
    
    def fix_issues_in_file(self, file_path: str, issues: List[LintIssue]):
        """Fix issues in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            modified = False
            
            # Sort issues by line number in reverse order to avoid line number shifts
            sorted_issues = sorted(issues, key=lambda x: x.line_number, reverse=True)
            
            for issue in sorted_issues:
                if issue.rule_id == "unused_import":
                    # Remove unused import
                    if issue.line_number <= len(lines):
                        lines.pop(issue.line_number - 1)
                        modified = True
                        self.fixed_issues.append(issue)
                
                elif issue.rule_id == "bare_except":
                    # Replace bare except with specific exception
                    if issue.line_number <= len(lines):
                        line = lines[issue.line_number - 1]
                        new_line = re.sub(r'except\s*:', 'except Exception as e:', line)
                        if new_line != line:
                            lines[issue.line_number - 1] = new_line
                            modified = True
                            self.fixed_issues.append(issue)
            
            # Write back to file if modified
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                    
        except Exception as e:
            logger.error(f"Error fixing issues in {file_path}: {e}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive linting report"""
        report = {
            'summary': {
                'total_issues': len(self.issues),
                'errors': len([i for i in self.issues if i.severity == LintSeverity.ERROR]),
                'warnings': len([i for i in self.issues if i.severity == LintSeverity.WARNING]),
                'info': len([i for i in self.issues if i.severity == LintSeverity.INFO]),
                'auto_fixable': len([i for i in self.issues if i.auto_fixable]),
                'fixed': len(self.fixed_issues)
            },
            'issues_by_severity': {
                'error': [i for i in self.issues if i.severity == LintSeverity.ERROR],
                'warning': [i for i in self.issues if i.severity == LintSeverity.WARNING],
                'info': [i for i in self.issues if i.severity == LintSeverity.INFO]
            },
            'issues_by_rule': {},
            'issues_by_file': {},
            'recommendations': []
        }
        
        # Group by rule
        for issue in self.issues:
            if issue.rule_id not in report['issues_by_rule']:
                report['issues_by_rule'][issue.rule_id] = []
            report['issues_by_rule'][issue.rule_id].append(issue)
        
        # Group by file
        for issue in self.issues:
            if issue.file_path not in report['issues_by_file']:
                report['issues_by_file'][issue.file_path] = []
            report['issues_by_file'][issue.file_path].append(issue)
        
        # Generate recommendations
        if report['summary']['errors'] > 0:
            report['recommendations'].append("Fix all errors before proceeding")
        
        if report['summary']['auto_fixable'] > 0:
            report['recommendations'].append(f"Run auto-fix to resolve {report['summary']['auto_fixable']} issues")
        
        if len(report['issues_by_rule'].get('bare_except', [])) > 0:
            report['recommendations'].append("Replace bare except clauses with specific exception types")
        
        if len(report['issues_by_rule'].get('unused_import', [])) > 0:
            report['recommendations'].append("Remove unused imports to improve code cleanliness")
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: str = "lint_report.json"):
        """Save the linting report to a file"""
        try:
            # Convert dataclasses to dictionaries for JSON serialization
            serializable_report = self.serialize_report(report)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_report, f, indent=2)
            
            logger.info(f"Lint report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving lint report: {e}")
    
    def serialize_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Convert report to JSON-serializable format"""
        serializable = {}
        
        for key, value in report.items():
            if key in ['issues_by_severity', 'issues_by_rule', 'issues_by_file']:
                serializable[key] = {}
                for sub_key, issues in value.items():
                    serializable[key][sub_key] = [
                        {
                            'file_path': issue.file_path,
                            'line_number': issue.line_number,
                            'column': issue.column,
                            'message': issue.message,
                            'severity': issue.severity.value,
                            'rule_id': issue.rule_id,
                            'fix_suggestion': issue.fix_suggestion,
                            'auto_fixable': issue.auto_fixable
                        }
                        for issue in issues
                    ]
            else:
                serializable[key] = value
        
        return serializable
    
    # Helper methods
    def get_python_files(self) -> List[str]:
        """Get all Python files in the project"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'node_modules', '.git', '.venv']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def is_flake8_fixable(self, code: str) -> bool:
        """Check if a Flake8 error code is auto-fixable"""
        fixable_codes = ['E201', 'E202', 'E203', 'E211', 'E221', 'E222', 'E223', 'E224', 'E225', 'E226', 'E227', 'E228', 'E231', 'E241', 'E242', 'E251', 'E261', 'E262', 'E265', 'E266', 'E271', 'E272', 'E273', 'E274', 'E275', 'E301', 'E302', 'E303', 'E304', 'E305', 'E306', 'E401', 'E402', 'E501', 'E502', 'E711', 'E712', 'E713', 'E714', 'E721', 'E722', 'E731', 'E741', 'E742', 'E743', 'E901', 'E902', 'E999', 'W191', 'W291', 'W292', 'W293', 'W391', 'W503', 'W504', 'W505', 'W601', 'W602', 'W603', 'W604', 'W605', 'W606']
        return code in fixable_codes
    
    def is_import_used(self, tree: ast.AST, import_name: str) -> bool:
        """Check if an import is used in the AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == import_name:
                return True
        return False
    
    def calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.AsyncWith):
                complexity += 1
        
        return complexity

# Global linter manager instance
linter_manager = LinterManager()

def run_linting():
    """Run comprehensive linting and return results"""
    return linter_manager.run_full_lint()

def auto_fix_linting():
    """Run auto-fix for linting issues"""
    return linter_manager.auto_fix_issues()

def generate_lint_report():
    """Generate and save a comprehensive linting report"""
    issues = linter_manager.run_full_lint()
    report = linter_manager.generate_report()
    linter_manager.save_report(report)
    return report

if __name__ == "__main__":
    # Run linting when script is executed directly
    report = generate_lint_report()
    print(f"Linting complete. Found {report['summary']['total_issues']} issues.")
    print(f"Fixed {report['summary']['fixed']} issues automatically.")
