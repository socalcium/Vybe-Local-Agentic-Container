/**
 * Marketplace Manager for Vybe
 * Provides frontend functionality for browsing and managing marketplace plugins
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

class MarketplaceManager {
    constructor() {
        this.plugins = [];
        this.categories = [];
        this.favorites = [];
        this.installed = [];
        this.featured = [];
        this.verified = [];
        this.currentCategory = null;
        this.currentSearch = '';
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.loading = false;
        this.stats = {};
        
        // Add missing currentFilters property
        this.currentFilters = {
            featured: false,
            verified: false
        };
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.init();
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
    
    async init() {
        await this.loadMarketplaceData();
        this.bindEvents();
        this.renderMarketplace();
    }
    
    async loadMarketplaceData() {
        try {
            this.loading = true;
            this.updateLoadingState();
            
            console.log('🔄 Loading marketplace data from backend API...');
            
            // Load marketplace status and stats
            try {
                const statusResponse = await fetch('/api/marketplace/status');
                if (!statusResponse.ok) {
                    throw new Error(`Failed to fetch stats: ${statusResponse.status} ${statusResponse.statusText}`);
                }
                
                const statusData = await statusResponse.json();
                if (statusData.success) {
                    this.stats = statusData.data;
                    console.log('✅ Stats loaded successfully');
                } else {
                    throw new Error(statusData.error || 'Failed to load marketplace stats');
                }
            } catch (error) {
                console.error('Failed to load marketplace stats:', error);
                window.notificationManager.showError('Failed to load marketplace statistics');
                this.stats = {}; // Empty stats as fallback
            }
            
            // Load categories
            try {
                const categoriesResponse = await fetch('/api/marketplace/categories');
                if (!categoriesResponse.ok) {
                    throw new Error(`Failed to fetch categories: ${categoriesResponse.status} ${categoriesResponse.statusText}`);
                }
                
                const categoriesData = await categoriesResponse.json();
                if (categoriesData.success) {
                    this.categories = categoriesData.data;
                    console.log('✅ Categories loaded successfully');
                } else {
                    throw new Error(categoriesData.error || 'Failed to load marketplace categories');
                }
            } catch (error) {
                console.error('Failed to load marketplace categories:', error);
                window.notificationManager.showError('Failed to load marketplace categories');
                this.categories = []; // Empty categories as fallback
            }
            
            // Load plugins
            await this.loadPlugins();
            
            // Load favorites
            await this.loadFavorites();
            
            // Load installed plugins
            await this.loadInstalledPlugins();
            
            // Load featured plugins
            await this.loadFeaturedPlugins();
            
            // Load verified plugins
            await this.loadVerifiedPlugins();
            
            console.log('✅ Marketplace data loaded successfully');
            window.notificationManager.showSuccess('Marketplace data loaded successfully');
            
        } catch (error) {
            console.error('Error loading marketplace data:', error);
            window.notificationManager.showError(`Failed to load marketplace data: ${error.message}`);
        } finally {
            this.loading = false;
            this.updateLoadingState();
        }
    }
    
    async loadPlugins(category = null, search = '', featured = false, verified = false) {
        try {
            const params = new URLSearchParams();
            if (category) params.append('category', category);
            if (search) params.append('search', search);
            if (featured) params.append('featured', 'true');
            if (verified) params.append('verified', 'true');
            params.append('limit', this.itemsPerPage);
            params.append('offset', (this.currentPage - 1) * this.itemsPerPage);
            
            const response = await fetch(`/api/marketplace/plugins?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success && data.data && data.data.plugins) {
                this.plugins = data.data.plugins;
                return data.data;
            } else {
                throw new Error(data.error || 'Invalid response format');
            }
        } catch (error) {
            console.error('Failed to load plugins:', error);
            window.notificationManager.showError(`Failed to load plugins: ${error.message}`);
            this.plugins = [];
            return { plugins: [], total_count: 0 };
        }
    }
    
    async loadFavorites() {
        try {
            const response = await fetch('/api/marketplace/favorites');
            if (!response.ok) {
                throw new Error(`Failed to fetch favorites: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.favorites = data.data;
                console.log('✅ Favorites loaded successfully');
            } else {
                throw new Error(data.error || 'Failed to load favorites');
            }
        } catch (error) {
            console.error('Failed to load favorites:', error);
            window.notificationManager.showError('Failed to load favorite plugins');
            this.favorites = [];
        }
    }
    
    async loadInstalledPlugins() {
        try {
            const response = await fetch('/api/marketplace/installed');
            if (!response.ok) {
                throw new Error(`Failed to fetch installed plugins: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.installed = data.data;
                console.log('✅ Installed plugins loaded successfully');
            } else {
                throw new Error(data.error || 'Failed to load installed plugins');
            }
        } catch (error) {
            console.error('Failed to load installed plugins:', error);
            window.notificationManager.showError('Failed to load installed plugins');
            this.installed = [];
        }
    }
    
    async loadFeaturedPlugins() {
        try {
            const response = await fetch('/api/marketplace/featured');
            if (!response.ok) {
                throw new Error(`Failed to fetch featured plugins: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.featured = data.data;
                console.log('✅ Featured plugins loaded successfully');
            } else {
                throw new Error(data.error || 'Failed to load featured plugins');
            }
        } catch (error) {
            console.error('Failed to load featured plugins:', error);
            window.notificationManager.showError('Failed to load featured plugins');
            this.featured = [];
        }
    }
    
    async loadVerifiedPlugins() {
        try {
            const response = await fetch('/api/marketplace/verified');
            if (!response.ok) {
                throw new Error(`Failed to fetch verified plugins: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.verified = data.data;
                console.log('✅ Verified plugins loaded successfully');
            } else {
                throw new Error(data.error || 'Failed to load verified plugins');
            }
        } catch (error) {
            console.error('Failed to load verified plugins:', error);
            window.notificationManager.showError('Failed to load verified plugins');
            this.verified = [];
        }
    }
    
    bindEvents() {
        // Search functionality
        const searchInput = document.getElementById('marketplace-search');
        if (searchInput) {
            window.eventManager.add(searchInput, 'input', window.eventManager.debounce((e) => {
                this.currentSearch = e.target.value;
                this.currentPage = 1;
                this.performSearch();
            }, 300));
        }
        
        // Category filter
        const categorySelect = document.getElementById('marketplace-category');
        if (categorySelect) {
            window.eventManager.add(categorySelect, 'change', (e) => {
                this.currentCategory = e.target.value || null;
                this.currentPage = 1;
                this.loadPluginsAndRender();
            });
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('marketplace-refresh');
        if (refreshBtn) {
            window.eventManager.add(refreshBtn, 'click', (e) => {
                e.preventDefault();
                this.loadMarketplaceData();
            });
        }
        
        // Filter buttons
        const featuredFilter = document.getElementById('filter-featured');
        if (featuredFilter) {
            window.eventManager.add(featuredFilter, 'click', (e) => {
                e.preventDefault();
                featuredFilter.classList.toggle('active');
                this.currentFilters.featured = featuredFilter.classList.contains('active');
                this.currentPage = 1;
                this.loadPluginsAndRender();
            });
        }
        
        const verifiedFilter = document.getElementById('filter-verified');
        if (verifiedFilter) {
            window.eventManager.add(verifiedFilter, 'click', (e) => {
                e.preventDefault();
                verifiedFilter.classList.toggle('active');
                this.currentFilters.verified = verifiedFilter.classList.contains('active');
                this.currentPage = 1;
                this.loadPluginsAndRender();
            });
        }
        
        // Tab navigation
        const tabs = document.querySelectorAll('.marketplace-tab');
        tabs.forEach(tab => {
            window.eventManager.add(tab, 'click', (e) => {
                e.preventDefault();
                const tabType = tab.dataset.tab;
                this.switchTab(tabType);
            });
        });
    }
    
    async performSearch() {
        if (!this.currentSearch.trim()) {
            await this.loadPluginsAndRender();
            return;
        }
        
        try {
            const params = new URLSearchParams({
                q: this.currentSearch,
                limit: this.itemsPerPage,
                offset: (this.currentPage - 1) * this.itemsPerPage
            });
            
            if (this.currentCategory) {
                params.append('category', this.currentCategory);
            }
            
            const response = await fetch(`/api/marketplace/search?${params}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.plugins = data.data.plugins;
                    this.renderPlugins();
                }
            }
        } catch (error) {
            console.error('Error performing search:', error);
            window.notificationManager.showError('Failed to perform search. Please check your connection and try again.');
        }
    }
    
    async loadPluginsAndRender() {
        const data = await this.loadPlugins(
            this.currentCategory,
            this.currentSearch,
            this.currentFilters.featured,
            this.currentFilters.verified
        );
        this.renderPlugins(data);
    }
    
    async refreshMarketplace() {
        try {
            const refreshBtn = document.getElementById('marketplace-refresh');
            if (refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Refreshing...';
            }
            
            const response = await fetch('/api/marketplace/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ force: true })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.notificationManager.showSuccess('Marketplace refreshed successfully');
                    await this.loadMarketplaceData();
                } else {
                    window.notificationManager.showError('Failed to refresh marketplace');
                }
            }
        } catch (error) {
            console.error('Error refreshing marketplace:', error);
            window.notificationManager.showError('Failed to refresh marketplace. Please check your connection and try again.');
        } finally {
            const refreshBtn = document.getElementById('marketplace-refresh');
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
            }
        }
    }
    
    async installPlugin(pluginId) {
        try {
            const response = await fetch(`/api/marketplace/plugins/${pluginId}/install`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.notificationManager.showSuccess(`Plugin ${pluginId} installed successfully`);
                    await this.loadInstalledPlugins();
                    this.renderPlugins();
                    return true;
                } else {
                    window.notificationManager.showError(data.error || 'Failed to install plugin');
                }
            }
        } catch (error) {
            console.error('Error installing plugin:', error);
            window.notificationManager.showError('Failed to install plugin. Please check your connection and try again.');
        }
        return false;
    }
    
    async uninstallPlugin(pluginId) {
        try {
            const response = await fetch(`/api/marketplace/plugins/${pluginId}/uninstall`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.notificationManager.showSuccess(`Plugin ${pluginId} uninstalled successfully`);
                    await this.loadInstalledPlugins();
                    this.renderPlugins();
                    return true;
                } else {
                    window.notificationManager.showError(data.error || 'Failed to uninstall plugin');
                }
            }
        } catch (error) {
            console.error('Error uninstalling plugin:', error);
            window.notificationManager.showError('Failed to uninstall plugin. Please check your connection and try again.');
        }
        return false;
    }
    
    async addToFavorites(pluginId) {
        try {
            const response = await fetch(`/api/marketplace/plugins/${pluginId}/favorite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.notificationManager.showSuccess(`Plugin ${pluginId} added to favorites`);
                    await this.loadFavorites();
                    this.renderPlugins();
                    return true;
                }
            }
        } catch (error) {
            console.error('Error adding to favorites:', error);
            window.notificationManager.showError('Failed to add to favorites. Please check your connection and try again.');
        }
        return false;
    }
    
    async removeFromFavorites(pluginId) {
        try {
            const response = await fetch(`/api/marketplace/plugins/${pluginId}/favorite`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.notificationManager.showSuccess(`Plugin ${pluginId} removed from favorites`);
                    await this.loadFavorites();
                    this.renderPlugins();
                    return true;
                }
            }
        } catch (error) {
            console.error('Error removing from favorites:', error);
            window.notificationManager.showError('Failed to remove from favorites. Please check your connection and try again.');
        }
        return false;
    }
    
    renderMarketplace() {
        this.renderStats();
        this.renderCategories();
        this.renderPlugins();
        this.renderFeaturedPlugins();
        this.renderFavorites();
        this.renderInstalledPlugins();
    }
    
    renderStats() {
        const statsContainer = document.getElementById('marketplace-stats');
        if (!statsContainer) return;
        
        statsContainer.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-puzzle"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.stats.total_plugins || 0}</div>
                            <div class="stat-label">Total Plugins</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-download"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.stats.installed_plugins || 0}</div>
                            <div class="stat-label">Installed</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-star"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.stats.favorite_plugins || 0}</div>
                            <div class="stat-label">Favorites</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-shield-check"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.stats.verified_plugins || 0}</div>
                            <div class="stat-label">Verified</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderCategories() {
        const categoriesContainer = document.getElementById('marketplace-categories');
        if (!categoriesContainer) return;
        
        const categoriesHtml = this.categories.map(category => `
            <div class="category-card" data-category="${category.id}">
                <div class="category-icon">
                    <i class="${category.icon}"></i>
                </div>
                <div class="category-content">
                    <div class="category-name">${category.name}</div>
                    <div class="category-description">${category.description}</div>
                    <div class="category-count">${category.plugin_count} plugins</div>
                </div>
            </div>
        `).join('');
        
        categoriesContainer.innerHTML = categoriesHtml;
        
        // Bind category click events
        const categoryCards = categoriesContainer.querySelectorAll('.category-card');
        categoryCards.forEach(card => {
            window.eventManager.add(card, 'click', (e) => {
                e.preventDefault();
                const categoryId = card.dataset.category;
                this.currentCategory = categoryId;
                this.currentPage = 1;
                this.loadPluginsAndRender();
            });
        });
    }
    
    renderPlugins(data = null) {
        const pluginsContainer = document.getElementById('marketplace-plugins');
        if (!pluginsContainer) return;
        
        const plugins = data ? data.plugins : this.plugins;
        
        if (plugins.length === 0) {
            pluginsContainer.innerHTML = `
                <div class="no-plugins">
                    <i class="bi bi-puzzle"></i>
                    <h3>No plugins found</h3>
                    <p>Try adjusting your search or filters</p>
                </div>
            `;
            return;
        }
        
        const pluginsHtml = plugins.map(plugin => this.renderPluginCard(plugin)).join('');
        pluginsContainer.innerHTML = pluginsHtml;
        
        // Bind plugin action events
        this.bindPluginEvents();
    }
    
    renderPluginCard(plugin) {
        const isInstalled = plugin.is_installed;
        const isFavorite = plugin.is_favorite;
        
        return `
            <div class="plugin-card" data-plugin-id="${plugin.id}">
                <div class="plugin-header">
                    <div class="plugin-icon">
                        <i class="${plugin.icon || 'bi bi-puzzle'}"></i>
                    </div>
                    <div class="plugin-badges">
                        ${plugin.verified ? '<span class="badge badge-verified"><i class="bi bi-shield-check"></i> Verified</span>' : ''}
                        ${plugin.featured ? '<span class="badge badge-featured"><i class="bi bi-star"></i> Featured</span>' : ''}
                        ${plugin.price ? `<span class="badge badge-paid">$${plugin.price}</span>` : '<span class="badge badge-free">Free</span>'}
                    </div>
                </div>
                <div class="plugin-content">
                    <h3 class="plugin-name">${plugin.name}</h3>
                    <p class="plugin-description">${plugin.description}</p>
                    <div class="plugin-meta">
                        <span class="plugin-author">by ${plugin.author}</span>
                        <span class="plugin-version">v${plugin.version}</span>
                        <span class="plugin-category">${this.getCategoryName(plugin.category)}</span>
                    </div>
                    <div class="plugin-stats">
                        <span class="plugin-rating">
                            <i class="bi bi-star-fill"></i>
                            ${plugin.rating ? plugin.rating.toFixed(1) : 'N/A'}
                        </span>
                        <span class="plugin-downloads">
                            <i class="bi bi-download"></i>
                            ${plugin.download_count}
                        </span>
                    </div>
                    <div class="plugin-tags">
                        ${plugin.tags.slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('')}
                        ${plugin.tags.length > 3 ? `<span class="tag-more">+${plugin.tags.length - 3}</span>` : ''}
                    </div>
                </div>
                <div class="plugin-actions">
                    <button class="btn btn-sm btn-outline-primary favorite-btn ${isFavorite ? 'active' : ''}" 
                            data-action="favorite" data-plugin-id="${plugin.id}">
                        <i class="bi bi-star${isFavorite ? '-fill' : ''}"></i>
                    </button>
                    ${isInstalled ? 
                        `<button class="btn btn-sm btn-outline-danger" data-action="uninstall" data-plugin-id="${plugin.id}">
                            <i class="bi bi-trash"></i> Uninstall
                        </button>` :
                        `<button class="btn btn-sm btn-primary" data-action="install" data-plugin-id="${plugin.id}">
                            <i class="bi bi-download"></i> Install
                        </button>`
                    }
                    <button class="btn btn-sm btn-outline-secondary" data-action="details" data-plugin-id="${plugin.id}">
                        <i class="bi bi-info-circle"></i> Details
                    </button>
                </div>
            </div>
        `;
    }
    
    renderFeaturedPlugins() {
        const featuredContainer = document.getElementById('featured-plugins');
        if (!featuredContainer || this.featured.length === 0) return;
        
        const featuredHtml = this.featured.slice(0, 6).map(plugin => this.renderPluginCard(plugin)).join('');
        featuredContainer.innerHTML = `
            <h3>Featured Plugins</h3>
            <div class="plugins-grid">
                ${featuredHtml}
            </div>
        `;
    }
    
    renderFavorites() {
        const favoritesContainer = document.getElementById('favorites-plugins');
        if (!favoritesContainer) return;
        
        if (this.favorites.length === 0) {
            favoritesContainer.innerHTML = `
                <div class="no-favorites">
                    <i class="bi bi-star"></i>
                    <h3>No favorite plugins</h3>
                    <p>Add plugins to your favorites to see them here</p>
                </div>
            `;
            return;
        }
        
        const favoritesHtml = this.favorites.map(plugin => this.renderPluginCard(plugin)).join('');
        favoritesContainer.innerHTML = `
            <h3>Favorite Plugins</h3>
            <div class="plugins-grid">
                ${favoritesHtml}
            </div>
        `;
    }
    
    renderInstalledPlugins() {
        const installedContainer = document.getElementById('installed-plugins');
        if (!installedContainer) return;
        
        if (this.installed.length === 0) {
            installedContainer.innerHTML = `
                <div class="no-installed">
                    <i class="bi bi-download"></i>
                    <h3>No installed plugins</h3>
                    <p>Install plugins from the marketplace to see them here</p>
                </div>
            `;
            return;
        }
        
        const installedHtml = this.installed.map(plugin => this.renderPluginCard(plugin)).join('');
        installedContainer.innerHTML = `
            <h3>Installed Plugins</h3>
            <div class="plugins-grid">
                ${installedHtml}
            </div>
        `;
    }
    
    bindPluginEvents() {
        const actionButtons = document.querySelectorAll('[data-action]');
        actionButtons.forEach(button => {
            window.eventManager.add(button, 'click', async (e) => {
                e.preventDefault();
                const action = button.dataset.action;
                const pluginId = button.dataset.pluginId;
                
                switch (action) {
                    case 'install':
                        await this.installPlugin(pluginId);
                        break;
                    case 'uninstall':
                        if (confirm('Are you sure you want to uninstall this plugin?')) {
                            await this.uninstallPlugin(pluginId);
                        }
                        break;
                    case 'favorite': {
                        const isFavorite = button.classList.contains('active');
                        if (isFavorite) {
                            await this.removeFromFavorites(pluginId);
                        } else {
                            await this.addToFavorites(pluginId);
                        }
                        break;
                    }
                    case 'details':
                        this.showPluginDetails(pluginId);
                        break;
                }
            });
        });
    }
    
    async showPluginDetails(pluginId) {
        try {
            const response = await fetch(`/api/marketplace/plugins/${pluginId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.showPluginModal(data.data);
                }
            }
        } catch (error) {
            console.error('Error loading plugin details:', error);
            window.notificationManager.showError('Failed to load plugin details. Please check your connection and try again.');
        }
    }
    
    showPluginModal(plugin) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'plugin-details-modal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${plugin.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="plugin-details">
                            <div class="plugin-header">
                                <div class="plugin-icon">
                                    <i class="${plugin.icon || 'bi bi-puzzle'}"></i>
                                </div>
                                <div class="plugin-info">
                                    <h3>${plugin.name}</h3>
                                    <p class="plugin-description">${plugin.description}</p>
                                    <div class="plugin-meta">
                                        <span class="plugin-author">by ${plugin.author}</span>
                                        <span class="plugin-version">v${plugin.version}</span>
                                        <span class="plugin-category">${this.getCategoryName(plugin.category)}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="plugin-details-content">
                                <div class="row">
                                    <div class="col-md-8">
                                        <h4>Description</h4>
                                        <p>${plugin.description}</p>
                                        
                                        <h4>Tags</h4>
                                        <div class="plugin-tags">
                                            ${plugin.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                                        </div>
                                        
                                        ${plugin.dependencies.length > 0 ? `
                                            <h4>Dependencies</h4>
                                            <ul>
                                                ${plugin.dependencies.map(dep => `<li>${dep}</li>`).join('')}
                                            </ul>
                                        ` : ''}
                                        
                                        ${plugin.requirements.length > 0 ? `
                                            <h4>Requirements</h4>
                                            <ul>
                                                ${plugin.requirements.map(req => `<li>${req}</li>`).join('')}
                                            </ul>
                                        ` : ''}
                                    </div>
                                    <div class="col-md-4">
                                        <div class="plugin-sidebar">
                                            <div class="plugin-stats">
                                                <div class="stat">
                                                    <span class="stat-label">Rating</span>
                                                    <span class="stat-value">
                                                        <i class="bi bi-star-fill"></i>
                                                        ${plugin.rating ? plugin.rating.toFixed(1) : 'N/A'}
                                                    </span>
                                                </div>
                                                <div class="stat">
                                                    <span class="stat-label">Downloads</span>
                                                    <span class="stat-value">${plugin.download_count}</span>
                                                </div>
                                                <div class="stat">
                                                    <span class="stat-label">File Size</span>
                                                    <span class="stat-value">${this.formatFileSize(plugin.file_size)}</span>
                                                </div>
                                                <div class="stat">
                                                    <span class="stat-label">Last Updated</span>
                                                    <span class="stat-value">${this.formatDate(plugin.last_updated)}</span>
                                                </div>
                                            </div>
                                            
                                            <div class="plugin-actions">
                                                <button class="btn btn-primary w-100 mb-2" data-action="install" data-plugin-id="${plugin.id}">
                                                    <i class="bi bi-download"></i> Install Plugin
                                                </button>
                                                <button class="btn btn-outline-primary w-100 mb-2" data-action="favorite" data-plugin-id="${plugin.id}">
                                                    <i class="bi bi-star"></i> Add to Favorites
                                                </button>
                                                ${plugin.website_url ? `
                                                    <a href="${plugin.website_url}" target="_blank" class="btn btn-outline-secondary w-100 mb-2">
                                                        <i class="bi bi-globe"></i> Visit Website
                                                    </a>
                                                ` : ''}
                                                ${plugin.documentation_url ? `
                                                    <a href="${plugin.documentation_url}" target="_blank" class="btn btn-outline-secondary w-100">
                                                        <i class="bi bi-book"></i> Documentation
                                                    </a>
                                                ` : ''}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Initialize Bootstrap modal
        const bootstrapModal = new window.bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Bind events
        window.eventManager.add(modal, 'hidden.bs.modal', () => {
            modal.remove();
        });
        
        // Bind action buttons
        const actionButtons = modal.querySelectorAll('[data-action]');
        actionButtons.forEach(button => {
            window.eventManager.add(button, 'click', async (e) => {
                e.preventDefault();
                const action = button.dataset.action;
                const pluginId = button.dataset.pluginId;
                
                switch (action) {
                    case 'install':
                        await this.installPlugin(pluginId);
                        bootstrapModal.hide();
                        break;
                    case 'favorite':
                        await this.addToFavorites(pluginId);
                        break;
                }
            });
        });
    }
    
    getCategoryName(categoryId) {
        const category = this.categories.find(cat => cat.id === categoryId);
        return category ? category.name : categoryId;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        return new Date(dateString).toLocaleDateString();
    }
    
    updateLoadingState() {
        const containers = document.querySelectorAll('.marketplace-container');
        containers.forEach(container => {
            if (this.loading) {
                container.classList.add('loading');
            } else {
                container.classList.remove('loading');
            }
        });
    }
    

    
    switchTab(tabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.marketplace-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Hide all tab content
        document.querySelectorAll('.marketplace-tab-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // Activate selected tab
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
        
        // Show selected tab content
        const activeContent = document.getElementById(`${tabName}-content`);
        if (activeContent) {
            activeContent.style.display = 'block';
        }
    }
    
    updateActiveCategory() {
        // Remove active class from all categories
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.remove('active');
        });
        
        // Add active class to current category
        if (this.currentCategory) {
            const activeCard = document.querySelector(`[data-category="${this.currentCategory}"]`);
            if (activeCard) {
                activeCard.classList.add('active');
            }
        }
    }
    
    // Utility method for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    

}

// Notification system handled by global NotificationManager

// Placeholder for bootstrap if not defined
if (typeof bootstrap === 'undefined') {
    window.bootstrap = {
        Modal: function() {
            return {
                show: () => console.log('Modal show'),
                hide: () => console.log('Modal hide')
            };
        }
    };
}

// Add CSS animations for toast notifications if not already present
if (!document.getElementById('marketplace-toast-styles')) {
    const style = document.createElement('style');
    style.id = 'marketplace-toast-styles';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .marketplace-toast {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        .marketplace-toast .toast-content {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .marketplace-toast .toast-close {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0;
            margin-left: auto;
            opacity: 0.7;
        }
        
        .marketplace-toast .toast-close:hover {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
}

// Enhanced initialization with multiple fallback strategies
function initializeMarketplaceManager() {
    try {
        // Check if marketplace container exists
        const marketplaceContainer = document.getElementById('marketplace-container');
        if (marketplaceContainer) {
            console.log('🚀 Initializing Marketplace Manager...');
            
            // Destroy existing instance if it exists
            if (window.marketplaceManager && typeof window.marketplaceManager.destroy === 'function') {
                window.marketplaceManager.destroy();
            }
            
            // Create new instance
            window.marketplaceManager = new MarketplaceManager();
            console.log('✅ Marketplace Manager initialized successfully');
            
            // Add global convenience methods
            window.refreshMarketplace = () => {
                if (window.marketplaceManager) {
                    window.marketplaceManager.loadMarketplaceData();
                }
            };
            
            window.searchMarketplace = (query) => {
                if (window.marketplaceManager) {
                    window.marketplaceManager.currentSearch = query || '';
                    window.marketplaceManager.currentPage = 1;
                    window.marketplaceManager.performSearch();
                }
            };
            
        } else {
            console.log('ℹ️ Marketplace container not found, skipping initialization');
        }
    } catch (error) {
        console.error('❌ Error initializing Marketplace Manager:', error);
    }
}

// Initialize marketplace manager when DOM is loaded
if (document.readyState === 'loading') {
    window.eventManager.add(document, 'DOMContentLoaded', initializeMarketplaceManager);
} else {
    // DOM is already loaded
    initializeMarketplaceManager();
}
