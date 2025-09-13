"""
Text processing utilities for RAG functionality.
"""

import os
import PyPDF2
from typing import List, Dict, Optional, Any


def process_document_with_llm(content: str, filename: str, backend_llm_controller) -> Dict[str, str]:
    """
    Process a document using the backend LLM to generate summary and tags.
    
    Args:
        content: The text content to process
        filename: Name of the file being processed
        backend_llm_controller: Instance of BackendLLMController
        
    Returns:
        Dictionary with 'summary' and 'tags' keys
    """
    try:
        # Generate summary using backend LLM
        summary = backend_llm_controller.generate_summary(content, filename)
        
        # Generate tags using backend LLM
        tags = backend_llm_controller.generate_tags(content, filename)
        
        return {
            'summary': summary,
            'tags': tags
        }
    except Exception as e:
        print(f"Error processing document with LLM: {e}")
        return {
            'summary': f"Auto-generated summary for {filename}",
            'tags': "document,text"
        }

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Splits a long text string into smaller, overlapping chunks.
    """
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start += (chunk_size - chunk_overlap)
    return chunks

def process_pdf_content(file_path: str) -> Optional[str]:
    """
    Extracts text content from a PDF file.
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            return text_content.strip()
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        return None

def process_text_file(file_path: str) -> Optional[str]:
    """
    Reads and returns the content of a text file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return None

def process_uploaded_file(file_obj, filename: str) -> Optional[str]:
    """
    Process an uploaded file and extract text content.
    Supports .txt, .md, and .pdf files.
    
    Args:
        file_obj: File object from Flask request.files
        filename: Name of the uploaded file
        
    Returns:
        Extracted text content or None if processing failed
    """
    try:
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension in ['.txt', '.md']:
            # Read text files directly
            content = file_obj.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            return content
            
        elif file_extension == '.pdf':
            # Extract text from PDF
            try:
                pdf_reader = PyPDF2.PdfReader(file_obj)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                return text_content.strip()
            except Exception as e:
                print(f"Error processing PDF {filename}: {e}")
                return None
                
        else:
            print(f"Unsupported file type: {file_extension}")
            return None
            
    except Exception as e:
        print(f"Error processing file {filename}: {e}")
        return None

def ingest_file_content_to_rag(collection_name: str, filename: str, content: str) -> bool:
    """
    Ingest text content from a file into a RAG collection.
    
    Args:
        collection_name: Name of the RAG collection
        filename: Original filename (used as source identifier)
        content: Text content to ingest
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not content or not content.strip():
            print(f"Warning: Empty content for file {filename}")
            return False
            
        # Import here to avoid circular imports
        from .vector_db import initialize_vector_db, add_content_to_vector_db
            
        # Initialize ChromaDB client
        rag_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag_data', 'chroma_db')
        chroma_client = initialize_vector_db(rag_data_path)
        if not chroma_client:
            return False
            
        # Create or get collection
        try:
            from .vector_db import get_connection_pool
            
            # Get connection pool and client
            pool = get_connection_pool()
            if not pool:
                print(f"Error: Could not get connection pool for ChromaDB")
                return False
                
            with pool.get_connection() as client:
                if not client:
                    print(f"Error: Could not get ChromaDB client from pool")
                    return False
                    
                collection = client.get_or_create_collection(name=collection_name)
                
                # Split content into chunks
                chunks = chunk_text(content)
                if not chunks:
                    print(f"Warning: No chunks generated from file {filename}")
                    return False
                    
                # Add to ChromaDB using the proper client
                success = add_content_to_vector_db(client, collection_name, filename, chunks)
                return success
                
        except Exception as e:
            print(f"Error creating/accessing collection {collection_name}: {e}")
            return False
        
    except Exception as e:
        print(f"Error ingesting file content {filename}: {e}")
        return False

def ingest_document(chroma_client: Any, collection_name: str, file_path: str) -> bool:
    """
    Helper function to ingest a single document into ChromaDB.
    Supports .txt, .md files for now.
    
    Args:
        chroma_client: ChromaDB client instance
        collection_name: Name of the collection to add to
        file_path: Path to the file to ingest
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check file extension
        if not file_path.lower().endswith(('.txt', '.md')):
            print(f"Skipping unsupported file type: {file_path}")
            return False
            
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content.strip():
            print(f"Warning: File {file_path} is empty or contains no readable content")
            return False
        
        # Chunk the content
        chunks = chunk_text(content)
        if not chunks:
            print(f"Warning: No chunks generated from {file_path}")
            return False
        
        # Import here to avoid circular imports
        from .vector_db import add_content_to_vector_db
        
        # Add to ChromaDB
        success = add_content_to_vector_db(chroma_client, collection_name, file_path, chunks)
        return success
        
    except Exception as e:
        print(f"Error ingesting document {file_path}: {e}")
        return False

def process_retrieved_documents_with_llm(documents_list: List[str], user_query: str, llm_api_url: str = "http://localhost:11435/v1/chat/completions", model: str = "local") -> str:
    """
    Processes retrieved RAG documents through an LLM to refine and extract relevant information.
    
    Args:
        documents_list: List of raw document snippets (strings)
        user_query: The user's original query for context
        llm_api_url: LLM API endpoint
        model: The LLM model to use for refinement
    
    Returns:
        Refined string containing only relevant information, or empty string on error
    """
    import requests
    import json
    
    if not documents_list:
        return ""
    
    # Construct the refinement system prompt
    system_prompt = """You are a data refiner. Your job is to analyze the provided documents and extract only the most relevant and concise information that directly answers or relates to the user's query.

Instructions:
- Read the provided documents carefully
- Consider the user's query context
- Extract only the most relevant and factual information from the documents
- If no relevant information is found, respond with "No relevant information found in the provided documents."
- Maintain factual accuracy from the original documents
- Avoid conversational filler; provide only the refined content
- Be concise but comprehensive
- Do not add information not present in the documents"""

    # Combine all documents into a single text block
    combined_documents = "\n\n--- Document ---\n".join(documents_list)
    
    # Construct the user message with query and documents
    user_content = f"User Query: {user_query}\n\nDocuments to analyze:\n{combined_documents}\n\nPlease extract and refine the most relevant information from these documents that relates to the user's query."
    
    # Prepare the payload for LLM backend
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "stream": False,  # Non-streaming request
        "options": {"temperature": 0.1}  # Low temperature for consistency
    }
    
    try:
        response = requests.post(llm_api_url, json=payload, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        refined_content = response_data.get('message', {}).get('content', '')
        
        if refined_content.strip():
            print(f"RAG refinement successful: {len(refined_content)} characters processed")
            return refined_content.strip()
        else:
            print("Warning: LLM returned empty response for RAG refinement")
            return ""
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM backend for RAG refinement: {e}")
        return ""
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM backend response for RAG refinement: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error during RAG refinement: {e}")
        return ""

# For compatibility with existing imports
list_rag_documents_metadata = None  # This will be imported from vector_db when needed
