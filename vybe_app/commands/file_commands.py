"""
File management CLI commands
"""

import click
import os
from flask import current_app
from ..logger import log_error, log_info
from .validation_utils import (
    check_rate_limit, validate_file_access, validate_file_size,
    scan_for_malicious_content, validate_content, log_command_usage,
    get_safe_directory, validate_directory_access
)


def register_file_commands(app):
    """Register file management commands"""
    
    @app.cli.command('ingest-file')
    @click.argument('filepath', type=click.Path(exists=True))
    def ingest_file(filepath):
        """Ingests content from a local file into the RAG knowledge base."""
        try:
            with current_app.app_context():
                # Check rate limiting
                rate_ok, rate_error = check_rate_limit('ingest-file')
                if not rate_ok:
                    click.echo(f"Error: {rate_error}", err=True)
                    return
                
                # Enhanced security validation
                if not validate_file_access(filepath):
                    click.echo(f"Error: File access denied for {filepath}", err=True)
                    log_command_usage('ingest-file', success=False, details={'filepath': filepath, 'error': 'access_denied'})
                    return
                
                # Check file size
                size_ok, size_error = validate_file_size(filepath, max_size_mb=50)
                if not size_ok:
                    click.echo(f"Error: {size_error}", err=True)
                    log_command_usage('ingest-file', success=False, details={'filepath': filepath, 'error': 'file_too_large'})
                    return
                
                # Scan for malicious content
                scan_ok, scan_error = scan_for_malicious_content(filepath)
                if not scan_ok:
                    click.echo(f"Error: {scan_error}", err=True)
                    log_command_usage('ingest-file', success=False, details={'filepath': filepath, 'error': 'malicious_content'})
                    return
                
                # Read and validate content
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if not validate_content(content):
                    click.echo(f"Error: File content appears to be binary or contains suspicious content.", err=True)
                    log_command_usage('ingest-file', success=False, details={'filepath': filepath, 'error': 'invalid_content'})
                    return
                
                # Process content - use lazy imports to avoid deep import chains
                try:
                    from vybe_app.rag.text_processing import chunk_text
                    from vybe_app.rag.vector_db import add_content_to_vector_db, initialize_vector_db
                    from vybe_app.config import Config
                except ImportError:
                    click.echo("Error: RAG modules not available", err=True)
                    return
                
                # Initialize ChromaDB client
                chroma_client = initialize_vector_db(Config.RAG_VECTOR_DB_PATH)
                if not chroma_client:
                    click.echo("Error: Failed to initialize ChromaDB client", err=True)
                    return
                
                chunks = chunk_text(content)
                add_content_to_vector_db(chroma_client, 'vybe_documents', filepath, chunks)
                
                click.echo(f"Successfully ingested content from {filepath}.")
                log_command_usage('ingest-file', success=True, details={'filepath': filepath, 'chunks': len(chunks)})
                
        except Exception as e:
            log_error(f"Error ingesting file {filepath}: {e}")
            click.echo(f"Error ingesting file {filepath}: {e}", err=True)
            log_command_usage('ingest-file', success=False, details={'filepath': filepath, 'error': str(e)})
    
    @app.cli.command('ingest-folder')
    @click.argument('folderpath', type=click.Path(exists=True, file_okay=False, dir_okay=True))
    def ingest_folder(folderpath):
        """Recursively ingests content from a local folder into the RAG knowledge base."""
        try:
            with current_app.app_context():
                if not click.confirm(f"Are you sure you want to ingest all supported files from '{folderpath}' and its subfolders? This may take a while.", abort=True):
                    return
                
                if not validate_directory_access(folderpath):
                    click.echo(f"Error: Directory access denied for {folderpath}", err=True)
                    return
                
                # Import RAG modules - use lazy imports to avoid deep import chains
                try:
                    from vybe_app.rag.text_processing import chunk_text
                    from vybe_app.rag.vector_db import add_content_to_vector_db, initialize_vector_db
                    from vybe_app.config import Config
                except ImportError:
                    click.echo("Error: RAG modules not available", err=True)
                    return
                
                # Initialize ChromaDB client once for the entire folder operation
                chroma_client = initialize_vector_db(Config.RAG_VECTOR_DB_PATH)
                if not chroma_client:
                    click.echo("Error: Failed to initialize ChromaDB client", err=True)
                    return
                
                processed_files = 0
                total_chunks = 0
                
                for root, _, files in os.walk(folderpath):
                    for file in files:
                        filepath = os.path.join(root, file)
                        
                        # Check if file type is supported
                        if not file.lower().endswith(('.txt', '.md', '.html', '.json', '.py', '.js', '.css')):
                            continue
                        
                        try:
                            # Validate file access
                            if not validate_file_access(filepath):
                                click.echo(f"Skipping {filepath} - access denied")
                                continue
                            
                            # Check file size
                            size_ok, _ = validate_file_size(filepath, max_size_mb=50)
                            if not size_ok:
                                click.echo(f"Skipping {filepath} - file too large")
                                continue
                            
                            # Read and process file
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            if not validate_content(content):
                                click.echo(f"Skipping {filepath} - invalid content")
                                continue
                            
                            chunks = chunk_text(content)
                            add_content_to_vector_db(chroma_client, 'vybe_documents', filepath, chunks)
                            
                            processed_files += 1
                            total_chunks += len(chunks)
                            click.echo(f"Ingested: {filepath}")
                            
                        except Exception as e:
                            click.echo(f"Skipping {filepath} due to error: {e}", err=True)
                            continue
                
                click.echo(f"Successfully ingested {processed_files} files with {total_chunks} total chunks.")
                log_command_usage('ingest-folder', success=True, details={
                    'folderpath': folderpath,
                    'processed_files': processed_files,
                    'total_chunks': total_chunks
                })
                
        except Exception as e:
            log_error(f"Error ingesting folder {folderpath}: {e}")
            click.echo(f"Error ingesting folder {folderpath}: {e}", err=True)
            log_command_usage('ingest-folder', success=False, details={'folderpath': folderpath, 'error': str(e)})
    
    @app.cli.command('list-workspace')
    def list_workspace():
        """List files in the workspace directory."""
        try:
            safe_dir = get_safe_directory()
            if not os.path.exists(safe_dir):
                click.echo(f"Workspace directory does not exist: {safe_dir}")
                return
            
            click.echo(f"Workspace contents ({safe_dir}):")
            for root, dirs, files in os.walk(safe_dir):
                level = root.replace(safe_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                click.echo(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    click.echo(f"{subindent}{file}")
                    
        except Exception as e:
            log_error(f"Error listing workspace: {e}")
            click.echo(f"Error listing workspace: {e}", err=True)
    
    @app.cli.command('clear-workspace')
    def clear_workspace():
        """Clear all files from the workspace directory."""
        try:
            safe_dir = get_safe_directory()
            if not os.path.exists(safe_dir):
                click.echo(f"Workspace directory does not exist: {safe_dir}")
                return
            
            if not click.confirm(f"Are you sure you want to delete ALL files in {safe_dir}? This action cannot be undone.", abort=True):
                return
            
            # Count files before deletion
            file_count = 0
            for root, _, files in os.walk(safe_dir):
                file_count += len(files)
            
            # Delete files
            for root, dirs, files in os.walk(safe_dir, topdown=False):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        click.echo(f"Error deleting {file}: {e}", err=True)
                
                for dir in dirs:
                    try:
                        os.rmdir(os.path.join(root, dir))
                    except Exception as e:
                        click.echo(f"Error deleting directory {dir}: {e}", err=True)
            
            click.echo(f"Successfully cleared workspace. Deleted {file_count} files.")
            log_command_usage('clear-workspace', success=True, details={'deleted_files': file_count})
            
        except Exception as e:
            log_error(f"Error clearing workspace: {e}")
            click.echo(f"Error clearing workspace: {e}", err=True)
            log_command_usage('clear-workspace', success=False, details={'error': str(e)})
    
    @app.cli.command('validate-workspace')
    def validate_workspace():
        """Validate workspace directory structure and permissions."""
        try:
            safe_dir = get_safe_directory()
            
            click.echo("Workspace validation:")
            click.echo(f"  Directory: {safe_dir}")
            
            # Check if directory exists
            if os.path.exists(safe_dir):
                click.echo("  ✓ Directory exists")
            else:
                click.echo("  ✗ Directory does not exist")
                return
            
            # Check permissions
            if os.access(safe_dir, os.R_OK | os.W_OK):
                click.echo("  ✓ Read/Write permissions")
            else:
                click.echo("  ✗ Permission issues")
                return
            
            # Check subdirectories
            subdirs = ['uploads', 'generated', 'temp']
            for subdir in subdirs:
                subdir_path = os.path.join(safe_dir, subdir)
                if os.path.exists(subdir_path):
                    click.echo(f"  ✓ Subdirectory exists: {subdir}")
                else:
                    click.echo(f"  - Subdirectory missing: {subdir}")
            
            click.echo("Workspace validation complete.")
            
        except Exception as e:
            log_error(f"Error validating workspace: {e}")
            click.echo(f"Error validating workspace: {e}", err=True)
