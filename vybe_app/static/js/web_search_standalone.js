/**
 * Web Search Standalone JavaScript
 * Handles the standalone web search interface functionality
 */

class WebSearchManager {
    constructor() {
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        // DOM elements
        this.searchInput = document.getElementById('search-query');
        this.searchButton = document.getElementById('search-button');
        this.searchResults = document.getElementById('search-results');
        this.searchStatus = document.getElementById('search-status');
        this.statusText = document.getElementById('status-text');
        this.noResultsMessage = document.getElementById('no-results-message');
        this.errorMessage = document.getElementById('error-message');
        this.errorText = document.getElementById('error-text');
        this.retryButton = document.getElementById('retry-button');
        this.resultsCountSelect = document.getElementById('results-count');
        this.safeSearchCheckbox = document.getElementById('safe-search');
        this.ragIntegrationCheckbox = document.getElementById('rag-integration');
        this.ragCollectionSelect = document.getElementById('rag-collection');
        
        // State variables
        this.currentQuery = '';
        this.isSearching = false;
        this.searchResults = [];
        this.eventListeners = []; // Track event listeners for cleanup
        
        this.bindEvents();
        
        // Cleanup on page unload
        const unloadHandler = () => {
            this.cleanup();
        };
        window.addEventListener('beforeunload', unloadHandler);
        this.cleanupFunctions.push(() => window.removeEventListener('beforeunload', unloadHandler));
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
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
    
    cleanup() {
        // Remove all tracked event listeners
        this.eventListeners.forEach(({element, event, handler}) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        this.eventListeners = [];
    }
    
    addEventListener(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.eventListeners.push({element, event, handler});
        }
    }

    // Utility method for debouncing
    debounce(func, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    bindEvents() {
        // Search button click
        if (this.searchButton) {
            const searchButtonHandler = () => this.performSearch();
            this.searchButton.addEventListener('click', searchButtonHandler);
            this.cleanupFunctions.push(() => this.searchButton.removeEventListener('click', searchButtonHandler));
        }
        
        // Enter key in search input
        if (this.searchInput) {
            const searchInputHandler = (e) => {
                if (e.key === 'Enter' && !this.isSearching) {
                    this.performSearch();
                }
            };
            this.searchInput.addEventListener('keypress', searchInputHandler);
            this.cleanupFunctions.push(() => this.searchInput.removeEventListener('keypress', searchInputHandler));
        }
        
        // Retry button click
        if (this.retryButton) {
            const retryButtonHandler = () => this.performSearch();
            this.retryButton.addEventListener('click', retryButtonHandler);
            this.cleanupFunctions.push(() => this.retryButton.removeEventListener('click', retryButtonHandler));
        }
        
        // Clear results when input is empty
        if (this.searchInput) {
            const inputHandler = this.debounce((e) => {
                if (e.target.value.trim() === '') {
                    this.clearResults();
                }
            }, 100);
            this.searchInput.addEventListener('input', inputHandler);
            this.cleanupFunctions.push(() => this.searchInput.removeEventListener('input', inputHandler));
        }
        
        // RAG integration toggle
        if (this.ragIntegrationCheckbox) {
            const ragCheckboxHandler = (e) => {
                const ragContainer = document.getElementById('rag-collection-container');
                if (e.target.checked) {
                    ragContainer.style.display = 'block';
                } else {
                    ragContainer.style.display = 'none';
                }
            };
            this.ragIntegrationCheckbox.addEventListener('change', ragCheckboxHandler);
            this.cleanupFunctions.push(() => this.ragIntegrationCheckbox.removeEventListener('change', ragCheckboxHandler));
        }
        
        // Add all to RAG button
        const addAllBtn = document.getElementById('add-all-rag-btn');
        if (addAllBtn) {
            const addAllHandler = () => this.addAllToRAG();
            addAllBtn.addEventListener('click', addAllHandler);
            this.cleanupFunctions.push(() => addAllBtn.removeEventListener('click', addAllHandler));
        }
        
        // Export results button
        const exportBtn = document.getElementById('export-results-btn');
        if (exportBtn) {
            const exportHandler = () => this.exportResults();
            exportBtn.addEventListener('click', exportHandler);
            this.cleanupFunctions.push(() => exportBtn.removeEventListener('click', exportHandler));
        }
        
        // Clear results button
        const clearBtn = document.getElementById('clear-results-btn');
        if (clearBtn) {
            const clearHandler = () => this.clearResults();
            clearBtn.addEventListener('click', clearHandler);
            this.cleanupFunctions.push(() => clearBtn.removeEventListener('click', clearHandler));
        }

        // Bookmarks button
        const bookmarksBtn = document.getElementById('bookmarks-btn');
        if (bookmarksBtn) {
            const bookmarksHandler = () => this.showBookmarks();
            bookmarksBtn.addEventListener('click', bookmarksHandler);
            this.cleanupFunctions.push(() => bookmarksBtn.removeEventListener('click', bookmarksHandler));
        }

        // Search history button
        const historyBtn = document.getElementById('search-history-btn');
        if (historyBtn) {
            const historyHandler = () => this.showSearchHistory();
            historyBtn.addEventListener('click', historyHandler);
            this.cleanupFunctions.push(() => historyBtn.removeEventListener('click', historyHandler));
        }

        // Advanced search toggle
        const advancedToggle = document.getElementById('advanced-search-toggle');
        if (advancedToggle) {
            const advancedHandler = () => this.toggleAdvancedSearch();
            advancedToggle.addEventListener('click', advancedHandler);
            this.cleanupFunctions.push(() => advancedToggle.removeEventListener('click', advancedHandler));
        }

        // Keyboard shortcuts
        const keyHandler = (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        if (this.searchInput) {
                            this.searchInput.focus();
                            this.searchInput.select();
                        }
                        break;
                    case 'Enter':
                        if (e.shiftKey && !this.isSearching) {
                            e.preventDefault();
                            this.performSearch();
                        }
                        break;
                    case 'b':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.showBookmarks();
                        }
                        break;
                    case 'h':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.showSearchHistory();
                        }
                        break;
                }
            } else if (e.key === 'Escape') {
                this.clearResults();
            }
        };
        
        document.addEventListener('keydown', keyHandler);
        this.cleanupFunctions.push(() => document.removeEventListener('keydown', keyHandler));

        // Auto-save search history
        if (this.searchInput) {
            const historyHandler = this.debounce(() => {
                this.saveToSearchHistory();
            }, 1000);
            this.searchInput.addEventListener('input', historyHandler);
            this.cleanupFunctions.push(() => this.searchInput.removeEventListener('input', historyHandler));
        }

        // Show keyboard shortcuts info
        setTimeout(() => {
            this.showToast('Shortcuts: Ctrl+K (focus search), Ctrl+Shift+Enter (search), Ctrl+Shift+B (bookmarks)', 'info');
        }, 2000);
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        
        if (!query) {
            this.showError('Please enter a search query');
            return;
        }

        if (this.isSearching) {
            return; // Prevent multiple simultaneous searches
        }

        this.currentQuery = query;
        this.showLoading();

        try {
            const resultsCount = parseInt(this.resultsCountSelect.value) || 10;
            const safeSearch = this.safeSearchCheckbox.checked;
            
            // Enhanced search with better bot detection avoidance
            const response = await fetch('/api/web_search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
                    'User-Agent': navigator.userAgent
                },
                body: JSON.stringify({
                    query: query,
                    count: resultsCount,
                    safe_search: safeSearch,
                    source: 'web_search_standalone',
                    timestamp: Date.now()
                })
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            this.displayResults(data.results || []);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError(error.message || 'An error occurred while searching');
        } finally {
            this.hideLoading();
        }
    }

    showLoading() {
        this.isSearching = true;
        this.searchButton.disabled = true;
        this.searchButton.textContent = 'Searching...';
        this.searchStatus.style.display = 'block';
        this.statusText.textContent = 'Searching...';
        this.hideMessages();
    }

    hideLoading() {
        this.isSearching = false;
        this.searchButton.disabled = false;
        this.searchButton.innerHTML = '<span class="search-icon">🔍</span> Search';
        this.searchStatus.style.display = 'none';
    }

    displayResults(results) {
        this.hideMessages();
        
        if (!results || results.length === 0) {
            this.showNoResults();
            return;
        }

        // Store results for other operations
        this.searchResults = results;
        this.showResultsActions();

        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '';
        
        // Add search summary
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'search-summary';
        summaryDiv.innerHTML = `
            <div class="summary-info">
                <span class="results-count">Found ${results.length} results for "${this.escapeHtml(this.currentQuery)}"</span>
                <div class="summary-actions">
                    <button onclick="window.webSearchManager.exportResults()" class="btn-sm">Export</button>
                    <button onclick="window.webSearchManager.clearResults()" class="btn-sm">Clear</button>
                </div>
            </div>
        `;
        resultsContainer.appendChild(summaryDiv);
        
        results.forEach((result, index) => {
            const resultElement = this.createEnhancedResultElement(result, index);
            resultsContainer.appendChild(resultElement);
        });

        // Add domain facets
        this.addDomainFacets(results, resultsContainer);
        
        resultsContainer.style.display = 'block';
        
        // Show results actions
        this.updateResultsCounter(results.length);
    }

    addDomainFacets(results, container) {
        try {
            const domains = {};
            results.forEach(result => {
                try {
                    const domain = new URL(result.link).hostname;
                    domains[domain] = (domains[domain] || 0) + 1;
                } catch {
                    // Ignore invalid URLs
                }
            });

            if (Object.keys(domains).length > 1) {
                const facetDiv = document.createElement('div');
                facetDiv.className = 'domain-facets';
                facetDiv.innerHTML = `
                    <div class="facets-title">Filter by domain:</div>
                    <div class="facets-list">
                        <button class="facet-chip active" onclick="window.webSearchManager.filterByDomain('')">
                            All (${results.length})
                        </button>
                        ${Object.entries(domains)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 6)
                            .map(([domain, count]) => 
                                `<button class="facet-chip" onclick="window.webSearchManager.filterByDomain('${domain}')">
                                    ${domain} (${count})
                                </button>`
                            ).join('')}
                    </div>
                `;
                container.appendChild(facetDiv);
            }
        } catch (error) {
            console.warn('Error creating domain facets:', error);
        }
    }

    filterByDomain(domain) {
        const items = Array.from(document.querySelectorAll('.search-result-item'));
        const chips = Array.from(document.querySelectorAll('.facet-chip'));
        
        // Update active chip
        chips.forEach(chip => chip.classList.remove('active'));
        if (domain === '') {
            chips[0].classList.add('active');
        } else {
            chips.find(chip => chip.textContent.includes(domain))?.classList.add('active');
        }
        
        // Filter results
        items.forEach(item => {
            const urlElement = item.querySelector('.result-url');
            if (!urlElement) return;
            
            if (domain === '' || urlElement.textContent.includes(domain)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
        
        // Update visible count
        const visibleCount = items.filter(item => item.style.display !== 'none').length;
        this.updateResultsCounter(visibleCount, domain);
    }

    updateResultsCounter(count, domain = '') {
        const counterElement = document.querySelector('.results-count');
        if (counterElement) {
            const baseText = `Found ${this.searchResults.length} results for "${this.escapeHtml(this.currentQuery)}"`;
            if (domain) {
                counterElement.innerHTML = `${baseText} (${count} from ${domain})`;
            } else if (count !== this.searchResults.length) {
                counterElement.innerHTML = `${baseText} (${count} visible)`;
            } else {
                counterElement.innerHTML = baseText;
            }
        }
    }

    createResultElement(result, index) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'search-result-item';
        resultDiv.setAttribute('data-index', index);
        
        // Extract domain from URL for display
        let domain = '';
        try {
            domain = new URL(result.link).hostname;
        } catch {
            domain = result.link;
        }

        resultDiv.innerHTML = `
            <div class="result-header">
                <h3 class="result-title">
                    <a href="${this.escapeHtml(result.link)}" target="_blank" rel="noopener noreferrer">
                        ${this.escapeHtml(result.title)}
                    </a>
                </h3>
                <div class="result-url">${this.escapeHtml(domain)}</div>
            </div>
                <div class="result-snippet">${this.escapeHtml(result.snippet)}</div>
            <div class="result-actions">
                <a href="${this.escapeHtml(result.link)}" target="_blank" rel="noopener noreferrer" class="visit-link-btn">
                    Visit Page 🔗
                </a>
                <button class="copy-url-btn" onclick="window.webSearchManager.copyToClipboard('${this.escapeHtml(result.link)}')">
                    Copy URL 📋
                </button>
            </div>
        `;

        return resultDiv;
    }

    showNoResults() {
        this.searchResults.style.display = 'none';
        this.noResultsMessage.style.display = 'block';
        this.errorMessage.style.display = 'none';
    }

    showError(message) {
        this.searchResults.style.display = 'none';
        this.noResultsMessage.style.display = 'none';
        this.errorMessage.style.display = 'block';
        this.errorText.textContent = message;
    }

    hideMessages() {
        this.searchResults.style.display = 'none';
        this.noResultsMessage.style.display = 'none';
        this.errorMessage.style.display = 'none';
    }

    clearResults() {
        this.hideMessages();
        this.searchResults.innerHTML = '';
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('URL copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy text: ', err);
            this.showToast('Failed to copy URL', 'error');
        }
    }

    showToast(message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Style the toast
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4CAF50' : '#f44336'};
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // RAG Integration Methods
    async addAllToRAG() {
        if (!this.searchResults || this.searchResults.length === 0) {
            this.showToast('No search results to add', 'error');
            return;
        }
        
        const addButton = document.getElementById('add-all-rag-btn');
        const originalText = addButton?.textContent || 'Add All to RAG';
        if (addButton) {
            addButton.textContent = '🔄 Adding...';
            addButton.disabled = true;
        }
        
        let successCount = 0;
        const totalResults = this.searchResults.length;
        
        for (let i = 0; i < totalResults; i++) {
            if (await this.addToRAG(i)) {
                successCount++;
            }
            // Small delay to avoid overwhelming the API
            await new Promise(resolve => setTimeout(resolve, 200));
        }
        
        if (addButton) {
            addButton.textContent = originalText;
            addButton.disabled = false;
        }
        
        this.showToast(`Added ${successCount}/${totalResults} results to RAG collection`, 'success');
    }
    
    // Enhanced result display with RAG integration
    createEnhancedResultElement(result, index) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'search-result-item enhanced-result';
        resultDiv.setAttribute('data-index', index);
        
        // Extract domain from URL for display
        let domain = '';
        try {
            domain = new URL(result.link).hostname;
        } catch {
            domain = result.link;
        }

        resultDiv.innerHTML = `
            <div class="result-header">
                <h3 class="result-title">
                    <a href="${this.escapeHtml(result.link)}" target="_blank" rel="noopener noreferrer">
                        ${this.escapeHtml(result.title)}
                    </a>
                </h3>
                <div class="result-actions">
                    <button class="rag-add-btn" onclick="window.webSearchManager.addToRAG(${index})" title="Add to RAG">
                        📚 Add to RAG
                    </button>
                    <button class="preview-btn" onclick="window.webSearchManager.previewContent(${index})" title="Preview Content">
                        👁️ Preview
                    </button>
                    <button class="share-btn" onclick="window.webSearchManager.shareResult(${index})" title="Share Result">
                        📤 Share
                    </button>
                </div>
            </div>
            <div class="result-url">${this.escapeHtml(result.link)}</div>
            <div class="result-snippet">${this.escapeHtml(result.snippet)}</div>
            <div class="result-footer">
                <span class="result-domain">${domain}</span>
                <div class="result-controls">
                    <a href="${this.escapeHtml(result.link)}" target="_blank" rel="noopener noreferrer" class="visit-btn">
                        🔗 Visit
                    </a>
                    <button class="copy-url-btn" onclick="window.webSearchManager.copyToClipboard('${this.escapeHtml(result.link)}')">
                        � Copy URL
                    </button>
                    <button class="bookmark-btn" onclick="window.webSearchManager.bookmarkResult(${index})" title="Bookmark">
                        ⭐ Bookmark
                    </button>
                </div>
            </div>
        `;
        
        return resultDiv;
    }

    async addToRAG(resultIndex) {
        try {
            const result = this.searchResults[resultIndex];
            if (!result) {
                throw new Error('Result not found');
            }

            const collection = this.ragCollectionSelect?.value || 'web_search_results';
            
            const response = await fetch('/api/rag/add_document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    title: result.title,
                    content: result.snippet,
                    url: result.link,
                    collection: collection,
                    source: 'web_search',
                    metadata: {
                        search_query: this.currentQuery,
                        domain: new URL(result.link).hostname,
                        timestamp: Date.now(),
                        index: resultIndex
                    }
                })
            });
            
            if (response.ok) {
                this.showToast(`Added "${result.title}" to RAG collection`, 'success');
                
                // Update button to show it was added
                const button = document.querySelector(`[onclick="window.webSearchManager.addToRAG(${resultIndex})"]`);
                if (button) {
                    button.innerHTML = '✅ Added';
                    button.disabled = true;
                    button.classList.add('added');
                }
                
                return true;
            } else {
                throw new Error('Failed to add to RAG');
            }
        } catch (error) {
            console.error('RAG integration error:', error);
            this.showToast('Failed to add to RAG collection', 'error');
            return false;
        }
    }

    shareResult(resultIndex) {
        const result = this.searchResults[resultIndex];
        if (!result) return;

        if (navigator.share) {
            navigator.share({
                title: result.title,
                text: result.snippet,
                url: result.link
            }).catch(err => console.log('Error sharing:', err));
        } else {
            // Fallback to copying share text
            const shareText = `${result.title}\n${result.snippet}\n${result.link}`;
            this.copyToClipboard(shareText);
            this.showToast('Share text copied to clipboard', 'success');
        }
    }

    bookmarkResult(resultIndex) {
        const result = this.searchResults[resultIndex];
        if (!result) return;

        // Store bookmark in localStorage
        let bookmarks = JSON.parse(localStorage.getItem('webSearchBookmarks') || '[]');
        
        // Check if already bookmarked
        const isBookmarked = bookmarks.some(bookmark => bookmark.link === result.link);
        
        if (isBookmarked) {
            bookmarks = bookmarks.filter(bookmark => bookmark.link !== result.link);
            this.showToast('Bookmark removed', 'info');
        } else {
            bookmarks.push({
                ...result,
                bookmarked_at: new Date().toISOString(),
                search_query: this.currentQuery
            });
            this.showToast('Result bookmarked', 'success');
        }
        
        localStorage.setItem('webSearchBookmarks', JSON.stringify(bookmarks));
        this.updateBookmarkButton(resultIndex, !isBookmarked);
    }

    updateBookmarkButton(resultIndex, isBookmarked) {
        const button = document.querySelector(`[onclick="window.webSearchManager.bookmarkResult(${resultIndex})"]`);
        if (button) {
            if (isBookmarked) {
                button.innerHTML = '⭐ Bookmarked';
                button.classList.add('bookmarked');
            } else {
                button.innerHTML = '⭐ Bookmark';
                button.classList.remove('bookmarked');
            }
        }
    }

    showBookmarks() {
        const bookmarks = JSON.parse(localStorage.getItem('webSearchBookmarks') || '[]');
        
        if (bookmarks.length === 0) {
            this.showToast('No bookmarks found', 'info');
            return;
        }

        const modal = this.createBookmarksModal(bookmarks);
        document.body.appendChild(modal);
    }

    createBookmarksModal(bookmarks) {
        const modal = document.createElement('div');
        modal.className = 'bookmarks-modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="this.parentElement.remove()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Bookmarked Results (${bookmarks.length})</h3>
                    <button onclick="this.parentElement.parentElement.remove()" class="close-btn">×</button>
                </div>
                <div class="bookmarks-list">
                    ${bookmarks.map((bookmark, index) => `
                        <div class="bookmark-item">
                            <h4><a href="${this.escapeHtml(bookmark.link)}" target="_blank">${this.escapeHtml(bookmark.title)}</a></h4>
                            <p>${this.escapeHtml(bookmark.snippet)}</p>
                            <div class="bookmark-meta">
                                <span>Saved: ${new Date(bookmark.bookmarked_at).toLocaleDateString()}</span>
                                <span>Query: "${bookmark.search_query}"</span>
                                <button onclick="window.webSearchManager.removeBookmark(${index})" class="remove-bookmark">Remove</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div class="modal-footer">
                    <button onclick="window.webSearchManager.exportBookmarks()">Export Bookmarks</button>
                    <button onclick="window.webSearchManager.clearBookmarks()">Clear All</button>
                </div>
            </div>
        `;

        return modal;
    }

    removeBookmark(index) {
        let bookmarks = JSON.parse(localStorage.getItem('webSearchBookmarks') || '[]');
        bookmarks.splice(index, 1);
        localStorage.setItem('webSearchBookmarks', JSON.stringify(bookmarks));
        
        // Refresh modal
        const modal = document.querySelector('.bookmarks-modal');
        if (modal) {
            modal.remove();
            this.showBookmarks();
        }
        
        this.showToast('Bookmark removed', 'success');
    }

    exportBookmarks() {
        const bookmarks = JSON.parse(localStorage.getItem('webSearchBookmarks') || '[]');
        
        if (bookmarks.length === 0) {
            this.showToast('No bookmarks to export', 'error');
            return;
        }

        const exportData = {
            exported_at: new Date().toISOString(),
            bookmarks: bookmarks
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `web-search-bookmarks-${new Date().toISOString().slice(0, 19)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('Bookmarks exported successfully', 'success');
    }

    clearBookmarks() {
        if (confirm('Are you sure you want to clear all bookmarks?')) {
            localStorage.removeItem('webSearchBookmarks');
            
            const modal = document.querySelector('.bookmarks-modal');
            if (modal) {
                modal.remove();
            }
            
            this.showToast('All bookmarks cleared', 'success');
        }
    }
    
    async previewContent(index) {
        const result = this.searchResults[index];
        if (!result) return;
        
        try {
            // Show loading in preview
            const previewModal = this.createPreviewModal('Loading content...');
            document.body.appendChild(previewModal);
            
            // Fetch content preview
            const response = await fetch('/api/web_search/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    url: result.link,
                    title: result.title
                })
            });
            
            if (response.ok) {
                const previewData = await response.json();
                previewModal.querySelector('.preview-content').innerHTML = `
                    <h3>${this.escapeHtml(result.title)}</h3>
                    <div class="preview-text">${previewData.content}</div>
                    <div class="preview-actions">
                        <button onclick="window.webSearchManager.addToRAG(${JSON.stringify(result)})" class="rag-add-btn">
                            📚 Add to RAG
                        </button>
                        <button onclick="window.webSearchManager.closePreview()" class="close-btn">
                            Close
                        </button>
                    </div>
                `;
            } else {
                previewModal.querySelector('.preview-content').innerHTML = `
                    <h3>Preview Unavailable</h3>
                    <p>Could not load content preview for this page.</p>
                    <button onclick="window.webSearchManager.closePreview()" class="close-btn">Close</button>
                `;
            }
        } catch (error) {
            console.error('Preview error:', error);
            this.showToast('Failed to load preview', 'error');
        }
    }
    
    createPreviewModal(content) {
        const modal = document.createElement('div');
        modal.className = 'preview-modal';
        modal.innerHTML = `
            <div class="preview-overlay"></div>
            <div class="preview-content">
                ${content}
            </div>
        `;
        
        // Style the modal
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        modal.querySelector('.preview-overlay').style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
        `;
        
        modal.querySelector('.preview-content').style.cssText = `
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            max-width: 80%;
            max-height: 80%;
            overflow-y: auto;
            position: relative;
            z-index: 1;
        `;
        
        // Close on overlay click
        modal.querySelector('.preview-overlay').addEventListener('click', () => this.closePreview());
        
        return modal;
    }
    
    closePreview() {
        const modal = document.querySelector('.preview-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    exportResults() {
        if (!this.searchResults || this.searchResults.length === 0) {
            this.showToast('No search results to export', 'error');
            return;
        }
        
        const exportData = {
            query: this.currentQuery,
            timestamp: new Date().toISOString(),
            results: this.searchResults.map(result => ({
                title: result.title,
                url: result.link,
                snippet: result.snippet,
                domain: new URL(result.link).hostname
            }))
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `web-search-results-${new Date().toISOString().slice(0, 19)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('Search results exported successfully', 'success');
    }
    
    showResultsActions() {
        const actionsContainer = document.getElementById('results-actions');
        if (actionsContainer) {
            actionsContainer.style.display = 'flex';
        }
    }
    
    hideResultsActions() {
        const actionsContainer = document.getElementById('results-actions');
        if (actionsContainer) {
            actionsContainer.style.display = 'none';
        }
    }

    saveToSearchHistory() {
        const query = this.searchInput?.value?.trim();
        if (!query || query.length < 2) return;

        let history = JSON.parse(localStorage.getItem('webSearchHistory') || '[]');
        
        // Remove duplicate if exists
        history = history.filter(item => item.query !== query);
        
        // Add to beginning
        history.unshift({
            query: query,
            timestamp: new Date().toISOString()
        });
        
        // Keep only last 50 searches
        history = history.slice(0, 50);
        
        localStorage.setItem('webSearchHistory', JSON.stringify(history));
    }

    showSearchHistory() {
        const history = JSON.parse(localStorage.getItem('webSearchHistory') || '[]');
        
        if (history.length === 0) {
            this.showToast('No search history found', 'info');
            return;
        }

        const modal = this.createSearchHistoryModal(history);
        document.body.appendChild(modal);
    }

    createSearchHistoryModal(history) {
        const modal = document.createElement('div');
        modal.className = 'search-history-modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="this.parentElement.remove()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Search History (${history.length})</h3>
                    <button onclick="this.parentElement.parentElement.remove()" class="close-btn">×</button>
                </div>
                <div class="history-list">
                    ${history.map((item, index) => `
                        <div class="history-item">
                            <span class="history-query" onclick="window.webSearchManager.useHistoryQuery('${this.escapeHtml(item.query)}')">${this.escapeHtml(item.query)}</span>
                            <span class="history-date">${new Date(item.timestamp).toLocaleDateString()}</span>
                            <button onclick="window.webSearchManager.removeFromHistory(${index})" class="remove-history">×</button>
                        </div>
                    `).join('')}
                </div>
                <div class="modal-footer">
                    <button onclick="window.webSearchManager.clearSearchHistory()">Clear All History</button>
                </div>
            </div>
        `;

        return modal;
    }

    useHistoryQuery(query) {
        if (this.searchInput) {
            this.searchInput.value = query;
            this.searchInput.focus();
        }
        
        // Close modal
        const modal = document.querySelector('.search-history-modal');
        if (modal) {
            modal.remove();
        }
        
        // Optionally auto-search
        if (!this.isSearching) {
            setTimeout(() => this.performSearch(), 300);
        }
    }

    removeFromHistory(index) {
        let history = JSON.parse(localStorage.getItem('webSearchHistory') || '[]');
        history.splice(index, 1);
        localStorage.setItem('webSearchHistory', JSON.stringify(history));
        
        // Refresh modal
        const modal = document.querySelector('.search-history-modal');
        if (modal) {
            modal.remove();
            this.showSearchHistory();
        }
    }

    clearSearchHistory() {
        if (confirm('Are you sure you want to clear all search history?')) {
            localStorage.removeItem('webSearchHistory');
            
            const modal = document.querySelector('.search-history-modal');
            if (modal) {
                modal.remove();
            }
            
            this.showToast('Search history cleared', 'success');
        }
    }

    toggleAdvancedSearch() {
        const advancedPanel = document.getElementById('advanced-search-panel');
        const toggle = document.getElementById('advanced-search-toggle');
        
        if (advancedPanel) {
            const isVisible = advancedPanel.style.display !== 'none';
            advancedPanel.style.display = isVisible ? 'none' : 'block';
            
            if (toggle) {
                toggle.textContent = isVisible ? '⚙️ Advanced' : '⚙️ Hide Advanced';
            }
        }
    }

    // Enhanced search with filters
    async performAdvancedSearch() {
        const query = this.searchInput?.value?.trim();
        if (!query) return;

        // Get advanced options
        const timeFilter = document.getElementById('time-filter')?.value || '';
        const languageFilter = document.getElementById('language-filter')?.value || '';
        const fileTypeFilter = document.getElementById('filetype-filter')?.value || '';
        const siteFilter = document.getElementById('site-filter')?.value || '';

        // Build enhanced query
        let enhancedQuery = query;
        
        if (timeFilter) {
            enhancedQuery += ` ${timeFilter}`;
        }
        if (languageFilter) {
            enhancedQuery += ` lang:${languageFilter}`;
        }
        if (fileTypeFilter) {
            enhancedQuery += ` filetype:${fileTypeFilter}`;
        }
        if (siteFilter) {
            enhancedQuery += ` site:${siteFilter}`;
        }

        // Update search input temporarily
        const originalQuery = this.searchInput.value;
        this.searchInput.value = enhancedQuery;
        
        await this.performSearch();
        
        // Restore original query
        this.searchInput.value = originalQuery;
    }
}

// Initialize the search manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.webSearchManager = new WebSearchManager();
});
