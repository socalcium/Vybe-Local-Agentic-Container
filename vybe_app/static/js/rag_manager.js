/**
 * RAG Manager - Document and Collection Management
 * Handles file uploads, collection management, and document operations
 * Enhanced with comprehensive error handling, logging, and user feedback
 * 
 * Features:
 * - Collection CRUD operations
 * - Document management (view, edit, delete, create)
 * - File upload with progress tracking
 * - URL content ingestion
 * - Automated scheduling system
 * - Modal management with keyboard shortcuts
 * - Comprehensive error handling and user notifications
 * - Real-time status updates
 */

(function() {
    // Global variables
    let currentCollection = null;
    let currentCollectionData = null;
    let eventListeners = [];
    let isInitialized = false;
    let isLoading = false;
    
    // DOM element references
    let collectionSelector, refreshButton, refreshCollectionsBtn;
    let createCollectionBtn, editCollectionBtn, deleteCollectionBtn;
    let fileInput, uploadFilesBtn, manageScheduleBtn;
    let createCollectionForm, editCollectionForm, scheduleForm, removeScheduleBtn;
    let createCollectionModal, editCollectionModal, editDocumentModal, createDocumentModal, scheduleModal;
    let newCollectionNameInput, newCollectionDescriptionInput, editCollectionNameInput, editCollectionDescriptionInput;
    let documentsListEl, loadingEl, noDocumentsEl, scheduleInfo;
    let scheduleUrlInput, scheduleFrequencySelect, currentScheduleStatus;
    let loadUrlButton, urlInput;
    
    // Enhanced element getter with validation
    function getElement(id, required = true) {
        const element = document.getElementById(id);
        if (!element && required) {
            console.warn(`[RAG Manager] Required element not found: ${id}`);
        }
        return element;
    }
    
    // Cleanup function for event listeners
    function cleanup() {
        eventListeners.forEach(({element, event, handler}) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        eventListeners = [];
    }
    
    function addEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            eventListeners.push({element, event, handler});
        }
    }

    async function loadCollections() {
        console.log('[RAG Manager] Loading collections...');
        
        // Prevent multiple simultaneous loads
        if (isLoading) {
            console.log('[RAG Manager] Load already in progress, skipping...');
            return;
        }
        
        isLoading = true;
        
        // Show loading state if possible
        if (collectionSelector) {
            collectionSelector.innerHTML = '<option value="">Loading collections...</option>';
        }
        
        try {
            const response = await fetch('/api/rag_collections');
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[RAG Manager] HTTP Error Response:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText.substring(0, 100)}`);
            }
            
            const data = await response.json();
            console.log('[RAG Manager] Collections loaded:', data);
            
            // Non-blocking banner when receiving default/fallback collections
            if (Array.isArray(data) && data.length === 1 && data[0] && data[0].status_message && /ChromaDB|Default|Initializing|Error/i.test(data[0].status_message)) {
                showNotification('Knowledge base is initializing. You can still upload and manage content; it will become available shortly.', 'info');
            }
            
            if (Array.isArray(data)) {
                // Direct array response
                populateCollectionSelector(data);
                // Load documents for the first collection after populating selector
                if (data.length > 0) {
                    currentCollection = typeof data[0] === 'string' ? data[0] : data[0].collection_name;
                    await loadDocumentsForCollection(currentCollection);
                }
            } else if (data.success && data.collections) {
                populateCollectionSelector(data.collections);
                // Load documents for the first collection after populating selector
                if (data.collections.length > 0) {
                    currentCollection = typeof data.collections[0] === 'string' ? data.collections[0] : data.collections[0].collection_name;
                    await loadDocumentsForCollection(currentCollection);
                }
            } else {
                throw new Error(data.error || 'Failed to load collections');
            }
            
            console.log('[RAG Manager] Collections loaded successfully');
            
        } catch (error) {
            console.error('[RAG Manager] Error loading collections:', error);
            if (collectionSelector) {
                collectionSelector.innerHTML = '<option value="">Error loading collections</option>';
            }
            showNotification('Error loading collections: ' + error.message, 'error');
        } finally {
            isLoading = false;
        }
    }

    function populateCollectionSelector(collections) {
        console.log('[RAG Manager] Populating collection selector with', collections.length, 'collections');
        
        if (!collectionSelector) {
            console.warn('[RAG Manager] Collection selector not found, cannot populate');
            return;
        }
        
        collectionSelector.innerHTML = '';
        
        if (collections.length === 0) {
            collectionSelector.innerHTML = '<option value="">No collections available</option>';
            
            // Disable related buttons safely
            if (deleteCollectionBtn) deleteCollectionBtn.disabled = true;
            if (editCollectionBtn) editCollectionBtn.disabled = true;
            if (uploadFilesBtn) uploadFilesBtn.disabled = true;
            if (manageScheduleBtn) manageScheduleBtn.disabled = true;
            
            showNotification('No collections found. Create a new collection to get started.', 'info');
            return;
        }

        collections.forEach(collection => {
            const option = document.createElement('option');
            option.value = typeof collection === 'string' ? collection : collection.name;
            const displayName = typeof collection === 'string' ? collection : collection.name;
            const description = typeof collection === 'object' && collection.description ? 
                ` - ${collection.description}` : '';
            
            // Add status indicator to display name
            let statusIndicator = '';
            if (typeof collection === 'object' && collection.is_ingesting) {
                statusIndicator = ' 🔄';
            }
            
            option.textContent = displayName + description + statusIndicator;
            option.setAttribute('data-description', typeof collection === 'object' ? (collection.description || '') : '');
            option.setAttribute('data-collection-data', JSON.stringify(collection));
            
            if ((typeof collection === 'string' ? collection : collection.name) === currentCollection) {
                option.selected = true;
                currentCollectionData = typeof collection === 'object' ? collection : null;
            }
            collectionSelector.appendChild(option);
        });

        // Enable/disable buttons safely
        if (deleteCollectionBtn) deleteCollectionBtn.disabled = false;
        if (editCollectionBtn) editCollectionBtn.disabled = false;
        if (uploadFilesBtn) uploadFilesBtn.disabled = false;
        if (manageScheduleBtn) manageScheduleBtn.disabled = false;
        
        // Update schedule info for current selection
        updateScheduleInfo();
        
        console.log('[RAG Manager] Collection selector populated successfully');
        
        // Documents will be loaded by loadCollections after this function
    }

    function updateScheduleInfo() {
        console.log('[RAG Manager] Updating schedule info...');
        
        if (!scheduleInfo) {
            console.warn('[RAG Manager] Schedule info element not found');
            return;
        }
        
        try {
            const selectedOption = collectionSelector?.selectedOptions[0];
            if (selectedOption) {
                try {
                    currentCollectionData = JSON.parse(selectedOption.getAttribute('data-collection-data') || '{}');
                } catch (error) {
                    // Error handling for parsing collection data
                    console.warn('[RAG Manager] Error parsing collection data:', error);
                    currentCollectionData = null;
                }
            }
            
            if (currentCollectionData && currentCollectionData.schedule_frequency && currentCollectionData.schedule_frequency !== 'never') {
                let scheduleText = `Scheduled: ${currentCollectionData.schedule_frequency}`;
                if (currentCollectionData.scheduled_url) {
                    scheduleText += ` from ${currentCollectionData.scheduled_url}`;
                }
                if (currentCollectionData.next_update_due_timestamp) {
                    const nextUpdate = new Date(currentCollectionData.next_update_due_timestamp);
                    scheduleText += `<br><small>Next update: ${nextUpdate.toLocaleString()}</small>`;
                }
                if (currentCollectionData.last_updated_timestamp) {
                    const lastUpdate = new Date(currentCollectionData.last_updated_timestamp);
                    scheduleText += `<br><small>Last updated: ${lastUpdate.toLocaleString()}</small>`;
                }
                scheduleInfo.innerHTML = `<p>${scheduleText}</p>`;
            } else {
                scheduleInfo.innerHTML = '<p>No schedule set for this collection</p>';
            }
            
            // Update status if ingesting
            if (currentCollectionData && currentCollectionData.is_ingesting) {
                scheduleInfo.innerHTML += `<p class="status-ingesting">🔄 ${currentCollectionData.status_message}</p>`;
            } else if (currentCollectionData && currentCollectionData.status_message && currentCollectionData.status_message !== 'Idle') {
                scheduleInfo.innerHTML += `<p class="status-message">${currentCollectionData.status_message}</p>`;
            }
            
            console.log('[RAG Manager] Schedule info updated successfully');
            
        } catch (error) {
            console.error('[RAG Manager] Error updating schedule info:', error);
            scheduleInfo.innerHTML = '<p>Error loading schedule information</p>';
        }
    }

    async function loadDocumentsForCollection(collectionName) {
        if (!collectionName) {
            collectionName = collectionSelector.value || 'general_knowledge';
        }
        
        currentCollection = collectionName;
        
        loadingEl.style.display = 'block';
        documentsListEl.style.display = 'none';
        noDocumentsEl.style.display = 'none';

        try {
            const response = await fetch(`/api/rag_collections/${encodeURIComponent(collectionName)}/documents`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('HTTP Error Response:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText.substring(0, 100)}`);
            }
            
            // Check if response is actually JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const textContent = await response.text();
                console.error('Non-JSON Response:', textContent);
                if (textContent.startsWith('<!doctype') || textContent.startsWith('<html')) {
                    throw new Error('Server returned HTML instead of JSON - likely an error page');
                }
                throw new Error('Server response is not JSON format');
            }
            
            const data = await response.json();
            
            if (data.success) {
                const documents = data.documents || [];
                if (documents.length === 0) {
                    noDocumentsEl.style.display = 'block';
                } else {
                    displayDocuments(documents);
                    documentsListEl.style.display = 'block';
                }
            } else {
                throw new Error(data.error || 'Failed to load documents');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            let errorMessage = error.message;
            
            // Provide more specific error messages
            if (error.name === 'SyntaxError' && error.message.includes('JSON')) {
                errorMessage = 'Server returned invalid JSON response. Check backend logs for errors.';
            } else if (error.message.includes('<!doctype')) {
                errorMessage = 'Server returned an error page instead of document data. Check backend status.';
            }
            
            documentsListEl.innerHTML = `<div class="error-message">Error loading documents: ${errorMessage}</div>`;
            documentsListEl.style.display = 'block';
        } finally {
            loadingEl.style.display = 'none';
        }
    }

    // Keep the old loadDocuments function for backward compatibility, but make it call the new function
    async function loadDocuments() {
        return loadDocumentsForCollection(currentCollection);
    }

    function displayDocuments(documents) {
        const documentElements = documents.map(doc => `
            <div class="document-item" data-doc-id="${doc.id}">
                <div class="document-header">
                    <div class="document-source">
                        <strong>Source:</strong> ${escapeHtml(doc.source)}
                    </div>
                    <div class="document-actions">
                        <button class="edit-document-btn" data-doc-id="${doc.id}">
                            ✏️ Edit
                        </button>
                        <button class="delete-document-btn" data-doc-id="${doc.id}">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
                <div class="document-snippet">
                    <strong>Content Preview:</strong>
                    <p>${escapeHtml(doc.snippet)}</p>
                </div>
                <div class="document-id">
                    <small><strong>ID:</strong> ${escapeHtml(doc.id)}</small>
                </div>
            </div>
        `).join('');

        documentsListEl.innerHTML = `
            <div class="documents-grid">
                ${documentElements}
            </div>
        `;

        // Add event listeners to edit and delete buttons
        document.querySelectorAll('.edit-document-btn').forEach(btn => {
            addEventListener(btn, 'click', handleEditDocument);
        });
        
        document.querySelectorAll('.delete-document-btn').forEach(btn => {
            addEventListener(btn, 'click', handleDeleteDocument);
        });
    }

    async function handleDeleteDocument(event) {
        const docId = event.target.getAttribute('data-doc-id');
        const documentItem = event.target.closest('.document-item');
        
        if (!confirm(`Are you sure you want to delete this document?\n\nID: ${docId}`)) {
            return;
        }

        // Disable the button and show loading state
        event.target.disabled = true;
        event.target.textContent = 'Deleting...';

        try {
            const response = await fetch(`/api/delete_rag_document/${encodeURIComponent(docId)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to delete document');
            }

            // Remove the document from the UI
            documentItem.remove();

            // Check if there are any documents left
            const remainingDocs = document.querySelectorAll('.document-item');
            if (remainingDocs.length === 0) {
                noDocumentsEl.style.display = 'block';
                documentsListEl.style.display = 'none';
            }

            showNotification('Document deleted successfully', 'success');

        } catch (error) {
            console.error('Error deleting document:', error);
            showNotification('Error deleting document: ' + error.message, 'error');
            
            // Re-enable the button
            event.target.disabled = false;
            event.target.textContent = '🗑️ Delete';
        }
    }

    async function handleEditDocument(event) {
        const docId = event.target.getAttribute('data-doc-id');
        
        // Disable the button and show loading state
        event.target.disabled = true;
        event.target.textContent = 'Loading...';
        
        try {
            await editDocument(docId);
        } catch (error) {
            console.error('Error editing document:', error);
            showNotification('Error loading document: ' + error.message, 'error');
        } finally {
            // Re-enable the button
            event.target.disabled = false;
            event.target.textContent = '✏️ Edit';
        }
    }

    // Collection Management Functions
    async function createCollection() {
        const collectionName = newCollectionNameInput.value.trim();
        const collectionDescription = newCollectionDescriptionInput.value.trim();
        
        if (!collectionName) {
            showNotification('Collection name is required', 'error');
            return;
        }

        // Validate collection name
        if (!/^[a-z0-9_]+$/.test(collectionName)) {
            showNotification('Collection name must contain only lowercase letters, numbers, and underscores', 'error');
            return;
        }

        try {
            const response = await fetch('/api/rag_collections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    collection_name: collectionName,
                    description: collectionDescription
                })
            });

            const data = await response.json();

            if (data.success) {
                showNotification('Collection created successfully', 'success');
                hideCreateCollectionModal();
                loadCollections();
                newCollectionNameInput.value = '';
                newCollectionDescriptionInput.value = '';
            } else {
                throw new Error(data.error || 'Failed to create collection');
            }
        } catch (error) {
            console.error('Error creating collection:', error);
            showNotification('Error creating collection: ' + error.message, 'error');
        }
    }

    async function deleteCollection() {
        const collectionName = collectionSelector.value;
        
        if (!collectionName) {
            showNotification('No collection selected', 'error');
            return;
        }

        if (collectionName === 'vybe_documents') {
            showNotification('Cannot delete the default system collection', 'error');
            return;
        }

        if (!confirm(`Are you sure you want to delete the collection "${collectionName}"?\n\nThis action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch('/api/rag_collections/delete', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: collectionName })
            });

            const data = await response.json();

            if (data.success) {
                showNotification('Collection deleted successfully', 'success');
                loadCollections();
            } else {
                throw new Error(data.error || 'Failed to delete collection');
            }
        } catch (error) {
            console.error('Error deleting collection:', error);
            showNotification('Error deleting collection: ' + error.message, 'error');
        }
    }

    // Web Content Loading Functions
    async function loadUrlIntoRag() {
        const urlInput = document.getElementById('url-input');
        const loadButton = document.getElementById('load-url-button');
        const url = urlInput.value.trim();

        if (!url) {
            showNotification('Please enter a URL', 'error');
            return;
        }

        // Validate URL format
        try {
            new URL(url);
        } catch {
            showNotification('Please enter a valid URL', 'error');
            return;
        }

        if (!currentCollection) {
            showNotification('No collection selected', 'error');
            return;
        }

        // Show loading state
        loadButton.disabled = true;
        loadButton.textContent = 'Loading...';
        
        try {
            const response = await fetch(`/api/rag_collections/${currentCollection}/load_url`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();

            if (result.success) {
                showNotification(result.message, 'success');
                urlInput.value = '';
                loadDocuments();
                loadCollections(); // Refresh to update status
            } else {
                showNotification('Error loading URL: ' + result.error, 'error');
            }

        } catch (error) {
            console.error('Error loading URL:', error);
            showNotification('Error loading URL: ' + error.message, 'error');
        } finally {
            loadButton.disabled = false;
            loadButton.textContent = 'Load URL into RAG';
        }
    }

    // Modal Functions
    function showCreateCollectionModal() {
        createCollectionModal.style.display = 'block';
        newCollectionNameInput.focus();
    }

    function hideCreateCollectionModal() {
        createCollectionModal.style.display = 'none';
        newCollectionNameInput.value = '';
        newCollectionDescriptionInput.value = '';
    }

    function showEditCollectionModal() {
        const selectedCollection = collectionSelector.value;
        if (!selectedCollection) {
            showNotification('Please select a collection to edit', 'error');
            return;
        }

        const selectedOption = collectionSelector.options[collectionSelector.selectedIndex];
        const description = selectedOption.getAttribute('data-description') || '';

        editCollectionNameInput.value = selectedCollection;
        editCollectionDescriptionInput.value = description;
        editCollectionModal.style.display = 'block';
        editCollectionDescriptionInput.focus();
    }

    function hideEditCollectionModal() {
        editCollectionModal.style.display = 'none';
        editCollectionNameInput.value = '';
        editCollectionDescriptionInput.value = '';
    }

    async function updateCollectionDescription() {
        const collectionName = editCollectionNameInput.value.trim();
        const collectionDescription = editCollectionDescriptionInput.value.trim();

        if (!collectionName) {
            showNotification('Collection name is required', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/rag_collections/${encodeURIComponent(collectionName)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    description: collectionDescription
                })
            });

            const data = await response.json();

            if (data.success) {
                showNotification('Collection description updated successfully', 'success');
                hideEditCollectionModal();
                loadCollections();
            } else {
                throw new Error(data.error || 'Failed to update collection description');
            }
        } catch (error) {
            console.error('Error updating collection description:', error);
            showNotification('Error updating collection description: ' + error.message, 'error');
        }
    }

    // Notification Function - Updated to use global notification manager
    function showNotification(message, type = 'info') {
        console.log(`[RAG Manager] ${type.toUpperCase()}: ${message}`);
        
        // Use the global notification manager
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
                case 'info':
                default:
                    window.notificationManager.showInfo(message);
                    break;
            }
        } else {
            // Fallback to console and alert for critical errors
            if (type === 'error') {
                alert(`Error: ${message}`);
            } else if (type === 'success') {
                console.info(`Success: ${message}`);
            } else {
                console.info(`Info: ${message}`);
            }
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize event listeners
    function initializeEventListeners() {
        // Get DOM references
        collectionSelector = document.getElementById('collection-selector');
        refreshButton = document.getElementById('refresh-button');
        refreshCollectionsBtn = document.getElementById('refresh-collections');
        createCollectionBtn = document.getElementById('create-collection');
        editCollectionBtn = document.getElementById('edit-collection');
        deleteCollectionBtn = document.getElementById('delete-collection');
        fileInput = document.getElementById('file-input');
        uploadFilesBtn = document.getElementById('upload-files');
        manageScheduleBtn = document.getElementById('manage-schedule');
        createCollectionForm = document.getElementById('create-collection-form');
        editCollectionForm = document.getElementById('edit-collection-form');
        scheduleForm = document.getElementById('schedule-form');
        removeScheduleBtn = document.getElementById('remove-schedule');
        loadUrlButton = document.getElementById('load-url-button');
        urlInput = document.getElementById('url-input');

        // Main action buttons
        if (refreshButton) {
            addEventListener(refreshButton, 'click', () => loadDocumentsForCollection(currentCollection));
        }
        if (refreshCollectionsBtn) {
            addEventListener(refreshCollectionsBtn, 'click', loadCollections);
        }
        if (collectionSelector) {
            addEventListener(collectionSelector, 'change', (e) => {
                currentCollection = e.target.value;
                loadDocumentsForCollection(currentCollection);
            });
        }
        if (createCollectionBtn) {
            addEventListener(createCollectionBtn, 'click', showCreateCollectionModal);
        }
        if (editCollectionBtn) {
            addEventListener(editCollectionBtn, 'click', showEditCollectionModal);
        }
        if (deleteCollectionBtn) {
            addEventListener(deleteCollectionBtn, 'click', deleteCollection);
        }
        
        // File upload listeners
        if (fileInput) {
            addEventListener(fileInput, 'change', (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    showSelectedFiles(files);
                }
            });
        }
        
        if (uploadFilesBtn) {
            addEventListener(uploadFilesBtn, 'click', uploadFiles);
        }
        if (manageScheduleBtn) {
            addEventListener(manageScheduleBtn, 'click', showScheduleModal);
        }
        
        // Modal form listeners
        if (createCollectionForm) {
            addEventListener(createCollectionForm, 'submit', (e) => {
                e.preventDefault();
                createCollection();
            });
        }

        // Utility function to show selected files
        function showSelectedFiles(files) {
            // Display selected files to user with enhanced feedback
            console.log('[RAG Manager] Selected files:', files);
            
            const fileList = Array.from(files).map(file => 
                `${file.name} (${(file.size / 1024).toFixed(1)} KB)`
            ).join(', ');
            
            showNotification(`Selected ${files.length} file(s): ${fileList}`, 'info');
            
            // Enable upload button if files are selected and collection is chosen
            if (uploadFilesBtn && currentCollection) {
                uploadFilesBtn.disabled = false;
                uploadFilesBtn.textContent = `Upload ${files.length} File(s) to RAG`;
            }
        }

        // Function to update collection
        async function updateCollection() {
            await updateCollectionDescription();
        }

        if (editCollectionForm) {
            addEventListener(editCollectionForm, 'submit', (e) => {
                e.preventDefault();
                updateCollection();
            });
        }

        // Schedule modal listeners
        if (scheduleForm) {
            addEventListener(scheduleForm, 'submit', (e) => {
                e.preventDefault();
                saveSchedule();
            });
        }
        
        if (removeScheduleBtn) {
            addEventListener(removeScheduleBtn, 'click', removeSchedule);
        }

        // URL loading listeners
        if (loadUrlButton) {
            addEventListener(loadUrlButton, 'click', loadUrlIntoRag);
        }
        
        if (urlInput) {
            addEventListener(urlInput, 'keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    loadUrlIntoRag();
                }
            });
        }
        
        // Enhanced keyboard shortcuts
        addEventListener(document, 'keydown', (e) => {
            // Ctrl+R to refresh documents
            if (e.ctrlKey && e.key === 'r' && !e.shiftKey) {
                e.preventDefault();
                if (currentCollection) {
                    loadDocumentsForCollection(currentCollection);
                    showNotification('Refreshing documents...', 'info');
                }
            }
            
            // Ctrl+Shift+R to refresh collections
            if (e.ctrlKey && e.shiftKey && e.key === 'R') {
                e.preventDefault();
                loadCollections();
                showNotification('Refreshing collections...', 'info');
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                const openModals = document.querySelectorAll('[id$="-modal"]');
                openModals.forEach(modal => {
                    if (modal.style.display === 'block') {
                        modal.style.display = 'none';
                    }
                });
            }
        });

        // Close modal when clicking outside
        addEventListener(window, 'click', (e) => {
            const modals = [
                {element: createCollectionModal, hide: hideCreateCollectionModal},
                {element: editCollectionModal, hide: hideEditCollectionModal},
                {element: scheduleModal, hide: hideScheduleModal}
            ];
            
            modals.forEach(({element, hide}) => {
                if (element && e.target === element) {
                    hide();
                }
            });
        });
        
        console.log('[RAG Manager] Event listeners initialized successfully');
    }

    // Initialize close modal event listeners (non-dynamic)
    function initializeModalCloseEvents() {
        console.log('[RAG Manager] Setting up modal close events...');
        
        // Create Collection Modal
        const createModalClose = document.querySelector('#create-collection-modal .close-modal');
        const createModalCancel = document.querySelector('#create-collection-modal .cancel-btn');
        if (createModalClose) createModalClose.addEventListener('click', hideCreateCollectionModal);
        if (createModalCancel) createModalCancel.addEventListener('click', hideCreateCollectionModal);

        // Edit Collection Modal
        const editModalClose = document.querySelector('#edit-collection-modal .close-modal');
        const editModalCancel = document.querySelector('#edit-collection-modal .cancel-btn');
        if (editModalClose) editModalClose.addEventListener('click', hideEditCollectionModal);
        if (editModalCancel) editModalCancel.addEventListener('click', hideEditCollectionModal);

        // Schedule Modal
        const scheduleModalClose = document.querySelector('#schedule-modal .close-modal');
        const scheduleModalCancel = document.querySelector('#schedule-modal .cancel-btn');
        if (scheduleModalClose) scheduleModalClose.addEventListener('click', hideScheduleModal);
        if (scheduleModalCancel) scheduleModalCancel.addEventListener('click', hideScheduleModal);

        // Edit Document Modal
        const editDocModalClose = document.querySelector('#edit-document-modal .close-modal');
        const editDocModalCancel = document.querySelector('#edit-document-modal .cancel-btn');
        if (editDocModalClose) editDocModalClose.addEventListener('click', hideEditDocumentModal);
        if (editDocModalCancel) editDocModalCancel.addEventListener('click', hideEditDocumentModal);

        // Create Document Modal
        const createDocModalClose = document.querySelector('#create-document-modal .close-modal');
        const createDocModalCancel = document.querySelector('#create-document-modal .cancel-btn');
        if (createDocModalClose) createDocModalClose.addEventListener('click', hideCreateDocumentModal);
        if (createDocModalCancel) createDocModalCancel.addEventListener('click', hideCreateDocumentModal);

        // Add click-outside-to-close functionality for all modals
        if (editDocumentModal) {
            editDocumentModal.addEventListener('click', (e) => {
                if (e.target === editDocumentModal) {
                    hideEditDocumentModal();
                }
            });
        }
        
        if (createDocumentModal) {
            createDocumentModal.addEventListener('click', (e) => {
                if (e.target === createDocumentModal) {
                    hideCreateDocumentModal();
                }
            });
        }
        
        console.log('[RAG Manager] Modal close events setup completed');
    }

    // Enhanced initialization system
    function initializeRAGManager() {
        console.log('[RAG Manager] Starting initialization...');
        
        // Prevent multiple initializations
        if (isInitialized) {
            console.log('[RAG Manager] Already initialized, skipping...');
            return;
        }
        
        try {
            // Initialize DOM elements first
            const domInitialized = initializeDOMElements();
            if (!domInitialized) {
                showNotification('RAG Manager: Failed to initialize DOM elements. Some features may not work.', 'warning');
            }
            
            // Initialize event listeners
            initializeEventListeners();
            
            // Initialize modal close events
            initializeModalCloseEvents();
            
            // Load initial collections
            loadCollections();
            
            isInitialized = true;
            console.log('[RAG Manager] Initialization completed successfully');
            showNotification('RAG Manager initialized successfully', 'success');
            
        } catch (error) {
            console.error('[RAG Manager] Initialization failed:', error);
            showNotification('RAG Manager initialization failed: ' + error.message, 'error');
        }
    }
    
    // Enhanced cleanup system
    function destroy() {
        console.log('[RAG Manager] Cleaning up event listeners...');
        cleanup();
        
        // Clear global variables
        currentCollection = null;
        currentCollectionData = null;
        isInitialized = false;
        isLoading = false;
        
        console.log('[RAG Manager] Cleanup completed');
    }

    // New functions for file upload and scheduling
    async function uploadFiles() {
        if (!fileInput.files.length || !currentCollection) {
            showNotification('Please select files and ensure a collection is selected', 'error');
            return;
        }

        const formData = new FormData();
        for (const file of fileInput.files) {
            formData.append('files', file);
        }

        try {
            uploadFilesBtn.disabled = true;
            uploadFilesBtn.textContent = 'Uploading...';

            const response = await fetch(`/api/rag_collections/${currentCollection}/upload_files`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showNotification(result.message, 'success');
                fileInput.value = '';
                loadDocuments();
                loadCollections(); // Refresh to update status
            } else {
                showNotification('Error uploading files: ' + result.error, 'error');
            }

        } catch (error) {
            console.error('Error uploading files:', error);
            showNotification('Error uploading files: ' + error.message, 'error');
        } finally {
            uploadFilesBtn.disabled = fileInput.files.length === 0 || !currentCollection;
            uploadFilesBtn.textContent = 'Upload Files to RAG';
        }
    }

    function showScheduleModal() {
        if (!currentCollection) {
            showNotification('Please select a collection first', 'error');
            return;
        }

        // Populate form with current schedule data
        if (currentCollectionData) {
            scheduleUrlInput.value = currentCollectionData.scheduled_url || '';
            scheduleFrequencySelect.value = currentCollectionData.schedule_frequency || 'never';
            
            let statusHtml = '';
            if (currentCollectionData.schedule_frequency && currentCollectionData.schedule_frequency !== 'never') {
                statusHtml += `<p><strong>Current Schedule:</strong> ${currentCollectionData.schedule_frequency}</p>`;
                if (currentCollectionData.scheduled_url) {
                    statusHtml += `<p><strong>URL:</strong> ${currentCollectionData.scheduled_url}</p>`;
                }
                if (currentCollectionData.next_update_due_timestamp) {
                    const nextUpdate = new Date(currentCollectionData.next_update_due_timestamp);
                    statusHtml += `<p><strong>Next Update:</strong> ${nextUpdate.toLocaleString()}</p>`;
                }
                if (currentCollectionData.last_updated_timestamp) {
                    const lastUpdate = new Date(currentCollectionData.last_updated_timestamp);
                    statusHtml += `<p><strong>Last Updated:</strong> ${lastUpdate.toLocaleString()}</p>`;
                }
            } else {
                statusHtml = '<p>No schedule currently set</p>';
            }
            currentScheduleStatus.innerHTML = statusHtml;
        }

        scheduleModal.style.display = 'block';
    }

    function hideScheduleModal() {
        scheduleModal.style.display = 'none';
    }

    async function saveSchedule() {
        const url = scheduleUrlInput.value.trim();
        const frequency = scheduleFrequencySelect.value;

        if (frequency !== 'never' && !url) {
            showNotification('Please enter a URL for scheduled updates', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/rag_collections/${currentCollection}/schedule`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    frequency: frequency
                })
            });

            const result = await response.json();

            if (result.success) {
                showNotification(result.message, 'success');
                hideScheduleModal();
                loadCollections(); // Refresh to update schedule info
            } else {
                showNotification('Error saving schedule: ' + result.error, 'error');
            }

        } catch (error) {
            console.error('Error saving schedule:', error);
            showNotification('Error saving schedule: ' + error.message, 'error');
        }
    }

    async function removeSchedule() {
        if (!confirm('Are you sure you want to remove the schedule for this collection?')) {
            return;
        }

        try {
            const response = await fetch(`/api/rag_collections/${currentCollection}/schedule`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                showNotification(result.message, 'success');
                hideScheduleModal();
                loadCollections(); // Refresh to update schedule info
            } else {
                showNotification('Error removing schedule: ' + result.error, 'error');
            }

        } catch (error) {
            console.error('Error removing schedule:', error);
            showNotification('Error removing schedule: ' + error.message, 'error');
        }
    }

    // Document Editor Functions
    async function editDocument(docId) {
        try {
            // Get the document content
            const response = await fetch(`/api/rag_collections/${currentCollection}/documents/${docId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch document: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to fetch document');
            }
            
            const document = result.document;
            
            // Populate the modal
            document.getElementById('edit-doc-id').value = document.id;
            document.getElementById('edit-doc-source').value = document.source || document.id;
            document.getElementById('edit-doc-content').value = document.content;
            
            // Show the modal
            document.getElementById('edit-document-modal').style.display = 'block';
            
        } catch (error) {
            console.error('Error fetching document:', error);
            showNotification('Error loading document: ' + error.message, 'error');
        }
    }

    async function saveDocument() {
        const docId = document.getElementById('edit-doc-id').value;
        const source = document.getElementById('edit-doc-source').value;
        const content = document.getElementById('edit-doc-content').value;
        
        if (!content.trim()) {
            showNotification('Content cannot be empty', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/rag_collections/${currentCollection}/documents/${docId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    source: source,
                    content: content
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                hideEditDocumentModal();
                loadDocuments(); // Refresh the documents list
            } else {
                showNotification('Error updating document: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('Error updating document:', error);
            showNotification('Error updating document: ' + error.message, 'error');
        }
    }

    async function deleteDocument(docId) {
        if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/rag_collections/${currentCollection}/documents/${docId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                loadDocuments(); // Refresh the documents list
            } else {
                showNotification('Error deleting document: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('Error deleting document:', error);
            showNotification('Error deleting document: ' + error.message, 'error');
        }
    }

    async function createNewDocument() {
        // Show the create document modal
        document.getElementById('new-doc-id').value = '';
        document.getElementById('new-doc-source').value = '';
        document.getElementById('new-doc-content').value = '';
        document.getElementById('create-document-modal').style.display = 'block';
    }

    async function saveNewDocument() {
        const docId = document.getElementById('new-doc-id').value.trim();
        const source = document.getElementById('new-doc-source').value.trim();
        const content = document.getElementById('new-doc-content').value;
        
        if (!content.trim()) {
            showNotification('Content cannot be empty', 'error');
            return;
        }
        
        try {
            const requestBody = {
                content: content
            };
            
            if (docId) {
                requestBody.id = docId;
            }
            
            if (source) {
                requestBody.source = source;
            }
            
            const response = await fetch(`/api/rag_collections/${currentCollection}/documents`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                hideCreateDocumentModal();
                loadDocuments(); // Refresh the documents list
            } else {
                showNotification('Error creating document: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('Error creating document:', error);
            showNotification('Error creating document: ' + error.message, 'error');
        }
    }

    function hideEditDocumentModal() {
        document.getElementById('edit-document-modal').style.display = 'none';
    }

    function hideCreateDocumentModal() {
        document.getElementById('create-document-modal').style.display = 'none';
    }

    // Initialize DOM element references with validation
    function initializeDOMElements() {
        console.log('[RAG Manager] Initializing DOM elements...');
        
        // Collection elements
        collectionSelector = getElement('collection-selector');
        refreshButton = getElement('refresh-button', false);
        refreshCollectionsBtn = getElement('refresh-collections-btn', false) || getElement('refresh-collections', false);
        createCollectionBtn = getElement('create-collection-btn', false) || getElement('create-collection', false);
        editCollectionBtn = getElement('edit-collection-btn', false) || getElement('edit-collection', false);
        deleteCollectionBtn = getElement('delete-collection-btn', false) || getElement('delete-collection', false);
        
        // File upload elements
        fileInput = getElement('file-input', false);
        uploadFilesBtn = getElement('upload-files-btn', false) || getElement('upload-files', false);
        manageScheduleBtn = getElement('manage-schedule-btn', false) || getElement('manage-schedule', false);
        
        // Form elements
        createCollectionForm = getElement('create-collection-form', false);
        editCollectionForm = getElement('edit-collection-form', false);
        scheduleForm = getElement('schedule-form', false);
        removeScheduleBtn = getElement('remove-schedule-btn', false) || getElement('remove-schedule', false);
        
        // Modal elements
        createCollectionModal = getElement('create-collection-modal', false);
        editCollectionModal = getElement('edit-collection-modal', false);
        editDocumentModal = getElement('edit-document-modal', false);
        createDocumentModal = getElement('create-document-modal', false);
        scheduleModal = getElement('schedule-modal', false);
        
        // Input elements
        newCollectionNameInput = getElement('new-collection-name', false);
        newCollectionDescriptionInput = getElement('new-collection-description', false);
        editCollectionNameInput = getElement('edit-collection-name', false);
        editCollectionDescriptionInput = getElement('edit-collection-description', false);
        
        // Document display elements
        documentsListEl = getElement('documents-list', false);
        loadingEl = getElement('loading', false);
        noDocumentsEl = getElement('no-documents', false);
        scheduleInfo = getElement('schedule-info', false);
        
        // Schedule elements
        scheduleUrlInput = getElement('schedule-url', false);
        scheduleFrequencySelect = getElement('schedule-frequency', false);
        currentScheduleStatus = getElement('current-schedule-status', false);
        
        // URL loading elements
        loadUrlButton = getElement('load-url-button', false);
        urlInput = getElement('url-input', false);
        
        // Validate essential elements
        if (!collectionSelector) {
            showNotification('RAG Manager: Critical DOM elements missing. Some functionality may not work.', 'warning');
            return false;
        }
        
        console.log('[RAG Manager] DOM elements initialized successfully');
        return true;
    }

    // Global functions for HTML onclick handlers and external access
    window.RAGManager = {
        editDocument: editDocument,
        saveDocument: saveDocument,
        deleteDocument: deleteDocument,
        createNewDocument: createNewDocument,
        saveNewDocument: saveNewDocument,
        hideEditDocumentModal: hideEditDocumentModal,
        hideCreateDocumentModal: hideCreateDocumentModal,
        destroy: destroy,
        loadCollections: loadCollections,
        refresh: () => loadDocumentsForCollection(currentCollection)
    };
    
    // Legacy global functions for backward compatibility
    window.editDocument = editDocument;
    window.saveDocument = saveDocument;
    window.deleteDocument = deleteDocument;
    window.createNewDocument = createNewDocument;
    window.saveNewDocument = saveNewDocument;
    window.hideEditDocumentModal = hideEditDocumentModal;
    window.hideCreateDocumentModal = hideCreateDocumentModal;

    // Initialize when DOM is ready
    function initializeWhenReady() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeRAGManager);
        } else {
            // DOM is already loaded
            initializeRAGManager();
        }
    }
    
    // Start initialization
    initializeWhenReady();
})();
