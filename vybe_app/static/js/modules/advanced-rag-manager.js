/**
 * Advanced RAG Manager
 * Enhanced document processing, intelligent chunking, and sophisticated retrieval
 */

export class AdvancedRAGManager {
    constructor() {
        this.documents = new Map();
        this.collections = new Map();
        this.processingQueue = [];
        this.activeProcessors = new Set();
        this.chunkingStrategies = new Map();
        this.retrievalMethods = new Map();
        
        // Search optimizations
        this.searchWorker = null;
        this.searchCache = new Map();
        this.maxCacheSize = 50;
        this.currentSearchId = 0;
        this.searchPagination = {
            currentPage: 1,
            itemsPerPage: 20,
            totalResults: 0,
            totalPages: 0
        };
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        // Terminate search worker
        if (this.searchWorker) {
            this.searchWorker.terminate();
            this.searchWorker = null;
        }
        
        // Clear caches
        this.searchCache.clear();
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
    }


    init() {
        this.setupChunkingStrategies();
        this.setupRetrievalMethods();
        this.initializeSearchWorker();
        this.setupEventListeners();
        this.initializeUI();
    }

    initializeSearchWorker() {
        try {
            // Initialize Web Worker for search operations
            this.searchWorker = new Worker('/static/js/workers/search_worker.js');
            
            this.searchWorker.onmessage = (event) => {
                this.handleWorkerMessage(event.data);
            };
            
            this.searchWorker.onerror = (error) => {
                console.error('Search worker error:', error);
                window.notificationManager?.showError('Search worker encountered an error');
            };
            
            console.log('[AdvancedRAGManager] Search worker initialized');
        } catch (error) {
            console.error('Failed to initialize search worker:', error);
            // Fallback to main thread search
            this.searchWorker = null;
        }
    }

    handleWorkerMessage(data) {
        const { type, results, cached, searchTime, totalMatches, id, error } = data;
        
        switch (type) {
            case 'SEARCH_RESULTS':
                this.handleSearchResults(results, { cached, searchTime, totalMatches, id });
                break;
                
            case 'SEARCH_ERROR':
                console.error('Search worker error:', error);
                window.notificationManager?.showError(`Search failed: ${error}`);
                this.resetSearchUI();
                break;
                
            case 'INIT_COMPLETE':
                console.log('[AdvancedRAGManager] Search worker documents initialized');
                break;
                
            default:
                console.warn('Unknown worker message type:', type);
        }
    }

    updateSearchWorkerDocuments() {
        if (!this.searchWorker) return;
        
        // Convert documents Map to Array for worker
        const documentsArray = Array.from(this.documents.values());
        
        this.searchWorker.postMessage({
            type: 'UPDATE_DOCUMENTS',
            data: documentsArray,
            id: this.generateSearchId()
        });
    }

    setupChunkingStrategies() {
        // Semantic chunking - split by meaning rather than just size
        this.chunkingStrategies.set('semantic', {
            name: 'Semantic Chunking',
            description: 'Split documents by semantic meaning and context',
            process: this.semanticChunking.bind(this)
        });

        // Hierarchical chunking - maintain document structure
        this.chunkingStrategies.set('hierarchical', {
            name: 'Hierarchical Chunking',
            description: 'Preserve document hierarchy and relationships',
            process: this.hierarchicalChunking.bind(this)
        });

        // Adaptive chunking - adjust based on content complexity
        this.chunkingStrategies.set('adaptive', {
            name: 'Adaptive Chunking',
            description: 'Dynamically adjust chunk size based on content complexity',
            process: this.adaptiveChunking.bind(this)
        });

        // Multi-modal chunking - handle different content types
        this.chunkingStrategies.set('multimodal', {
            name: 'Multi-modal Chunking',
            description: 'Process text, images, tables, and structured data',
            process: this.multimodalChunking.bind(this)
        });
    }

    setupRetrievalMethods() {
        // Hybrid retrieval - combine multiple search methods
        this.retrievalMethods.set('hybrid', {
            name: 'Hybrid Retrieval',
            description: 'Combine semantic and keyword search for better results',
            process: this.hybridRetrieval.bind(this)
        });

        // Contextual retrieval - consider conversation context
        this.retrievalMethods.set('contextual', {
            name: 'Contextual Retrieval',
            description: 'Use conversation history to improve relevance',
            process: this.contextualRetrieval.bind(this)
        });

        // Multi-hop retrieval - chain multiple queries
        this.retrievalMethods.set('multihop', {
            name: 'Multi-hop Retrieval',
            description: 'Chain multiple queries to find complex information',
            process: this.multihopRetrieval.bind(this)
        });

        // Temporal retrieval - consider time-based relevance
        this.retrievalMethods.set('temporal', {
            name: 'Temporal Retrieval',
            description: 'Prioritize recent or time-relevant information',
            process: this.temporalRetrieval.bind(this)
        });
    }

    setupEventListeners() {
        // Document upload and processing
        const uploadBtn = document.getElementById('upload-documents');
        if (uploadBtn) {
            window.eventManager.add(uploadBtn, 'click', () => this.showDocumentUpload());
        }

        // Collection management
        const createCollectionBtn = document.getElementById('create-collection');
        if (createCollectionBtn) {
            window.eventManager.add(createCollectionBtn, 'click', () => this.createCollection());
        }

        // Processing controls
        const startProcessingBtn = document.getElementById('start-processing');
        if (startProcessingBtn) {
            window.eventManager.add(startProcessingBtn, 'click', () => this.startBatchProcessing());
        }

        // Search functionality
        const searchBtn = document.getElementById('search-documents');
        if (searchBtn) {
            window.eventManager.add(searchBtn, 'click', () => this.performSearch());
        }

        // Refresh collections
        const refreshBtn = document.getElementById('refresh-collections');
        if (refreshBtn) {
            window.eventManager.add(refreshBtn, 'click', () => this.loadCollections());
        }

        // Process documents button
        const processBtn = document.getElementById('process-documents');
        if (processBtn) {
            window.eventManager.add(processBtn, 'click', () => this.processSelectedDocuments());
        }
    }

    initializeUI() {
        this.createAdvancedRAGInterface();
        this.createDocumentProcessor();
        this.createCollectionManager();
        this.createRetrievalInterface();
    }

    createAdvancedRAGInterface() {
        const container = document.getElementById('advanced-rag-interface');
        if (!container) return;

        container.innerHTML = `
            <div class="advanced-rag-header">
                <h3>Advanced RAG System</h3>
                <div class="rag-controls">
                    <button id="upload-documents" class="btn btn-primary">
                        <i class="fas fa-upload"></i> Upload Documents
                    </button>
                    <button id="create-collection" class="btn btn-info">
                        <i class="fas fa-folder-plus"></i> Create Collection
                    </button>
                    <button id="start-processing" class="btn btn-success">
                        <i class="fas fa-cogs"></i> Start Processing
                    </button>
                </div>
            </div>
            <div class="rag-dashboard">
                <div class="dashboard-stats">
                    <div class="stat-card">
                        <h4>Documents Processed</h4>
                        <div class="stat-value" id="documents-processed">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Collections</h4>
                        <div class="stat-value" id="collections-count">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Total Chunks</h4>
                        <div class="stat-value" id="total-chunks">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Processing Queue</h4>
                        <div class="stat-value" id="queue-size">0</div>
                    </div>
                </div>
            </div>
        `;
    }

    createDocumentProcessor() {
        const container = document.getElementById('document-processor');
        if (!container) return;

        container.innerHTML = `
            <div class="processor-header">
                <h4>Document Processing</h4>
                <div class="processor-controls">
                    <select id="chunking-strategy">
                        <option value="semantic">Semantic Chunking</option>
                        <option value="hierarchical">Hierarchical Chunking</option>
                        <option value="adaptive">Adaptive Chunking</option>
                        <option value="multimodal">Multi-modal Chunking</option>
                    </select>
                    <button id="process-documents" class="btn btn-primary">Process</button>
                </div>
            </div>
            <div class="processing-queue" id="processing-queue">
                <h5>Processing Queue</h5>
                <div class="queue-items"></div>
            </div>
            <div class="processing-results" id="processing-results">
                <h5>Processing Results</h5>
                <div class="results-list"></div>
            </div>
        `;
    }

    createCollectionManager() {
        const container = document.getElementById('collection-manager');
        if (!container) return;

        container.innerHTML = `
            <div class="collection-header">
                <h4>Collection Management</h4>
                <button id="refresh-collections" class="btn btn-secondary">
                    <i class="fas fa-sync"></i> Refresh
                </button>
            </div>
            <div class="collections-grid" id="collections-grid"></div>
        `;

        this.loadCollections();
    }

    createRetrievalInterface() {
        const container = document.getElementById('retrieval-interface');
        if (!container) return;

        container.innerHTML = `
            <div class="retrieval-header">
                <h4>Advanced Retrieval</h4>
                <div class="retrieval-controls">
                    <input type="text" id="search-query" placeholder="Enter search query..." style="flex: 1; margin-right: 10px;">
                    <select id="retrieval-method">
                        <option value="hybrid">Hybrid Retrieval</option>
                        <option value="contextual">Contextual Retrieval</option>
                        <option value="multihop">Multi-hop Retrieval</option>
                        <option value="temporal">Temporal Retrieval</option>
                    </select>
                    <input type="number" id="max-results" placeholder="Max results" value="10" min="1" max="50">
                    <button id="search-documents" class="btn btn-primary">Search</button>
                </div>
            </div>
            <div class="search-results" id="search-results">
                <h5>Search Results</h5>
                <div class="results-container"></div>
            </div>
        `;
    }

    async semanticChunking(document, options = {}) {
        const { minChunkSize = 100, maxChunkSize = 1000 } = options;
        
        // Use NLP to identify semantic boundaries
        const sentences = await this.extractSentences(document.content);
        const chunks = [];
        let currentChunk = '';
        
        for (const sentence of sentences) {
            if (currentChunk.length + sentence.length > maxChunkSize && currentChunk.length > minChunkSize) {
                chunks.push({
                    content: currentChunk.trim(),
                    metadata: {
                        type: 'semantic',
                        source: document.id,
                        position: chunks.length
                    }
                });
                currentChunk = sentence + ' ';
            } else {
                currentChunk += sentence + ' ';
            }
        }
        
        if (currentChunk.trim()) {
            chunks.push({
                content: currentChunk.trim(),
                metadata: {
                    type: 'semantic',
                    source: document.id,
                    position: chunks.length
                }
            });
        }
        
        return chunks;
    }

    async hierarchicalChunking(document) {
        const chunks = [];
        const structure = await this.analyzeDocumentStructure(document.content);
        
        for (const section of structure.sections) {
            chunks.push({
                content: section.content,
                metadata: {
                    type: 'hierarchical',
                    source: document.id,
                    level: section.level,
                    title: section.title,
                    position: section.position
                }
            });
        }
        
        return chunks;
    }

    async adaptiveChunking(document, options = {}) {
        const complexity = await this.analyzeContentComplexity(document.content);
        const baseChunkSize = options.baseChunkSize || 500;
        
        // Adjust chunk size based on complexity
        const adjustedChunkSize = Math.max(200, Math.min(2000, 
            baseChunkSize * (1 + (complexity.score - 0.5) * 0.5)
        ));
        
        return this.semanticChunking(document, { 
            ...options, 
            maxChunkSize: adjustedChunkSize 
        });
    }

    async multimodalChunking(document, options = {}) {
        const chunks = [];
        
        // Extract different content types
        const textContent = await this.extractTextContent(document.content);
        const imageContent = await this.extractImageContent(document.content);
        const tableContent = await this.extractTableContent(document.content);
        
        // Process each content type
        if (textContent) {
            const textChunks = await this.semanticChunking({ ...document, content: textContent }, options);
            chunks.push(...textChunks);
        }
        
        if (imageContent) {
            const imageChunks = await this.processImageContent(imageContent, document.id);
            chunks.push(...imageChunks);
        }
        
        if (tableContent) {
            const tableChunks = await this.processTableContent(tableContent, document.id);
            chunks.push(...tableChunks);
        }
        
        return chunks;
    }

    async hybridRetrieval(query, context = {}, options = {}) {
        const { collectionId, maxResults = 10 } = options;
        console.log('Hybrid retrieval for:', query, 'Context:', context);
        
        // Perform semantic search
        const semanticResults = await this.semanticSearch(query, collectionId, maxResults);
        
        // Perform keyword search
        const keywordResults = await this.keywordSearch(query, collectionId, maxResults);
        
        // Combine and rank results
        const combinedResults = this.combineSearchResults(semanticResults, keywordResults);
        
        return combinedResults.slice(0, maxResults);
    }

    async contextualRetrieval(query, context = {}, options = {}) {
        const { conversationHistory = [], maxResults = 10 } = options;
        
        // Build context-aware query
        const contextualQuery = await this.buildContextualQuery(query, conversationHistory);
        
        // Perform search with context
        const results = await this.hybridRetrieval(contextualQuery, context, { maxResults });
        
        // Re-rank based on conversation relevance
        const rerankedResults = await this.rerankByContext(results, conversationHistory);
        
        return rerankedResults.slice(0, maxResults);
    }

    async multihopRetrieval(query, context = {}, options = {}) {
        const { maxHops = 3, maxResults = 10 } = options;
        
        let currentQuery = query;
        let allResults = [];
        
        for (let hop = 0; hop < maxHops; hop++) {
            // Perform search for current query
            const hopResults = await this.hybridRetrieval(currentQuery, context, { maxResults: maxResults * 2 });
            
            // Add to all results
            allResults.push(...hopResults);
            
            // Generate next query based on results
            if (hop < maxHops - 1) {
                currentQuery = await this.generateFollowUpQuery(query, hopResults);
            }
        }
        
        // Deduplicate and rank final results
        const uniqueResults = this.deduplicateResults(allResults);
        return uniqueResults.slice(0, maxResults);
    }

    async temporalRetrieval(query, context = {}, options = {}) {
        const { timeRange = 'all', maxResults = 10 } = options;
        
        // Add temporal filters to query
        const temporalQuery = await this.addTemporalFilters(query, timeRange);
        
        // Perform search with temporal relevance
        const results = await this.hybridRetrieval(temporalQuery, context, { maxResults });
        
        // Re-rank by temporal relevance
        const temporalResults = await this.rerankByTemporalRelevance(results, timeRange);
        
        return temporalResults.slice(0, maxResults);
    }

    async showDocumentUpload() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Upload Documents</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="upload-area" id="upload-area">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <p>Drag and drop files here or click to browse</p>
                        <input type="file" id="file-input" multiple accept=".pdf,.docx,.txt,.md,.html,.json,.csv">
                    </div>
                    <div class="upload-options">
                        <h4>Processing Options</h4>
                        <div class="option-group">
                            <label>Chunking Strategy:</label>
                            <select id="upload-chunking-strategy">
                                <option value="semantic">Semantic Chunking</option>
                                <option value="hierarchical">Hierarchical Chunking</option>
                                <option value="adaptive">Adaptive Chunking</option>
                                <option value="multimodal">Multi-modal Chunking</option>
                            </select>
                        </div>
                        <div class="option-group">
                            <label>Collection:</label>
                            <select id="upload-collection">
                                <option value="">Create New Collection</option>
                            </select>
                        </div>
                    </div>
                    <div class="upload-progress" id="upload-progress" style="display: none;">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progress-fill"></div>
                        </div>
                        <div class="progress-text" id="progress-text">0%</div>
                    </div>
                    <div class="file-list" id="file-list"></div>
                </div>
                <div class="modal-footer">
                    <button id="start-upload" class="btn btn-primary">Start Upload</button>
                    <button class="btn btn-secondary close-modal">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupUploadHandlers(modal);
    }

    setupUploadHandlers(modal) {
        const uploadArea = modal.querySelector('#upload-area');
        const fileInput = modal.querySelector('#file-input');
        const startUploadBtn = modal.querySelector('#start-upload');

        // Drag and drop handlers
        if (uploadArea) {
            window.eventManager.add(uploadArea, 'dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            window.eventManager.add(uploadArea, 'dragleave', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });

            window.eventManager.add(uploadArea, 'drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                this.handleFileSelection(files);
            });
        }

        // File input handler
        if (fileInput) {
            window.eventManager.add(fileInput, 'change', (e) => {
                this.handleFileSelection(e.target.files);
            });
        }

        // Start upload handler
        if (startUploadBtn) {
            window.eventManager.add(startUploadBtn, 'click', () => {
                this.processUploadedFiles();
            });
        }

        // Close modal handlers
        modal.querySelectorAll('.close-modal').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });
    }

    async handleFileSelection(files) {
        const fileList = document.getElementById('file-list');
        if (!fileList) return;

        fileList.innerHTML = '';
        this.selectedFiles = Array.from(files);

        this.selectedFiles.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <i class="fas fa-file"></i>
                <span>${file.name}</span>
                <span class="file-size">${this.formatFileSize(file.size)}</span>
            `;
            fileList.appendChild(fileItem);
        });
    }

    async handleDocumentUpload(files, collectionName, chunkingStrategy) {
        if (!files || files.length === 0) {
            throw new Error('No files to upload');
        }

        const formData = new FormData();
        
        // Add all files to form data
        Array.from(files).forEach((file) => {
            formData.append('files', file);
        });
        
        // Add metadata
        formData.append('chunking_strategy', chunkingStrategy);

        try {
            const response = await fetch(`/api/rag_collections/${collectionName}/upload_files`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Upload result:', result);
            
            return result;
            
        } catch (error) {
            console.error('Document upload error:', error);
            throw error;
        }
    }

    async processUploadedFiles() {
        if (!this.selectedFiles || this.selectedFiles.length === 0) {
            this.showNotification('No files selected', 'error');
            return;
        }

        const chunkingStrategy = document.getElementById('upload-chunking-strategy').value;
        const collectionSelect = document.getElementById('upload-collection');
        const collectionName = collectionSelect.value;

        if (!collectionName) {
            this.showNotification('Please select a collection', 'warning');
            return;
        }

        this.showUploadProgress();

        try {
            await this.handleDocumentUpload(this.selectedFiles, collectionName, chunkingStrategy);
            this.hideUploadProgress();
            this.showNotification('Files uploaded successfully', 'success');
            this.loadCollections();
            
            // Close the upload modal
            const modal = document.querySelector('.modal');
            if (modal) {
                modal.remove();
            }
        } catch (error) {
            this.hideUploadProgress();
            console.error('Upload error:', error);
            this.showNotification(`Upload failed: ${error.message}`, 'error');
        }
    }

    async viewDocument(documentId) {
        console.log('Viewing document:', documentId);
        
        // Show a simple modal with document details
        // In a real implementation, this would fetch full document details
        this.showNotification(`Viewing document: ${documentId}`, 'info');
        
        // Create a simple preview modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Document Preview</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="document-preview">
                        <p>Document ID: ${documentId}</p>
                        <p>This is a preview of the document. Full document viewing would require additional API implementation.</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal handlers
        modal.querySelectorAll('.close-modal').forEach(btn => {
            if (window.eventManager) {
                window.eventManager.add(btn, 'click', () => modal.remove());
            } else {
                btn.addEventListener('click', () => modal.remove());
            }
        });
    }

    async deleteDocument(documentId) {
        console.log('Deleting document:', documentId);
        
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            // This would require the actual API endpoint for document deletion
            // For now, just show a notification
            this.showNotification(`Document deletion requested: ${documentId}`, 'info');
            
            // In a real implementation:
            // const response = await fetch(`/api/delete_rag_document/${documentId}`, {
            //     method: 'DELETE'
            // });
            
        } catch (error) {
            console.error('Error deleting document:', error);
            this.showNotification('Failed to delete document', 'error');
        }
    }

    async processDocument(document, strategy) {
        const strategyHandler = this.chunkingStrategies.get(strategy);
        if (!strategyHandler) {
            throw new Error(`Unknown chunking strategy: ${strategy}`);
        }

        return await strategyHandler.process(document);
    }



    async loadCollections() {
        try {
            // Show loading indicator
            const grid = document.getElementById('collections-grid');
            if (grid) {
                grid.innerHTML = '<div class="loading-spinner">Loading collections...</div>';
            }

            const response = await fetch('/api/rag_collections');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const collections = await response.json();
            
            // Convert array to map for compatibility with existing code
            this.collections = new Map();
            collections.forEach(collection => {
                this.collections.set(collection.id.toString(), {
                    id: collection.id,
                    name: collection.collection_name,
                    display_name: collection.display_name,
                    description: collection.description,
                    document_count: collection.document_count,
                    is_ingesting: collection.is_ingesting,
                    status_message: collection.status_message,
                    created_at: collection.created_at,
                    last_updated: collection.last_updated
                });
            });

            this.updateCollectionsGrid();
            this.updateCollectionSelectors();
            this.updateProcessingStats();
            
            if (typeof window.showToast === 'function') {
                window.showToast(`Loaded ${collections.length} collections`, 'success');
            }

        } catch (error) {
            console.error('Error loading collections:', error);
            const grid = document.getElementById('collections-grid');
            if (grid) {
                grid.innerHTML = `<div class="error-message">Failed to load collections: ${error.message}</div>`;
            }
            
            if (typeof window.showToast === 'function') {
                window.showToast('Failed to load collections', 'error');
            }
        }
    }

    updateCollectionsGrid() {
        const grid = document.getElementById('collections-grid');
        if (!grid) return;

        grid.innerHTML = Array.from(this.collections.values()).map(collection => `
            <div class="collection-card" data-id="${collection.id}">
                <div class="collection-header">
                    <h5>${collection.name}</h5>
                    <div class="collection-actions">
                        <button class="btn btn-sm btn-primary" onclick="advancedRAGManager.viewCollection('${collection.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="advancedRAGManager.deleteCollection('${collection.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="collection-info">
                    <span>${collection.document_count || 0} documents</span>
                    <span>${collection.chunk_count || 0} chunks</span>
                </div>
                <div class="collection-meta">
                    <small>Created: ${new Date(collection.created_at).toLocaleDateString()}</small>
                </div>
            </div>
        `).join('');
    }

    updateCollectionSelectors() {
        const selectors = document.querySelectorAll('#upload-collection, #search-collection');
        selectors.forEach(selector => {
            const currentValue = selector.value;
            selector.innerHTML = '<option value="">Select Collection</option>';
            
            this.collections.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection.name; // Use collection name for API compatibility
                option.textContent = collection.display_name || collection.name;
                selector.appendChild(option);
            });
            
            selector.value = currentValue;
        });
    }

    // Utility methods
    generateDocumentId() {
        return 'doc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showUploadProgress() {
        const progress = document.getElementById('upload-progress');
        if (progress) progress.style.display = 'block';
    }

    hideUploadProgress() {
        const progress = document.getElementById('upload-progress');
        if (progress) progress.style.display = 'none';
    }

    updateUploadProgress(percentage) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressFill) progressFill.style.width = percentage + '%';
        if (progressText) progressText.textContent = Math.round(percentage) + '%';
    }

    showNotification(message, type = 'info') {
        console.log(`[AdvancedRAGManager] ${type.toUpperCase()}: ${message}`);
        
        // Use centralized notification manager if available
        if (window.notificationManager) {
            switch (type) {
                case 'success':
                    window.notificationManager.showSuccess(message);
                    break;
                case 'error':
                    window.notificationManager.showError(message);
                    break;
                case 'warning':
                    window.notificationManager.showWarning(message);
                    break;
                default:
                    window.notificationManager.showInfo(message);
            }
        } else if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            // Fallback: create simple notification element
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 4px;
                color: white;
                z-index: 10000;
                max-width: 300px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
            `;
            
            document.body.appendChild(notification);
            
            // Remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);
        }
    }

    // Advanced NLP methods integrated with backend API
    async extractSentences(text) {
        console.log('[AdvancedRAGManager] Extracting sentences via backend API...');
        
        try {
            const response = await fetch('/api/rag/analyze/sentences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    options: {
                        preserve_formatting: true,
                        include_metadata: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Extracted ${data.sentences.length} sentences`);
                return data.sentences.map(sentence => sentence.text || sentence);
            } else {
                console.error('Failed to extract sentences:', data.error);
                // Fallback to simple extraction
                return text.split(/[.!?]+/).filter(s => s.trim().length > 0);
            }
        } catch (error) {
            console.error('Error extracting sentences:', error);
            window.notificationManager?.showWarning('Using fallback sentence extraction');
            // Fallback to simple extraction
            return text.split(/[.!?]+/).filter(s => s.trim().length > 0);
        }
    }

    async analyzeDocumentStructure(content) {
        console.log('[AdvancedRAGManager] Analyzing document structure via backend API...');
        
        try {
            const response = await fetch('/api/rag/analyze/structure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    options: {
                        detect_headings: true,
                        extract_sections: true,
                        analyze_hierarchy: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Analyzed document structure: ${data.structure.sections.length} sections`);
                return data.structure;
            } else {
                console.error('Failed to analyze document structure:', data.error);
                // Fallback to simple structure
                return { sections: [{ content, level: 1, title: 'Document', position: 0 }] };
            }
        } catch (error) {
            console.error('Error analyzing document structure:', error);
            window.notificationManager?.showWarning('Using fallback document structure analysis');
            // Fallback to simple structure
            return { sections: [{ content, level: 1, title: 'Document', position: 0 }] };
        }
    }

    async analyzeContentComplexity(content) {
        console.log('[AdvancedRAGManager] Analyzing content complexity via backend API...');
        
        try {
            const response = await fetch('/api/rag/analyze/complexity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    options: {
                        include_readability: true,
                        include_vocabulary: true,
                        include_structure: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Content complexity score: ${data.complexity.score}`);
                return data.complexity;
            } else {
                console.error('Failed to analyze content complexity:', data.error);
                // Fallback to simple analysis
                return this.fallbackComplexityAnalysis(content);
            }
        } catch (error) {
            console.error('Error analyzing content complexity:', error);
            window.notificationManager?.showWarning('Using fallback complexity analysis');
            // Fallback to simple analysis
            return this.fallbackComplexityAnalysis(content);
        }
    }
    
    fallbackComplexityAnalysis(content) {
        // Simple complexity analysis based on sentence length and vocabulary
        const sentences = content.split(/[.!?]+/);
        const avgSentenceLength = sentences.reduce((sum, s) => sum + s.length, 0) / sentences.length;
        const uniqueWords = new Set(content.toLowerCase().split(/\s+/)).size;
        const totalWords = content.split(/\s+/).length;
        
        const complexityScore = Math.min(1, (avgSentenceLength / 100 + uniqueWords / totalWords) / 2);
        return { 
            score: complexityScore,
            metrics: {
                avg_sentence_length: avgSentenceLength,
                unique_words: uniqueWords,
                total_words: totalWords
            }
        };
    }

    async extractTextContent(content) {
        console.log('[AdvancedRAGManager] Extracting text content via backend API...');
        
        try {
            const response = await fetch('/api/rag/extract/content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    type: 'text',
                    options: {
                        remove_html: true,
                        preserve_formatting: false,
                        clean_whitespace: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[AdvancedRAGManager] Text content extracted successfully');
                return data.extracted_content || data.content;
            } else {
                console.error('Failed to extract text content:', data.error);
                // Fallback to simple extraction
                return this.fallbackTextExtraction(content);
            }
        } catch (error) {
            console.error('Error extracting text content:', error);
            window.notificationManager?.showWarning('Using fallback text extraction');
            // Fallback to simple extraction
            return this.fallbackTextExtraction(content);
        }
    }
    
    fallbackTextExtraction(content) {
        // Remove HTML tags and extract plain text
        const textContent = content.replace(/<[^>]*>/g, ' ').trim();
        return textContent || content;
    }

    async extractImageContent(content) {
        console.log('[AdvancedRAGManager] Extracting image content via backend API...');
        
        try {
            const response = await fetch('/api/rag/extract/content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    type: 'image',
                    options: {
                        extract_alt_text: true,
                        extract_captions: true,
                        analyze_images: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Extracted ${data.images?.length || 0} image references`);
                return data.images || data.extracted_content;
            } else {
                console.error('Failed to extract image content:', data.error);
                // Fallback to simple extraction
                return this.fallbackImageExtraction(content);
            }
        } catch (error) {
            console.error('Error extracting image content:', error);
            window.notificationManager?.showWarning('Using fallback image extraction');
            // Fallback to simple extraction
            return this.fallbackImageExtraction(content);
        }
    }
    
    fallbackImageExtraction(content) {
        // Extract image references and alt text from HTML content
        const imageRegex = /<img[^>]+alt="([^"]*)"[^>]*>/gi;
        const matches = [...content.matchAll(imageRegex)];
        return matches.length > 0 ? matches.map(match => match[1]) : null;
    }

    async extractTableContent(content) {
        console.log('[AdvancedRAGManager] Extracting table content via backend API...');
        
        try {
            const response = await fetch('/api/rag/extract/content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    type: 'table',
                    options: {
                        parse_structure: true,
                        extract_headers: true,
                        convert_to_text: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Extracted ${data.tables?.length || 0} tables`);
                return data.tables || data.extracted_content;
            } else {
                console.error('Failed to extract table content:', data.error);
                // Fallback to simple extraction
                return this.fallbackTableExtraction(content);
            }
        } catch (error) {
            console.error('Error extracting table content:', error);
            window.notificationManager?.showWarning('Using fallback table extraction');
            // Fallback to simple extraction
            return this.fallbackTableExtraction(content);
        }
    }
    
    fallbackTableExtraction(content) {
        // Extract table data from HTML content
        const tableRegex = /<table[^>]*>(.*?)<\/table>/gis;
        const matches = [...content.matchAll(tableRegex)];
        return matches.length > 0 ? matches.map(match => match[1]) : null;
    }

    async processImageContent(imageContent, documentId) {
        console.log('Processing image content for document:', documentId);
        // Process extracted image descriptions
        return imageContent.map((alt, index) => ({
            content: `Image: ${alt}`,
            metadata: {
                type: 'image',
                source: documentId,
                position: index,
                altText: alt
            }
        }));
    }

    async processTableContent(tableContent, documentId) {
        console.log('Processing table content for document:', documentId);
        // Process extracted table data
        return tableContent.map((table, index) => ({
            content: `Table data: ${table.replace(/<[^>]*>/g, ' ').trim()}`,
            metadata: {
                type: 'table',
                source: documentId,
                position: index
            }
        }));
    }





    async buildContextualQuery(query, conversationHistory) {
        console.log('Building contextual query for:', query);
        // Add conversation context to query
        const context = conversationHistory.slice(-3).join(' ');
        return context ? `${context} ${query}` : query;
    }

    async rerankByContext(results, conversationHistory) {
        console.log('Reranking results by context');
        // Boost results that match conversation context
        const contextTerms = conversationHistory.join(' ').toLowerCase().split(' ');
        return results.map(result => ({
            ...result,
            score: result.score + (contextTerms.some(term => 
                result.content.toLowerCase().includes(term)) ? 0.1 : 0)
        })).sort((a, b) => b.score - a.score);
    }

    async generateFollowUpQuery(originalQuery, results) {
        console.log('Generating follow-up query for:', originalQuery);
        // Extract key terms from top results for follow-up
        const topResult = results[0];
        return topResult ? `${originalQuery} ${topResult.content.split(' ')[0]}` : originalQuery;
    }

    deduplicateResults(results) {
        console.log('Deduplicating results');
        // Remove duplicate results based on content similarity
        const unique = [];
        const seen = new Set();
        
        for (const result of results) {
            const key = result.content.substring(0, 50); // Use first 50 chars as key
            if (!seen.has(key)) {
                seen.add(key);
                unique.push(result);
            }
        }
        return unique;
    }

    async addTemporalFilters(query, timeRange) {
        console.log('Adding temporal filters for:', timeRange);
        // Add time-based constraints to query
        const timeFilter = timeRange === 'recent' ? ' recent' : '';
        return query + timeFilter;
    }

    async rerankByTemporalRelevance(results, timeRange) {
        console.log('Reranking by temporal relevance:', timeRange);
        // Boost recent results if timeRange is 'recent'
        if (timeRange === 'recent') {
            return results.map(result => ({
                ...result,
                score: result.score * 1.1 // Boost all scores for recent queries
            }));
        }
        return results;
    }

    async readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    }

    // Missing method implementations
    async createCollection() {
        console.log('Creating new collection...');
        
        // Create a proper modal dialog for collection creation
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create New Collection</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="collection-name">Collection Name:</label>
                        <input type="text" id="collection-name" class="form-control" placeholder="Enter collection name" required>
                    </div>
                    <div class="form-group">
                        <label for="collection-description">Description (optional):</label>
                        <textarea id="collection-description" class="form-control" placeholder="Enter collection description" rows="3"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="create-collection-btn" class="btn btn-primary">Create Collection</button>
                    <button class="btn btn-secondary close-modal">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Handle form submission
        const createBtn = modal.querySelector('#create-collection-btn');
        const nameInput = modal.querySelector('#collection-name');
        const descInput = modal.querySelector('#collection-description');

        const handleCreate = async () => {
            const name = nameInput.value.trim();
            const description = descInput.value.trim();
            
            if (!name) {
                this.showNotification('Collection name is required', 'warning');
                return;
            }

            try {
                // Disable button and show loading
                createBtn.disabled = true;
                createBtn.textContent = 'Creating...';

                const response = await fetch('/api/rag_collections', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        name: name,
                        description: description || `Collection: ${name}`
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                await response.json();
                this.showNotification(`Collection "${name}" created successfully`, 'success');
                modal.remove();
                this.loadCollections();
                
            } catch (error) {
                console.error('Error creating collection:', error);
                this.showNotification(`Failed to create collection: ${error.message}`, 'error');
                
                // Re-enable button
                createBtn.disabled = false;
                createBtn.textContent = 'Create Collection';
            }
        };

        if (window.eventManager) {
            window.eventManager.add(createBtn, 'click', handleCreate);
            
            // Handle enter key in name input
            window.eventManager.add(nameInput, 'keypress', (e) => {
                if (e.key === 'Enter') {
                    handleCreate();
                }
            });

            // Close modal handlers
            modal.querySelectorAll('.close-modal').forEach(btn => {
                window.eventManager.add(btn, 'click', () => modal.remove());
            });
        } else {
            // Fallback if eventManager is not available
            createBtn.addEventListener('click', handleCreate);
            nameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handleCreate();
                }
            });
            modal.querySelectorAll('.close-modal').forEach(btn => {
                btn.addEventListener('click', () => modal.remove());
            });
        }

        // Focus on name input
        nameInput.focus();
    }

    async startBatchProcessing() {
        console.log('Starting batch processing...');
        this.showNotification('Batch processing started', 'info');
        
        if (this.processingQueue.length === 0) {
            this.showNotification('No documents in processing queue', 'warning');
            return;
        }

        try {
            for (const item of this.processingQueue) {
                await this.processDocument(item.document, item.strategy);
                this.updateProcessingStats();
            }
            this.processingQueue = [];
            this.showNotification('Batch processing completed', 'success');
        } catch (error) {
            console.error('Error in batch processing:', error);
            this.showNotification('Batch processing failed', 'error');
        }
    }

    async viewCollection(collectionId) {
        console.log('Viewing collection:', collectionId);
        const collection = this.collections.get(collectionId);
        if (!collection) {
            this.showNotification('Collection not found', 'error');
            return;
        }
        
        this.showNotification(`Viewing collection: ${collection.name}`, 'info');
        // Display collection details in a modal or dedicated view
        this.displayCollectionDetails(collection);
    }

    async deleteCollection(collectionId) {
        console.log('Deleting collection:', collectionId);
        const collection = this.collections.get(collectionId.toString());
        if (!collection) {
            this.showNotification('Collection not found', 'error');
            return;
        }

        if (!confirm(`Are you sure you want to delete collection "${collection.display_name || collection.name}"?`)) {
            return;
        }

        try {
            // Use the collection name for the API call
            const response = await fetch(`/api/rag_collections/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    collection_name: collection.name
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            await response.json();
            this.collections.delete(collectionId.toString());
            this.showNotification(`Collection "${collection.display_name || collection.name}" deleted`, 'success');
            this.loadCollections();
            
        } catch (error) {
            console.error('Error deleting collection:', error);
            this.showNotification(`Failed to delete collection: ${error.message}`, 'error');
        }
    }

    displayCollectionDetails(collection) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Collection: ${collection.name}</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="collection-stats">
                        <div class="stat-item">
                            <label>Documents:</label>
                            <span>${collection.document_count || 0}</span>
                        </div>
                        <div class="stat-item">
                            <label>Chunks:</label>
                            <span>${collection.chunk_count || 0}</span>
                        </div>
                        <div class="stat-item">
                            <label>Created:</label>
                            <span>${new Date(collection.created_at).toLocaleString()}</span>
                        </div>
                    </div>
                    <div class="collection-documents" id="collection-documents">
                        <h4>Documents in Collection</h4>
                        <div class="documents-list"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        // Close modal handlers
        modal.querySelectorAll('.close-modal').forEach(btn => {
            if (window.eventManager) {
                window.eventManager.add(btn, 'click', () => modal.remove());
            } else {
                btn.addEventListener('click', () => modal.remove());
            }
        });

        this.loadCollectionDocuments(collection.id);
    }

    async loadCollectionDocuments(collectionId) {
        console.log('Loading documents for collection:', collectionId);
        
        try {
            // Show loading state
            this.showNotification('Loading collection documents...', 'info');
            
            const collection = this.collections.get(collectionId.toString());
            if (!collection) {
                throw new Error('Collection not found');
            }

            const response = await fetch(`/api/rag_collections/${collection.name}/documents`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const documents = await response.json();
            
            // Update the documents list in the modal
            const documentsList = document.querySelector('.documents-list');
            if (documentsList) {
                if (documents.length === 0) {
                    documentsList.innerHTML = '<p>No documents found in this collection.</p>';
                } else {
                    documentsList.innerHTML = documents.map(doc => `
                        <div class="document-item" data-id="${doc.id}">
                            <div class="document-header">
                                <h5>${doc.title || doc.filename}</h5>
                                <span class="document-type">${doc.document_type}</span>
                            </div>
                            <div class="document-preview">
                                ${doc.content_preview}
                            </div>
                            <div class="document-meta">
                                <span>Size: ${doc.file_size}</span>
                                <span>Chunks: ${doc.chunk_count}</span>
                                <span>Uploaded: ${new Date(doc.upload_date).toLocaleDateString()}</span>
                            </div>
                            <div class="document-actions">
                                <button class="btn btn-sm btn-primary" onclick="advancedRAGManager.viewDocument('${doc.id}')">
                                    <i class="fas fa-eye"></i> View
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="advancedRAGManager.deleteDocument('${doc.id}')">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </div>
                        </div>
                    `).join('');
                }
            }
            
            this.showNotification(`Loaded ${documents.length} documents`, 'success');
            
        } catch (error) {
            console.error('Error loading collection documents:', error);
            this.showNotification(`Failed to load documents: ${error.message}`, 'error');
            
            const documentsList = document.querySelector('.documents-list');
            if (documentsList) {
                documentsList.innerHTML = `<div class="error-message">Failed to load documents: ${error.message}</div>`;
            }
        }
    }

    updateProcessingStats() {
        const docsProcessed = document.getElementById('documents-processed');
        const collectionsCount = document.getElementById('collections-count');
        const totalChunks = document.getElementById('total-chunks');
        const queueSize = document.getElementById('queue-size');

        if (docsProcessed) docsProcessed.textContent = this.documents.size;
        if (collectionsCount) collectionsCount.textContent = this.collections.size;
        if (queueSize) queueSize.textContent = this.processingQueue.length;
        
        // Calculate total chunks
        let chunks = 0;
        this.documents.forEach(doc => {
            chunks += doc.chunks ? doc.chunks.length : 0;
        });
        if (totalChunks) totalChunks.textContent = chunks;
    }

    async performSearch() {
        console.log('[AdvancedRAGManager] Performing optimized document search...');
        const searchInput = document.querySelector('#search-query');
        const retrievalMethod = document.querySelector('#retrieval-method');
        const maxResults = document.querySelector('#max-results');
        
        if (!searchInput) {
            window.notificationManager?.showError('Search input not found');
            return;
        }

        const query = searchInput.value.trim();
        if (!query) {
            window.notificationManager?.showWarning('Please enter a search query');
            return;
        }

        const method = retrievalMethod ? retrievalMethod.value : 'hybrid';
        const maxRes = maxResults ? parseInt(maxResults.value) : this.searchPagination.itemsPerPage;

        // Check cache first for instant results
        const cacheKey = `${query}-${method}-${maxRes}`;
        if (this.searchCache.has(cacheKey)) {
            console.log('[AdvancedRAGManager] Serving cached search results');
            const cachedResults = this.searchCache.get(cacheKey);
            this.displaySearchResults(cachedResults, { cached: true });
            window.notificationManager?.showSuccess(`Found ${cachedResults.length} cached results for "${query}"`);
            return;
        }

        try {
            window.notificationManager?.showInfo('Searching documents...');
            this.showSearchLoadingState();
            
            const searchId = this.generateSearchId();
            
            if (this.searchWorker) {
                // Use Web Worker for non-blocking search
                this.searchWorker.postMessage({
                    type: 'SEARCH',
                    data: {
                        query: query,
                        options: {
                            maxResults: maxRes,
                            threshold: 0.1,
                            searchFields: ['title', 'content', 'tags'],
                            sortBy: 'relevance'
                        }
                    },
                    id: searchId
                });
            } else {
                // Fallback to main thread search
                const results = await this.searchKnowledgeFallback(query, method, maxRes);
                this.handleSearchResults(results, { cached: false, searchId });
            }
            
        } catch (error) {
            console.error('Search error:', error);
            window.notificationManager?.showError(`Search failed: ${error.message}`);
            this.showSearchErrorState();
        }
    }

    generateSearchId() {
        return ++this.currentSearchId;
    }

    showSearchLoadingState() {
        const resultsContainer = document.querySelector('#search-results .results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="search-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Searching knowledge base...</p>
                </div>
            `;
        }
        
        // Disable search controls
        const searchBtn = document.querySelector('#search-documents');
        const searchInput = document.querySelector('#search-query');
        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
        }
        if (searchInput) {
            searchInput.disabled = true;
        }
    }

    showSearchErrorState() {
        const resultsContainer = document.querySelector('#search-results .results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="search-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Search failed. Please try again.</p>
                </div>
            `;
        }
        this.resetSearchUI();
    }

    resetSearchUI() {
        const searchBtn = document.querySelector('#search-documents');
        const searchInput = document.querySelector('#search-query');
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<i class="fas fa-search"></i> Search';
        }
        if (searchInput) {
            searchInput.disabled = false;
        }
    }

    handleSearchResults(results, metadata = {}) {
        const { cached = false, searchTime, totalMatches } = metadata;
        
        // Store results for pagination
        this.lastSearchResults = results;
        
        // Cache results if not from cache
        if (!cached && results.length > 0) {
            this.cacheSearchResults(results);
        }
        
        // Update pagination info
        this.searchPagination.totalResults = totalMatches || results.length;
        this.searchPagination.totalPages = Math.ceil(this.searchPagination.totalResults / this.searchPagination.itemsPerPage);
        this.searchPagination.currentPage = 1;
        
        this.displaySearchResults(results, { cached, searchTime });
        this.resetSearchUI();
        
        const successMessage = cached 
            ? `Found ${results.length} cached results`
            : `Found ${results.length} results${searchTime ? ` in ${searchTime.toFixed(0)}ms` : ''}`;
        window.notificationManager?.showSuccess(successMessage);
    }

    cacheSearchResults(results) {
        const searchInput = document.querySelector('#search-query');
        if (!searchInput) return;
        
        const query = searchInput.value.trim();
        const cacheKey = `${query}-hybrid-${this.searchPagination.itemsPerPage}`;
        
        // Implement LRU cache
        if (this.searchCache.size >= this.maxCacheSize) {
            const firstKey = this.searchCache.keys().next().value;
            this.searchCache.delete(firstKey);
        }
        
        this.searchCache.set(cacheKey, results);
    }

    async searchKnowledgeFallback(query, method, maxResults) {
        // Fallback search implementation for when Web Worker is unavailable
        const results = [];
        const queryLower = query.toLowerCase();
        
        this.documents.forEach((doc, id) => {
            const titleMatch = (doc.title || '').toLowerCase().includes(queryLower);
            const contentMatch = (doc.content || '').toLowerCase().includes(queryLower);
            
            if (titleMatch || contentMatch) {
                let score = 0;
                if (titleMatch) score += 0.8;
                if (contentMatch) score += 0.5;
                
                results.push({
                    id: id,
                    title: doc.title,
                    content: doc.content,
                    score: score,
                    type: doc.type || 'document',
                    source: doc.source || 'unknown',
                    search_query: query
                });
            }
        });
        
        return results.sort((a, b) => b.score - a.score).slice(0, maxResults);
    }

    async searchKnowledge(query, method = 'hybrid', maxResults = 10) {
        console.log(`[AdvancedRAGManager] Searching knowledge: "${query}" using ${method} method`);
        
        try {
            const response = await fetch('/api/rag/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    method: method,
                    max_results: maxResults,
                    options: {
                        include_metadata: true,
                        include_scores: true,
                        rerank_results: true
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[AdvancedRAGManager] Found ${data.results.length} results`);
                return data.results.map(result => ({
                    ...result,
                    relevance_score: result.score || result.relevance_score || 0,
                    method_used: method
                }));
            } else {
                console.error('Search failed:', data.error);
                window.notificationManager?.showError(`Search failed: ${data.error}`);
                return [];
            }
        } catch (error) {
            console.error('Error searching knowledge:', error);
            window.notificationManager?.showWarning('Search service unavailable, using fallback');
            
            // Fallback to client-side search
            return await this.fallbackSearch(query, method, maxResults);
        }
    }
    
    async fallbackSearch(query, method, maxResults) {
        console.log('[AdvancedRAGManager] Using fallback search method');
        
        let allDocuments = [];
        
        // Load documents from all collections
        for (const [collectionId, collection] of this.collections) {
            try {
                const response = await fetch(`/api/rag_collections/${collection.name}/documents`);
                if (response.ok) {
                    const documents = await response.json();
                    documents.forEach(doc => {
                        doc.collection_id = collectionId;
                        doc.collection_name = collection.name;
                    });
                    allDocuments.push(...documents);
                }
            } catch (error) {
                console.warn(`Failed to load documents from collection ${collection.name}:`, error);
            }
        }

        // Perform client-side search based on the method
        let results = [];
        const lowerQuery = query.toLowerCase();

        switch (method) {
            case 'hybrid':
                results = this.performHybridSearch(allDocuments, lowerQuery);
                break;
                case 'contextual':
                    results = this.performContextualSearch(allDocuments, lowerQuery);
                    break;
                case 'multihop':
                    results = this.performMultihopSearch(allDocuments, lowerQuery);
                    break;
                case 'temporal':
                    results = this.performTemporalSearch(allDocuments, lowerQuery);
                    break;
                default:
                    results = this.performHybridSearch(allDocuments, lowerQuery);
            }

        // Limit results and add search metadata
        return results.slice(0, maxResults).map(result => ({
            ...result,
            search_method: method,
            search_query: query,
            search_timestamp: new Date().toISOString()
        }));
    }

    performHybridSearch(documents, query) {
        const results = [];
        
        documents.forEach(doc => {
            let score = 0;
            const content = (doc.content_preview || '').toLowerCase();
            const title = (doc.title || doc.filename || '').toLowerCase();
            
            // Title match (higher weight)
            if (title.includes(query)) {
                score += 0.8;
            }
            
            // Content match
            if (content.includes(query)) {
                score += 0.6;
            }
            
            // Word-based scoring
            const queryWords = query.split(' ');
            queryWords.forEach(word => {
                if (word.length > 2) { // Skip very short words
                    if (title.includes(word)) score += 0.2;
                    if (content.includes(word)) score += 0.1;
                }
            });
            
            if (score > 0) {
                results.push({
                    id: doc.id,
                    content: doc.content_preview || doc.title || doc.filename,
                    title: doc.title || doc.filename,
                    score: score,
                    source: doc.collection_name,
                    type: 'hybrid',
                    document_type: doc.document_type,
                    file_size: doc.file_size,
                    upload_date: doc.upload_date,
                    chunk_count: doc.chunk_count
                });
            }
        });
        
        return results.sort((a, b) => b.score - a.score);
    }

    performContextualSearch(documents, query) {
        // Enhanced search considering document context and type
        const results = this.performHybridSearch(documents, query);
        
        // Boost results based on document type and recency
        return results.map(result => {
            let contextBoost = 0;
            
            // Boost based on document type
            if (result.document_type === 'text') contextBoost += 0.1;
            if (result.document_type === 'pdf') contextBoost += 0.05;
            
            // Boost recent documents
            const uploadDate = new Date(result.upload_date);
            const daysDiff = (new Date() - uploadDate) / (1000 * 60 * 60 * 24);
            if (daysDiff < 7) contextBoost += 0.15;
            else if (daysDiff < 30) contextBoost += 0.1;
            
            return {
                ...result,
                score: result.score + contextBoost,
                type: 'contextual'
            };
        }).sort((a, b) => b.score - a.score);
    }

    performMultihopSearch(documents, query) {
        // Multi-step search with related terms
        let results = this.performHybridSearch(documents, query);
        
        // Find related terms from top results
        if (results.length > 0) {
            const relatedTerms = this.extractRelatedTerms(results.slice(0, 3));
            const secondaryQuery = relatedTerms.join(' ').toLowerCase();
            
            if (secondaryQuery && secondaryQuery !== query) {
                const secondaryResults = this.performHybridSearch(documents, secondaryQuery);
                
                // Combine results with lower weight for secondary
                secondaryResults.forEach(result => {
                    const existingIndex = results.findIndex(r => r.id === result.id);
                    if (existingIndex >= 0) {
                        results[existingIndex].score += result.score * 0.3;
                    } else {
                        results.push({
                            ...result,
                            score: result.score * 0.3,
                            type: 'multihop'
                        });
                    }
                });
            }
        }
        
        return results.sort((a, b) => b.score - a.score);
    }

    performTemporalSearch(documents, query) {
        const results = this.performHybridSearch(documents, query);
        
        // Heavy boost for recent documents
        return results.map(result => {
            const uploadDate = new Date(result.upload_date);
            const daysDiff = (new Date() - uploadDate) / (1000 * 60 * 60 * 24);
            
            let temporalBoost = 0;
            if (daysDiff < 1) temporalBoost = 0.5;
            else if (daysDiff < 7) temporalBoost = 0.3;
            else if (daysDiff < 30) temporalBoost = 0.2;
            else if (daysDiff < 90) temporalBoost = 0.1;
            
            return {
                ...result,
                score: result.score + temporalBoost,
                type: 'temporal'
            };
        }).sort((a, b) => b.score - a.score);
    }

    extractRelatedTerms(documents) {
        const terms = [];
        documents.forEach(doc => {
            const content = (doc.content || '').toLowerCase();
            const words = content.split(/\s+/).filter(word => 
                word.length > 3 && 
                !/^\d+$/.test(word) && // Skip pure numbers
                !['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'man', 'men', 'she', 'use', 'add', 'say', 'where', 'from', 'with', 'have', 'this', 'that', 'they', 'will', 'been', 'each', 'more', 'than', 'what', 'were', 'call', 'come', 'does', 'down', 'find', 'here', 'into', 'just', 'like', 'look', 'made', 'make', 'many', 'most', 'much', 'only', 'over', 'part', 'some', 'take', 'than', 'them', 'time', 'very', 'well', 'when'].includes(word)
            );
            terms.push(...words.slice(0, 3)); // Take first 3 significant words
        });
        return [...new Set(terms)].slice(0, 5); // Return unique terms, max 5
    }

    displaySearchResults(results, metadata = {}) {
        const container = document.querySelector('#search-results .results-container');
        if (!container) return;

        const { cached = false, searchTime } = metadata;

        if (results.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>No results found for your search query.</p>
                    <p>Try using different keywords or check your spelling.</p>
                </div>
            `;
            return;
        }

        // Calculate pagination
        const startIndex = (this.searchPagination.currentPage - 1) * this.searchPagination.itemsPerPage;
        const endIndex = startIndex + this.searchPagination.itemsPerPage;
        const paginatedResults = results.slice(startIndex, endIndex);

        // Results header with metadata
        const headerHtml = `
            <div class="search-results-header">
                <div class="results-meta">
                    <span class="results-count">
                        Showing ${startIndex + 1}-${Math.min(endIndex, results.length)} of ${results.length} results
                    </span>
                    ${cached ? '<span class="cache-indicator"><i class="fas fa-bolt"></i> Cached</span>' : ''}
                    ${searchTime ? `<span class="search-time">${searchTime.toFixed(0)}ms</span>` : ''}
                </div>
                <div class="view-options">
                    <button class="btn btn-sm btn-outline-secondary" onclick="advancedRAGManager.clearSearchCache()">
                        <i class="fas fa-refresh"></i> Clear Cache
                    </button>
                </div>
            </div>
        `;

        // Results list
        const resultsHtml = paginatedResults.map((result, index) => {
            const globalIndex = startIndex + index;
            return `
                <div class="search-result" data-id="${result.id}">
                    <div class="result-header">
                        <div class="result-meta">
                            <span class="result-rank">#${globalIndex + 1}</span>
                            <span class="result-score" title="Relevance Score">
                                <i class="fas fa-star"></i> ${result.score ? result.score.toFixed(3) : 'N/A'}
                            </span>
                            <span class="result-type badge badge-${result.type}">${result.type}</span>
                            ${result.document_type ? `<span class="doc-type badge badge-secondary">${result.document_type}</span>` : ''}
                        </div>
                        <div class="result-actions">
                            <button class="btn btn-sm btn-outline-primary" onclick="advancedRAGManager.viewDocument('${result.id}')">
                                <i class="fas fa-eye"></i> View
                            </button>
                        </div>
                    </div>
                    <div class="result-title">
                        <h6>${result.title || 'Untitled Document'}</h6>
                    </div>
                    <div class="result-content">
                        ${this.highlightSearchTerms(result.content ? result.content.substring(0, 250) : '', result.search_query)}${result.content && result.content.length > 250 ? '...' : ''}
                    </div>
                    <div class="result-footer">
                        <div class="result-source">
                            <i class="fas fa-folder"></i> Collection: ${result.source || 'Unknown'}
                        </div>
                        <div class="result-details">
                            ${result.file_size ? `<span><i class="fas fa-file"></i> ${result.file_size}</span>` : ''}
                            ${result.chunk_count ? `<span><i class="fas fa-cubes"></i> ${result.chunk_count} chunks</span>` : ''}
                            ${result.upload_date ? `<span><i class="fas fa-calendar"></i> ${new Date(result.upload_date).toLocaleDateString()}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Pagination controls
        const paginationHtml = this.createPaginationControls();

        // Combine all HTML
        container.innerHTML = headerHtml + resultsHtml + paginationHtml;
    }

    createPaginationControls() {
        if (this.searchPagination.totalPages <= 1) {
            return ''; // No pagination needed
        }

        const currentPage = this.searchPagination.currentPage;
        const totalPages = this.searchPagination.totalPages;
        
        let paginationHtml = '<div class="search-pagination">';
        
        // Previous button
        paginationHtml += `
            <button class="btn btn-sm btn-outline-primary pagination-btn" 
                    ${currentPage <= 1 ? 'disabled' : ''} 
                    onclick="advancedRAGManager.goToPage(${currentPage - 1})">
                <i class="fas fa-chevron-left"></i> Previous
            </button>
        `;
        
        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            paginationHtml += `
                <button class="btn btn-sm btn-outline-secondary pagination-btn" onclick="advancedRAGManager.goToPage(1)">1</button>
            `;
            if (startPage > 2) {
                paginationHtml += '<span class="pagination-ellipsis">...</span>';
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <button class="btn btn-sm ${i === currentPage ? 'btn-primary' : 'btn-outline-secondary'} pagination-btn" 
                        onclick="advancedRAGManager.goToPage(${i})">${i}</button>
            `;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += '<span class="pagination-ellipsis">...</span>';
            }
            paginationHtml += `
                <button class="btn btn-sm btn-outline-secondary pagination-btn" onclick="advancedRAGManager.goToPage(${totalPages})">${totalPages}</button>
            `;
        }
        
        // Next button
        paginationHtml += `
            <button class="btn btn-sm btn-outline-primary pagination-btn" 
                    ${currentPage >= totalPages ? 'disabled' : ''} 
                    onclick="advancedRAGManager.goToPage(${currentPage + 1})">
                Next <i class="fas fa-chevron-right"></i>
            </button>
        `;
        
        paginationHtml += '</div>';
        
        return paginationHtml;
    }

    goToPage(pageNumber) {
        if (pageNumber < 1 || pageNumber > this.searchPagination.totalPages) {
            return;
        }
        
        this.searchPagination.currentPage = pageNumber;
        
        // Re-display current search results with new pagination
        const container = document.querySelector('#search-results .results-container');
        if (container && this.lastSearchResults) {
            this.displaySearchResults(this.lastSearchResults);
        }
    }

    clearSearchCache() {
        this.searchCache.clear();
        
        if (this.searchWorker) {
            this.searchWorker.postMessage({
                type: 'CLEAR_CACHE',
                id: this.generateSearchId()
            });
        }
        
        window.notificationManager?.showSuccess('Search cache cleared');
        console.log('[AdvancedRAGManager] Search cache cleared');
    }

    highlightSearchTerms(text, query) {
        if (!query) return text;
        
        const words = query.toLowerCase().split(' ').filter(word => word.length > 2);
        let highlightedText = text;
        
        words.forEach(word => {
            const regex = new RegExp(`(${word})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
        });
        
        return highlightedText;
    }

    async processSelectedDocuments() {
        console.log('Processing selected documents...');
        const strategy = document.querySelector('#chunking-strategy');
        const strategyValue = strategy ? strategy.value : 'semantic';
        
        if (this.processingQueue.length === 0) {
            this.showNotification('No documents in queue to process', 'warning');
            return;
        }

        try {
            this.showNotification('Processing documents...', 'info');
            
            for (const item of this.processingQueue) {
                await this.processDocument(item.document, strategyValue);
            }
            
            this.processingQueue = [];
            this.updateProcessingStats();
            this.showNotification('Documents processed successfully', 'success');
            
        } catch (error) {
            console.error('Processing error:', error);
            this.showNotification('Document processing failed', 'error');
        }
    }
}

// Initialize the advanced RAG manager
window.advancedRAGManager = new AdvancedRAGManager();
