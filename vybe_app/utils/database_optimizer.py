#!/usr/bin/env python3
"""
Database Optimization Utilities for Vybe AI Desktop Application
Addresses N+1 query problems, connection pooling, and performance optimization
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from functools import wraps
from contextlib import contextmanager
from sqlalchemy import text, Index, and_, or_
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
import time

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization utilities for performance improvement"""
    
    # Query performance tracking
    _query_stats = {
        'total_queries': 0,
        'slow_queries': 0,
        'n_plus_one_detected': 0,
        'cache_hits': 0,
        'cache_misses': 0
    }
    
    # Slow query threshold (in seconds)
    SLOW_QUERY_THRESHOLD = 1.0
    
    @classmethod
    def optimize_query(cls, query, eager_loads: Optional[List[Any]] = None, 
                      select_in_loads: Optional[List[Any]] = None,
                      subquery_loads: Optional[List[Any]] = None):
        """
        Optimize a SQLAlchemy query with appropriate eager loading
        
        Args:
            query: SQLAlchemy query object
            eager_loads: List of relationships to eager load with joinedload
            select_in_loads: List of relationships to eager load with selectinload
            subquery_loads: List of relationships to eager load with subqueryload
            
        Returns:
            Optimized query
        """
        try:
            # Apply joinedload for foreign key relationships
            if eager_loads:
                for relationship in eager_loads:
                    try:
                        query = query.options(joinedload(relationship))
                    except Exception as e:
                        logger.warning(f"Could not apply joinedload for {relationship}: {e}")
            
            # Apply selectinload for collections (prevents N+1)
            if select_in_loads:
                for relationship in select_in_loads:
                    try:
                        query = query.options(selectinload(relationship))
                    except Exception as e:
                        logger.warning(f"Could not apply selectinload for {relationship}: {e}")
            
            # Apply subqueryload for complex relationships
            if subquery_loads:
                for relationship in subquery_loads:
                    try:
                        query = query.options(subqueryload(relationship))
                    except Exception as e:
                        logger.warning(f"Could not apply subqueryload for {relationship}: {e}")
            
            return query
            
        except Exception as e:
            logger.error(f"Error optimizing query: {e}")
            return query
    
    @classmethod
    def batch_load_relationships(cls, model_class, ids: List[int], 
                               relationship_name: str, 
                               initial_batch_size: int = 1000):
        """
        Batch load relationships to prevent N+1 queries with adaptive batch sizing
        
        Args:
            model_class: SQLAlchemy model class
            ids: List of primary key IDs
            relationship_name: Name of the relationship to load
            initial_batch_size: Initial size of each batch (will be adapted based on memory usage)
            
        Returns:
            Dict mapping ID to relationship data
        """
        try:
            results = {}
            current_batch_size = initial_batch_size
            min_batch_size = 10  # Minimum batch size to prevent infinite reduction
            max_retries = 3  # Maximum number of retries for a single batch
            
            i = 0
            while i < len(ids):
                batch_ids = ids[i:i + current_batch_size]
                retry_count = 0
                batch_processed = False
                
                while not batch_processed and retry_count < max_retries:
                    try:
                        # Use selectinload for efficient batch loading
                        query = model_class.query.filter(
                            model_class.id.in_(batch_ids)
                        )
                        # Try to apply selectinload if relationship exists
                        if hasattr(model_class, relationship_name):
                            query = query.options(selectinload(getattr(model_class, relationship_name)))
                        
                        batch_results = query.all()
                        
                        # Build results dictionary
                        for item in batch_results:
                            results[item.id] = getattr(item, relationship_name)
                        
                        batch_processed = True
                        logger.debug(f"Successfully processed batch of {len(batch_ids)} items")
                        
                    except (MemoryError, Exception) as e:
                        error_str = str(e).lower()
                        is_memory_related = (
                            isinstance(e, MemoryError) or
                            any(term in error_str for term in ['memory', 'out of memory', 'cannot allocate'])
                        )
                        
                        if is_memory_related and current_batch_size > min_batch_size:
                            # Reduce batch size on memory-related errors
                            current_batch_size = max(min_batch_size, current_batch_size // 2)
                            logger.warning(f"Memory-related error detected, reducing batch size to {current_batch_size}: {e}")
                            
                            # Adjust current batch to new size
                            batch_ids = ids[i:i + current_batch_size]
                            retry_count += 1
                        else:
                            # For non-memory errors or when we can't reduce further, try without selectinload
                            logger.warning(f"Could not apply selectinload for {relationship_name}: {e}")
                            try:
                                batch_results = model_class.query.filter(model_class.id.in_(batch_ids)).all()
                                
                                # Build results dictionary
                                for item in batch_results:
                                    results[item.id] = getattr(item, relationship_name)
                                
                                batch_processed = True
                            except Exception as fallback_error:
                                logger.error(f"Fallback query also failed for batch: {fallback_error}")
                                # Skip this batch to prevent infinite loop
                                batch_processed = True
                
                if not batch_processed:
                    logger.error(f"Failed to process batch after {max_retries} attempts, skipping batch")
                
                # Move to next batch
                i += len(batch_ids)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch loading relationships: {e}")
            return {}
    
    @classmethod
    def create_composite_indexes(cls, model_class, indexes: List[Tuple[str, ...]]):
        """
        Create composite indexes for common query patterns
        
        Args:
            model_class: SQLAlchemy model class
            indexes: List of column tuples for composite indexes
        """
        try:
            for i, columns in enumerate(indexes):
                index_name = f"idx_{model_class.__tablename__}_{'_'.join(columns)}_{i}"
                index = Index(index_name, *columns)
                index.create(current_app.extensions['sqlalchemy'].db.engine)
                logger.info(f"Created composite index: {index_name}")
                
        except Exception as e:
            logger.error(f"Error creating composite indexes: {e}")
    
    @classmethod
    def analyze_query_performance(cls, query_func):
        """
        Decorator to analyze query performance and detect N+1 problems
        
        Args:
            query_func: Function that executes database queries
            
        Returns:
            Decorated function with performance monitoring
        """
        @wraps(query_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            initial_queries = cls._query_stats['total_queries']
            
            try:
                result = query_func(*args, **kwargs)
                
                # Calculate performance metrics
                execution_time = time.time() - start_time
                queries_executed = cls._query_stats['total_queries'] - initial_queries
                
                # Detect potential N+1 problems
                if queries_executed > 10:  # Threshold for N+1 detection
                    cls._query_stats['n_plus_one_detected'] += 1
                    logger.warning(f"Potential N+1 query detected in {query_func.__name__}: "
                                 f"{queries_executed} queries executed")
                
                # Log slow queries
                if execution_time > cls.SLOW_QUERY_THRESHOLD:
                    cls._query_stats['slow_queries'] += 1
                    logger.warning(f"Slow query detected in {query_func.__name__}: "
                                 f"{execution_time:.3f}s, {queries_executed} queries")
                
                return result
                
            except Exception as e:
                logger.error(f"Query execution failed in {query_func.__name__}: {e}")
                raise
                
        return wrapper
    
    @classmethod
    def get_query_stats(cls) -> Dict[str, Any]:
        """Get current query performance statistics"""
        return cls._query_stats.copy()
    
    @classmethod
    def reset_query_stats(cls):
        """Reset query performance statistics"""
        cls._query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'n_plus_one_detected': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }


class QueryCache:
    """Simple query result caching to reduce database load"""
    
    _cache = {}
    _cache_stats = {
        'hits': 0,
        'misses': 0,
        'evictions': 0
    }
    
    @classmethod
    def get(cls, key: str, ttl: int = 300):
        """
        Get cached query result
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            Cached result or None if not found/expired
        """
        if key in cls._cache:
            result, timestamp = cls._cache[key]
            if time.time() - timestamp < ttl:
                cls._cache_stats['hits'] += 1
                return result
            else:
                # Expired, remove from cache
                del cls._cache[key]
                cls._cache_stats['evictions'] += 1
        
        cls._cache_stats['misses'] += 1
        return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 300):
        """
        Cache query result
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        cls._cache[key] = (value, time.time())
        
        # Simple cache eviction (remove oldest entries if cache is too large)
        if len(cls._cache) > 1000:
            oldest_key = min(cls._cache.keys(), 
                           key=lambda k: cls._cache[k][1])
            del cls._cache[oldest_key]
            cls._cache_stats['evictions'] += 1
    
    @classmethod
    def invalidate(cls, pattern: Optional[str] = None):
        """
        Invalidate cache entries
        
        Args:
            pattern: Pattern to match keys (if None, invalidate all)
        """
        if pattern is None:
            cls._cache.clear()
        else:
            keys_to_remove = [k for k in cls._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del cls._cache[key]
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(cls._cache),
            'hits': cls._cache_stats['hits'],
            'misses': cls._cache_stats['misses'],
            'evictions': cls._cache_stats['evictions'],
            'hit_rate': (cls._cache_stats['hits'] / 
                        (cls._cache_stats['hits'] + cls._cache_stats['misses'])) 
                        if (cls._cache_stats['hits'] + cls._cache_stats['misses']) > 0 else 0
        }


class DatabaseConnectionPool:
    """Database connection pool management"""
    
    @staticmethod
    def configure_pool(app, pool_size: int = 10, max_overflow: int = 20,
                      pool_timeout: int = 30, pool_recycle: int = 3600):
        """
        Configure database connection pool
        
        Args:
            app: Flask application
            pool_size: Number of connections to maintain
            max_overflow: Additional connections when pool is full
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after specified seconds
        """
        try:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'poolclass': 'QueuePool',
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'pool_timeout': pool_timeout,
                'pool_recycle': pool_recycle,
                'pool_pre_ping': True,
                'echo': False
            }
            logger.info("Database connection pool configured successfully")
            
        except Exception as e:
            logger.error(f"Error configuring database connection pool: {e}")
    
    @staticmethod
    def get_pool_status(app) -> Dict[str, Any]:
        """
        Get database connection pool status
        
        Args:
            app: Flask application
            
        Returns:
            Pool status information
        """
        try:
            engine = app.extensions['sqlalchemy'].db.engine
            pool = engine.pool
            
            return {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid()
            }
            
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {}


class TransactionManager:
    """Database transaction management with automatic rollback"""
    
    @staticmethod
    @contextmanager
    def transaction():
        """
        Context manager for database transactions with automatic rollback on error
        
        Usage:
            with TransactionManager.transaction():
                # Database operations
                pass
        """
        try:
            from ..models import db
        except ImportError:
            logger.error("Failed to import database models")
            raise
        
        try:
            yield db.session
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database transaction failed, rolled back: {e}")
            raise
    
    @staticmethod
    def safe_operation(operation_func):
        """
        Decorator for safe database operations
        
        Args:
            operation_func: Function that performs database operations
            
        Returns:
            Decorated function with transaction management
        """
        @wraps(operation_func)
        def wrapper(*args, **kwargs):
            with TransactionManager.transaction():
                return operation_func(*args, **kwargs)
        return wrapper


# Performance monitoring decorator
def monitor_query_performance(func):
    """
    Decorator to monitor query performance
    
    Args:
        func: Function to monitor
        
    Returns:
        Decorated function with performance monitoring
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow operations
            if execution_time > DatabaseOptimizer.SLOW_QUERY_THRESHOLD:
                logger.warning(f"Slow operation detected in {func.__name__}: {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Operation failed in {func.__name__}: {e}")
            raise
    
    return wrapper


# Cache decorator
def cache_query_result(ttl: int = 300, key_func=None):
    """
    Decorator to cache query results
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from function arguments
        
    Returns:
        Decorated function with caching
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = QueryCache.get(cache_key, ttl)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            QueryCache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Adaptive batch processing utility
def adaptive_batch_process(items: List[Any], initial_batch_size: int = 1000, 
                          process_func=None, progress_callback=None):
    """
    Process items in batches with adaptive batch sizing to avoid memory issues
    
    Args:
        items: List of items to process
        initial_batch_size: Initial size of each batch (will be adapted)
        process_func: Function to process each batch
        progress_callback: Callback function for progress updates
        
    Returns:
        List of processed results
    """
    results = []
    current_batch_size = initial_batch_size
    min_batch_size = 1  # Minimum batch size
    max_retries = 3  # Maximum retries per batch
    
    i = 0
    total_items = len(items)
    
    while i < total_items:
        batch = items[i:i + current_batch_size]
        retry_count = 0
        batch_processed = False
        
        while not batch_processed and retry_count < max_retries:
            try:
                if progress_callback:
                    progress = (i + len(batch)) / total_items * 100
                    progress_callback(progress, len(batch), current_batch_size)
                
                if process_func:
                    batch_results = process_func(batch)
                    if isinstance(batch_results, list):
                        results.extend(batch_results)
                    else:
                        results.append(batch_results)
                else:
                    results.extend(batch)
                
                batch_processed = True
                logger.debug(f"Successfully processed batch of {len(batch)} items")
                
            except (MemoryError, Exception) as e:
                error_str = str(e).lower()
                is_memory_related = (
                    isinstance(e, MemoryError) or
                    any(term in error_str for term in ['memory', 'out of memory', 'cannot allocate'])
                )
                
                if is_memory_related and current_batch_size > min_batch_size:
                    # Reduce batch size on memory-related errors
                    current_batch_size = max(min_batch_size, current_batch_size // 2)
                    logger.warning(f"Memory-related error detected, reducing batch size to {current_batch_size}: {e}")
                    
                    # Adjust current batch to new size
                    batch = items[i:i + current_batch_size]
                    retry_count += 1
                else:
                    # For non-memory errors or minimum batch size reached
                    logger.error(f"Failed to process batch: {e}")
                    if current_batch_size == min_batch_size:
                        # Skip this item if we can't process even single items
                        logger.error(f"Skipping item at index {i} due to persistent error")
                        batch_processed = True
                        current_batch_size = 1  # Ensure we only skip one item
                    else:
                        retry_count += 1
        
        if not batch_processed:
            logger.error(f"Failed to process batch after {max_retries} attempts, skipping batch")
        
        # Move to next batch
        i += len(batch)
    
    return results


# Original batch processing utility (maintained for compatibility)
def batch_process(items: List[Any], batch_size: int = 1000, 
                 process_func=None, progress_callback=None):
    """
    Process items in batches to avoid memory issues
    
    Args:
        items: List of items to process
        batch_size: Size of each batch
        process_func: Function to process each batch
        progress_callback: Callback function for progress updates
        
    Returns:
        List of processed results
    """
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        if progress_callback:
            progress_callback(batch_num, total_batches)
        
        if process_func:
            batch_results = process_func(batch)
            results.extend(batch_results)
        else:
            results.extend(batch)
    
    return results
