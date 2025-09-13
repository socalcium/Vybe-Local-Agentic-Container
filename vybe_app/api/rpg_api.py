#!/usr/bin/env python3
"""
RPG API endpoints for Vybe AI Assistant
Handles campaign management, game actions, and multiplayer functionality
"""

import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit, join_room, leave_room

from ..logger import logger
from ..core.rpg_engine import rpg_engine

# Create Blueprint
rpg_bp = Blueprint('rpg', __name__)

# In-memory storage for multiplayer sessions (in production, use Redis or database)
rpg_sessions = {}

def safe_get_campaign_attribute(campaign, attr_name, default_value="Unknown"):
    """Safely get campaign attribute with fallback values"""
    if not campaign:
        return default_value
    return getattr(campaign, attr_name, default_value)

def load_campaign(campaign_id):
    """Load campaign data from storage"""
    try:
        # This would load from database in production
        # For now, return a basic campaign structure
        return {
            'id': campaign_id,
            'campaign_name': 'Multiplayer Campaign',
            'character_name': 'Adventurer',
            'world_description': 'A mysterious world of adventure',
            'current_scene': 'The adventure begins...',
            'inventory': [],
            'quests': [],
            'characters': []
        }
    except Exception as e:
        logger.error(f"Error loading campaign: {e}")
        return None

def save_campaign(campaign_data):
    """Save campaign data to storage"""
    try:
        # This would save to database in production
        logger.info(f"Campaign saved: {campaign_data.get('campaign_name', 'Unknown')}")
        return True
    except Exception as e:
        logger.error(f"Error saving campaign: {e}")
        return False

@rpg_bp.route('/api/rpg/campaign/new', methods=['POST'])
def create_new_campaign():
    """Create a new RPG campaign with advanced world generation"""
    try:
        data = request.get_json()
        
        # Use enhanced world generation if not provided
        world_description = data.get('world_description')
        if not world_description:
            genre = data.get('genre', 'fantasy')
            world_description = rpg_engine.generate_world_description(
                data.get('name', 'New Campaign'), 
                genre
            )
        
        # Generate character backstory if not provided
        character_backstory = data.get('character_backstory')
        if not character_backstory:
            character_name = data.get('character_name', 'Adventurer')
            character_class = data.get('character_class', 'adventurer')
            character_backstory = rpg_engine.generate_character_backstory(
                character_name, 
                character_class
            )
        
        campaign_data = {
            'id': str(uuid.uuid4()),
            'campaign_name': data.get('name', 'New Campaign'),
            'world_description': world_description,
            'character_name': data.get('character_name', 'Adventurer'),
            'character_backstory': character_backstory,
            'character_class': data.get('character_class', 'adventurer'),
            'genre': data.get('genre', 'fantasy'),
            'current_scene': 'The adventure begins...',
            'inventory': [],
            'quests': [],
            'characters': [],
            'created_at': datetime.now().isoformat()
        }
        
        # Save campaign
        if save_campaign(campaign_data):
            return jsonify({
                'success': True,
                'campaign': campaign_data
            })
        else:
            return jsonify({'error': 'Failed to save campaign'}), 500
            
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        return jsonify({'error': 'Failed to create campaign'}), 500

@rpg_bp.route('/api/rpg/campaign/current', methods=['GET'])
def get_current_campaign():
    """Get the current campaign"""
    try:
        # This would load from database in production
        # For now, return a sample campaign
        campaign = {
            'id': 'sample-campaign',
            'campaign_name': 'Sample Campaign',
            'character_name': 'Adventurer',
            'world_description': 'A mysterious world of adventure',
            'current_scene': 'The adventure begins...',
            'inventory': [],
            'quests': [],
            'characters': []
        }
        
        return jsonify({
            'success': True,
            'campaign': campaign
        })
        
    except Exception as e:
        logger.error(f"Error getting current campaign: {e}")
        return jsonify({'error': 'Failed to get campaign'}), 500

@rpg_bp.route('/api/rpg/action', methods=['POST'])
def process_player_action():
    """Process a player action and get DM response"""
    try:
        data = request.get_json()
        action = data.get('action')
        campaign_id = data.get('campaign_id')
        
        if not action:
            return jsonify({'error': 'Action is required'}), 400
        
        # Load campaign if needed
        if not rpg_engine.current_campaign:
            rpg_engine.load_campaign(campaign_id)
        
        # Null check for current_campaign
        if not rpg_engine.current_campaign:
            return jsonify({
                'error': 'No active campaign found.'
            }), 404

        # Generate DM response using the RPG engine
        dm_prompt = rpg_engine.generate_dm_prompt(action)
        
        # For now, return a placeholder response
        # In a full implementation, this would call the LLM
        response_text = f"The DM considers your action: {action}. The adventure continues..."
        
        # Update game state
        campaign_summary = rpg_engine.get_campaign_summary()
        game_state = {
            'current_scene': campaign_summary.get('current_scene', 'Unknown scene'),
            'inventory': campaign_summary.get('inventory', []),
            'quests': campaign_summary.get('quest_log', []),
            'characters': campaign_summary.get('characters', [])
        }
        
        return jsonify({
            'success': True,
            'response': response_text,
            'game_state': game_state
        })
        
    except Exception as e:
        logger.error(f"Error processing player action: {e}")
        return jsonify({'error': 'Failed to process action'}), 500

@rpg_bp.route('/api/rpg/dice/roll', methods=['POST'])
def roll_dice():
    """Roll dice for RPG actions"""
    try:
        data = request.get_json()
        dice_notation = data.get('dice', '1d20')
        
        # Parse dice notation (e.g., "2d6+3")
        result = rpg_engine.roll_dice(dice_notation)
        
        return jsonify({
            'success': True,
            'dice': dice_notation,
            'result': result['total'],
            'rolls': result['rolls'],
            'modifier': result.get('modifier', 0)
        })
        
    except Exception as e:
        logger.error(f"Error rolling dice: {e}")
        return jsonify({'error': 'Failed to roll dice'}), 500

@rpg_bp.route('/api/rpg/world/generate', methods=['POST'])
def generate_world():
    """Generate a rich world description"""
    try:
        data = request.get_json()
        campaign_name = data.get('campaign_name', 'New Campaign')
        genre = data.get('genre', 'fantasy')
        
        world_description = rpg_engine.generate_world_description(campaign_name, genre)
        
        return jsonify({
            'success': True,
            'world_description': world_description,
            'genre': genre
        })
        
    except Exception as e:
        logger.error(f"Error generating world: {e}")
        return jsonify({'error': 'Failed to generate world'}), 500

@rpg_bp.route('/api/rpg/character/backstory', methods=['POST'])
def generate_character_backstory():
    """Generate a character backstory"""
    try:
        data = request.get_json()
        character_name = data.get('character_name', 'Adventurer')
        character_class = data.get('character_class', 'adventurer')
        
        backstory = rpg_engine.generate_character_backstory(character_name, character_class)
        
        return jsonify({
            'success': True,
            'backstory': backstory,
            'character_name': character_name,
            'character_class': character_class
        })
        
    except Exception as e:
        logger.error(f"Error generating character backstory: {e}")
        return jsonify({'error': 'Failed to generate character backstory'}), 500

@rpg_bp.route('/api/rpg/npc/create', methods=['POST'])
def create_npc():
    """Create a dynamic NPC"""
    try:
        data = request.get_json()
        name = data.get('name', 'NPC')
        role = data.get('role', 'merchant')
        
        npc = rpg_engine.create_dynamic_npc(name, role)
        
        return jsonify({
            'success': True,
            'npc': {
                'name': npc.name,
                'level': npc.level,
                'health': npc.health,
                'max_health': npc.max_health,
                'personality_traits': getattr(npc, 'personality_traits', 'Unknown'),
                'role': getattr(npc, 'role', 'unknown')
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating NPC: {e}")
        return jsonify({'error': 'Failed to create NPC'}), 500

@rpg_bp.route('/api/rpg/story/analyze', methods=['POST'])
def analyze_story():
    """Analyze the current story state and provide suggestions"""
    try:
        data = request.get_json()
        current_action = data.get('action', '')
        campaign_id = data.get('campaign_id')
        
        if not rpg_engine.current_campaign:
            rpg_engine.load_campaign(campaign_id)
        
        # Additional safety check after attempting to load campaign
        if not rpg_engine.current_campaign:
            return jsonify({
                'error': 'No active campaign found. Please create or load a campaign first.'
            }), 404
        
        # Store campaign reference safely to prevent null pointer issues
        campaign = rpg_engine.current_campaign
        if not campaign:
            return jsonify({
                'error': 'Campaign became unavailable during processing.'
            }), 500
        
        # Generate story analysis prompt
        analysis_prompt = f"""As an expert storyteller and game master, analyze this RPG action and provide suggestions:

ACTION: {current_action}

CAMPAIGN CONTEXT:
- Name: {getattr(campaign, 'campaign_name', 'Unknown')}
- World: {getattr(campaign, 'world_description', 'Unknown world')}
- Current Scene: {getattr(campaign, 'current_scene', 'Unknown scene')}
- Turn Count: {getattr(campaign, 'turn_count', 0)}

Provide:
1. **Narrative Opportunities**: What story elements could emerge from this action?
2. **Character Development**: How could this action reveal character growth or conflict?
3. **World Building**: What aspects of the world could be revealed or affected?
4. **Pacing Suggestions**: How should the story flow from this point?
5. **Challenge Ideas**: What obstacles or complications could arise?

Keep suggestions creative, engaging, and focused on enhancing the player experience."""

        # For now, return the analysis prompt (in a full implementation, this would call the LLM)
        return jsonify({
            'success': True,
            'analysis_prompt': analysis_prompt,
            'suggestions': {
                'narrative_opportunities': ['Character reveals', 'World secrets', 'Plot twists'],
                'character_development': ['Personal growth', 'Relationship dynamics', 'Moral choices'],
                'world_building': ['Cultural details', 'Historical context', 'Geographic features'],
                'pacing': ['Build tension', 'Provide relief', 'Create momentum'],
                'challenges': ['Environmental obstacles', 'Social complications', 'Moral dilemmas']
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing story: {e}")
        return jsonify({'error': 'Failed to analyze story'}), 500

# Multiplayer RPG endpoints
@rpg_bp.route('/api/rpg/multiplayer/create', methods=['POST'])
def create_multiplayer_session():
    """Create a new multiplayer RPG session"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        player_name = data.get('player_name', 'Player')
        
        if not campaign_id:
            return jsonify({'error': 'Campaign ID is required'}), 400
        
        # Generate session ID
        session_id = str(uuid.uuid4())[:8].upper()
        player_id = str(uuid.uuid4())
        
        # Create session
        rpg_sessions[session_id] = {
            'campaign_id': campaign_id,
            'players': [{
                'id': player_id,
                'name': player_name,
                'is_dm': True,  # First player is DM
                'joined_at': datetime.now().isoformat()
            }],
            'created_at': datetime.now().isoformat(),
            'game_state': None
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'player_id': player_id,
            'session_code': session_id
        })
        
    except Exception as e:
        logger.error(f"Error creating multiplayer session: {e}")
        return jsonify({'error': 'Failed to create multiplayer session'}), 500

@rpg_bp.route('/api/rpg/multiplayer/join', methods=['POST'])
def join_multiplayer_session():
    """Join an existing multiplayer RPG session"""
    try:
        data = request.get_json()
        session_code = data.get('session_code')
        player_name = data.get('player_name', 'Player')
        
        if not session_code:
            return jsonify({'error': 'Session code is required'}), 400
        
        session = rpg_sessions.get(session_code.upper())
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if player name is already taken
        existing_players = [p['name'] for p in session['players']]
        if player_name in existing_players:
            return jsonify({'error': 'Player name already taken'}), 400
        
        # Add player to session
        player_id = str(uuid.uuid4())
        session['players'].append({
            'id': player_id,
            'name': player_name,
            'is_dm': False,
            'joined_at': datetime.now().isoformat()
        })
        
        # Load campaign data
        campaign = load_campaign(session['campaign_id'])
        
        return jsonify({
            'success': True,
            'session_id': session_code.upper(),
            'player_id': player_id,
            'campaign': campaign
        })
        
    except Exception as e:
        logger.error(f"Error joining multiplayer session: {e}")
        return jsonify({'error': 'Failed to join session'}), 500

@rpg_bp.route('/api/rpg/multiplayer/leave', methods=['POST'])
def leave_multiplayer_session():
    """Leave a multiplayer RPG session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        player_id = data.get('player_id')
        
        if not session_id or not player_id:
            return jsonify({'error': 'Session ID and Player ID are required'}), 400
        
        session = rpg_sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Remove player from session
        session['players'] = [p for p in session['players'] if p['id'] != player_id]
        
        # If no players left, remove session
        if not session['players']:
            del rpg_sessions[session_id]
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error leaving multiplayer session: {e}")
        return jsonify({'error': 'Failed to leave session'}), 500

@rpg_bp.route('/api/rpg/multiplayer/session/<session_id>/status', methods=['GET'])
def get_multiplayer_session_status(session_id):
    """Get status of a multiplayer session"""
    try:
        session = rpg_sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'session': {
                'id': session_id,
                'players': session['players'],
                'created_at': session['created_at'],
                'campaign_id': session['campaign_id']
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return jsonify({'error': 'Failed to get session status'}), 500

# WebSocket event handlers for multiplayer
def handle_player_join(session_id, player_id, player_name):
    """Handle player joining a session"""
    try:
        session = rpg_sessions.get(session_id)
        if not session:
            return
        
        # Join WebSocket room
        join_room(session_id)
        
        # Notify other players
        emit('player_joined', {
            'type': 'player_joined',
            'player_id': player_id,
            'player_name': player_name,
            'players': session['players']
        }, room=session_id)
        
    except Exception as e:
        logger.error(f"Error handling player join: {e}")

def handle_player_action(session_id, player_id, action):
    """Handle player action in multiplayer session"""
    try:
        session = rpg_sessions.get(session_id)
        if not session:
            return
        
        # Find player
        player = next((p for p in session['players'] if p['id'] == player_id), None)
        if not player:
            return
        
        # Load campaign if needed
        if not rpg_engine.current_campaign:
            rpg_engine.load_campaign(session['campaign_id'])
        
        # Null check for current_campaign
        if not rpg_engine.current_campaign:
            return

        # Store campaign reference safely to prevent null pointer issues
        campaign = rpg_engine.current_campaign
        if not campaign:
            return

        # Generate DM response using the RPG engine
        dm_prompt = rpg_engine.generate_dm_prompt(action)
        
        # For now, return a placeholder response
        # In a full implementation, this would call the LLM
        response_text = f"The DM considers your action: {action}. The adventure continues..."
        
        # Update game state
        campaign_summary = rpg_engine.get_campaign_summary()
        session['game_state'] = {
            'current_scene': campaign_summary.get('current_scene', 'Unknown scene'),
            'inventory': campaign_summary.get('inventory', []),
            'quests': campaign_summary.get('quest_log', []),
            'characters': campaign_summary.get('characters', [])
        }
        
        # Broadcast to all players
        emit('dm_response', {
            'type': 'dm_response',
            'response': response_text,
            'game_state': session['game_state']
        }, room=session_id)
        
    except Exception as e:
        logger.error(f"Error handling player action: {e}")

def handle_dice_roll(session_id, player_id, dice_notation):
    """Handle dice roll in multiplayer session"""
    try:
        session = rpg_sessions.get(session_id)
        if not session:
            return
        
        # Find player
        player = next((p for p in session['players'] if p['id'] == player_id), None)
        if not player:
            return
        
        # Roll dice
        result = rpg_engine.roll_dice(dice_notation)
        
        # Broadcast to all players
        emit('dice_roll', {
            'type': 'dice_roll',
            'player_name': player['name'],
            'dice': dice_notation,
            'result': result['total'],
            'rolls': result['rolls']
        }, room=session_id)
        
    except Exception as e:
        logger.error(f"Error handling dice roll: {e}")

# WebSocket event handlers (to be connected to Flask-SocketIO)
def on_connect(session_id):
    """Handle WebSocket connection"""
    join_room(session_id)

def on_disconnect(session_id):
    """Handle WebSocket disconnection"""
    leave_room(session_id)

def on_player_join(data):
    """Handle player join event"""
    session_id = data.get('session_id')
    player_id = data.get('player_id')
    player_name = data.get('player_name')
    handle_player_join(session_id, player_id, player_name)

def on_player_action(data):
    """Handle player action event"""
    session_id = data.get('session_id')
    player_id = data.get('player_id')
    action = data.get('action')
    handle_player_action(session_id, player_id, action)

def on_dice_roll(data):
    """Handle dice roll event"""
    session_id = data.get('session_id')
    player_id = data.get('player_id')
    dice_notation = data.get('dice')
    handle_dice_roll(session_id, player_id, dice_notation)

