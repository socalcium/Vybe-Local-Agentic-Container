"""
Enhanced Vector database operations for RAG functionality with connection pooling.
"""

import os
import time
import threading
import chromadb
from queue import Queue, Empty
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class VectorDBConnectionPool:
    """Connection pool for ChromaDB operations with health checks and retry logic"""
    
    def __init__(self, db_path: str, pool_size: int = 10, max_retries: int = 3, 
                 health_check_interval: int = 300):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.health_check_interval = health_check_interval
        
        # Connection pool
        self.pool = Queue(maxsize=pool_size)
        self.active_connections = set()
        self.pool_lock = threading.Lock()
        
        # Health monitoring
        self.connection_stats = {
            'total_created': 0,
            'total_errors': 0,
            'active_count': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'last_health_check': None
        }
        
        # Initialize pool
        self._initialize_pool()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_running = True
        self.health_check_thread.start()
    
    def _initialize_pool(self):
        """Initialize the connection pool with ChromaDB clients"""
        try:
            os.makedirs(self.db_path, exist_ok=True)
            
            for _ in range(self.pool_size):
                client = self._create_client()
                if client:
                    self.pool.put(client)
                    self.connection_stats['total_created'] += 1
            
            logger.info(f"ChromaDB connection pool initialized with {self.pool.qsize()} connections")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB connection pool: {e}")
            self.connection_stats['total_errors'] += 1
    
    def _create_client(self) -> Optional[Any]:
        """Create a new ChromaDB client"""
        try:
            client = chromadb.PersistentClient(path=self.db_path)
            return client
        except Exception as e:
            logger.error(f"Error creating ChromaDB client: {e}")
            self.connection_stats['total_errors'] += 1
            return None
    
    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """Get a connection from the pool with automatic return"""
        client = None
        start_time = time.time()
        
        try:
            # Try to get from pool first
            try:
                client = self.pool.get(timeout=timeout)
                self.connection_stats['pool_hits'] += 1
            except Empty:
                # Pool is empty, create new connection
                client = self._create_client()
                if not client:
                    raise Exception("Failed to create new ChromaDB connection")
                self.connection_stats['pool_misses'] += 1
            
            # Track active connection
            with self.pool_lock:
                self.active_connections.add(client)
                self.connection_stats['active_count'] = len(self.active_connections)
            
            # Test connection health
            if not self._test_connection(client):
                raise Exception("Connection health check failed")
            
            yield client
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_stats['total_errors'] += 1
            
            # If connection failed, try to create a new one
            if client is None:
                client = self._create_client()
                if client:
                    yield client
                else:
                    raise e
            else:
                raise e
        
        finally:
            # Return connection to pool
            if client:
                with self.pool_lock:
                    self.active_connections.discard(client)
                    self.connection_stats['active_count'] = len(self.active_connections)
                
                # Only return to pool if it's not full and connection is healthy
                if not self.pool.full() and self._test_connection(client):
                    self.pool.put(client)
                else:
                    # Connection is unhealthy or pool is full, let it be garbage collected
                    pass
    
    def _test_connection(self, client: Any) -> bool:
        """Test if a connection is healthy"""
        try:
            # Simple test - try to list collections
            client.list_collections()
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False
    
    def _health_check_loop(self):
        """Background health check for connections"""
        while self.health_check_running:
            try:
                self._perform_health_check()
                self.connection_stats['last_health_check'] = datetime.utcnow()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(30)  # Shorter retry interval on error
    
    def _perform_health_check(self):
        """Perform comprehensive health check"""
        with self.pool_lock:
            unhealthy_connections = []
            
            # Check all active connections
            for client in list(self.active_connections):
                if not self._test_connection(client):
                    unhealthy_connections.append(client)
            
            # Remove unhealthy connections
            for client in unhealthy_connections:
                self.active_connections.discard(client)
                logger.warning("Removed unhealthy connection from active set")
            
            self.connection_stats['active_count'] = len(self.active_connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self.pool_lock:
            return {
                **self.connection_stats,
                'pool_size': self.pool_size,
                'available_connections': self.pool.qsize(),
                'active_connections': len(self.active_connections),
                'last_health_check': self.connection_stats['last_health_check'].isoformat() 
                                   if self.connection_stats['last_health_check'] else None
            }
    
    def close(self):
        """Close the connection pool and cleanup resources"""
        self.health_check_running = False
        if self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
        
        # Close all connections
        while not self.pool.empty():
            try:
                client = self.pool.get_nowait()
                # ChromaDB clients don't have explicit close methods
                del client
            except Empty:
                break
        
        with self.pool_lock:
            self.active_connections.clear()
        
        logger.info("ChromaDB connection pool closed")


# Global connection pool instance
_connection_pool: Optional[VectorDBConnectionPool] = None


def initialize_vector_db(path: str, pool_size: int = 10) -> bool:
    """
    Initialize the global ChromaDB connection pool.
    """
    global _connection_pool
    
    try:
        _connection_pool = VectorDBConnectionPool(path, pool_size=pool_size)
        logger.info(f"ChromaDB connection pool initialized successfully at {path}")
        return True
    except Exception as e:
        logger.error(f"Error initializing ChromaDB connection pool at {path}: {e}")
        return False


def get_connection_pool() -> Optional[VectorDBConnectionPool]:
    """Get the global connection pool instance"""
    return _connection_pool

def ensure_agent_memory_collection() -> bool:
    """
    Ensure the agent_memory collection exists and is properly configured using connection pool
    """
    if not _connection_pool:
        logger.error("Connection pool not initialized")
        return False
    
    try:
        with _connection_pool.get_connection() as client:
            # Create or get agent memory collection
            collection = client.get_or_create_collection(
                name="agent_memory",
                metadata={
                    "description": "Long-term memory for autonomous agents",
                    "created_at": datetime.now().isoformat()
                }
            )
            logger.info("Agent memory collection initialized successfully.")
            return True
    except Exception as e:
        logger.error(f"Error initializing agent memory collection: {e}")
        return False

def store_agent_memory(memory_id: str, content: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Store an agent memory in the agent_memory collection using connection pool
    
    Args:
        memory_id: Unique identifier for this memory
        content: The memory content (summary, experience, learned knowledge)
        metadata: Additional metadata (agent_id, task_type, success, etc.)
    
    Returns:
        bool: Success status
    """
    if not _connection_pool:
        logger.error("Connection pool not initialized")
        return False
    
    try:
        with _connection_pool.get_connection() as client:
            collection = client.get_or_create_collection(name="agent_memory")
            
            # Prepare metadata
            memory_metadata = {
                "stored_at": datetime.now().isoformat(),
                "memory_type": "agent_experience",
                **(metadata or {})
            }
            
            # Store the memory
            collection.add(
                documents=[content],
                metadatas=[memory_metadata],
                ids=[memory_id]
            )
            
            logger.info(f"Stored agent memory: {memory_id}")
            return True
        
    except Exception as e:
        logger.error(f"Error storing agent memory {memory_id}: {e}")
        return False

def retrieve_agent_memories(query: str, 
                           agent_id: Optional[str] = None,
                           memory_type: Optional[str] = None,
                           n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve relevant agent memories based on query using connection pool
    
    Args:
        query: Query to search for relevant memories
        agent_id: Optional filter by specific agent
        memory_type: Optional filter by memory type
        n_results: Number of results to return
    
    Returns:
        List of memory dictionaries with content and metadata
    """
    if not _connection_pool:
        logger.error("Connection pool not initialized")
        return []
    
    try:
        with _connection_pool.get_connection() as client:
            collection = client.get_collection(name="agent_memory")
            
            # Build where clause for filtering
            where_clause = {}
            if agent_id:
                where_clause["agent_id"] = agent_id
            if memory_type:
                where_clause["memory_type"] = memory_type
            
            # Query the collection
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            memories = []
            if results and "documents" in results and results["documents"]:
                documents = results["documents"][0]
                metadatas = results.get("metadatas", [None])[0] or []
                distances = results.get("distances", [None])[0] or []
                ids = results.get("ids", [None])[0] or []
                
                for i, doc in enumerate(documents):
                    memory = {
                        "id": ids[i] if i < len(ids) else f"memory_{i}",
                        "content": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "relevance_score": 1 - distances[i] if i < len(distances) else 0.0
                    }
                    memories.append(memory)
            
            logger.info(f"Retrieved {len(memories)} agent memories for query: {query[:50]}...")
            return memories
        
    except Exception as e:
        logger.error(f"Error retrieving agent memories: {e}")
        return []

def get_agent_memory_stats(chroma_client: Any, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics about agent memories
    
    Args:
        chroma_client: ChromaDB client
        agent_id: Optional specific agent ID to get stats for
    
    Returns:
        Dictionary with memory statistics
    """
    try:
        collection = chroma_client.get_collection(name="agent_memory")
        
        # Get all memories (or filtered by agent)
        where_clause = {"agent_id": agent_id} if agent_id else None
        
        results = collection.get(
            where=where_clause,
            include=["metadatas"]
        )
        
        total_memories = len(results.get("ids", []))
        metadatas = results.get("metadatas", [])
        
        # Analyze memory types
        memory_types = {}
        agent_counts = {}
        
        for metadata in metadatas:
            if metadata:
                # Count memory types
                mem_type = metadata.get("memory_type", "unknown")
                memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                
                # Count per agent
                agent = metadata.get("agent_id", "unknown")
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        stats = {
            "total_memories": total_memories,
            "memory_types": memory_types,
            "agent_counts": agent_counts if not agent_id else {agent_id: total_memories},
            "collection_exists": True
        }
        
        return stats
        
    except Exception as e:
        print(f"Error getting agent memory stats: {e}")
        return {
            "total_memories": 0,
            "memory_types": {},
            "agent_counts": {},
            "collection_exists": False,
            "error": str(e)
        }

def add_content_to_vector_db(chroma_client: Any, collection_name: str, content_id: str, text_chunks: List[str]) -> bool:
    """
    Adds text chunks to a ChromaDB collection.
    """
    try:
        collection = chroma_client.get_or_create_collection(name=collection_name)
        if not text_chunks:
            print(f"Warning: No text chunks to add for {content_id}.")
            return False
        documents = []
        metadatas = []
        ids = []
        for i, chunk in enumerate(text_chunks):
            documents.append(chunk)
            metadatas.append({"source": content_id, "chunk_id": f"{content_id}_{i}"})
            ids.append(f"{content_id}_{i}")
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            print(f"Added {len(documents)} chunks from {content_id} to ChromaDB collection '{collection_name}'.")
            return True
        return False
    except Exception as e:
        print(f"Error adding content to ChromaDB for {content_id}: {e}")
        return False

def retrieve_relevant_chunks(chroma_client: Any, collection_name: str, query_text: str, n_results: int = 5) -> List[str]:
    """
    Queries the ChromaDB collection for relevant text chunks.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return []
    try:
        collection = chroma_client.get_collection(name=collection_name)
        results = collection.query(query_texts=[query_text], n_results=n_results)
        return results['documents'][0] if results and results['documents'] else []
    except Exception as e:
        print(f"Error retrieving from ChromaDB collection '{collection_name}': {e}")
        return []

def list_rag_documents_metadata(chroma_client: Any, collection_name: str) -> List[Dict[str, str]]:
    """
    Lists all documents in the RAG knowledge base with metadata.
    Returns a list of dicts with id, source, and snippet.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return []
    
    try:
        # Try to get the collection, create it if it doesn't exist
        try:
            collection = chroma_client.get_collection(name=collection_name)
        except Exception as get_error:
            print(f"Collection '{collection_name}' does not exist, creating it...")
            collection = chroma_client.get_or_create_collection(name=collection_name)
            print(f"Created collection '{collection_name}' successfully.")
        
        # Get all documents from the collection
        results = collection.get()
        
        documents = []
        if results and results['ids']:
            for i, doc_id in enumerate(results['ids']):
                doc_text = results['documents'][i] if i < len(results['documents']) else ""
                metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
                
                # Create snippet (first 200 characters)
                snippet = doc_text[:200] + "..." if len(doc_text) > 200 else doc_text
                
                documents.append({
                    'id': doc_id,
                    'source': metadata.get('source', 'Unknown'),
                    'snippet': snippet
                })
        
        return documents
    except Exception as e:
        print(f"Error listing documents from ChromaDB collection '{collection_name}': {e}")
        # Don't raise the exception, just return empty list to maintain API contract
        return []

def delete_rag_document_by_id(chroma_client: Any, collection_name: str, doc_id: str) -> bool:
    """
    Deletes a specific document from the ChromaDB collection by ID.
    Returns True if successful, False otherwise.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return False
    
    try:
        collection = chroma_client.get_collection(name=collection_name)
        collection.delete(ids=[doc_id])
        print(f"Successfully deleted document {doc_id} from collection '{collection_name}'")
        return True
    except Exception as e:
        print(f"Error deleting document {doc_id} from ChromaDB collection '{collection_name}': {e}")
        return False

def get_document_full_content(chroma_client: Any, collection_name: str, doc_id: str) -> Optional[Dict[str, str]]:
    """
    Retrieves the full content of a document by reconstructing all its chunks.
    Returns a dict with 'id', 'source', and 'content' or None if not found.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return None
    
    try:
        collection = chroma_client.get_collection(name=collection_name)
        
        # Get all chunks for this document (chunks have IDs like doc_id_0, doc_id_1, etc.)
        results = collection.get()
        
        if not results or not results['ids']:
            return None
        
        # Find all chunks that belong to this document
        document_chunks = []
        source = None
        
        for i, chunk_id in enumerate(results['ids']):
            # Check if this chunk belongs to our document
            if chunk_id.startswith(f"{doc_id}_"):
                chunk_text = results['documents'][i] if i < len(results['documents']) else ""
                metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
                
                # Extract chunk number for proper ordering
                try:
                    chunk_num = int(chunk_id.split('_')[-1])
                    document_chunks.append((chunk_num, chunk_text))
                    if source is None:
                        source = metadata.get('source', doc_id)
                except (ValueError, IndexError):
                    # If we can't parse chunk number, just append at the end
                    document_chunks.append((999999, chunk_text))
        
        if not document_chunks:
            return None
        
        # Sort chunks by their number and reconstruct full content
        document_chunks.sort(key=lambda x: x[0])
        full_content = ' '.join([chunk[1] for chunk in document_chunks])
        
        return {
            'id': doc_id,
            'source': source or doc_id,
            'content': full_content
        }
        
    except Exception as e:
        print(f"Error retrieving document {doc_id} from collection '{collection_name}': {e}")
        return None

def add_single_document_to_rag(chroma_client: Any, collection_name: str, doc_id: str, source: str, content: str) -> bool:
    """
    Adds a single document with specified ID to the RAG collection.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return False
    
    try:
        # Import here to avoid circular imports
        from .text_processing import chunk_text
        
        # Chunk the content
        chunks = chunk_text(content)
        if not chunks:
            print(f"Warning: No chunks generated from content")
            return False
        
        # Add to ChromaDB using the specific doc_id
        success = add_content_to_vector_db(chroma_client, collection_name, doc_id, chunks)
        return success
        
    except Exception as e:
        print(f"Error adding document {doc_id} to collection '{collection_name}': {e}")
        return False

def update_document_in_rag(chroma_client: Any, collection_name: str, doc_id: str, new_source: str, new_content: str) -> bool:
    """
    Updates an existing document by deleting the old version and adding the new content.
    """
    if not chroma_client:
        print("Error: ChromaDB client is not initialized.")
        return False
    
    try:
        # First, delete the existing document
        delete_success = delete_rag_document_by_id(chroma_client, collection_name, doc_id)
        if not delete_success:
            print(f"Warning: Could not delete existing document {doc_id}, proceeding with add...")
        
        # Then add the new content
        add_success = add_single_document_to_rag(chroma_client, collection_name, doc_id, new_source, new_content)
        return add_success
        
    except Exception as e:
        print(f"Error updating document {doc_id} in collection '{collection_name}': {e}")
        return False
