#!/usr/bin/env python3
"""
Vybe Project Installer Manifest Generator
Generates a clean, focused [Files] section for Inno Setup by scanning actual project files
and intelligently excluding bloatware, test files, and unnecessary installer spam.
"""
import os
import fnmatch
from pathlib import Path

def load_gitignore_patterns():
    """Load patterns from .gitignore file"""
    patterns = []
    gitignore_path = Path('.gitignore')
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    
    return patterns

def get_hardcoded_exclusions():
    """Return list of patterns that should always be excluded (bloatware, spam, etc.)"""
    return [
        # Version control and git
        '.git',
        '.git/**',
        '.gitignore',
        
        # Build outputs and distributions
        'dist',
        'dist/**',
        'build',
        'build/**',
        'Output',
        'Output/**',
        
        # Virtual environments
        'vybe-env',
        'vybe-env/**',
        '.venv',
        '.venv/**',
        'env',
        'env/**',
        
        # Rust/Tauri build artifacts
        '**/target',
        '**/target/**',
        'Cargo.lock',
        '*.rlib',
        '*.rmeta',
        
        # Python cache and compiled files
        '__pycache__',
        '__pycache__/**',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        
        # Installer spam files (the bloatware you mentioned)
        '*installer*.py',
        '*_installer*.py', 
        'installer_*.py',
        'enhanced_installer.py',
        'simple_installer.py',
        'debug_install.py',
        'end_user_installer.py',
        'gui_installer.py',
        'iron_plated_installer.py',
        
        # Test files and cleanup scripts
        'test_*.py',
        '*_test.py',
        'cleanup*.py',
        'cleanup*.bat',
        '*cleanup*',
        
        # Inno Setup files (except templates)
        '*.iss',
        '*.spec',
        
        # Executable files that shouldn't be included
        '*.exe',
        '*.dll',
        '*.msi',
        
        # Documentation spam (excessive markdown files)
        '*_COMPLETE*.md',
        '*_SUMMARY*.md',
        '*_REPORT*.md',
        '*_NOTES*.md',
        '*COMPLETION*',
        'COMPREHENSIVE_*.md',
        'IMPLEMENTATION_*.md',
        'PROFESSIONAL_*.md',
        'DESKTOP_COMPLETE.md',
        'PYLANCE_FIX_SUMMARY.md',
        'DISTRIBUTION_PLAN.md',
        'DUAL_MODE_IMPLEMENTATION.md',
        'END_USER_STRATEGY.md',
        
        # Log files and temporary files
        '*.log',
        '*.tmp',
        'logs',
        'logs/**',
        'temp',
        'temp/**',
        
        # IDE and editor files
        '.vscode',
        '.vscode/**',
        '.idea',
        '.idea/**',
        '*.swp',
        '*.swo',
        
        # OS files
        'Thumbs.db',
        '.DS_Store',
        'desktop.ini',
        
        # This script itself and related tools
        'generate_inno_manifest.py',
        'generate_inno_manifest_new.py',
        'iron_plated_installer.py',
        'nuclear_cleanup.py',
        
        # Setup and build scripts that aren't needed in distribution
        'setup/**',
        'build_*.py',
        'build_*.bat',
        'verify_*.py',
        'migrate_*.py',
        'list_routes.py',
        
        # HTML test files
        'test_*.html',
        
        # Cookie and session files
        'cookies.txt',
        
        # Large model files and vendor directories
        'vendor/**',
        'models/**',
        'checkpoints/**',
        '*.safetensors',
        '*.ckpt',
        '*.bin',
        '*.pt',
        
        # Development environment files
        'environment.yml',
        'pyrightconfig.json',
        '.env.example',
        
        # Instance and generated files that shouldn't be in installer
        'instance/**',
        '*.db',
        '*.sqlite3',
        
        # Manifest files themselves
        'inno_files_manifest.txt',
        'vybe_setup_template.iss',
    ]

def should_exclude_file(file_path, exclusion_patterns):
    """Check if a file should be excluded based on patterns"""
    # Convert to forward slashes for consistent pattern matching
    normalized_path = str(file_path).replace('\\', '/')
    file_name = os.path.basename(normalized_path)
    
    for pattern in exclusion_patterns:
        # Handle different pattern types
        if pattern.endswith('/**'):
            # Directory and all contents
            dir_pattern = pattern[:-3]
            if normalized_path.startswith(dir_pattern + '/') or normalized_path == dir_pattern:
                return True
        elif pattern.startswith('**/'):
            # Recursive pattern - match anywhere in path
            target_pattern = pattern[3:]  # Remove the **/
            if ('/' + target_pattern + '/') in normalized_path or normalized_path.endswith('/' + target_pattern):
                return True
        elif '/' in pattern:
            # Path-based pattern
            if fnmatch.fnmatch(normalized_path, pattern):
                return True
        else:
            # Filename-based pattern
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(normalized_path, pattern):
                return True
    
    return False

def generate_inno_files_section():
    """Generate the [Files] section for Inno Setup"""
    print("🔍 Scanning project files...")
    
    # Load exclusion patterns
    gitignore_patterns = load_gitignore_patterns()
    hardcoded_patterns = get_hardcoded_exclusions()
    all_patterns = gitignore_patterns + hardcoded_patterns
    
    print(f"📋 Loaded {len(gitignore_patterns)} patterns from .gitignore")
    print(f"🚫 Added {len(hardcoded_patterns)} hardcoded exclusion patterns")
    
    # Scan files
    included_files = []
    excluded_files = []
    
    project_root = Path('.')
    
    for file_path in project_root.rglob('*'):
        if file_path.is_file():
            relative_path = file_path.relative_to(project_root)
            
            if should_exclude_file(relative_path, all_patterns):
                excluded_files.append(str(relative_path))
            else:
                included_files.append(relative_path)
    
    print(f"✅ Found {len(included_files)} files to include")
    print(f"🗑️  Excluded {len(excluded_files)} files")
    
    # Generate Inno Setup [Files] entries
    files_entries = []
    files_entries.append("; Auto-generated [Files] section for Vybe AI Assistant")
    files_entries.append("; Generated by generate_inno_manifest.py")
    files_entries.append("")
    
    # Group files by directory for better organization
    files_by_dir = {}
    for file_path in sorted(included_files):
        dir_path = file_path.parent
        if dir_path not in files_by_dir:
            files_by_dir[dir_path] = []
        files_by_dir[dir_path].append(file_path)
    
    # Generate entries
    for dir_path in sorted(files_by_dir.keys()):
        if str(dir_path) != '.':
            files_entries.append(f"; Files in {dir_path}")
        else:
            files_entries.append("; Root directory files")
            
        for file_path in files_by_dir[dir_path]:
            source_path = str(file_path).replace('/', '\\')
            
            if str(file_path.parent) == '.':
                dest_dir = "{app}"
            else:
                dest_dir = "{app}\\" + str(file_path.parent).replace('/', '\\')
            
            entry = f'Source: "{source_path}"; DestDir: "{dest_dir}"; Flags: ignoreversion'
            files_entries.append(entry)
        
        files_entries.append("")
    
    # Write to manifest file
    manifest_path = Path('inno_files_manifest.txt')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(files_entries))
    
    print(f"📄 Generated manifest: {manifest_path}")
    print(f"📊 Total entries: {len(included_files)}")
    
    # Show some examples of what was excluded
    if excluded_files:
        print("\n🗑️  Sample excluded files:")
        for excluded in excluded_files[:10]:
            print(f"   - {excluded}")
        if len(excluded_files) > 10:
            print(f"   ... and {len(excluded_files) - 10} more")
    
    return len(included_files)

if __name__ == "__main__":
    print("🚀 Vybe Installer Manifest Generator")
    print("=" * 50)
    
    try:
        file_count = generate_inno_files_section()
        print("\n✅ Manifest generation completed successfully!")
        print(f"📦 Ready to package {file_count} files")
        print("\nNext steps:")
        print("1. Review inno_files_manifest.txt")
        print("2. Copy contents to vybe_setup_template.iss")
        print("3. Build the installer")
        
    except Exception as e:
        print(f"\n❌ Error generating manifest: {e}")
        exit(1)
