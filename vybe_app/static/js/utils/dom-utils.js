/* global module */
/**
 * DOM Utilities for Vybe AI Desktop Application
 * Provides safer alternatives to innerHTML and better DOM manipulation
 */

class DOMUtils {
    /**
     * Safely set text content of an element
     * @param {Element} element - The target element
     * @param {string} text - The text content to set
     */
    static setTextContent(element, text) {
        if (!element) return;
        element.textContent = text || '';
    }

    /**
     * Safely create an element with text content
     * @param {string} tagName - The HTML tag name
     * @param {string} text - The text content
     * @param {Object} attributes - Optional attributes
     * @returns {Element} The created element
     */
    static createElement(tagName, text = '', attributes = {}) {
        const element = document.createElement(tagName);
        if (text) {
            element.textContent = text;
        }
        
        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'classList') {
                element.classList.add(...value.split(' '));
            } else {
                element.setAttribute(key, value);
            }
        });
        
        return element;
    }

    /**
     * Safely append child elements
     * @param {Element} parent - The parent element
     * @param {Element|Element[]} children - Child element(s) to append
     */
    static appendChildren(parent, children) {
        if (!parent) return;
        
        if (Array.isArray(children)) {
            children.forEach(child => {
                if (child) parent.appendChild(child);
            });
        } else if (children) {
            parent.appendChild(children);
        }
    }

    /**
     * Safely clear element content
     * @param {Element} element - The element to clear
     */
    static clearElement(element) {
        if (!element) return;
        element.innerHTML = '';
    }

    /**
     * Create a loading indicator element
     * @param {string} message - Loading message
     * @returns {Element} Loading element
     */
    static createLoadingIndicator(message = 'Loading...') {
        return this.createElement('div', message, {
            className: 'loading-indicator'
        });
    }

    /**
     * Create an error message element
     * @param {string} message - Error message
     * @returns {Element} Error element
     */
    static createErrorMessage(message = 'An error occurred') {
        return this.createElement('div', message, {
            className: 'error-message text-danger'
        });
    }

    /**
     * Create a success message element
     * @param {string} message - Success message
     * @returns {Element} Success element
     */
    static createSuccessMessage(message = 'Operation completed successfully') {
        return this.createElement('div', message, {
            className: 'success-message text-success'
        });
    }

    /**
     * Create a button element
     * @param {string} text - Button text
     * @param {Object} options - Button options
     * @returns {Element} Button element
     */
    static createButton(text, options = {}) {
        const {
            className = 'btn btn-primary',
            type = 'button',
            disabled = false,
            onClick = null
        } = options;

        const button = this.createElement('button', text, {
            type,
            className,
            disabled: disabled ? 'disabled' : null
        });

        if (onClick && typeof onClick === 'function') {
            window.eventManager.add(button, 'click', onClick);
        }

        return button;
    }

    /**
     * Create a card element
     * @param {string} title - Card title
     * @param {string} content - Card content
     * @param {Object} options - Card options
     * @returns {Element} Card element
     */
    static createCard(title, content, options = {}) {
        const {
            className = 'card',
            headerClass = 'card-header',
            bodyClass = 'card-body'
        } = options;

        const card = this.createElement('div', '', { className });
        
        if (title) {
            const header = this.createElement('div', title, { className: headerClass });
            card.appendChild(header);
        }
        
        if (content) {
            const body = this.createElement('div', content, { className: bodyClass });
            card.appendChild(body);
        }
        
        return card;
    }

    /**
     * Create a list item element
     * @param {string} text - List item text
     * @param {Object} options - List item options
     * @returns {Element} List item element
     */
    static createListItem(text, options = {}) {
        const {
            className = 'list-group-item',
            badge = null,
            action = false
        } = options;

        const item = this.createElement('li', text, { className });
        
        if (action) {
            item.classList.add('list-group-item-action');
        }
        
        if (badge) {
            const badgeElement = this.createElement('span', badge, {
                className: 'badge bg-primary float-end'
            });
            item.appendChild(badgeElement);
        }
        
        return item;
    }

    /**
     * Create a table row element
     * @param {string[]} cells - Array of cell contents
     * @param {Object} options - Row options
     * @returns {Element} Table row element
     */
    static createTableRow(cells, options = {}) {
        const {
            className = '',
            header = false
        } = options;

        const row = this.createElement('tr', '', { className });
        
        cells.forEach(cellText => {
            const cell = this.createElement(header ? 'th' : 'td', cellText);
            row.appendChild(cell);
        });
        
        return row;
    }

    /**
     * Safely update element content with fallback
     * @param {Element} element - Target element
     * @param {Function} contentGenerator - Function that returns content
     * @param {string} fallbackMessage - Fallback message if generation fails
     */
    static safeUpdate(element, contentGenerator, fallbackMessage = 'Content unavailable') {
        if (!element) return;
        
        try {
            const content = contentGenerator();
            if (content instanceof Element) {
                this.clearElement(element);
                element.appendChild(content);
            } else if (typeof content === 'string') {
                element.textContent = content;
            }
        } catch (error) {
            console.error('Error updating element content:', error);
            element.textContent = fallbackMessage;
        }
    }

    /**
     * Create a modal element
     * @param {string} title - Modal title
     * @param {string|Element} content - Modal content
     * @param {Object} options - Modal options
     * @returns {Element} Modal element
     */
    static createModal(title, content, options = {}) {
        const {
            id = 'dynamic-modal',
            size = 'modal-lg',
            showCloseButton = true
        } = options;

        const modal = this.createElement('div', '', {
            className: 'modal fade',
            id
        });

        const modalDialog = this.createElement('div', '', {
            className: `modal-dialog ${size}`
        });

        const modalContent = this.createElement('div', '', {
            className: 'modal-content'
        });

        // Modal header
        const modalHeader = this.createElement('div', '', {
            className: 'modal-header'
        });

        const modalTitle = this.createElement('h5', title, {
            className: 'modal-title'
        });

        modalHeader.appendChild(modalTitle);

        if (showCloseButton) {
            const closeButton = this.createElement('button', '×', {
                type: 'button',
                className: 'btn-close',
                'data-bs-dismiss': 'modal',
                'aria-label': 'Close'
            });
            modalHeader.appendChild(closeButton);
        }

        // Modal body
        const modalBody = this.createElement('div', '', {
            className: 'modal-body'
        });

        if (typeof content === 'string') {
            modalBody.textContent = content;
        } else if (content instanceof Element) {
            modalBody.appendChild(content);
        }

        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modal.appendChild(modalDialog);

        return modal;
    }

    /**
     * Create a toast notification element
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, warning, info)
     * @param {Object} options - Toast options
     * @returns {Element} Toast element
     */
    static createToast(message, type = 'info', options = {}) {
        const {
            title = ''
        } = options;

        const toast = this.createElement('div', '', {
            className: `toast align-items-center text-white bg-${type} border-0`,
            role: 'alert',
            'aria-live': 'assertive',
            'aria-atomic': 'true'
        });

        const toastHeader = this.createElement('div', '', {
            className: 'toast-header'
        });

        if (title) {
            const titleElement = this.createElement('strong', title, {
                className: 'me-auto'
            });
            toastHeader.appendChild(titleElement);
        }

        const closeButton = this.createElement('button', '×', {
            type: 'button',
            className: 'btn-close btn-close-white me-2 m-auto',
            'data-bs-dismiss': 'toast',
            'aria-label': 'Close'
        });
        toastHeader.appendChild(closeButton);

        const toastBody = this.createElement('div', message, {
            className: 'toast-body'
        });

        toast.appendChild(toastHeader);
        toast.appendChild(toastBody);

        return toast;
    }

    /**
     * Debounce function for performance optimization
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    static debounce(func, wait) {
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

    /**
     * Throttle function for performance optimization
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in milliseconds
     * @returns {Function} Throttled function
     */
    static throttle(func, limit) {
        let inThrottle;
        return (...args) => {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DOMUtils;
} else if (typeof window !== 'undefined') {
    window.DOMUtils = DOMUtils;
}
