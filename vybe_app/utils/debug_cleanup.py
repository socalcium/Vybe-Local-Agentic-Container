#!/usr/bin/env python3
"""
Debug Code Cleanup Utilities for Vybe AI Desktop Application
Identifies and helps remove debug print statements and other debug code from production files
"""

import re
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DebugCodeIssue:
    """Represents a debug code issue found in a file"""
    file_path: str
    line_number: int
    line_content: str
    issue_type: str
    severity: str
    description: str


class DebugCodeCleaner:
    """Utility to identify and clean up debug code in production files"""
    
    # Patterns to identify debug code
    DEBUG_PATTERNS = {
        'print_statement': {
            'pattern': r'^\s*print\s*\(',
            'description': 'Debug print statement',
            'severity': 'medium'
        },
        'debug_log': {
            'pattern': r'logger\.debug\s*\(',
            'description': 'Debug logging statement',
            'severity': 'low'
        },
        'todo_comment': {
            'pattern': r'#\s*TODO|#\s*FIXME|#\s*HACK',
            'description': 'TODO/FIXME comment',
            'severity': 'medium'
        },
        'debug_variable': {
            'pattern': r'\bdebug\w*\s*=',
            'description': 'Debug variable assignment',
            'severity': 'medium'
        },
        'breakpoint': {
            'pattern': r'\bbreakpoint\s*\(\)',
            'description': 'Breakpoint statement',
            'severity': 'high'
        },
        'pdb_import': {
            'pattern': r'import\s+pdb|from\s+pdb\s+import',
            'description': 'PDB debugger import',
            'severity': 'high'
        },
        'ipdb_import': {
            'pattern': r'import\s+ipdb|from\s+ipdb\s+import',
            'description': 'IPDB debugger import',
            'severity': 'high'
        },
        'debug_assert': {
            'pattern': r'assert\s+False',
            'description': 'Debug assertion',
            'severity': 'high'
        },
        'hardcoded_debug': {
            'pattern': r'debug\s*=\s*True',
            'description': 'Hardcoded debug flag',
            'severity': 'medium'
        },
        'console_log': {
            'pattern': r'console\.log\s*\(',
            'description': 'JavaScript console.log statement',
            'severity': 'medium'
        },
        'alert_statement': {
            'pattern': r'alert\s*\(',
            'description': 'JavaScript alert statement',
            'severity': 'medium'
        }
    }
    
    # Files to exclude from scanning
    EXCLUDE_PATTERNS = [
        r'\.git/',
        r'__pycache__/',
        r'\.pyc$',
        r'\.pyo$',
        r'\.pyd$',
        r'\.so$',
        r'\.dll$',
        r'\.exe$',
        r'\.log$',
        r'\.tmp$',
        r'\.bak$',
        r'\.swp$',
        r'\.swo$',
        r'node_modules/',
        r'\.venv/',
        r'venv/',
        r'env/',
        r'\.env/',
        r'target/',
        r'build/',
        r'dist/',
        r'\.idea/',
        r'\.vscode/',
        r'\.DS_Store$',
        r'Thumbs\.db$'
    ]
    
    # File extensions to scan
    SCAN_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.md': 'markdown',
        '.txt': 'text'
    }
    
    def __init__(self, root_path: Optional[str] = None):
        """Initialize the debug code cleaner"""
        if root_path is None:
            self.root_path = Path.cwd()
        else:
            self.root_path = Path(root_path)
        self.issues: List[DebugCodeIssue] = []
        self.stats = {
            'files_scanned': 0,
            'issues_found': 0,
            'by_severity': {'high': 0, 'medium': 0, 'low': 0},
            'by_type': {}
        }
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned"""
        # Check if file is in excluded patterns
        file_str = str(file_path)
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, file_str, re.IGNORECASE):
                return False
        
        # Check if file has a supported extension
        return file_path.suffix.lower() in self.SCAN_EXTENSIONS
    
    def scan_file(self, file_path: Path) -> List[DebugCodeIssue]:
        """Scan a single file for debug code issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for issue_type, config in self.DEBUG_PATTERNS.items():
                    if re.search(config['pattern'], line, re.IGNORECASE):
                        issue = DebugCodeIssue(
                            file_path=str(file_path),
                            line_number=line_num,
                            line_content=line.rstrip(),
                            issue_type=issue_type,
                            severity=config['severity'],
                            description=config['description']
                        )
                        issues.append(issue)
                        
        except Exception as e:
            logger.warning(f"Error scanning file {file_path}: {e}")
        
        return issues
    
    def scan_directory(self, directory: Optional[Path] = None) -> List[DebugCodeIssue]:
        """Scan a directory recursively for debug code issues"""
        if directory is None:
            directory = self.root_path
        
        all_issues = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and self.should_scan_file(file_path):
                self.stats['files_scanned'] += 1
                file_issues = self.scan_file(file_path)
                all_issues.extend(file_issues)
                
                # Update statistics
                self.stats['issues_found'] += len(file_issues)
                for issue in file_issues:
                    self.stats['by_severity'][issue.severity] += 1
                    self.stats['by_type'][issue.issue_type] = self.stats['by_type'].get(issue.issue_type, 0) + 1
        
        self.issues = all_issues
        return all_issues
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of debug code issues"""
        if not self.issues:
            return "No debug code issues found."
        
        report_lines = [
            "🔍 DEBUG CODE CLEANUP REPORT",
            "=" * 50,
            f"Files Scanned: {self.stats['files_scanned']}",
            f"Total Issues Found: {self.stats['issues_found']}",
            "",
            "📊 ISSUES BY SEVERITY:",
        ]
        
        for severity in ['high', 'medium', 'low']:
            count = self.stats['by_severity'][severity]
            if count > 0:
                report_lines.append(f"  {severity.upper()}: {count}")
        
        report_lines.extend([
            "",
            "📋 ISSUES BY TYPE:",
        ])
        
        for issue_type, count in sorted(self.stats['by_type'].items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {issue_type}: {count}")
        
        report_lines.extend([
            "",
            "🚨 HIGH PRIORITY ISSUES:",
        ])
        
        high_priority = [issue for issue in self.issues if issue.severity == 'high']
        for issue in high_priority:
            report_lines.append(f"  {issue.file_path}:{issue.line_number} - {issue.description}")
            report_lines.append(f"    {issue.line_content}")
        
        report_lines.extend([
            "",
            "⚠️  MEDIUM PRIORITY ISSUES:",
        ])
        
        medium_priority = [issue for issue in self.issues if issue.severity == 'medium']
        for issue in medium_priority[:10]:  # Show first 10
            report_lines.append(f"  {issue.file_path}:{issue.line_number} - {issue.description}")
        
        if len(medium_priority) > 10:
            report_lines.append(f"  ... and {len(medium_priority) - 10} more")
        
        return "\n".join(report_lines)
    
    def create_cleanup_script(self, output_file: str = "debug_cleanup_script.py") -> str:
        """Create a Python script to automatically clean up debug code"""
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            "Auto-generated debug code cleanup script",
            "Generated by DebugCodeCleaner",
            '"""',
            "",
            "import re",
            "import os",
            "from pathlib import Path",
            "",
            "def cleanup_debug_code():",
            '    """Remove debug code from files"""',
            "    changes_made = 0",
            "",
            "    # Debug code patterns to remove",
            "    patterns_to_remove = [",
        ]
        
        for issue_type, config in self.DEBUG_PATTERNS.items():
            if config['severity'] in ['high', 'medium']:
                script_lines.append(f"        (r'{config['pattern']}', '{config['description']}'),")
        
        script_lines.extend([
            "    ]",
            "",
            "    # Files to process",
            "    files_to_process = [",
        ])
        
        # Add unique files with issues
        unique_files = list(set(issue.file_path for issue in self.issues))
        for file_path in unique_files:
            script_lines.append(f"        '{file_path}',")
        
        script_lines.extend([
            "    ]",
            "",
            "    for file_path in files_to_process:",
            "        if not os.path.exists(file_path):",
            "            continue",
            "",
            "        try:",
            "            with open(file_path, 'r', encoding='utf-8') as f:",
            "                content = f.read()",
            "",
            "            original_content = content",
            "",
            "            # Remove debug code",
            "            for pattern, description in patterns_to_remove:",
            "                content = re.sub(pattern, '', content, flags=re.MULTILINE)",
            "",
            "            # Write back if changes were made",
            "            if content != original_content:",
            "                with open(file_path, 'w', encoding='utf-8') as f:",
            "                    f.write(content)",
            "                changes_made += 1",
            "                print(f'Cleaned {file_path}')",
            "",
            "        except Exception as e:",
            "            print(f'Error processing {file_path}: {e}')",
            "",
            "    print(f'Total files cleaned: {changes_made}')",
            "",
            "if __name__ == '__main__':",
            "    cleanup_debug_code()",
        ])
        
        script_content = "\n".join(script_lines)
        
        # Write the script to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return output_file
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations for cleaning up debug code"""
        recommendations = [
            "🔧 DEBUG CODE CLEANUP RECOMMENDATIONS:",
            "",
        ]
        
        if self.stats['by_severity']['high'] > 0:
            recommendations.extend([
                "🚨 HIGH PRIORITY:",
                "  - Remove all breakpoint() statements immediately",
                "  - Remove PDB/IPDB imports and usage",
                "  - Remove debug assertions (assert False)",
                "",
            ])
        
        if self.stats['by_severity']['medium'] > 0:
            recommendations.extend([
                "⚠️  MEDIUM PRIORITY:",
                "  - Replace print() statements with proper logging",
                "  - Remove TODO/FIXME comments or create tickets",
                "  - Remove hardcoded debug flags",
                "  - Replace console.log() with proper error handling",
                "",
            ])
        
        if self.stats['by_severity']['low'] > 0:
            recommendations.extend([
                "📝 LOW PRIORITY:",
                "  - Review debug logging statements",
                "  - Consider removing verbose debug output",
                "",
            ])
        
        recommendations.extend([
            "📋 GENERAL RECOMMENDATIONS:",
            "  - Use environment variables for debug flags",
            "  - Implement proper logging levels (DEBUG, INFO, WARNING, ERROR)",
            "  - Use feature flags for debug functionality",
            "  - Add debug code detection to CI/CD pipeline",
            "  - Regular code reviews to prevent debug code accumulation",
        ])
        
        return recommendations


def scan_project_for_debug_code(project_path: Optional[str] = None) -> DebugCodeCleaner:
    """Convenience function to scan a project for debug code"""
    if project_path is None:
        cleaner = DebugCodeCleaner()
    else:
        cleaner = DebugCodeCleaner(project_path)
    cleaner.scan_directory()
    return cleaner


def main():
    """Main function to run debug code cleanup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan for debug code in project")
    parser.add_argument("--path", default=".", help="Project path to scan")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--script", action="store_true", help="Generate cleanup script")
    parser.add_argument("--recommendations", action="store_true", help="Show recommendations")
    
    args = parser.parse_args()
    
    print("🔍 Scanning for debug code...")
    cleaner = scan_project_for_debug_code(args.path)
    
    if args.report:
        print(cleaner.generate_report())
    
    if args.script:
        script_file = cleaner.create_cleanup_script()
        print(f"📝 Cleanup script generated: {script_file}")
    
    if args.recommendations:
        for rec in cleaner.get_recommendations():
            print(rec)
    
    if not any([args.report, args.script, args.recommendations]):
        print(cleaner.generate_report())


if __name__ == "__main__":
    main()
