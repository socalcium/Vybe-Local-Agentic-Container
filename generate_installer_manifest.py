#!/usr/bin/env python3
"""
Generate installer manifest for Vybe 1.0Test
Creates a detailed list of all files included in the installer
"""

import os
import json
from pathlib import Path
from datetime import datetime

def get_file_info(file_path):
    """Get file information including size and modification time"""
    try:
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'exists': True
        }
    except Exception as e:
        print(f"Warning: Error getting file info for {file_path}: {e}")
        return {
            'size': 0,
            'size_mb': 0,
            'modified': '',
            'exists': False
        }

def scan_directory(dir_path, prefix=""):
    """Recursively scan directory and return file list"""
    files = []
    try:
        for item in dir_path.iterdir():
            relative_path = f"{prefix}/{item.name}" if prefix else item.name
            
            if item.is_file():
                files.append({
                    'path': relative_path,
                    'full_path': str(item),
                    'type': 'file',
                    **get_file_info(item)
                })
            elif item.is_dir() and not item.name.startswith('.'):
                # Add directory entry
                files.append({
                    'path': relative_path,
                    'full_path': str(item),
                    'type': 'directory',
                    'size': 0,
                    'size_mb': 0,
                    'modified': '',
                    'exists': True
                })
                # Recursively scan subdirectory
                files.extend(scan_directory(item, relative_path))
    except PermissionError:
        pass
    except Exception as e:
        print(f"Warning: Error scanning {dir_path}: {e}")
    
    return files

def generate_manifest():
    """Generate the complete installer manifest"""
    print("Generating Vybe 1.0Test Installer Manifest...")
    
    manifest = {
        'name': 'Vybe AI Assistant',
        'version': '1.0Test',
        'generated': datetime.now().isoformat(),
        'total_files': 0,
        'total_size_mb': 0,
        'components': {}
    }
    
    # Define installer components
    components = {
        'core': {
            'description': 'Core Application Files',
            'directories': ['vybe_app'],
            'files': ['run.py', 'pyproject.toml', 'requirements.txt', 'installer_backend.py', 
                     'download_default_model.py', 'setup_python_env.bat', 'launch_vybe.bat', 
                     'shutdown.bat', 'shutdown_quiet.bat']
        },
        'desktop': {
            'description': 'Desktop Application (Tauri)',
            'directories': ['vybe-desktop'],
            'files': []
        },
        'assets': {
            'description': 'Assets and Icons',
            'directories': ['assets'],
            'files': []
        },
        'models': {
            'description': 'Default AI Model',
            'directories': ['models'],
            'files': []
        },
        'documentation': {
            'description': 'Documentation and Guides',
            'directories': [],
            'files': ['README.md', 'USER_GUIDE.md', 'RELEASE_NOTES.md', 
                     'INSTALLATION_GUIDE.md', 'LICENSE.txt']
        },
        'data': {
            'description': 'RAG Data and Templates',
            'directories': ['rag_data'],
            'files': []
        },
        'external': {
            'description': 'External Dependencies',
            'directories': [],
            'files': ['python-3.11.9-amd64.exe']
        }
    }
    
    # Scan each component
    for comp_name, comp_info in components.items():
        print(f"Scanning component: {comp_name}")
        
        component_files = []
        component_size = 0
        
        # Scan directories
        for dir_name in comp_info['directories']:
            dir_path = Path(dir_name)
            if dir_path.exists():
                dir_files = scan_directory(dir_path)
                component_files.extend(dir_files)
                component_size += sum(f['size'] for f in dir_files if f['type'] == 'file')
        
        # Scan individual files
        for file_name in comp_info['files']:
            file_path = Path(file_name)
            file_info = get_file_info(file_path)
            if file_info['exists']:
                component_files.append({
                    'path': file_name,
                    'full_path': str(file_path),
                    'type': 'file',
                    **file_info
                })
                component_size += file_info['size']
        
        manifest['components'][comp_name] = {
            'description': comp_info['description'],
            'file_count': len([f for f in component_files if f['type'] == 'file']),
            'directory_count': len([f for f in component_files if f['type'] == 'directory']),
            'total_size_mb': round(component_size / (1024 * 1024), 2),
            'files': component_files
        }
        
        manifest['total_files'] += len([f for f in component_files if f['type'] == 'file'])
        manifest['total_size_mb'] += round(component_size / (1024 * 1024), 2)
    
    # Add summary statistics
    manifest['summary'] = {
        'core_size_mb': manifest['components']['core']['total_size_mb'],
        'model_size_mb': manifest['components']['models']['total_size_mb'],
        'desktop_size_mb': manifest['components']['desktop']['total_size_mb'],
        'docs_size_mb': manifest['components']['documentation']['total_size_mb'],
        'estimated_install_time_minutes': round(manifest['total_size_mb'] / 50, 1),  # Rough estimate
        'disk_space_required_mb': manifest['total_size_mb'] * 1.5,  # Include temp space
    }
    
    return manifest

def main():
    """Generate and save the manifest"""
    try:
        manifest = generate_manifest()
        
        # Save to JSON file
        manifest_file = Path('installer_manifest.json')
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Generate human-readable summary
        print("\n" + "=" * 60)
        print("VYBE 1.0TEST INSTALLER MANIFEST SUMMARY")
        print("=" * 60)
        print(f"Total Files: {manifest['total_files']}")
        print(f"Total Size: {manifest['total_size_mb']} MB")
        print(f"Estimated Install Time: {manifest['summary']['estimated_install_time_minutes']} minutes")
        print(f"Required Disk Space: {manifest['summary']['disk_space_required_mb']} MB")
        print()
        
        print("COMPONENTS:")
        for comp_name, comp_data in manifest['components'].items():
            print(f"  {comp_name.upper()}: {comp_data['file_count']} files, {comp_data['total_size_mb']} MB")
        
        print("\nMANIFEST SAVED TO: installer_manifest.json")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"Error generating manifest: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)