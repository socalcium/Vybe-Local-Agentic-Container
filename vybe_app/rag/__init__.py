"""
RAG module initialization - provides a unified interface for RAG functionality.
"""

from .web_search import perform_web_search, apply_post_retrieval_filtering, scrape_url_content
from .vector_db import (
    initialize_vector_db, 
    add_content_to_vector_db, 
    retrieve_relevant_chunks, 
    list_rag_documents_metadata,
    delete_rag_document_by_id,
    get_document_full_content,
    add_single_document_to_rag,
    update_document_in_rag
)
from .text_processing import (
    chunk_text, 
    process_pdf_content, 
    process_text_file,
    process_uploaded_file,
    ingest_file_content_to_rag,
    ingest_document,
    process_retrieved_documents_with_llm
)

__all__ = [
    'perform_web_search',
    'apply_post_retrieval_filtering', 
    'scrape_url_content',
    'initialize_vector_db',
    'add_content_to_vector_db',
    'retrieve_relevant_chunks',
    'chunk_text',
    'process_pdf_content',
    'process_text_file',
    'process_uploaded_file',
    'ingest_file_content_to_rag',
    'ingest_document',
    'process_retrieved_documents_with_llm',
    'list_rag_documents_metadata',
    'delete_rag_document_by_id',
    'get_document_full_content',
    'add_single_document_to_rag',
    'update_document_in_rag'
]
