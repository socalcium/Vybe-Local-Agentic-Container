"""
Marketplace API for Vybe
Provides endpoints for browsing and managing marketplace plugins
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.marketplace_manager import marketplace_manager, PluginCategory, PluginSource
from ..logger import log_info, log_error, log_warning

# Create blueprint
marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/api/marketplace')


@marketplace_bp.route('/status', methods=['GET'])
@login_required
def get_marketplace_status():
    """Get marketplace status and statistics"""
    try:
        stats = marketplace_manager.get_marketplace_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        log_error(f"Error getting marketplace status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get marketplace status'
        }), 500


@marketplace_bp.route('/refresh', methods=['POST'])
@login_required
def refresh_marketplace():
    """Refresh marketplace data from external sources"""
    try:
        force = request.json.get('force', False) if request.json else False
        success = marketplace_manager.refresh_marketplace(force=force)
        
        if success:
            log_info(f"Marketplace refreshed by user {current_user.username}")
            return jsonify({
                'success': True,
                'message': 'Marketplace refreshed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to refresh marketplace'
            }), 500
            
    except Exception as e:
        log_error(f"Error refreshing marketplace: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to refresh marketplace'
        }), 500


@marketplace_bp.route('/plugins', methods=['GET'])
@login_required
def get_plugins():
    """Get plugins with optional filtering"""
    try:
        # Get query parameters
        category = request.args.get('category')
        search = request.args.get('search')
        featured = request.args.get('featured', 'false').lower() == 'true'
        verified = request.args.get('verified', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get plugins
        plugins = marketplace_manager.get_plugins(
            category=category,
            search=search,
            featured=featured,
            verified=verified
        )
        
        # Apply pagination
        total_count = len(plugins)
        plugins = plugins[offset:offset + limit]
        
        # Convert to dict format
        plugins_data = []
        for plugin in plugins:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': plugin.verified,
                'featured': plugin.featured,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': plugin.id in marketplace_manager.installed_plugins,
                'is_favorite': plugin.id in marketplace_manager.favorite_plugins
            }
            plugins_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'plugins': plugins_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        log_error(f"Error getting plugins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get plugins'
        }), 500


@marketplace_bp.route('/plugins/<plugin_id>', methods=['GET'])
@login_required
def get_plugin(plugin_id: str):
    """Get specific plugin details"""
    try:
        plugin = marketplace_manager.get_plugin(plugin_id)
        if not plugin:
            return jsonify({
                'success': False,
                'error': 'Plugin not found'
            }), 404
        
        plugin_dict = {
            'id': plugin.id,
            'name': plugin.name,
            'version': plugin.version,
            'description': plugin.description,
            'author': plugin.author,
            'category': plugin.category.value,
            'source': plugin.source.value,
            'download_url': plugin.download_url,
            'repository_url': plugin.repository_url,
            'documentation_url': plugin.documentation_url,
            'website_url': plugin.website_url,
            'license': plugin.license,
            'tags': plugin.tags,
            'icon': plugin.icon,
            'screenshots': plugin.screenshots,
            'min_vybe_version': plugin.min_vybe_version,
            'max_vybe_version': plugin.max_vybe_version,
            'dependencies': plugin.dependencies,
            'requirements': plugin.requirements,
            'permissions': plugin.permissions,
            'rating': plugin.rating,
            'download_count': plugin.download_count,
            'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
            'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
            'verified': plugin.verified,
            'featured': plugin.featured,
            'price': plugin.price,
            'currency': plugin.currency,
            'file_size': plugin.file_size,
            'checksum': plugin.checksum,
            'is_installed': plugin.id in marketplace_manager.installed_plugins,
            'is_favorite': plugin.id in marketplace_manager.favorite_plugins
        }
        
        return jsonify({
            'success': True,
            'data': plugin_dict
        })
        
    except Exception as e:
        log_error(f"Error getting plugin {plugin_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get plugin details'
        }), 500


@marketplace_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all marketplace categories"""
    try:
        categories = marketplace_manager.get_categories()
        categories_data = []
        
        for category in categories:
            category_dict = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'plugin_count': category.plugin_count,
                'featured_plugins': category.featured_plugins
            }
            categories_data.append(category_dict)
        
        return jsonify({
            'success': True,
            'data': categories_data
        })
        
    except Exception as e:
        log_error(f"Error getting categories: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get categories'
        }), 500


@marketplace_bp.route('/categories/<category_id>', methods=['GET'])
@login_required
def get_category(category_id: str):
    """Get specific category details"""
    try:
        category = marketplace_manager.get_category(category_id)
        if not category:
            return jsonify({
                'success': False,
                'error': 'Category not found'
            }), 404
        
        category_dict = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'icon': category.icon,
            'plugin_count': category.plugin_count,
            'featured_plugins': category.featured_plugins
        }
        
        return jsonify({
            'success': True,
            'data': category_dict
        })
        
    except Exception as e:
        log_error(f"Error getting category {category_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get category details'
        }), 500


@marketplace_bp.route('/plugins/<plugin_id>/install', methods=['POST'])
@login_required
def install_plugin(plugin_id: str):
    """Install a plugin from marketplace"""
    try:
        success = marketplace_manager.install_plugin(plugin_id)
        
        if success:
            log_info(f"Plugin {plugin_id} installed by user {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} installed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to install plugin {plugin_id}'
            }), 500
            
    except Exception as e:
        log_error(f"Error installing plugin {plugin_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to install plugin {plugin_id}'
        }), 500


@marketplace_bp.route('/plugins/<plugin_id>/uninstall', methods=['POST'])
@login_required
def uninstall_plugin(plugin_id: str):
    """Uninstall a marketplace plugin"""
    try:
        success = marketplace_manager.uninstall_plugin(plugin_id)
        
        if success:
            log_info(f"Plugin {plugin_id} uninstalled by user {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} uninstalled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to uninstall plugin {plugin_id}'
            }), 500
            
    except Exception as e:
        log_error(f"Error uninstalling plugin {plugin_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to uninstall plugin {plugin_id}'
        }), 500


@marketplace_bp.route('/plugins/<plugin_id>/favorite', methods=['POST'])
@login_required
def add_to_favorites(plugin_id: str):
    """Add plugin to favorites"""
    try:
        success = marketplace_manager.add_to_favorites(plugin_id)
        
        if success:
            log_info(f"Plugin {plugin_id} added to favorites by user {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} added to favorites'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to add plugin {plugin_id} to favorites'
            }), 500
            
    except Exception as e:
        log_error(f"Error adding plugin {plugin_id} to favorites: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to add plugin {plugin_id} to favorites'
        }), 500


@marketplace_bp.route('/plugins/<plugin_id>/favorite', methods=['DELETE'])
@login_required
def remove_from_favorites(plugin_id: str):
    """Remove plugin from favorites"""
    try:
        success = marketplace_manager.remove_from_favorites(plugin_id)
        
        if success:
            log_info(f"Plugin {plugin_id} removed from favorites by user {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} removed from favorites'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to remove plugin {plugin_id} from favorites'
            }), 500
            
    except Exception as e:
        log_error(f"Error removing plugin {plugin_id} from favorites: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to remove plugin {plugin_id} from favorites'
        }), 500


@marketplace_bp.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    """Get user's favorite plugins"""
    try:
        favorites = marketplace_manager.get_favorites()
        favorites_data = []
        
        for plugin in favorites:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': plugin.verified,
                'featured': plugin.featured,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': plugin.id in marketplace_manager.installed_plugins,
                'is_favorite': True
            }
            favorites_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': favorites_data
        })
        
    except Exception as e:
        log_error(f"Error getting favorites: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get favorites'
        }), 500


@marketplace_bp.route('/installed', methods=['GET'])
@login_required
def get_installed_plugins():
    """Get user's installed marketplace plugins"""
    try:
        installed = marketplace_manager.get_installed_plugins()
        installed_data = []
        
        for plugin in installed:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': plugin.verified,
                'featured': plugin.featured,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': True,
                'is_favorite': plugin.id in marketplace_manager.favorite_plugins
            }
            installed_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': installed_data
        })
        
    except Exception as e:
        log_error(f"Error getting installed plugins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get installed plugins'
        }), 500


@marketplace_bp.route('/search', methods=['GET'])
@login_required
def search_plugins():
    """Search plugins with advanced filtering"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        plugins = marketplace_manager.search_plugins(query, category)
        
        # Apply pagination
        total_count = len(plugins)
        plugins = plugins[offset:offset + limit]
        
        # Convert to dict format
        plugins_data = []
        for plugin in plugins:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': plugin.verified,
                'featured': plugin.featured,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': plugin.id in marketplace_manager.installed_plugins,
                'is_favorite': plugin.id in marketplace_manager.favorite_plugins
            }
            plugins_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'plugins': plugins_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'query': query,
                'category': category
            }
        })
        
    except Exception as e:
        log_error(f"Error searching plugins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search plugins'
        }), 500


@marketplace_bp.route('/featured', methods=['GET'])
@login_required
def get_featured_plugins():
    """Get featured plugins"""
    try:
        featured = marketplace_manager.get_featured_plugins()
        featured_data = []
        
        for plugin in featured:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': plugin.verified,
                'featured': True,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': plugin.id in marketplace_manager.installed_plugins,
                'is_favorite': plugin.id in marketplace_manager.favorite_plugins
            }
            featured_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': featured_data
        })
        
    except Exception as e:
        log_error(f"Error getting featured plugins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get featured plugins'
        }), 500


@marketplace_bp.route('/verified', methods=['GET'])
@login_required
def get_verified_plugins():
    """Get verified plugins"""
    try:
        verified = marketplace_manager.get_verified_plugins()
        verified_data = []
        
        for plugin in verified:
            plugin_dict = {
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'category': plugin.category.value,
                'source': plugin.source.value,
                'download_url': plugin.download_url,
                'repository_url': plugin.repository_url,
                'documentation_url': plugin.documentation_url,
                'website_url': plugin.website_url,
                'license': plugin.license,
                'tags': plugin.tags,
                'icon': plugin.icon,
                'screenshots': plugin.screenshots,
                'min_vybe_version': plugin.min_vybe_version,
                'max_vybe_version': plugin.max_vybe_version,
                'dependencies': plugin.dependencies,
                'requirements': plugin.requirements,
                'permissions': plugin.permissions,
                'rating': plugin.rating,
                'download_count': plugin.download_count,
                'last_updated': plugin.last_updated.isoformat() if plugin.last_updated else None,
                'created_at': plugin.created_at.isoformat() if plugin.created_at else None,
                'verified': True,
                'featured': plugin.featured,
                'price': plugin.price,
                'currency': plugin.currency,
                'file_size': plugin.file_size,
                'checksum': plugin.checksum,
                'is_installed': plugin.id in marketplace_manager.installed_plugins,
                'is_favorite': plugin.id in marketplace_manager.favorite_plugins
            }
            verified_data.append(plugin_dict)
        
        return jsonify({
            'success': True,
            'data': verified_data
        })
        
    except Exception as e:
        log_error(f"Error getting verified plugins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get verified plugins'
        }), 500
