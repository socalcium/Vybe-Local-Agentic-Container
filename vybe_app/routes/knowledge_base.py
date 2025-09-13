"""
Interactive Knowledge Base System
=================================
Transparent document and chunk management with user approval workflow
"""

import os
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from typing import List, Dict, Any, Optional

# Initialize Flask Blueprint
knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')

class DocumentManager:
    """Manages documents and chunks in the knowledge base"""
    
    def __init__(self, base_path: str = "rag_data/knowledge_base"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.documents_dir = self.base_path / "documents"
        self.chunks_dir = self.base_path / "chunks"
        self.documents_dir.mkdir(exist_ok=True)
        self.chunks_dir.mkdir(exist_ok=True)
        
        # Load existing documents
        self.documents_file = self.base_path / "documents.json"
        self.documents = self._load_documents()
    
    def _load_documents(self) -> Dict:
        """Load documents metadata from JSON file"""
        if self.documents_file.exists():
            try:
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading documents: {e}")
        return {}
    
    def _save_documents(self):
        """Save documents metadata to JSON file"""
        try:
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving documents: {e}")
    
    def add_document(self, title: str, content: str, source_type: str = "text", 
                    source_url: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        """Add a new document to the knowledge base"""
        
        # Input validation
        if not title or not title.strip():
            raise ValueError("Document title is required")
        
        if not content or not content.strip():
            raise ValueError("Document content is required")
        
        if len(title) > 500:
            raise ValueError("Document title too long (max 500 characters)")
        
        if len(content) > 10000000:  # 10MB limit
            raise ValueError("Document content too large (max 10MB)")
        
        # Sanitize inputs
        title = title.strip()
        content = content.strip()
        
        doc_id = str(uuid.uuid4())
        
        # Save document metadata
        doc_data = {
            "id": doc_id,
            "title": title,
            "source_type": source_type,
            "source_url": source_url,
            "metadata": metadata or {},
            "created_date": datetime.now().isoformat(),
            "chunk_count": 0
        }
        
        # Save full content to separate file
        content_file = self.base_path / f"{doc_id}_content.txt"
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create chunks
        chunks = self._create_chunks(content, doc_id)
        doc_data["chunk_count"] = len(chunks)
        
        # Save to documents registry
        self.documents[doc_id] = doc_data
        self._save_documents()
        
        print(f"Added document '{title}' with {len(chunks)} chunks")
        return doc_id
    
    def _create_chunks(self, content: str, doc_id: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
        """Create overlapping chunks from document content"""
        chunks = []
        
        # Simple chunking by characters with overlap
        for i in range(0, len(content), chunk_size - overlap):
            chunk_text = content[i:i + chunk_size]
            if len(chunk_text.strip()) < 50:  # Skip very short chunks
                continue
            
            chunk_id = f"{doc_id}_{len(chunks)}"
            chunk_data = {
                "id": chunk_id,
                "document_id": doc_id,
                "chunk_index": len(chunks),
                "text": chunk_text,
                "char_start": i,
                "char_end": i + len(chunk_text),
                "created_date": datetime.now().isoformat()
            }
            
            # Save chunk to file
            chunk_file = self.chunks_dir / f"{chunk_id}.json"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, indent=2, ensure_ascii=False)
            
            chunks.append(chunk_data)
        
        return chunks
    
    def get_document_chunks(self, doc_id: str) -> List[Dict]:
        """Get all chunks for a specific document"""
        chunks = []
        
        # Find all chunk files for this document
        for chunk_file in self.chunks_dir.glob(f"{doc_id}_*.json"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    chunks.append(chunk_data)
            except Exception as e:
                print(f"Error loading chunk {chunk_file}: {e}")
        
        # Sort by chunk index
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        return chunks
    
    def update_chunk(self, chunk_id: str, new_text: str) -> bool:
        """Update the text content of a specific chunk"""
        chunk_file = self.chunks_dir / f"{chunk_id}.json"
        
        if not chunk_file.exists():
            return False
        
        try:
            # Load existing chunk
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            # Update text and timestamp
            chunk_data['text'] = new_text
            chunk_data['modified_date'] = datetime.now().isoformat()
            
            # Save updated chunk
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, indent=2, ensure_ascii=False)
            
            print(f"Updated chunk {chunk_id}")
            return True
            
        except Exception as e:
            print(f"Error updating chunk {chunk_id}: {e}")
            return False
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a specific chunk"""
        chunk_file = self.chunks_dir / f"{chunk_id}.json"
        
        if chunk_file.exists():
            try:
                chunk_file.unlink()
                print(f"Deleted chunk {chunk_id}")
                return True
            except Exception as e:
                print(f"Error deleting chunk {chunk_id}: {e}")
        
        return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks"""
        if doc_id not in self.documents:
            return False
        
        try:
            # Delete all chunks
            chunks = self.get_document_chunks(doc_id)
            for chunk in chunks:
                self.delete_chunk(chunk['id'])
            
            # Delete content file
            content_file = self.base_path / f"{doc_id}_content.txt"
            if content_file.exists():
                content_file.unlink()
            
            # Remove from documents metadata
            del self.documents[doc_id]
            self._save_documents()
            
            print(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False
    
    def get_all_documents(self) -> List[Dict]:
        """Get metadata for all documents"""
        return list(self.documents.values())
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get metadata for a specific document"""
        return self.documents.get(doc_id)
    
    def search_documents(self, query: str) -> List[Dict]:
        """Search documents by title or content"""
        results = []
        query_lower = query.lower()
        
        for doc_id, doc_data in self.documents.items():
            # Check title match
            if query_lower in doc_data['title'].lower():
                results.append(doc_data)
                continue
            
            # Check content match in chunks
            chunks = self.get_document_chunks(doc_id)
            for chunk in chunks:
                if query_lower in chunk['text'].lower():
                    results.append(doc_data)
                    break
        
        return results

# Global document manager instance
doc_manager = DocumentManager()

@knowledge_bp.route('/')
def knowledge_dashboard():
    """Main knowledge base dashboard"""
    documents = doc_manager.get_all_documents()
    return render_template('knowledge/dashboard.html', documents=documents)

@knowledge_bp.route('/document/<doc_id>')
def view_document(doc_id):
    """View document details and chunks"""
    document = doc_manager.get_document(doc_id)
    if not document:
        return "Document not found", 404
    
    chunks = doc_manager.get_document_chunks(doc_id)
    return render_template('knowledge/document_detail.html', 
                         document=document, chunks=chunks)

@knowledge_bp.route('/add_text', methods=['GET', 'POST'])
def add_text_document():
    """Add a new text document"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400
        
        doc_id = doc_manager.add_document(
            title=title,
            content=content,
            source_type='text'
        )
        
        return redirect(url_for('knowledge.view_document', doc_id=doc_id))
    
    return render_template('knowledge/add_text.html')

@knowledge_bp.route('/api/chunk/<chunk_id>', methods=['PUT', 'DELETE'])
def manage_chunk(chunk_id):
    """Update or delete a specific chunk"""
    if request.method == 'PUT':
        data = request.get_json()
        new_text = data.get('text')
        
        if not new_text:
            return jsonify({'error': 'Text is required'}), 400
        
        success = doc_manager.update_chunk(chunk_id, new_text)
        return jsonify({'success': success})
    
    elif request.method == 'DELETE':
        success = doc_manager.delete_chunk(chunk_id)
        return jsonify({'success': success})
    
    return jsonify({'error': 'Method not allowed'}), 405

@knowledge_bp.route('/api/document/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document and all its chunks"""
    success = doc_manager.delete_document(doc_id)
    return jsonify({'success': success})

@knowledge_bp.route('/api/documents/search')
def search_documents():
    """Search documents by query"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    results = doc_manager.search_documents(query)
    return jsonify(results)

@knowledge_bp.route('/review_extraction', methods=['POST'])
def review_extraction():
    """Review extracted content before ingestion"""
    data = request.get_json()
    extracted_text = data.get('text', '')
    source_url = data.get('url', '')
    title = data.get('title', 'Extracted Content')
    
    # Return the extracted text for user review
    return render_template('knowledge/review_extraction.html',
                         text=extracted_text,
                         url=source_url,
                         title=title)

@knowledge_bp.route('/approve_ingestion', methods=['POST'])
def approve_ingestion():
    """Approve and ingest reviewed content"""
    title = request.form.get('title')
    content = request.form.get('content')
    source_url = request.form.get('source_url')
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    doc_id = doc_manager.add_document(
        title=title,
        content=content,
        source_type='url',
        source_url=source_url
    )
    
    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'message': 'Content successfully ingested into knowledge base'
    })
