/**
 * Search Worker - Optimized client-side search algorithms
 * Runs search computations in background to prevent UI blocking
 */

class SearchWorker {
    constructor() {
        this.documents = new Map();
        this.searchCache = new Map();
        this.maxCacheSize = 100;
    }

    // Receive messages from main thread
    onmessage(event) {
        const { type, data, id } = event.data;
        
        try {
            switch (type) {
                case 'INIT_DOCUMENTS':
                    this.initializeDocuments(data);
                    this.postMessage({ type: 'INIT_COMPLETE', id });
                    break;
                    
                case 'SEARCH':
                    this.performSearch(data, id);
                    break;
                    
                case 'UPDATE_DOCUMENTS':
                    this.updateDocuments(data);
                    this.postMessage({ type: 'UPDATE_COMPLETE', id });
                    break;
                    
                case 'CLEAR_CACHE':
                    this.clearCache();
                    this.postMessage({ type: 'CACHE_CLEARED', id });
                    break;
                    
                default:
                    this.postMessage({ 
                        type: 'ERROR', 
                        error: `Unknown message type: ${type}`,
                        id 
                    });
            }
        } catch (error) {
            this.postMessage({ 
                type: 'ERROR', 
                error: error.message,
                id 
            });
        }
    }

    initializeDocuments(documents) {
        this.documents.clear();
        documents.forEach(doc => {
            this.documents.set(doc.id, this.preprocessDocument(doc));
        });
    }

    updateDocuments(documents) {
        documents.forEach(doc => {
            this.documents.set(doc.id, this.preprocessDocument(doc));
        });
        // Clear cache when documents are updated
        this.searchCache.clear();
    }

    preprocessDocument(doc) {
        // Preprocess document for faster searching
        const processed = {
            ...doc,
            contentLower: (doc.content || '').toLowerCase(),
            titleLower: (doc.title || '').toLowerCase(),
            keywords: this.extractKeywords(doc.content || ''),
            wordCount: (doc.content || '').split(/\s+/).length,
            lastIndexed: Date.now()
        };

        // Create searchable text combining title, content, and metadata
        processed.searchableText = [
            processed.title || '',
            processed.content || '',
            processed.description || '',
            processed.tags ? processed.tags.join(' ') : '',
            processed.category || ''
        ].join(' ').toLowerCase();

        return processed;
    }

    extractKeywords(text) {
        if (!text) return [];
        
        const words = text.toLowerCase()
            .replace(/[^\w\s]/g, ' ')
            .split(/\s+/)
            .filter(word => 
                word.length > 3 && 
                !this.isStopWord(word)
            );
        
        // Count word frequency
        const frequency = {};
        words.forEach(word => {
            frequency[word] = (frequency[word] || 0) + 1;
        });
        
        // Return top keywords sorted by frequency
        return Object.entries(frequency)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 20)
            .map(([word]) => word);
    }

    isStopWord(word) {
        const stopWords = new Set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their'
        ]);
        return stopWords.has(word);
    }

    async performSearch(searchData, requestId) {
        const { query, options = {} } = searchData;
        const {
            maxResults = 20,
            threshold = 0.1,
            searchFields = ['title', 'content', 'tags'],
            sortBy = 'relevance'
        } = options;

        // Check cache first
        const cacheKey = JSON.stringify({ query, options });
        if (this.searchCache.has(cacheKey)) {
            this.postMessage({
                type: 'SEARCH_RESULTS',
                results: this.searchCache.get(cacheKey),
                cached: true,
                id: requestId
            });
            return;
        }

        try {
            const startTime = performance.now();
            
            // Preprocess query
            const queryTerms = this.preprocessQuery(query);
            const results = [];

            // Search through documents
            for (const [docId, doc] of this.documents) {
                const score = this.calculateRelevanceScore(doc, queryTerms, searchFields);
                
                if (score >= threshold) {
                    results.push({
                        id: docId,
                        title: doc.title,
                        content: doc.content,
                        score: score,
                        type: doc.type || 'document',
                        source: doc.source || 'unknown',
                        document_type: doc.document_type,
                        file_size: doc.file_size,
                        chunk_count: doc.chunk_count,
                        upload_date: doc.upload_date,
                        search_query: query,
                        highlights: this.getHighlights(doc, queryTerms)
                    });
                }
            }

            // Sort results
            this.sortResults(results, sortBy);
            
            // Limit results
            const limitedResults = results.slice(0, maxResults);
            
            // Cache results
            this.cacheResults(cacheKey, limitedResults);
            
            const endTime = performance.now();
            
            this.postMessage({
                type: 'SEARCH_RESULTS',
                results: limitedResults,
                cached: false,
                searchTime: endTime - startTime,
                totalMatches: results.length,
                id: requestId
            });

        } catch (error) {
            this.postMessage({
                type: 'SEARCH_ERROR',
                error: error.message,
                id: requestId
            });
        }
    }

    preprocessQuery(query) {
        return query.toLowerCase()
            .replace(/[^\w\s]/g, ' ')
            .split(/\s+/)
            .filter(term => term.length > 2 && !this.isStopWord(term));
    }

    calculateRelevanceScore(doc, queryTerms, searchFields) {
        let totalScore = 0;
        let totalWeight = 0;

        // Field weights
        const fieldWeights = {
            title: 3.0,
            content: 1.0,
            tags: 2.0,
            keywords: 1.5,
            category: 1.2
        };

        searchFields.forEach(field => {
            const weight = fieldWeights[field] || 1.0;
            let fieldScore = 0;

            switch (field) {
                case 'title':
                    fieldScore = this.calculateFieldScore(doc.titleLower, queryTerms);
                    break;
                case 'content':
                    fieldScore = this.calculateFieldScore(doc.contentLower, queryTerms);
                    break;
                case 'tags': {
                    const tagsText = (doc.tags || []).join(' ').toLowerCase();
                    fieldScore = this.calculateFieldScore(tagsText, queryTerms);
                    break;
                }
                case 'keywords': {
                    const keywordsText = (doc.keywords || []).join(' ');
                    fieldScore = this.calculateFieldScore(keywordsText, queryTerms);
                    break;
                }
                case 'category':
                    fieldScore = this.calculateFieldScore(doc.category || '', queryTerms);
                    break;
            }

            totalScore += fieldScore * weight;
            totalWeight += weight;
        });

        // Normalize score
        const normalizedScore = totalWeight > 0 ? totalScore / totalWeight : 0;
        
        // Apply document quality modifiers
        return this.applyQualityModifiers(normalizedScore, doc, queryTerms);
    }

    calculateFieldScore(fieldText, queryTerms) {
        if (!fieldText || queryTerms.length === 0) return 0;

        let score = 0;
        const fieldWords = fieldText.split(/\s+/);
        
        queryTerms.forEach(term => {
            // Exact matches get higher score
            const exactMatches = (fieldText.match(new RegExp(`\\b${term}\\b`, 'g')) || []).length;
            score += exactMatches * 2;
            
            // Partial matches get lower score
            const partialMatches = (fieldText.match(new RegExp(term, 'g')) || []).length - exactMatches;
            score += partialMatches * 0.5;
            
            // Proximity bonus: terms appearing close together
            if (queryTerms.length > 1) {
                score += this.calculateProximityBonus(fieldText, queryTerms) * 0.3;
            }
        });

        // Normalize by field length
        return Math.min(score / Math.max(fieldWords.length, 1), 1.0);
    }

    calculateProximityBonus(text, terms) {
        if (terms.length < 2) return 0;
        
        let bonus = 0;
        const words = text.split(/\s+/);
        
        for (let i = 0; i < words.length - 1; i++) {
            for (let j = i + 1; j < Math.min(i + 10, words.length); j++) {
                const word1 = words[i];
                const word2 = words[j];
                
                if (terms.includes(word1) && terms.includes(word2)) {
                    const distance = j - i;
                    bonus += 1 / distance; // Closer terms get higher bonus
                }
            }
        }
        
        return bonus;
    }

    applyQualityModifiers(score, doc, queryTerms) {
        let modifiedScore = score;
        
        // Boost recent documents slightly
        if (doc.upload_date) {
            const daysSinceUpload = (Date.now() - new Date(doc.upload_date).getTime()) / (1000 * 60 * 60 * 24);
            if (daysSinceUpload < 30) {
                modifiedScore *= 1.1; // 10% boost for documents uploaded in last 30 days
            }
        }
        
        // Boost documents with good keyword match
        if (doc.keywords && doc.keywords.length > 0) {
            const keywordMatches = queryTerms.filter(term => 
                doc.keywords.some(keyword => keyword.includes(term))
            ).length;
            const keywordBoost = keywordMatches / queryTerms.length * 0.2;
            modifiedScore *= (1 + keywordBoost);
        }
        
        // Penalize very short documents
        if (doc.wordCount < 50) {
            modifiedScore *= 0.8;
        }
        
        return Math.min(modifiedScore, 1.0);
    }

    getHighlights(doc, queryTerms) {
        const highlights = [];
        const content = doc.content || '';
        
        queryTerms.forEach(term => {
            const regex = new RegExp(`(.{0,50})(${term})(.{0,50})`, 'gi');
            const matches = [...content.matchAll(regex)];
            
            matches.slice(0, 3).forEach(match => { // Limit to 3 highlights per term
                highlights.push({
                    term: term,
                    context: match[1] + `<mark>${match[2]}</mark>` + match[3],
                    position: match.index
                });
            });
        });
        
        return highlights.slice(0, 10); // Maximum 10 highlights total
    }

    sortResults(results, sortBy) {
        switch (sortBy) {
            case 'relevance':
                results.sort((a, b) => b.score - a.score);
                break;
            case 'date':
                results.sort((a, b) => {
                    const dateA = new Date(a.upload_date || 0);
                    const dateB = new Date(b.upload_date || 0);
                    return dateB - dateA;
                });
                break;
            case 'title':
                results.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
                break;
            case 'size':
                results.sort((a, b) => (b.file_size || 0) - (a.file_size || 0));
                break;
            default:
                results.sort((a, b) => b.score - a.score);
        }
    }

    cacheResults(key, results) {
        // Implement LRU cache
        if (this.searchCache.size >= this.maxCacheSize) {
            const firstKey = this.searchCache.keys().next().value;
            this.searchCache.delete(firstKey);
        }
        
        this.searchCache.set(key, results);
    }

    clearCache() {
        this.searchCache.clear();
    }

    postMessage(data) {
        if (typeof self !== 'undefined' && self.postMessage) {
            self.postMessage(data);
        }
    }
}

// Initialize worker
const searchWorker = new SearchWorker();

// Set up message handler
if (typeof self !== 'undefined') {
    self.onmessage = (event) => {
        searchWorker.onmessage(event);
    };
}

// Export for testing
/* global module */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchWorker;
}
