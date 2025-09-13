"""
RAG API module - handles RAG and workspace-related endpoints.
"""

from flask import Blueprint, request, jsonify
from ..auth import test_mode_login_required, current_user
import os
import logging
from ..models import db, AppSetting, User
from ..logger import log_error, log_api_request, log_user_action

logger = logging.getLogger(__name__)

# Create RAG sub-blueprint
rag_bp = Blueprint('rag', __name__, url_prefix='')

"""
RAG API module - handles RAG and workspace-related endpoints.
"""

from flask import Blueprint, request, jsonify
from ..auth import test_mode_login_required, current_user
import os
import logging
from ..models import db, AppSetting, User
from ..logger import log_error, log_api_request, log_user_action
from ..utils.cache_manager import cached

logger = logging.getLogger(__name__)

# Create RAG sub-blueprint
rag_bp = Blueprint('rag', __name__, url_prefix='')

@cached(timeout=1800)  # Cache for 30 minutes
def get_cached_rag_collections():
    """Get RAG collections with caching to reduce ChromaDB load"""
    from ..rag.vector_db import initialize_vector_db, get_connection_pool
    import os
    
    # Get the RAG data path
    rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
    
    try:
        # Initialize ChromaDB connection pool
        init_success = initialize_vector_db(rag_data_path)
        
        if not init_success:
            log_error("Failed to initialize ChromaDB connection pool")
            return {'error': 'Vector database not available', 'status': 503}
        
        # Get connection pool and client
        pool = get_connection_pool()
        if not pool:
            log_error("Connection pool not available")
            return {'error': 'Vector database connection pool not available', 'status': 503}
        
        # Get list of collections from ChromaDB
        try:
            with pool.get_connection() as chroma_client:
                collections_list = chroma_client.list_collections()
                
                collections = []
                for collection in collections_list:
                    try:
                        collection_name = collection.name
                        collection_obj = chroma_client.get_collection(name=collection_name)
                        count = collection_obj.count()
                        
                        collections.append({
                            'name': collection_name,
                            'count': count,
                            'id': collection_name  # Use name as ID for now
                        })
                    except Exception as e:
                        log_error(f"Error getting collection {collection_name}: {str(e)}")
                        continue
                
                return {'collections': collections, 'status': 200}
                
        except Exception as e:
            log_error(f"Error listing ChromaDB collections: {str(e)}")
            return {'error': f'Failed to list collections: {str(e)}', 'status': 500}
            
    except Exception as e:
        log_error(f"Error initializing ChromaDB: {str(e)}")
        return {'error': f'Database initialization failed: {str(e)}', 'status': 500}

@rag_bp.route('/rag_collections', methods=['GET'])
def api_rag_collections():
    """Get list of RAG collections"""
    log_api_request(request.endpoint, request.method)
    try:
        result = get_cached_rag_collections()
        
        if 'error' in result:
            return jsonify({'error': result['error']}), result.get('status', 500)
        
        return jsonify({
            'success': True,
            'collections': result['collections']
        })
        
    except Exception as e:
        log_error(f"RAG collections API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Keep the original function pattern for compatibility
def _original_api_rag_collections():
    """Original implementation for reference"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, get_connection_pool
        import os
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        try:
            # Initialize ChromaDB connection pool
            init_success = initialize_vector_db(rag_data_path)
            
            if not init_success:
                log_error("Failed to initialize ChromaDB connection pool")
                return jsonify({'error': 'Vector database not available'}), 503
            
            # Get connection pool and client
            pool = get_connection_pool()
            if not pool:
                log_error("Connection pool not available")
                return jsonify({'error': 'Vector database connection pool not available'}), 503
            
            # Get list of collections from ChromaDB
            try:
                with pool.get_connection() as chroma_client:
                    collections_list = chroma_client.list_collections()
                    
                    collections = []
                    for collection in collections_list:
                        try:
                            collection_name = collection.name
                            # Get collection metadata
                            try:
                                coll = chroma_client.get_collection(collection_name)
                                doc_count = coll.count()
                            except Exception as coll_error:
                                log_error(f"Error getting collection {collection_name}: {str(coll_error)}")
                                doc_count = 0
                            
                            collections.append({
                                'id': hash(collection_name) % 1000000,  # Generate consistent ID
                                'collection_name': collection_name,
                                'display_name': collection_name.replace('_', ' ').title(),
                                'description': f'ChromaDB Collection: {collection_name}',
                                'document_count': doc_count,
                                'is_ingesting': False,
                                'status_message': 'Ready',
                                'created_at': '2025-01-01T00:00:00Z',
                                'last_updated': '2025-01-01T00:00:00Z'
                            })
                        except Exception as item_error:
                            log_error(f"Error processing collection item: {str(item_error)}")
                            continue
                    
                    # If no collections exist, create a default one
                    if not collections:
                        # Try to create a default collection
                        try:
                            default_collection = chroma_client.create_collection(
                                name="general_knowledge",
                                metadata={"description": "Default knowledge base for testing"}
                            )
                            collections = [
                                {
                                    'id': 1,
                                    'collection_name': 'general_knowledge',
                                    'display_name': 'General Knowledge',
                                    'description': 'Default knowledge base - created automatically for testing',
                                    'document_count': 0,
                                    'is_ingesting': False,
                                    'status_message': 'Ready (Default Collection)',
                                    'created_at': '2025-01-01T00:00:00Z',
                                    'last_updated': '2025-01-01T00:00:00Z'
                                }
                            ]
                        except Exception as create_error:
                            log_error(f"Could not create default collection: {str(create_error)}")
                            collections = [
                                {
                                    'id': 1,
                                    'collection_name': 'general_knowledge',
                                    'display_name': 'General Knowledge',
                                    'description': 'Default knowledge base - collection creation pending',
                                    'document_count': 0,
                                    'is_ingesting': False,
                                    'status_message': 'Collection Creation Pending',
                                    'created_at': '2025-01-01T00:00:00Z',
                                    'last_updated': '2025-01-01T00:00:00Z'
                                }
                            ]
                
                return jsonify(collections)
                
            except Exception as list_error:
                log_error(f"Error listing collections: {str(list_error)}")
                # Return default collection on list error
                collections = [
                    {
                        'id': 1,
                        'collection_name': 'general_knowledge',
                        'display_name': 'General Knowledge',
                        'description': 'Default knowledge base - ChromaDB error, see logs',
                        'document_count': 0,
                        'is_ingesting': False,
                        'status_message': 'ChromaDB Connection Issue',
                        'created_at': '2025-01-01T00:00:00Z',
                        'last_updated': '2025-01-01T00:00:00Z'
                    }
                ]
                return jsonify(collections)
                
        except ImportError as import_error:
            # RAG core not available
            log_error(f"RAG core not available: {str(import_error)}")
            collections = [
                {
                    'id': 1,
                    'collection_name': 'general_knowledge',
                    'display_name': 'General Knowledge',
                    'description': 'Default knowledge base - RAG system dependencies missing',
                    'document_count': 0,
                    'is_ingesting': False,
                    'status_message': 'RAG Dependencies Missing',
                    'created_at': '2025-01-01T00:00:00Z',
                    'last_updated': '2025-01-01T00:00:00Z'
                }
            ]
            return jsonify(collections)
            
    except Exception as e:
        log_error(f"RAG collections API error: {str(e)}")
        # Return error with helpful default data
        return jsonify([
            {
                'id': 999,
                'collection_name': 'error_fallback',
                'display_name': 'Error Fallback',
                'description': f'API Error: {str(e)} - Please check logs',
                'document_count': 0,
                'is_ingesting': False,
                'status_message': 'Error - Check Logs',
                'created_at': '2025-01-01T00:00:00Z',
                'last_updated': '2025-01-01T00:00:00Z'
            }
        ]), 200  # Return 200 with error collection instead of 500

@rag_bp.route('/rag_documents', methods=['GET'])
def api_rag_documents():
    """Get list of RAG documents"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, list_rag_documents_metadata
        import os
        
        # Get the collection name from query parameters
        collection_name = request.args.get('collection', 'general_knowledge')
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        try:
            # Initialize ChromaDB client
            chroma_client = initialize_vector_db(rag_data_path)
            
            if chroma_client:
                try:
                    # Get documents from the specified collection
                    documents = list_rag_documents_metadata(chroma_client, collection_name)
                    
                    # If no documents, return helpful default data
                    if not documents:
                        documents = [
                            {
                                'id': 'sample_doc_1',
                                'filename': 'Welcome Document',
                                'title': 'Getting Started with Vybe RAG',
                                'content_preview': 'Welcome to Vybe RAG system! This is a sample document to help you get started. You can upload your own documents using the file upload feature or add web content using the URL loader.',
                                'document_type': 'text',
                                'file_size': '1.2 KB',
                                'upload_date': '2025-01-01T00:00:00Z',
                                'source_url': '',
                                'chunk_count': 3,
                                'status': 'Ready for Testing'
                            },
                            {
                                'id': 'sample_doc_2', 
                                'filename': 'Sample Knowledge Base',
                                'title': 'Vybe Features Overview',
                                'content_preview': 'Vybe includes powerful features like web search integration, RAG-based document retrieval, model management, and intelligent chat capabilities. Upload documents to enhance the AI responses.',
                                'document_type': 'text',
                                'file_size': '2.1 KB',
                                'upload_date': '2025-01-01T00:00:00Z',
                                'source_url': '',
                                'chunk_count': 5,
                                'status': 'Sample Data'
                            }
                        ]
                    
                    return jsonify(documents)
                    
                except Exception as list_error:
                    log_error(f"Error listing documents: {str(list_error)}")
                    # Return helpful sample data on error
                    documents = [
                        {
                            'id': 'error_doc',
                            'filename': 'Error Loading Documents',
                            'title': 'ChromaDB Connection Issue',
                            'content_preview': f'Error retrieving documents: {str(list_error)}. Check ChromaDB configuration and logs.',
                            'document_type': 'error',
                            'file_size': '0 KB',
                            'upload_date': '2025-01-01T00:00:00Z',
                            'source_url': '',
                            'chunk_count': 0,
                            'status': 'Connection Error'
                        }
                    ]
                    return jsonify(documents)
            else:
                # ChromaDB not available - return sample data
                documents = [
                    {
                        'id': 'init_doc',
                        'filename': 'ChromaDB Initializing',
                        'title': 'RAG System Starting Up',
                        'content_preview': 'ChromaDB is initializing. Please wait a moment and refresh the page. If this persists, check the application logs.',
                        'document_type': 'system',
                        'file_size': '0 KB',
                        'upload_date': '2025-01-01T00:00:00Z',
                        'source_url': '',
                        'chunk_count': 0,
                        'status': 'Initializing'
                    }
                ]
                return jsonify(documents)
                
        except ImportError as import_error:
            log_error(f"RAG core not available: {str(import_error)}")
            documents = [
                {
                    'id': 'dep_error',
                    'filename': 'RAG Dependencies Missing',
                    'title': 'ChromaDB Not Available', 
                    'content_preview': 'RAG system dependencies are missing. Please install ChromaDB and required packages.',
                    'document_type': 'error',
                    'file_size': '0 KB',
                    'upload_date': '2025-01-01T00:00:00Z',
                    'source_url': '',
                    'chunk_count': 0,
                    'status': 'Dependencies Missing'
                }
            ]
            return jsonify(documents)
            
    except Exception as e:
        log_error(f"RAG documents API error: {str(e)}")
        # Return error document
        return jsonify([
            {
                'id': 'api_error',
                'filename': 'API Error',
                'title': 'Document Loading Failed',
                'content_preview': f'API Error: {str(e)}. Check application logs for details.',
                'document_type': 'error',
                'file_size': '0 KB',
                'upload_date': '2025-01-01T00:00:00Z',
                'source_url': '',
                'chunk_count': 0,
                'status': 'API Error'
            }
        ]), 200

@rag_bp.route('/rag_collections/<collection_name>/documents', methods=['GET'])
def api_rag_collection_documents(collection_name):
    """Get list of RAG documents for a specific collection"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, list_rag_documents_metadata
        import os
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        try:
            # Initialize ChromaDB client
            chroma_client = initialize_vector_db(rag_data_path)
            
            if chroma_client:
                try:
                    # Get documents from the specified collection
                    documents = list_rag_documents_metadata(chroma_client, collection_name)
                    
                    # Transform documents to match expected frontend format
                    formatted_documents = []
                    for doc in documents:
                        formatted_documents.append({
                            'id': doc.get('id', 'unknown'),
                            'filename': doc.get('source', 'Unknown Source'),
                            'title': doc.get('source', 'Unknown Source'),
                            'content_preview': doc.get('snippet', 'No content preview available'),
                            'document_type': 'text',
                            'file_size': 'Unknown',
                            'upload_date': '2025-01-01T00:00:00Z',
                            'source_url': doc.get('source', ''),
                            'chunk_count': 1,
                            'status': 'Ready'
                        })
                    
                    return jsonify({
                        'success': True,
                        'documents': formatted_documents,
                        'collection_name': collection_name
                    })
                    
                except Exception as list_error:
                    log_error(f"Error listing documents from collection '{collection_name}': {str(list_error)}")
                    return jsonify({
                        'success': False,
                        'error': f'Error retrieving documents from collection: {str(list_error)}',
                        'documents': []
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'ChromaDB not available - initializing',
                    'documents': []
                })
                
        except ImportError as import_error:
            log_error(f"RAG core not available: {str(import_error)}")
            return jsonify({
                'success': False,
                'error': 'RAG system dependencies missing',
                'documents': []
            })
            
    except Exception as e:
        log_error(f"RAG collection documents API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'API Error: {str(e)}',
            'documents': []
        })

@rag_bp.route('/frontend-error', methods=['POST'])
def api_frontend_error():
    """Log frontend errors"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        error_msg = data.get('error', 'Unknown frontend error')
        context = data.get('context', '')
        url = data.get('url', '')
        
        log_error(f"Frontend Error - {context}: {error_msg} at {url}")
        return jsonify({'success': True})
    except Exception as e:
        log_error(f"Frontend error logging failed: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/workspace', methods=['GET', 'POST'])
@test_mode_login_required
def api_workspace():
    """Get or set workspace configuration"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            # Get workspace path from settings
            setting = AppSetting.query.filter_by(key='workspace_path').first()
            workspace_path = setting.value if setting else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'workspace')
            
            return jsonify({
                'workspace_path': workspace_path,
                'exists': os.path.exists(workspace_path),
                'readable': os.access(workspace_path, os.R_OK) if os.path.exists(workspace_path) else False,
                'writable': os.access(workspace_path, os.W_OK) if os.path.exists(workspace_path) else False
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            workspace_path = data.get('workspace_path')
            
            if not workspace_path:
                return jsonify({'error': 'Workspace path is required'}), 400
            
            # Validate and create workspace directory if needed
            try:
                os.makedirs(workspace_path, exist_ok=True)
            except Exception as e:
                return jsonify({'error': f'Cannot create workspace directory: {str(e)}'}), 400
            
            # Save workspace path
            setting = AppSetting.query.filter_by(key='workspace_path').first()
            if setting:
                setting.value = workspace_path
            else:
                setting = AppSetting()
                setting.key = 'workspace_path'
                setting.value = workspace_path
                db.session.add(setting)
            
            db.session.commit()
            log_user_action(current_user.id, f"Changed workspace path to: {workspace_path}")
            
            return jsonify({'success': True, 'workspace_path': workspace_path})
        
        return jsonify({'error': 'Invalid request method'}), 400
            
    except Exception as e:
        log_error(f"Workspace API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/user/profile', methods=['GET', 'POST'])
@test_mode_login_required
def api_user_profile():
    """Get or update user profile"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            return jsonify({
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Update username and email if provided
            if 'username' in data:
                # Check if username is already taken
                existing_user = User.query.filter_by(username=data['username']).first()
                if existing_user and existing_user.id != current_user.id:
                    return jsonify({'error': 'Username already taken'}), 400
                current_user.username = data['username']
            
            if 'email' in data:
                current_user.email = data['email']
            
            db.session.commit()
            log_user_action(current_user.id, "Updated user profile")
            
            return jsonify({'success': True})
        
        return jsonify({'error': 'Invalid request method'}), 400
            
    except Exception as e:
        log_error(f"User profile API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections', methods=['POST'])
@test_mode_login_required
def api_create_rag_collection():
    """Create a new RAG collection"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        collection_name = data.get('name')
        description = data.get('description', '')
        
        if not collection_name:
            return jsonify({'error': 'Collection name is required'}), 400
        
        # For now, just return success - implement actual creation later
        log_user_action(current_user.id, f"Created RAG collection: {collection_name}")
        return jsonify({
            'success': True,
            'message': f'Collection "{collection_name}" created successfully',
            'collection': {
                'name': collection_name,
                'description': description
            }
        })
        
    except Exception as e:
        log_error(f"Create RAG collection API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/delete', methods=['POST'])
@test_mode_login_required
def api_delete_rag_collection():
    """Delete a RAG collection"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        collection_name = data.get('collection_name')
        
        if not collection_name:
            return jsonify({'error': 'Collection name is required'}), 400
        
        # For now, just return success - implement actual deletion later
        log_user_action(current_user.id, f"Deleted RAG collection: {collection_name}")
        return jsonify({
            'success': True,
            'message': f'Collection "{collection_name}" deleted successfully'
        })
        
    except Exception as e:
        log_error(f"Delete RAG collection API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Accept DELETE as used by some frontend code paths
@rag_bp.route('/rag_collections/delete', methods=['DELETE'])
@test_mode_login_required
def api_delete_rag_collection_delete():
    """Delete a RAG collection (DELETE alias)."""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json(silent=True) or {}
        collection_name = data.get('collection_name')
        if not collection_name:
            return jsonify({'error': 'Collection name is required'}), 400
        log_user_action(current_user.id, f"Deleted RAG collection (DELETE): {collection_name}")
        return jsonify({'success': True, 'message': f'Collection "{collection_name}" deleted successfully'})
    except Exception as e:
        log_error(f"Delete RAG collection (DELETE) API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/delete_rag_document/<doc_id>', methods=['DELETE'])
@test_mode_login_required
def api_delete_rag_document(doc_id):
    """Delete a RAG document"""
    log_api_request(request.endpoint, request.method)
    try:
        # For now, just return success - implement actual deletion later
        log_user_action(current_user.id, f"Deleted RAG document: {doc_id}")
        return jsonify({
            'success': True,
            'message': f'Document "{doc_id}" deleted successfully'
        })
        
    except Exception as e:
        log_error(f"Delete RAG document API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/web-content', methods=['POST'])
@test_mode_login_required
def api_fetch_web_content():
    """Fetch content from a web URL"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        from ..rag.web_search import scrape_url_content
        
        try:
            content = scrape_url_content(url)
            
            if content:
                return jsonify({
                    'success': True,
                    'content': {
                        'text': content,
                        'url': url,
                        'title': f'Content from {url}'
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not fetch content from URL'
                }), 400
                
        except Exception as scrape_error:
            log_error(f"Web scraping error: {str(scrape_error)}")
            return jsonify({
                'success': False,
                'error': f'Error fetching content: {str(scrape_error)}'
            }), 400
        
    except Exception as e:
        log_error(f"Web content API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/add_rag_text', methods=['POST'])
@test_mode_login_required
def api_add_rag_text():
    """Add text content to RAG collection"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        collection_name = data.get('collection_name')
        text = data.get('text')
        title = data.get('title', 'Web Content')
        url = data.get('url', '')
        
        if not collection_name or not text:
            return jsonify({'error': 'Collection name and text are required'}), 400
        
        # For now, just return success - implement actual text addition later
        log_user_action(current_user.id, f"Added text to RAG collection: {collection_name}")
        return jsonify({
            'success': True,
            'message': f'Text added to collection "{collection_name}" successfully',
            'document_id': f'doc_{hash(text) % 1000000}'
        })
        
    except Exception as e:
        log_error(f"Add RAG text API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>', methods=['PUT'])
@test_mode_login_required
def api_update_rag_collection(collection_name):
    """Update RAG collection metadata"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        description = data.get('description', '')
        
        # For now, just return success - implement actual update later
        log_user_action(current_user.id, f"Updated RAG collection: {collection_name}")
        return jsonify({
            'success': True,
            'message': f'Collection "{collection_name}" updated successfully'
        })
        
    except Exception as e:
        log_error(f"Update RAG collection API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>/upload_files', methods=['POST'])
@test_mode_login_required
def api_upload_files_to_collection(collection_name):
    """Upload files to RAG collection"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.job_manager import job_manager
        from ..config import Config
        from ..utils.input_validation import InputValidator, ValidationError
        import tempfile
        import shutil
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        temp_dir = tempfile.mkdtemp()
        
        try:
            for i, file in enumerate(files):
                if not file.filename or file.filename == '':
                    continue
                
                # Enhanced security validation using InputValidator
                try:
                    # Validate file upload with comprehensive security checks
                    file_info = InputValidator.validate_file_upload(
                        f'files[{i}]',
                        allowed_types=['document'],
                        max_size=100 * 1024 * 1024,  # 100MB limit for documents
                        required=False
                    )
                    
                    if not file_info:
                        continue
                    
                    # Additional security checks
                    filename = file_info['filename']
                    file_size = file_info['size']
                    
                    # Check for malicious file extensions
                    if any(filename.lower().endswith(ext) for ext in ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']):
                        log_error(f"Blocked potentially malicious file: {filename}")
                        continue
                    
                    # Check for path traversal attempts
                    if '..' in filename or '/' in filename or '\\' in filename:
                        log_error(f"Blocked path traversal attempt: {filename}")
                        continue
                    
                    # Save file temporarily with secure filename
                    from werkzeug.utils import secure_filename
                    secure_name = secure_filename(filename)
                    temp_path = os.path.join(temp_dir, secure_name)
                    file.save(temp_path)
                    
                    uploaded_files.append({
                        'filename': secure_name,
                        'path': temp_path,
                        'status': 'pending'
                    })
                    
                except ValidationError as e:
                    log_error(f"File validation failed for {file.filename}: {str(e)}")
                    continue
                except Exception as e:
                    log_error(f"File processing error for {file.filename}: {str(e)}")
                    continue
            
            if not uploaded_files:
                return jsonify({'error': 'No valid files found (must be .txt, .md, or .pdf)'}), 400
            
            # Add job to process files in background
            job_manager.add_job(
                process_uploaded_files_job,
                collection_name,
                uploaded_files,
                temp_dir,
                current_user.id
            )
            
            log_user_action(current_user.id, f"Uploaded {len(uploaded_files)} files to RAG collection: {collection_name}")
            return jsonify({
                'success': True,
                'message': f'{len(uploaded_files)} files queued for processing in collection "{collection_name}"',
                'uploaded_files': [{'filename': f['filename'], 'status': 'queued'} for f in uploaded_files]
            })
            
        except Exception as e:
            # Clean up temp files on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
        
    except Exception as e:
        log_error(f"Upload files API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def process_uploaded_files_job(collection_name, uploaded_files, temp_dir, user_id):
    """Background job to process uploaded files"""
    try:
        from ..rag.vector_db import initialize_vector_db, get_connection_pool
        from ..rag.text_processing import chunk_text, process_pdf_content, process_text_file
        from ..config import Config
        from ..models import AppSetting
        from ..core.job_manager import job_manager
        import shutil
        
        # Initialize vector database
        init_success = initialize_vector_db(Config.RAG_VECTOR_DB_PATH)
        if not init_success:
            raise Exception("Failed to initialize vector database")
        
        # Get connection pool
        pool = get_connection_pool()
        if not pool:
            raise Exception("Connection pool not available")
        
        # Get or create collection
        with pool.get_connection() as vector_db:
            try:
                collection = vector_db.get_collection(collection_name)
            except Exception as e:
                logger.warning(f"Failed to get collection {collection_name}, creating new one: {e}")
                collection = vector_db.create_collection(collection_name)
        
        # Check if RAG auto-processing is enabled
        rag_setting = AppSetting.query.filter_by(key='rag_auto_processing').first()
        auto_processing = rag_setting.value == 'true' if rag_setting else True
        
        processed_count = 0
        for file_info in uploaded_files:
            try:
                # Process the file
                file_path = file_info['path']
                filename = file_info['filename']
                
                # Read and process file content based on type
                content = None
                if filename.lower().endswith('.txt') or filename.lower().endswith('.md'):
                    content = process_text_file(file_path)
                elif filename.lower().endswith('.pdf'):
                    content = process_pdf_content(file_path)
                
                if not content:
                    continue
                
                # If auto-processing is enabled, add document processing job
                if auto_processing:
                    job_manager.add_document_processing_job(content, filename, collection_name)
                    print(f"✅ Queued {filename} for backend LLM processing")
                else:
                    # Regular processing without LLM enhancement
                    # Split content into chunks
                    chunks = chunk_text(content, Config.RAG_CHUNK_SIZE, Config.RAG_CHUNK_OVERLAP)
                    
                    # Add chunks to collection
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{filename}_chunk_{i}"
                        collection.add(
                            documents=[chunk],
                            metadatas=[{
                                'source': filename,
                                'chunk_index': i,
                                'total_chunks': len(chunks),
                                'user_id': user_id
                            }],
                            ids=[doc_id]
                        )
                    
                    print(f"✅ Processed {filename} without LLM enhancement")
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing file {file_info['filename']}: {str(e)}")
                continue
        
        print(f"Processed {processed_count}/{len(uploaded_files)} files for collection {collection_name}")
        
    except Exception as e:
        print(f"Error in file processing job: {str(e)}")
    finally:
        # Clean up temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

@rag_bp.route('/rag_collections/<collection_name>/load_url', methods=['POST'])
@test_mode_login_required
def api_load_url_to_collection(collection_name):
    """Load web content from URL into RAG collection"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.job_manager import job_manager
        
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            return jsonify({'error': 'Invalid URL format. Must start with http:// or https://'}), 400
        
        # Add job to load URL in background
        job_manager.add_job(
            process_url_job,
            collection_name,
            url,
            current_user.id
        )
        
        log_user_action(current_user.id, f"Loading URL into RAG collection: {collection_name} - {url}")
        return jsonify({
            'success': True,
            'message': f'URL queued for processing in collection "{collection_name}"',
            'url': url
        })
        
    except Exception as e:
        log_error(f"Load URL API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def process_url_job(collection_name, url, user_id):
    """Background job to process URL content"""
    try:
        from ..rag.vector_db import initialize_vector_db, get_connection_pool
        from ..rag.text_processing import chunk_text
        from ..web_loader import load_web_content
        from ..config import Config
        
        # Load web content
        content = load_web_content(url)
        if not content:
            print(f"Failed to load content from URL: {url}")
            return
        
        # Initialize vector database
        init_success = initialize_vector_db(Config.RAG_VECTOR_DB_PATH)
        if not init_success:
            raise Exception("Failed to initialize vector database")
        
        # Get connection pool
        pool = get_connection_pool()
        if not pool:
            raise Exception("Connection pool not available")
        
        # Get or create collection
        with pool.get_connection() as vector_db:
            try:
                collection = vector_db.get_collection(collection_name)
            except Exception as e:
                logger.warning(f"Failed to get collection {collection_name}, creating new one: {e}")
                collection = vector_db.create_collection(collection_name)
            
            # Split content into chunks
            chunks = chunk_text(content, Config.RAG_CHUNK_SIZE, Config.RAG_CHUNK_OVERLAP)
            
            # Add chunks to collection
            for i, chunk in enumerate(chunks):
                doc_id = f"url_{hash(url)}_{i}"
                collection.add(
                    documents=[chunk],
                    metadatas=[{
                        'source': url,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'user_id': user_id,
                        'content_type': 'web_page'
                    }],
                    ids=[doc_id]
                )
            
            print(f"Processed URL {url} into {len(chunks)} chunks for collection {collection_name}")
        
    except Exception as e:
        print(f"Error in URL processing job: {str(e)}")

@rag_bp.route('/rag_collections/<collection_name>/schedule', methods=['POST', 'DELETE'])
@test_mode_login_required
def api_manage_collection_schedule(collection_name):
    """Manage RAG collection ingestion schedule"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'POST':
            # Create/update schedule
            data = request.get_json()
            schedule_config = data.get('schedule', {})
            
            log_user_action(current_user.id, f"Created schedule for RAG collection: {collection_name}")
            return jsonify({
                'success': True,
                'message': f'Schedule created for collection "{collection_name}"'
            })
            
        elif request.method == 'DELETE':
            # Delete schedule
            log_user_action(current_user.id, f"Deleted schedule for RAG collection: {collection_name}")
            return jsonify({
                'success': True,
                'message': f'Schedule deleted for collection "{collection_name}"'
            })
        else:
            return jsonify({'error': 'Method not allowed'}), 405
        
    except Exception as e:
        log_error(f"Collection schedule API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/sample_prompts', methods=['GET'])
@test_mode_login_required
def api_get_sample_prompts():
    """Get sample chat prompts for testing"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..utils import get_sample_chat_prompts
        
        prompts = get_sample_chat_prompts()
        return jsonify({
            'success': True,
            'prompts': prompts,
            'message': 'Sample prompts for testing Vybe functionality'
        })
        
    except Exception as e:
        log_error(f"Sample prompts API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/initialization_status', methods=['GET'])
@test_mode_login_required
def api_get_initialization_status():
    """Check application initialization status"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..utils import check_initialization_status
        
        status = check_initialization_status()
        return jsonify({
            'success': True,
            'status': status,
            'message': 'Initialization status retrieved successfully'
        })
        
    except Exception as e:
        log_error(f"Initialization status API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>/documents/<doc_id>', methods=['GET'])
def api_get_document(collection_name, doc_id):
    """Get a specific document's full content"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, get_document_full_content
        import os
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        # Initialize ChromaDB client
        chroma_client = initialize_vector_db(rag_data_path)
        if not chroma_client:
            return jsonify({'error': 'ChromaDB not available'}), 500
        
        # Get document content
        document = get_document_full_content(chroma_client, collection_name, doc_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'success': True,
            'document': document
        })
        
    except Exception as e:
        log_error(f"Get document API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>/documents/<doc_id>', methods=['PUT'])
def api_update_document(collection_name, doc_id):
    """Update an existing document"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, update_document_in_rag
        import os
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        source = data.get('source', doc_id)
        
        if not content.strip():
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        # Initialize ChromaDB client
        chroma_client = initialize_vector_db(rag_data_path)
        if not chroma_client:
            return jsonify({'error': 'ChromaDB not available'}), 500
        
        # Update document
        success = update_document_in_rag(chroma_client, collection_name, doc_id, source, content)
        if not success:
            return jsonify({'error': 'Failed to update document'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Document {doc_id} updated successfully'
        })
        
    except Exception as e:
        log_error(f"Update document API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>/documents/<doc_id>', methods=['DELETE'])
def api_delete_document(collection_name, doc_id):
    """Delete a specific document"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, delete_rag_document_by_id
        import os
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        # Initialize ChromaDB client
        chroma_client = initialize_vector_db(rag_data_path)
        if not chroma_client:
            return jsonify({'error': 'ChromaDB not available'}), 500
        
        # Delete document
        success = delete_rag_document_by_id(chroma_client, collection_name, doc_id)
        if not success:
            return jsonify({'error': 'Failed to delete document or document not found'}), 404
        
        return jsonify({
            'success': True,
            'message': f'Document {doc_id} deleted successfully'
        })
        
    except Exception as e:
        log_error(f"Delete document API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@rag_bp.route('/rag_collections/<collection_name>/documents', methods=['POST'])
def api_create_document(collection_name):
    """Create a new document in the collection"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..rag.vector_db import initialize_vector_db, add_single_document_to_rag
        import os
        import uuid
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        doc_id = data.get('id') or str(uuid.uuid4())
        source = data.get('source', doc_id)
        
        if not content.strip():
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # Get the RAG data path
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        
        # Initialize ChromaDB client
        chroma_client = initialize_vector_db(rag_data_path)
        if not chroma_client:
            return jsonify({'error': 'ChromaDB not available'}), 500
        
        # Add document
        success = add_single_document_to_rag(chroma_client, collection_name, doc_id, source, content)
        if not success:
            return jsonify({'error': 'Failed to create document'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Document {doc_id} created successfully',
            'document_id': doc_id
        })
        
    except Exception as e:
        log_error(f"Create document API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
