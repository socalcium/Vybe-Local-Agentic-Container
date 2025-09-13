"""
Collaboration Manager for Vybe
Provides multi-user support and collaboration tools
"""

import json
import uuid
import time
import bcrypt
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from threading import Lock

from ..logger import log_info, log_error, log_warning
from ..models import db, AppSetting, User

# Import app for Flask application context
try:
    from .. import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    log_warning("Flask app not available for collaboration manager")


class CollaborationType(Enum):
    """Types of collaboration sessions"""
    CHAT = "chat"
    DOCUMENT = "document"
    PROJECT = "project"
    WORKSPACE = "workspace"
    MEETING = "meeting"
    BRAINSTORMING = "brainstorming"


class UserRole(Enum):
    """User roles in collaboration sessions"""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    PARTICIPANT = "participant"
    VIEWER = "viewer"
    GUEST = "guest"


class SessionStatus(Enum):
    """Collaboration session status"""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"


@dataclass
class CollaborationSession:
    """Collaboration session information"""
    id: str
    name: str
    description: str
    session_type: CollaborationType
    owner_id: str
    created_at: datetime
    status: SessionStatus
    max_participants: int = 10
    current_participants: int = 0
    participants: List[str] = field(default_factory=list)
    moderators: List[str] = field(default_factory=list)
    admins: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_activity: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    requires_invitation: bool = True
    password_protected: bool = False
    password_hash: Optional[str] = None


@dataclass
class SessionParticipant:
    """Participant information in a collaboration session"""
    user_id: str
    username: str
    role: UserRole
    joined_at: datetime
    last_activity: Optional[datetime] = None
    permissions: List[str] = field(default_factory=list)
    status: str = "online"
    avatar_url: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class CollaborationMessage:
    """Message in a collaboration session"""
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str = "text"
    timestamp: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    reply_to: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CollaborationManager:
    """Manages collaboration sessions and multi-user features"""
    
    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.participants: Dict[str, Dict[str, SessionParticipant]] = {}  # session_id -> {user_id -> participant}
        self.messages: Dict[str, List[CollaborationMessage]] = {}  # session_id -> messages
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        self.session_locks: Dict[str, Lock] = {}
        
        # Load existing sessions from database
        self._load_sessions()
    
    def _validate_session_data(self, session_data: Dict[str, Any]) -> bool:
        """
        Validate session data loaded from database
        
        Args:
            session_data: Dictionary containing session data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            required_fields = ['id', 'name', 'session_type', 'owner_id', 'created_at', 'status']
            
            # Check for required fields
            for field in required_fields:
                if field not in session_data:
                    log_warning(f"Session validation failed: missing required field '{field}'")
                    return False
            
            # Validate field types and values
            if not isinstance(session_data['id'], str) or not session_data['id']:
                log_warning("Session validation failed: invalid id")
                return False
            
            if not isinstance(session_data['name'], str) or not session_data['name']:
                log_warning("Session validation failed: invalid name")
                return False
                
            if not isinstance(session_data['owner_id'], str) or not session_data['owner_id']:
                log_warning("Session validation failed: invalid owner_id")
                return False
            
            # Validate session_type is a valid enum value
            try:
                CollaborationType(session_data['session_type'])
            except ValueError:
                log_warning(f"Session validation failed: invalid session_type '{session_data['session_type']}'")
                return False
            
            # Validate status is a valid enum value
            try:
                SessionStatus(session_data['status'])
            except ValueError:
                log_warning(f"Session validation failed: invalid status '{session_data['status']}'")
                return False
            
            # Validate numeric fields
            if 'max_participants' in session_data:
                if not isinstance(session_data['max_participants'], int) or session_data['max_participants'] < 1:
                    log_warning("Session validation failed: invalid max_participants")
                    return False
            
            if 'current_participants' in session_data:
                if not isinstance(session_data['current_participants'], int) or session_data['current_participants'] < 0:
                    log_warning("Session validation failed: invalid current_participants")
                    return False
            
            # Validate list fields
            list_fields = ['participants', 'moderators', 'admins', 'tags']
            for field in list_fields:
                if field in session_data and not isinstance(session_data[field], list):
                    log_warning(f"Session validation failed: {field} must be a list")
                    return False
            
            # Validate dict fields
            dict_fields = ['settings', 'metadata']
            for field in dict_fields:
                if field in session_data and not isinstance(session_data[field], dict):
                    log_warning(f"Session validation failed: {field} must be a dict")
                    return False
            
            # Validate boolean fields
            bool_fields = ['is_public', 'requires_invitation', 'password_protected']
            for field in bool_fields:
                if field in session_data and not isinstance(session_data[field], bool):
                    log_warning(f"Session validation failed: {field} must be a boolean")
                    return False
            
            return True
            
        except Exception as e:
            log_error(f"Error validating session data: {e}")
            return False
    
    def _validate_participant_data(self, participant_data: Dict[str, Any]) -> bool:
        """
        Validate participant data loaded from database
        
        Args:
            participant_data: Dictionary containing participant data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            required_fields = ['user_id', 'username', 'role', 'joined_at']
            
            # Check for required fields
            for field in required_fields:
                if field not in participant_data:
                    log_warning(f"Participant validation failed: missing required field '{field}'")
                    return False
            
            # Validate field types
            if not isinstance(participant_data['user_id'], str) or not participant_data['user_id']:
                log_warning("Participant validation failed: invalid user_id")
                return False
            
            if not isinstance(participant_data['username'], str) or not participant_data['username']:
                log_warning("Participant validation failed: invalid username")
                return False
            
            # Validate role is a valid enum value
            try:
                UserRole(participant_data['role'])
            except ValueError:
                log_warning(f"Participant validation failed: invalid role '{participant_data['role']}'")
                return False
            
            # Validate permissions is a list
            if 'permissions' in participant_data and not isinstance(participant_data['permissions'], list):
                log_warning("Participant validation failed: permissions must be a list")
                return False
            
            return True
            
        except Exception as e:
            log_error(f"Error validating participant data: {e}")
            return False
    
    def _validate_message_data(self, message_data: Dict[str, Any]) -> bool:
        """
        Validate message data loaded from database
        
        Args:
            message_data: Dictionary containing message data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            required_fields = ['id', 'session_id', 'user_id', 'username', 'content', 'timestamp', 'message_type']
            
            # Check for required fields
            for field in required_fields:
                if field not in message_data:
                    log_warning(f"Message validation failed: missing required field '{field}'")
                    return False
            
            # Validate field types
            string_fields = ['id', 'session_id', 'user_id', 'username', 'content', 'message_type']
            for field in string_fields:
                if not isinstance(message_data[field], str) or not message_data[field]:
                    log_warning(f"Message validation failed: invalid {field}")
                    return False
            
            return True
            
        except Exception as e:
            log_error(f"Error validating message data: {e}")
            return False
        
    def _load_sessions(self):
        """Load existing collaboration sessions from database"""
        try:
            if not APP_AVAILABLE:
                log_warning("Flask app not available - using in-memory sessions only")
                return
                
            with app.app_context():
                # Load sessions from AppSetting
                setting = AppSetting.query.filter_by(key='collaboration_sessions').first()
                if setting:
                    sessions_data = json.loads(setting.value)
                    for session_data in sessions_data:
                        # Validate session data before processing
                        if not self._validate_session_data(session_data):
                            log_warning(f"Skipping invalid session data: {session_data.get('id', 'unknown')}")
                            continue
                        
                        # Convert datetime strings back to datetime objects
                        try:
                            if session_data.get('created_at'):
                                session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                            if session_data.get('last_activity'):
                                session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])
                            if session_data.get('scheduled_start'):
                                session_data['scheduled_start'] = datetime.fromisoformat(session_data['scheduled_start'])
                            if session_data.get('scheduled_end'):
                                session_data['scheduled_end'] = datetime.fromisoformat(session_data['scheduled_end'])
                        except ValueError as e:
                            log_warning(f"Skipping session with invalid datetime format: {session_data.get('id', 'unknown')} - {e}")
                            continue
                        
                        try:
                            session = CollaborationSession(**session_data)
                            self.sessions[session.id] = session
                            self.session_locks[session.id] = Lock()
                        except Exception as e:
                            log_warning(f"Failed to create session object: {session_data.get('id', 'unknown')} - {e}")
                            continue
                    
                # Load participants
                setting = AppSetting.query.filter_by(key='collaboration_participants').first()
                if setting:
                    participants_data = json.loads(setting.value)
                    for session_id, session_participants in participants_data.items():
                        # Only load participants for valid sessions
                        if session_id not in self.sessions:
                            log_warning(f"Skipping participants for unknown session: {session_id}")
                            continue
                            
                        self.participants[session_id] = {}
                        for user_id, participant_data in session_participants.items():
                            # Validate participant data before processing
                            if not self._validate_participant_data(participant_data):
                                log_warning(f"Skipping invalid participant data: {user_id} in session {session_id}")
                                continue
                            
                            try:
                                if participant_data.get('joined_at'):
                                    participant_data['joined_at'] = datetime.fromisoformat(participant_data['joined_at'])
                                if participant_data.get('last_activity'):
                                    participant_data['last_activity'] = datetime.fromisoformat(participant_data['last_activity'])
                            except ValueError as e:
                                log_warning(f"Skipping participant with invalid datetime format: {user_id} - {e}")
                                continue
                        
                            try:
                                participant = SessionParticipant(**participant_data)
                                self.participants[session_id][user_id] = participant
                            except Exception as e:
                                log_warning(f"Failed to create participant object: {user_id} - {e}")
                                continue
                        
                # Load messages
                setting = AppSetting.query.filter_by(key='collaboration_messages').first()
                if setting:
                    messages_data = json.loads(setting.value)
                    for session_id, session_messages in messages_data.items():
                        # Only load messages for valid sessions
                        if session_id not in self.sessions:
                            log_warning(f"Skipping messages for unknown session: {session_id}")
                            continue
                            
                        self.messages[session_id] = []
                        for message_data in session_messages:
                            # Validate message data before processing
                            if not self._validate_message_data(message_data):
                                log_warning(f"Skipping invalid message data in session {session_id}")
                                continue
                            
                            try:
                                if message_data.get('timestamp'):
                                    message_data['timestamp'] = datetime.fromisoformat(message_data['timestamp'])
                                if message_data.get('edited_at'):
                                    message_data['edited_at'] = datetime.fromisoformat(message_data['edited_at'])
                            except ValueError as e:
                                log_warning(f"Skipping message with invalid datetime format: {message_data.get('id', 'unknown')} - {e}")
                                continue
                        
                            try:
                                message = CollaborationMessage(**message_data)
                                self.messages[session_id].append(message)
                            except Exception as e:
                                log_warning(f"Failed to create message object: {message_data.get('id', 'unknown')} - {e}")
                                continue
                        
            # Build user sessions mapping
            for session_id, session_participants in self.participants.items():
                for user_id in session_participants.keys():
                    if user_id not in self.user_sessions:
                        self.user_sessions[user_id] = set()
                    self.user_sessions[user_id].add(session_id)
                    
        except Exception as e:
            log_error(f"Error loading collaboration sessions: {e}")
            
    def _save_sessions(self):
        """Save collaboration sessions to database"""
        try:
            if not APP_AVAILABLE:
                log_warning("Flask app not available - cannot save sessions to database")
                return
                
            with app.app_context():
                # Save sessions
                sessions_data = [asdict(session) for session in self.sessions.values()]
                setting = AppSetting.query.filter_by(key='collaboration_sessions').first()
                if setting:
                    setting.value = json.dumps(sessions_data, default=str)
                else:
                    setting = AppSetting()
                    setting.key = 'collaboration_sessions'
                    setting.value = json.dumps(sessions_data, default=str)
                    db.session.add(setting)                # Save participants
                participants_data = {}
                for session_id, session_participants in self.participants.items():
                    participants_data[session_id] = {
                        user_id: asdict(participant) 
                        for user_id, participant in session_participants.items()
                    }
            
                setting = AppSetting.query.filter_by(key='collaboration_participants').first()
                if setting:
                    setting.value = json.dumps(participants_data, default=str)
                else:
                    setting = AppSetting()
                    setting.key = 'collaboration_participants'
                    setting.value = json.dumps(participants_data, default=str)
                    db.session.add(setting)
                
                # Save messages
                messages_data = {}
                for session_id, session_messages in self.messages.items():
                    messages_data[session_id] = [asdict(message) for message in session_messages]
            
                setting = AppSetting.query.filter_by(key='collaboration_messages').first()
                if setting:
                    setting.value = json.dumps(messages_data, default=str)
                else:
                    setting = AppSetting()
                    setting.key = 'collaboration_messages'
                    setting.value = json.dumps(messages_data, default=str)
                    db.session.add(setting)
                
                db.session.commit()
            
        except Exception as e:
            log_error(f"Error saving collaboration sessions: {e}")
            
    def create_session(self, name: str, description: str, session_type: CollaborationType, 
                      owner_id: str, max_participants: int = 10, is_public: bool = False,
                      requires_invitation: bool = True, password_protected: bool = False,
                      password: Optional[str] = None, scheduled_start: Optional[datetime] = None,
                      scheduled_end: Optional[datetime] = None, tags: Optional[List[str]] = None) -> Optional[str]:
        """Create a new collaboration session"""
        try:
            session_id = str(uuid.uuid4())
            
            # Hash password if provided
            password_hash = None
            if password_protected and password:
                salt = bcrypt.gensalt()
                password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            session = CollaborationSession(
                id=session_id,
                name=name,
                description=description,
                session_type=session_type,
                owner_id=owner_id,
                created_at=datetime.now(),
                status=SessionStatus.ACTIVE if not scheduled_start else SessionStatus.SCHEDULED,
                max_participants=max_participants,
                is_public=is_public,
                requires_invitation=requires_invitation,
                password_protected=password_protected,
                password_hash=password_hash,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                tags=tags or []
            )
            
            self.sessions[session_id] = session
            self.session_locks[session_id] = Lock()
            self.participants[session_id] = {}
            self.messages[session_id] = []
            
            # Add owner as participant
            self.add_participant(session_id, owner_id, UserRole.OWNER)
            
            # Update user sessions mapping
            if owner_id not in self.user_sessions:
                self.user_sessions[owner_id] = set()
            self.user_sessions[owner_id].add(session_id)
            
            self._save_sessions()
            
            log_info(f"Created collaboration session: {session_id} by user {owner_id}")
            return session_id
            
        except Exception as e:
            log_error(f"Error creating collaboration session: {e}")
            return None
            
    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get a collaboration session by ID"""
        return self.sessions.get(session_id)
        
    def get_user_sessions(self, user_id: str) -> List[CollaborationSession]:
        """Get all sessions for a user"""
        user_session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in user_session_ids if sid in self.sessions]
        
    def get_public_sessions(self) -> List[CollaborationSession]:
        """Get all public sessions"""
        return [session for session in self.sessions.values() if session.is_public]
        
    def verify_session_password(self, session_id: str, password: str) -> bool:
        """
        Verify password for a password-protected session
        
        Args:
            session_id: ID of the session
            password: Password to verify
            
        Returns:
            True if password is correct, False otherwise
        """
        try:
            session = self.sessions.get(session_id)
            if not session:
                log_error(f"Session {session_id} not found")
                return False
                
            if not session.password_protected:
                # Session is not password protected
                return True
                
            if not session.password_hash:
                log_error(f"Session {session_id} is password protected but has no hash")
                return False
                
            # Verify password using bcrypt
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                session.password_hash.encode('utf-8')
            )
            
        except Exception as e:
            log_error(f"Error verifying session password: {e}")
            return False
        
    def add_participant(self, session_id: str, user_id: str, role: UserRole = UserRole.PARTICIPANT, 
                       password: Optional[str] = None) -> bool:
        """Add a participant to a collaboration session"""
        try:
            if session_id not in self.sessions:
                log_error(f"Session {session_id} not found")
                return False
                
            session = self.sessions[session_id]
            
            # Check password for password-protected sessions
            if session.password_protected and role != UserRole.OWNER:
                if not password or not self.verify_session_password(session_id, password):
                    log_error(f"Invalid password for session {session_id}")
                    return False
            
            # Check if session is full
            if session.current_participants >= session.max_participants:
                log_error(f"Session {session_id} is full")
                return False
                
            # Get user information
            user = User.query.get(user_id)
            if not user:
                log_error(f"User {user_id} not found")
                return False
                
            # Check if user is already a participant
            if user_id in self.participants.get(session_id, {}):
                log_warning(f"User {user_id} is already a participant in session {session_id}")
                return True
                
            participant = SessionParticipant(
                user_id=user_id,
                username=user.username,
                role=role,
                joined_at=datetime.now(),
                display_name=user.display_name or user.username
            )
            
            if session_id not in self.participants:
                self.participants[session_id] = {}
            self.participants[session_id][user_id] = participant
            
            # Update session participant count
            session.current_participants += 1
            session.last_activity = datetime.now()
            
            # Update user sessions mapping
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            
            # Update role lists
            if role == UserRole.ADMIN:
                session.admins.append(user_id)
            elif role == UserRole.MODERATOR:
                session.moderators.append(user_id)
            elif role == UserRole.PARTICIPANT:
                session.participants.append(user_id)
                
            self._save_sessions()
            
            log_info(f"Added participant {user_id} to session {session_id}")
            return True
            
        except Exception as e:
            log_error(f"Error adding participant to session: {e}")
            return False
            
    def remove_participant(self, session_id: str, user_id: str) -> bool:
        """Remove a participant from a collaboration session"""
        try:
            if session_id not in self.sessions or session_id not in self.participants:
                log_error(f"Session {session_id} not found")
                return False
                
            if user_id not in self.participants[session_id]:
                log_error(f"User {user_id} is not a participant in session {session_id}")
                return False
                
            session = self.sessions[session_id]
            participant = self.participants[session_id][user_id]
            
            # Remove from session
            del self.participants[session_id][user_id]
            session.current_participants -= 1
            session.last_activity = datetime.now()
            
            # Remove from role lists
            if user_id in session.admins:
                session.admins.remove(user_id)
            if user_id in session.moderators:
                session.moderators.remove(user_id)
            if user_id in session.participants:
                session.participants.remove(user_id)
                
            # Update user sessions mapping
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                
            self._save_sessions()
            
            log_info(f"Removed participant {user_id} from session {session_id}")
            return True
            
        except Exception as e:
            log_error(f"Error removing participant from session: {e}")
            return False
            
    def get_session_participants(self, session_id: str) -> List[SessionParticipant]:
        """Get all participants in a session"""
        if session_id not in self.participants:
            return []
        return list(self.participants[session_id].values())
        
    def send_message(self, session_id: str, sender_id: str, content: str, 
                    message_type: str = "text", reply_to: Optional[str] = None,
                    attachments: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Send a message in a collaboration session"""
        try:
            if session_id not in self.sessions:
                log_error(f"Session {session_id} not found")
                return None
                
            if sender_id not in self.participants.get(session_id, {}):
                log_error(f"User {sender_id} is not a participant in session {session_id}")
                return None
                
            participant = self.participants[session_id][sender_id]
            
            message_id = str(uuid.uuid4())
            message = CollaborationMessage(
                id=message_id,
                session_id=session_id,
                sender_id=sender_id,
                sender_name=participant.display_name or participant.username,
                content=content,
                message_type=message_type,
                reply_to=reply_to,
                attachments=attachments or []
            )
            
            if session_id not in self.messages:
                self.messages[session_id] = []
            self.messages[session_id].append(message)
            
            # Update session activity
            session = self.sessions[session_id]
            session.last_activity = datetime.now()
            
            # Update participant activity
            participant.last_activity = datetime.now()
            
            self._save_sessions()
            
            log_info(f"Message sent in session {session_id} by {sender_id}")
            return message_id
            
        except Exception as e:
            log_error(f"Error sending message: {e}")
            return None
            
    def get_session_messages(self, session_id: str, limit: int = 50, offset: int = 0) -> List[CollaborationMessage]:
        """Get messages from a collaboration session"""
        if session_id not in self.messages:
            return []
            
        messages = self.messages[session_id]
        return messages[offset:offset + limit]
        
    def edit_message(self, session_id: str, message_id: str, user_id: str, new_content: str) -> bool:
        """Edit a message in a collaboration session"""
        try:
            if session_id not in self.messages:
                log_error(f"Session {session_id} not found")
                return False
                
            # Find the message
            message = None
            for msg in self.messages[session_id]:
                if msg.id == message_id:
                    message = msg
                    break
                    
            if not message:
                log_error(f"Message {message_id} not found")
                return False
                
            # Check if user can edit the message
            if message.sender_id != user_id:
                # Check if user is admin/moderator
                if session_id not in self.participants or user_id not in self.participants[session_id]:
                    log_error(f"User {user_id} cannot edit message {message_id}")
                    return False
                    
                participant = self.participants[session_id][user_id]
                if participant.role not in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.OWNER]:
                    log_error(f"User {user_id} cannot edit message {message_id}")
                    return False
                    
            # Edit the message
            message.content = new_content
            message.edited_at = datetime.now()
            
            self._save_sessions()
            
            log_info(f"Message {message_id} edited by {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Error editing message: {e}")
            return False
            
    def delete_message(self, session_id: str, message_id: str, user_id: str) -> bool:
        """Delete a message from a collaboration session"""
        try:
            if session_id not in self.messages:
                log_error(f"Session {session_id} not found")
                return False
                
            # Find the message
            message = None
            message_index = None
            for i, msg in enumerate(self.messages[session_id]):
                if msg.id == message_id:
                    message = msg
                    message_index = i
                    break
                    
            if not message or message_index is None:
                log_error(f"Message {message_id} not found")
                return False
                
            # Check if user can delete the message
            if message.sender_id != user_id:
                # Check if user is admin/moderator
                if session_id not in self.participants or user_id not in self.participants[session_id]:
                    log_error(f"User {user_id} cannot delete message {message_id}")
                    return False
                    
                participant = self.participants[session_id][user_id]
                if participant.role not in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.OWNER]:
                    log_error(f"User {user_id} cannot delete message {message_id}")
                    return False
                    
            # Delete the message
            del self.messages[session_id][message_index]
            
            self._save_sessions()
            
            log_info(f"Message {message_id} deleted by {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Error deleting message: {e}")
            return False
            
    def update_session_status(self, session_id: str, status: SessionStatus, user_id: str) -> bool:
        """Update the status of a collaboration session"""
        try:
            if session_id not in self.sessions:
                log_error(f"Session {session_id} not found")
                return False
                
            session = self.sessions[session_id]
            
            # Check if user can update session status
            if session.owner_id != user_id:
                if session_id not in self.participants or user_id not in self.participants[session_id]:
                    log_error(f"User {user_id} cannot update session {session_id} status")
                    return False
                    
                participant = self.participants[session_id][user_id]
                if participant.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
                    log_error(f"User {user_id} cannot update session {session_id} status")
                    return False
                    
            session.status = status
            session.last_activity = datetime.now()
            
            self._save_sessions()
            
            log_info(f"Session {session_id} status updated to {status.value} by {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Error updating session status: {e}")
            return False
            
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a collaboration session"""
        try:
            if session_id not in self.sessions:
                return {}
                
            session = self.sessions[session_id]
            participants = self.get_session_participants(session_id)
            messages = self.get_session_messages(session_id, limit=1000)  # Get all messages for stats
            
            # Calculate statistics
            total_messages = len(messages)
            unique_senders = len(set(msg.sender_id for msg in messages))
            avg_message_length = sum(len(msg.content) for msg in messages) / total_messages if total_messages > 0 else 0
            
            # Activity over time
            activity_by_hour = {}
            for msg in messages:
                if msg.timestamp:
                    hour = msg.timestamp.hour
                    activity_by_hour[hour] = activity_by_hour.get(hour, 0) + 1
                
            # Participant activity
            participant_activity = {}
            for participant in participants:
                participant_messages = [msg for msg in messages if msg.sender_id == participant.user_id]
                participant_activity[participant.user_id] = {
                    'message_count': len(participant_messages),
                    'last_activity': participant.last_activity.isoformat() if participant.last_activity else None
                }
                
            return {
                'session_id': session_id,
                'total_participants': len(participants),
                'total_messages': total_messages,
                'unique_senders': unique_senders,
                'avg_message_length': round(avg_message_length, 2),
                'activity_by_hour': activity_by_hour,
                'participant_activity': participant_activity,
                'session_duration': (datetime.now() - session.created_at).total_seconds() if session.created_at else 0,
                'last_activity': session.last_activity.isoformat() if session.last_activity else None
            }
            
        except Exception as e:
            log_error(f"Error getting session statistics: {e}")
            return {}
            
    def search_sessions(self, query: str, user_id: Optional[str] = None) -> List[CollaborationSession]:
        """Search for collaboration sessions"""
        try:
            results = []
            query_lower = query.lower()
            
            for session in self.sessions.values():
                # Check if session matches query
                if (query_lower in session.name.lower() or 
                    query_lower in session.description.lower() or
                    any(query_lower in tag.lower() for tag in session.tags)):
                    
                    # Check if user has access
                    if user_id:
                        if session.is_public or session.owner_id == user_id:
                            results.append(session)
                        elif session.id in self.user_sessions.get(user_id, set()):
                            results.append(session)
                    else:
                        # If no user specified, only return public sessions
                        if session.is_public:
                            results.append(session)
                            
            return results
            
        except Exception as e:
            log_error(f"Error searching sessions: {e}")
            return []
            
    def cleanup_inactive_sessions(self, max_inactive_days: int = 30):
        """Clean up inactive collaboration sessions"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_inactive_days)
            sessions_to_remove = []
            
            for session_id, session in self.sessions.items():
                if (session.last_activity and session.last_activity < cutoff_date and 
                    session.status in [SessionStatus.ENDED, SessionStatus.ARCHIVED]):
                    sessions_to_remove.append(session_id)
                    
            for session_id in sessions_to_remove:
                # Remove session data
                if session_id in self.sessions:
                    del self.sessions[session_id]
                if session_id in self.participants:
                    del self.participants[session_id]
                if session_id in self.messages:
                    del self.messages[session_id]
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
                    
                # Remove from user sessions mapping
                for user_sessions in self.user_sessions.values():
                    user_sessions.discard(session_id)
                    
            if sessions_to_remove:
                self._save_sessions()
                log_info(f"Cleaned up {len(sessions_to_remove)} inactive sessions")
                
        except Exception as e:
            log_error(f"Error cleaning up inactive sessions: {e}")


# Global collaboration manager instance
collaboration_manager = CollaborationManager()
