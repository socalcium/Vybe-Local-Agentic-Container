#!/usr/bin/env python3
"""
Enhanced Cache Optimization Utilities for Vybe AI Desktop Application
Identifies API endpoints and functions that could benefit from caching with
intelligent scheduling and incremental analysis capabilities
"""

import re
import os
import ast
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheOpportunity:
    """Represents a caching opportunity found in the codebase"""
    file_path: str
    line_number: int
    function_name: str
    opportunity_type: str
    description: str
    priority: str
    estimated_impact: str
    suggested_ttl: int
    cache_name: str
    first_detected: datetime = field(default_factory=datetime.utcnow)
    last_analyzed: datetime = field(default_factory=datetime.utcnow)
    analysis_count: int = 0


@dataclass
class FileChangeTracker:
    """Track file changes for incremental analysis"""
    file_path: str
    last_modified: float
    content_hash: str
    last_analyzed: datetime
    cache_opportunities_count: int = 0


class IntelligentCacheOptimizer:
    """Enhanced cache optimizer with intelligent scheduling and incremental analysis"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.file_trackers: Dict[str, FileChangeTracker] = {}
        self.cache_opportunities: Dict[str, CacheOpportunity] = {}
        self.analysis_lock = threading.Lock()
        
        # Scheduling configuration
        self.auto_analysis_enabled = True
        self.analysis_interval_seconds = 300  # 5 minutes
        self.incremental_analysis_enabled = True
        self.last_full_analysis = None
        self.analysis_thread = None
        self.stop_analysis = threading.Event()
        
        # Performance metrics
        self.analysis_stats = {
            'total_runs': 0,
            'incremental_runs': 0,
            'full_runs': 0,
            'files_analyzed': 0,
            'opportunities_found': 0,
            'avg_analysis_time': 0.0,
            'last_analysis_duration': 0.0
        }
    
    def start_scheduled_analysis(self):
        """Start the scheduled analysis thread"""
        if self.analysis_thread and self.analysis_thread.is_alive():
            logger.warning("Analysis thread already running")
            return
        
        self.stop_analysis.clear()
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        logger.info(f"Started intelligent cache analysis with {self.analysis_interval_seconds}s interval")
    
    def stop_scheduled_analysis(self):
        """Stop the scheduled analysis thread"""
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.stop_analysis.set()
            self.analysis_thread.join(timeout=10)
            logger.info("Stopped intelligent cache analysis")
    
    def _analysis_loop(self):
        """Main analysis loop for scheduled execution"""
        while not self.stop_analysis.is_set():
            try:
                start_time = time.time()
                
                if self.incremental_analysis_enabled and self._has_file_changes():
                    self._run_incremental_analysis()
                elif self._should_run_full_analysis():
                    self._run_full_analysis()
                
                # Update performance metrics
                duration = time.time() - start_time
                self._update_analysis_stats(duration)
                
            except Exception as e:
                logger.error(f"Error in cache analysis loop: {e}")
            
            # Wait for next analysis cycle
            self.stop_analysis.wait(self.analysis_interval_seconds)
    
    def _has_file_changes(self) -> bool:
        """Check if any tracked files have changed"""
        for file_path in self._get_python_files():
            if self._file_has_changed(file_path):
                return True
        return False
    
    def _file_has_changed(self, file_path: Path) -> bool:
        """Check if a specific file has changed since last analysis"""
        try:
            current_mtime = file_path.stat().st_mtime
            file_key = str(file_path)
            
            if file_key not in self.file_trackers:
                return True  # New file
            
            tracker = self.file_trackers[file_key]
            return current_mtime > tracker.last_modified
            
        except (OSError, IOError):
            return False
    
    def _should_run_full_analysis(self) -> bool:
        """Determine if a full analysis should be run"""
        if not self.last_full_analysis:
            return True
        
        # Run full analysis every 24 hours
        time_since_full = datetime.utcnow() - self.last_full_analysis
        return time_since_full > timedelta(hours=24)
    
    def _run_incremental_analysis(self):
        """Run incremental analysis on changed files only"""
        with self.analysis_lock:
            changed_files = []
            
            for file_path in self._get_python_files():
                if self._file_has_changed(file_path):
                    changed_files.append(file_path)
                    self._update_file_tracker(file_path)
            
            if changed_files:
                logger.info(f"Running incremental cache analysis on {len(changed_files)} changed files")
                for file_path in changed_files:
                    self._analyze_file_for_caching(file_path)
                
                self.analysis_stats['incremental_runs'] += 1
                self.analysis_stats['files_analyzed'] += len(changed_files)
    
    def _run_full_analysis(self):
        """Run full analysis on all files"""
        with self.analysis_lock:
            logger.info("Running full cache analysis")
            python_files = list(self._get_python_files())
            
            for file_path in python_files:
                self._analyze_file_for_caching(file_path)
                self._update_file_tracker(file_path)
            
            self.last_full_analysis = datetime.utcnow()
            self.analysis_stats['full_runs'] += 1
            self.analysis_stats['files_analyzed'] += len(python_files)
    
    def _update_file_tracker(self, file_path: Path):
        """Update file tracker with current state"""
        try:
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            
            file_key = str(file_path)
            self.file_trackers[file_key] = FileChangeTracker(
                file_path=file_key,
                last_modified=file_stat.st_mtime,
                content_hash=content_hash,
                last_analyzed=datetime.utcnow()
            )
            
        except (OSError, IOError) as e:
            logger.warning(f"Could not update tracker for {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ""
    
    def _update_analysis_stats(self, duration: float):
        """Update performance statistics"""
        self.analysis_stats['total_runs'] += 1
        self.analysis_stats['last_analysis_duration'] = duration
        
        # Update rolling average
        current_avg = self.analysis_stats['avg_analysis_time']
        total_runs = self.analysis_stats['total_runs']
        
        self.analysis_stats['avg_analysis_time'] = (
            (current_avg * (total_runs - 1) + duration) / total_runs
        )
    
    def get_analysis_metrics(self) -> Dict[str, Any]:
        """Get comprehensive analysis performance metrics"""
        with self.analysis_lock:
            return {
                **self.analysis_stats,
                'tracked_files': len(self.file_trackers),
                'total_opportunities': len(self.cache_opportunities),
                'last_full_analysis': self.last_full_analysis.isoformat() if self.last_full_analysis else None,
                'auto_analysis_enabled': self.auto_analysis_enabled,
                'incremental_enabled': self.incremental_analysis_enabled,
                'analysis_interval_seconds': self.analysis_interval_seconds
            }
    
    def _get_python_files(self):
        """Get all Python files in the project"""
        for file_path in self.project_root.rglob("*.py"):
            if not self._should_skip_file(file_path):
                yield file_path
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis"""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            'venv',
            '.env',
            'migrations',
            'test_',
            '_test.py'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _analyze_file_for_caching(self, file_path: Path):
        """Analyze a single file for caching opportunities"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple pattern-based analysis for now
            opportunities = self._find_cache_patterns(content, file_path)
            
            for opportunity in opportunities:
                # Store opportunity with unique key
                key = f"{opportunity.file_path}:{opportunity.line_number}:{opportunity.function_name}"
                if key in self.cache_opportunities:
                    self.cache_opportunities[key].analysis_count += 1
                    self.cache_opportunities[key].last_analyzed = datetime.utcnow()
                else:
                    self.cache_opportunities[key] = opportunity
                    self.analysis_stats['opportunities_found'] += 1
                    
        except (OSError, IOError, UnicodeDecodeError) as e:
            logger.warning(f"Could not analyze file {file_path}: {e}")
    
    def _find_cache_patterns(self, content: str, file_path: Path) -> List[CacheOpportunity]:
        """Find caching opportunities in file content"""
        opportunities = []
        lines = content.split('\n')
        
        # Database query patterns
        db_patterns = [
            r'\.query\.all\(\)',
            r'\.query\.first\(\)',
            r'\.query\.filter\(',
            r'\.query\.filter_by\(',
            r'\.query\.get\(',
            r'\.query\.count\(\)'
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in db_patterns:
                if re.search(pattern, line):
                    opportunities.append(CacheOpportunity(
                        file_path=str(file_path),
                        line_number=line_num,
                        function_name=self._extract_function_name(lines, line_num),
                        opportunity_type='database_query',
                        description=f'Database query on line {line_num}',
                        priority='medium',
                        estimated_impact='medium',
                        suggested_ttl=300,  # 5 minutes
                        cache_name=f'db_cache_{line_num}'
                    ))
        
        return opportunities
    
    def _extract_function_name(self, lines: List[str], line_num: int) -> str:
        """Extract the function name containing the given line"""
        for i in range(line_num - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('def '):
                match = re.match(r'def\s+(\w+)', line)
                if match:
                    return match.group(1)
        return 'unknown_function'


class CacheOptimizer(IntelligentCacheOptimizer):
    """Legacy compatibility class - extends IntelligentCacheOptimizer"""
    
    # Patterns that indicate caching opportunities
    CACHE_PATTERNS = {
        'database_query': [
            r'\.query\.all\(\)',
            r'\.query\.first\(\)',
            r'\.query\.filter\(\)',
            r'\.query\.filter_by\(\)',
            r'\.query\.get\(\)',
            r'\.query\.count\(\)',
            r'\.query\.paginate\(\)'
        ],
        'file_operation': [
            r'open\([^)]*\)',
            r'Path\([^)]*\)\.read_text\(\)',
            r'Path\([^)]*\)\.write_text\(\)',
            r'Path\([^)]*\)\.exists\(\)',
            r'os\.path\.exists\([^)]*\)',
            r'os\.listdir\([^)]*\)',
            r'glob\.glob\([^)]*\)'
        ],
        'api_endpoint': [
            r'@.*\.route\([^)]*\)',
            r'def [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\):',
            r'return jsonify\([^)]*\)',
            r'return render_template\([^)]*\)'
        ],
        'expensive_operation': [
            r'requests\.get\([^)]*\)',
            r'requests\.post\([^)]*\)',
            r'subprocess\.run\([^)]*\)',
            r'subprocess\.Popen\([^)]*\)',
            r'hashlib\.sha256\([^)]*\)',
            r'hashlib\.md5\([^)]*\)',
            r'json\.loads\([^)]*\)',
            r'json\.dumps\([^)]*\)'
        ]
    }
    
    # File types to scan
    SCAN_EXTENSIONS = {'.py', '.js', '.html', '.css'}
    
    # Directories to exclude
    EXCLUDE_DIRS = {
        '__pycache__', '.git', '.vscode', 'node_modules', 
        'venv', 'env', '.pytest_cache', 'build', 'dist'
    }
    
    def __init__(self, root_path: Optional[str] = None):
        super().__init__(root_path or ".")
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.opportunities: List[CacheOpportunity] = []
        self.stats = {
            'files_scanned': 0,
            'opportunities_found': 0,
            'by_type': defaultdict(int),
            'by_priority': defaultdict(int)
        }
    
    def scan_codebase(self) -> List[CacheOpportunity]:
        """Scan the entire codebase for caching opportunities"""
        logger.info(f"Scanning codebase at {self.root_path}")
        
        for file_path in self._get_files_to_scan():
            try:
                self._scan_file(file_path)
                self.stats['files_scanned'] += 1
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        logger.info(f"Scan complete. Found {len(self.opportunities)} caching opportunities")
        return self.opportunities
    
    def _get_files_to_scan(self) -> List[Path]:
        """Get all files to scan"""
        files = []
        for root, dirs, filenames in os.walk(self.root_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for filename in filenames:
                if Path(filename).suffix in self.SCAN_EXTENSIONS:
                    files.append(Path(root) / filename)
        
        return files
    
    def _scan_file(self, file_path: Path):
        """Scan a single file for caching opportunities"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Scan for different types of opportunities
            self._scan_database_queries(file_path, lines)
            self._scan_file_operations(file_path, lines)
            self._scan_api_endpoints(file_path, lines)
            self._scan_expensive_operations(file_path, lines)
            
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
    
    def _scan_database_queries(self, file_path: Path, lines: List[str]):
        """Scan for database queries that could be cached"""
        for i, line in enumerate(lines, 1):
            for pattern in self.CACHE_PATTERNS['database_query']:
                if re.search(pattern, line):
                    opportunity = CacheOpportunity(
                        file_path=str(file_path),
                        line_number=i,
                        function_name=self._extract_function_name(lines, i),
                        opportunity_type='database_query',
                        description=f"Database query: {line.strip()}",
                        priority='high',
                        estimated_impact='high',
                        suggested_ttl=300,  # 5 minutes
                        cache_name='model_data'
                    )
                    self.opportunities.append(opportunity)
                    self.stats['opportunities_found'] += 1
                    self.stats['by_type']['database_query'] += 1
                    self.stats['by_priority']['high'] += 1
                    break
    
    def _scan_file_operations(self, file_path: Path, lines: List[str]):
        """Scan for file operations that could be cached"""
        for i, line in enumerate(lines, 1):
            for pattern in self.CACHE_PATTERNS['file_operation']:
                if re.search(pattern, line):
                    opportunity = CacheOpportunity(
                        file_path=str(file_path),
                        line_number=i,
                        function_name=self._extract_function_name(lines, i),
                        opportunity_type='file_operation',
                        description=f"File operation: {line.strip()}",
                        priority='medium',
                        estimated_impact='medium',
                        suggested_ttl=600,  # 10 minutes
                        cache_name='file_data'
                    )
                    self.opportunities.append(opportunity)
                    self.stats['opportunities_found'] += 1
                    self.stats['by_type']['file_operation'] += 1
                    self.stats['by_priority']['medium'] += 1
                    break
    
    def _scan_api_endpoints(self, file_path: Path, lines: List[str]):
        """Scan for API endpoints that could be cached"""
        current_function = None
        
        for i, line in enumerate(lines, 1):
            # Check for route decorators
            if re.search(r'@.*\.route\([^)]*\)', line):
                # Look for function definition on next few lines
                for j in range(i, min(i + 5, len(lines))):
                    func_match = re.search(r'def ([a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):', lines[j])
                    if func_match:
                        current_function = func_match.group(1)
                        break
                
                # Check if this endpoint returns data that could be cached
                if current_function:
                    # Look for jsonify or render_template in the function
                    for j in range(i, len(lines)):
                        if re.search(r'def [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\):', lines[j]):
                            break  # New function, stop looking
                        
                        if re.search(r'return jsonify\([^)]*\)', lines[j]) or \
                           re.search(r'return render_template\([^)]*\)', lines[j]):
                            opportunity = CacheOpportunity(
                                file_path=str(file_path),
                                line_number=i,
                                function_name=current_function,
                                opportunity_type='api_endpoint',
                                description=f"API endpoint: {current_function}",
                                priority='high',
                                estimated_impact='high',
                                suggested_ttl=180,  # 3 minutes
                                cache_name='api_responses'
                            )
                            self.opportunities.append(opportunity)
                            self.stats['opportunities_found'] += 1
                            self.stats['by_type']['api_endpoint'] += 1
                            self.stats['by_priority']['high'] += 1
                            break
    
    def _scan_expensive_operations(self, file_path: Path, lines: List[str]):
        """Scan for expensive operations that could be cached"""
        for i, line in enumerate(lines, 1):
            for pattern in self.CACHE_PATTERNS['expensive_operation']:
                if re.search(pattern, line):
                    opportunity = CacheOpportunity(
                        file_path=str(file_path),
                        line_number=i,
                        function_name=self._extract_function_name(lines, i),
                        opportunity_type='expensive_operation',
                        description=f"Expensive operation: {line.strip()}",
                        priority='medium',
                        estimated_impact='medium',
                        suggested_ttl=900,  # 15 minutes
                        cache_name='system_data'
                    )
                    self.opportunities.append(opportunity)
                    self.stats['opportunities_found'] += 1
                    self.stats['by_type']['expensive_operation'] += 1
                    self.stats['by_priority']['medium'] += 1
                    break
    
    def _extract_function_name(self, lines: List[str], line_number: int) -> str:
        """Extract the function name for a given line"""
        # Look backwards for function definition
        for i in range(line_number - 1, max(0, line_number - 10), -1):
            func_match = re.search(r'def ([a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):', lines[i])
            if func_match:
                return func_match.group(1)
        
        return "unknown_function"
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of caching opportunities"""
        return {
            'summary': {
                'total_opportunities': len(self.opportunities),
                'files_scanned': self.stats['files_scanned'],
                'by_type': dict(self.stats['by_type']),
                'by_priority': dict(self.stats['by_priority'])
            },
            'opportunities': [
                {
                    'file_path': opp.file_path,
                    'line_number': opp.line_number,
                    'function_name': opp.function_name,
                    'opportunity_type': opp.opportunity_type,
                    'description': opp.description,
                    'priority': opp.priority,
                    'estimated_impact': opp.estimated_impact,
                    'suggested_ttl': opp.suggested_ttl,
                    'cache_name': opp.cache_name
                }
                for opp in self.opportunities
            ],
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate specific recommendations for caching improvements"""
        recommendations = []
        
        # High priority recommendations
        high_priority = [opp for opp in self.opportunities if opp.priority == 'high']
        if high_priority:
            recommendations.append(f"Found {len(high_priority)} high-priority caching opportunities")
            recommendations.append("Focus on database queries and API endpoints first")
        
        # Database query recommendations
        db_queries = [opp for opp in self.opportunities if opp.opportunity_type == 'database_query']
        if db_queries:
            recommendations.append(f"Consider caching {len(db_queries)} database queries")
            recommendations.append("Use model_data cache with 5-minute TTL for most queries")
        
        # API endpoint recommendations
        api_endpoints = [opp for opp in self.opportunities if opp.opportunity_type == 'api_endpoint']
        if api_endpoints:
            recommendations.append(f"Consider caching {len(api_endpoints)} API endpoints")
            recommendations.append("Use api_responses cache with 3-minute TTL for GET endpoints")
        
        # File operation recommendations
        file_ops = [opp for opp in self.opportunities if opp.opportunity_type == 'file_operation']
        if file_ops:
            recommendations.append(f"Consider caching {len(file_ops)} file operations")
            recommendations.append("Use file_data cache with 10-minute TTL for read operations")
        
        return recommendations
    
    def create_optimization_script(self, output_file: str = "cache_optimizations.py"):
        """Create a script with suggested cache optimizations"""
        script_content = [
            "#!/usr/bin/env python3",
            '"""',
            "Cache Optimization Script for Vybe AI Desktop Application",
            "Generated by CacheOptimizer",
            '"""',
            "",
            "from vybe_app.utils.cache_manager import cached, get_cache_manager",
            "from functools import wraps",
            "",
            "# Cache manager instance",
            "cache_manager = get_cache_manager()",
            "",
            "# Suggested cache optimizations:",
            ""
        ]
        
        # Group opportunities by file
        by_file = defaultdict(list)
        for opp in self.opportunities:
            by_file[opp.file_path].append(opp)
        
        for file_path, opportunities in by_file.items():
            script_content.append(f"# File: {file_path}")
            for opp in opportunities:
                script_content.append(f"# Line {opp.line_number}: {opp.description}")
                script_content.append(f"# Suggested: @cached('{opp.cache_name}', ttl={opp.suggested_ttl})")
            script_content.append("")
        
        script_content.extend([
            "# Example implementation:",
            "",
            "# For database queries:",
            "# @cached('model_data', ttl=300)",
            "# def get_user_data(user_id):",
            "#     return User.query.get(user_id)",
            "",
            "# For API endpoints:",
            "# @cached('api_responses', ttl=180)",
            "# def get_system_status():",
            "#     return jsonify({'status': 'ok'})",
            "",
            "# For file operations:",
            "# @cached('file_data', ttl=600)",
            "# def read_config_file():",
            "#     return Path('config.json').read_text()",
            ""
        ])
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(script_content))
        
        logger.info(f"Optimization script written to {output_file}")
        return output_file


def main():
    """Main function to run cache optimization analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cache Optimization Analysis')
    parser.add_argument('--path', default='.', help='Path to scan')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--script', action='store_true', help='Generate optimization script')
    parser.add_argument('--output', default='cache_optimizations.py', help='Output script filename')
    
    args = parser.parse_args()
    
    optimizer = CacheOptimizer(args.path)
    opportunities = optimizer.scan_codebase()
    
    if args.report:
        report = optimizer.generate_report()
        print("Cache Optimization Report:")
        print("=" * 50)
        print(f"Files scanned: {report['summary']['files_scanned']}")
        print(f"Opportunities found: {report['summary']['total_opportunities']}")
        print(f"By type: {report['summary']['by_type']}")
        print(f"By priority: {report['summary']['by_priority']}")
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")
    
    if args.script:
        optimizer.create_optimization_script(args.output)
    
    return opportunities


if __name__ == "__main__":
    main()
