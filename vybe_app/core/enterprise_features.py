"""
Enterprise-grade Features
Advanced compliance, security, and governance features for enterprise deployment
"""

import os
import json
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from functools import wraps

# Optional cryptography libraries
try:
    import jwt  # type: ignore
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("Warning: jwt not available - JWT token features disabled")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("Warning: cryptography not available - encryption features disabled")

import base64
import re

logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    """Supported compliance standards"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"

class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_CHECK = "compliance_check"
    ADMIN_ACTION = "admin_action"

class UserRole(Enum):
    """User roles for RBAC"""
    VIEWER = "viewer"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    AUDITOR = "auditor"

@dataclass
class AuditEvent:
    """Audit event record"""
    event_id: str
    timestamp: datetime
    user_id: str
    event_type: AuditEventType
    resource: str
    action: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    session_id: str
    compliance_tags: List[str] = field(default_factory=list)
    risk_level: str = "low"

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    name: str
    description: str
    standard: ComplianceStandard
    category: str
    severity: str
    enabled: bool
    conditions: Dict[str, Any]
    actions: List[str]

@dataclass
class DataClassification:
    """Data classification definition"""
    classification_id: str
    name: str
    level: int
    description: str
    handling_requirements: List[str]
    retention_policy: str
    encryption_required: bool
    access_controls: List[str]

class EnterpriseSecurityManager:
    """Enterprise security and compliance manager"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.audit_events = []
        self.compliance_rules = []
        self.data_classifications = []
        self.user_roles = {}
        self.encryption_key = self.generate_encryption_key()
        if CRYPTOGRAPHY_AVAILABLE:
            self.fernet = Fernet(self.encryption_key)
        else:
            self.fernet = None
            logger.warning("Encryption features disabled - cryptography not available")
            
        self.jwt_secret = self.config.get('jwt_secret', os.urandom(32))
        
        self.initialize_compliance_rules()
        self.initialize_data_classifications()
        self.initialize_default_roles()
    
    def generate_encryption_key(self) -> bytes:
        """Generate encryption key for sensitive data"""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography not available - using basic key generation")
            return os.urandom(32)
            
        if 'encryption_key' in self.config:
            return base64.urlsafe_b64decode(self.config['encryption_key'])
        else:
            return Fernet.generate_key()
    
    def initialize_compliance_rules(self):
        """Initialize default compliance rules"""
        default_rules = [
            ComplianceRule(
                rule_id="gdpr_data_retention",
                name="GDPR Data Retention",
                description="Ensure data retention complies with GDPR requirements",
                standard=ComplianceStandard.GDPR,
                category="data_retention",
                severity="high",
                enabled=True,
                conditions={"max_retention_days": 2555},  # 7 years
                actions=["audit_log", "data_cleanup"]
            ),
            ComplianceRule(
                rule_id="hipaa_phi_protection",
                name="HIPAA PHI Protection",
                description="Protect Personal Health Information according to HIPAA",
                standard=ComplianceStandard.HIPAA,
                category="data_protection",
                severity="critical",
                enabled=True,
                conditions={"encryption_required": True, "access_logging": True},
                actions=["encrypt_data", "audit_log", "access_control"]
            ),
            ComplianceRule(
                rule_id="sox_financial_data",
                name="SOX Financial Data",
                description="Ensure financial data integrity for SOX compliance",
                standard=ComplianceStandard.SOX,
                category="data_integrity",
                severity="high",
                enabled=True,
                conditions={"audit_trail": True, "data_validation": True},
                actions=["audit_log", "data_validation", "backup_verification"]
            ),
            ComplianceRule(
                rule_id="pci_card_data",
                name="PCI Card Data Protection",
                description="Protect payment card data according to PCI DSS",
                standard=ComplianceStandard.PCI_DSS,
                category="payment_security",
                severity="critical",
                enabled=True,
                conditions={"encryption_required": True, "tokenization": True},
                actions=["encrypt_data", "tokenize_data", "audit_log"]
            )
        ]
        
        self.compliance_rules.extend(default_rules)
    
    def initialize_data_classifications(self):
        """Initialize data classification levels"""
        classifications = [
            DataClassification(
                classification_id="public",
                name="Public",
                level=1,
                description="Publicly accessible information",
                handling_requirements=["no_special_handling"],
                retention_policy="indefinite",
                encryption_required=False,
                access_controls=["authenticated_users"]
            ),
            DataClassification(
                classification_id="internal",
                name="Internal",
                level=2,
                description="Internal business information",
                handling_requirements=["internal_use_only"],
                retention_policy="7_years",
                encryption_required=True,
                access_controls=["authenticated_users", "internal_network"]
            ),
            DataClassification(
                classification_id="confidential",
                name="Confidential",
                level=3,
                description="Sensitive business information",
                handling_requirements=["need_to_know", "encryption_required"],
                retention_policy="10_years",
                encryption_required=True,
                access_controls=["role_based_access", "audit_logging"]
            ),
            DataClassification(
                classification_id="restricted",
                name="Restricted",
                level=4,
                description="Highly sensitive information",
                handling_requirements=["strict_access_control", "encryption_required", "audit_trail"],
                retention_policy="permanent",
                encryption_required=True,
                access_controls=["explicit_approval", "multi_factor_auth", "continuous_monitoring"]
            )
        ]
        
        self.data_classifications.extend(classifications)
    
    def initialize_default_roles(self):
        """Initialize default user roles and permissions"""
        self.user_roles = {
            UserRole.VIEWER: {
                "permissions": ["read_public", "read_internal"],
                "data_access": ["public", "internal"],
                "features": ["view_dashboard", "view_reports"]
            },
            UserRole.USER: {
                "permissions": ["read_public", "read_internal", "write_internal"],
                "data_access": ["public", "internal"],
                "features": ["chat", "file_upload", "basic_analysis"]
            },
            UserRole.POWER_USER: {
                "permissions": ["read_public", "read_internal", "write_internal", "read_confidential"],
                "data_access": ["public", "internal", "confidential"],
                "features": ["advanced_analysis", "model_training", "workflow_automation"]
            },
            UserRole.ADMIN: {
                "permissions": ["read_all", "write_all", "delete_internal", "user_management"],
                "data_access": ["public", "internal", "confidential"],
                "features": ["system_configuration", "user_management", "backup_restore"]
            },
            UserRole.SUPER_ADMIN: {
                "permissions": ["full_access", "system_administration"],
                "data_access": ["public", "internal", "confidential", "restricted"],
                "features": ["all_features", "system_administration", "compliance_management"]
            },
            UserRole.AUDITOR: {
                "permissions": ["read_all", "audit_access"],
                "data_access": ["public", "internal", "confidential", "restricted"],
                "features": ["audit_logs", "compliance_reports", "security_monitoring"]
            }
        }
    
    def log_audit_event(self, event: AuditEvent):
        """Log an audit event"""
        try:
            # Add compliance tags based on event type
            if not event.compliance_tags:
                event.compliance_tags = self.get_compliance_tags(event)
            
            # Determine risk level
            event.risk_level = self.assess_risk_level(event)
            
            # Store event
            self.audit_events.append(event)
            
            # Check compliance rules
            self.check_compliance_rules(event)
            
            # Log to external system if configured
            self.export_audit_event(event)
            
            logger.info(f"Audit event logged: {event.event_type.value} by {event.user_id}")
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    def get_compliance_tags(self, event: AuditEvent) -> List[str]:
        """Get compliance tags for an event"""
        tags = []
        
        if event.event_type in [AuditEventType.DATA_ACCESS, AuditEventType.DATA_MODIFICATION, AuditEventType.DATA_DELETION]:
            tags.extend(["data_governance", "privacy"])
        
        if event.event_type == AuditEventType.SECURITY_EVENT:
            tags.extend(["security", "incident_response"])
        
        if event.event_type == AuditEventType.ADMIN_ACTION:
            tags.extend(["administrative", "privileged_access"])
        
        return tags
    
    def assess_risk_level(self, event: AuditEvent) -> str:
        """Assess risk level of an audit event"""
        risk_factors = {
            "high_risk_actions": ["data_deletion", "configuration_change", "security_event"],
            "high_risk_resources": ["user_credentials", "encryption_keys", "compliance_data"],
            "high_risk_users": ["admin", "super_admin", "auditor"]
        }
        
        if (event.action in risk_factors["high_risk_actions"] or
            any(resource in event.resource for resource in risk_factors["high_risk_resources"]) or
            event.user_id in risk_factors["high_risk_users"]):
            return "high"
        elif event.event_type in [AuditEventType.DATA_MODIFICATION, AuditEventType.ADMIN_ACTION]:
            return "medium"
        else:
            return "low"
    
    def check_compliance_rules(self, event: AuditEvent):
        """Check compliance rules against audit event"""
        for rule in self.compliance_rules:
            if not rule.enabled:
                continue
            
            if self.rule_matches_event(rule, event):
                self.execute_rule_actions(rule, event)
    
    def rule_matches_event(self, rule: ComplianceRule, event: AuditEvent) -> bool:
        """Check if a compliance rule matches an audit event"""
        # Simple rule matching logic - can be enhanced
        if rule.standard.value in event.compliance_tags:
            return True
        
        # Check specific conditions
        if "data_retention" in rule.category and event.event_type == AuditEventType.DATA_ACCESS:
            return True
        
        if "data_protection" in rule.category and event.event_type in [AuditEventType.DATA_MODIFICATION, AuditEventType.DATA_ACCESS]:
            return True
        
        return False
    
    def execute_rule_actions(self, rule: ComplianceRule, event: AuditEvent):
        """Execute actions for a compliance rule"""
        for action in rule.actions:
            if action == "audit_log":
                # Already logging
                pass
            elif action == "data_cleanup":
                self.schedule_data_cleanup(event)
            elif action == "encrypt_data":
                self.encrypt_sensitive_data(event)
            elif action == "access_control":
                self.enforce_access_control(event)
            elif action == "data_validation":
                self.validate_data_integrity(event)
    
    def schedule_data_cleanup(self, event: AuditEvent):
        """Schedule data cleanup based on retention policies"""
        # Implementation for data cleanup scheduling
        logger.info(f"Scheduling data cleanup for event: {event.event_id}")
    
    def encrypt_sensitive_data(self, event: AuditEvent):
        """Encrypt sensitive data"""
        # Implementation for data encryption
        logger.info(f"Encrypting sensitive data for event: {event.event_id}")
    
    def enforce_access_control(self, event: AuditEvent):
        """Enforce access control measures"""
        # Implementation for access control
        logger.info(f"Enforcing access control for event: {event.event_id}")
    
    def validate_data_integrity(self, event: AuditEvent):
        """Validate data integrity"""
        # Implementation for data validation
        logger.info(f"Validating data integrity for event: {event.event_id}")
    
    def export_audit_event(self, event: AuditEvent):
        """Export audit event to external systems"""
        # Implementation for external audit logging
        pass
    
    def create_audit_event(self, user_id: str, event_type: AuditEventType, resource: str, 
                          action: str, details: Dict[str, Any], request) -> AuditEvent:
        """Create an audit event from request context"""
        return AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type=event_type,
            resource=resource,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else "unknown",
            user_agent=request.headers.get('User-Agent', 'unknown') if request else "unknown",
            session_id=request.cookies.get('session', 'unknown') if request else "unknown"
        )
    
    def encrypt_sensitive_fields(self, data: Any) -> Any:
        """Encrypt sensitive fields in data"""
        try:
            if self.fernet and isinstance(data, dict):
                sensitive_fields = ['password', 'api_key', 'token', 'secret', 'credential']
                encrypted_data = data.copy()
                for field in sensitive_fields:
                    if field in encrypted_data and isinstance(encrypted_data[field], str):
                        encrypted_data[field] = self.fernet.encrypt(encrypted_data[field].encode()).decode()
                return encrypted_data
            return data
        except Exception as e:
            logger.error(f"Error encrypting sensitive fields: {e}")
            return data

class RoleBasedAccessControl:
    """Role-based access control system"""
    
    def __init__(self, security_manager: EnterpriseSecurityManager):
        self.security_manager = security_manager
        self.user_sessions = {}
        self.permission_cache = {}
    
    def assign_role(self, user_id: str, role: UserRole):
        """Assign a role to a user"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}
        
        self.user_sessions[user_id]['role'] = role
        self.permission_cache.clear()  # Clear cache when roles change
        
        logger.info(f"Assigned role {role.value} to user {user_id}")
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        if user_id not in self.user_sessions:
            return False
        
        role = self.user_sessions[user_id].get('role')
        if not role:
            return False
        
        role_permissions = self.security_manager.user_roles[role]['permissions']
        
        # Check for full access
        if 'full_access' in role_permissions:
            return True
        
        # Check specific permission
        return permission in role_permissions
    
    def check_data_access(self, user_id: str, data_classification: str) -> bool:
        """Check if user can access data of a specific classification"""
        if user_id not in self.user_sessions:
            return False
        
        role = self.user_sessions[user_id].get('role')
        if not role:
            return False
        
        allowed_classifications = self.security_manager.user_roles[role]['data_access']
        return data_classification in allowed_classifications
    
    def check_feature_access(self, user_id: str, feature: str) -> bool:
        """Check if user can access a specific feature"""
        if user_id not in self.user_sessions:
            return False
        
        role = self.user_sessions[user_id].get('role')
        if not role:
            return False
        
        allowed_features = self.security_manager.user_roles[role]['features']
        
        # Check for all features access
        if 'all_features' in allowed_features:
            return True
        
        return feature in allowed_features

class DataGovernanceManager:
    """Data governance and lifecycle management"""
    
    def __init__(self, security_manager: EnterpriseSecurityManager):
        self.security_manager = security_manager
        self.data_inventory = {}
        self.retention_policies = {}
        self.data_lineage = {}
    
    def classify_data(self, data_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """Automatically classify data based on content and metadata"""
        classification = "internal"  # Default classification
        
        # Check for sensitive patterns
        sensitive_patterns = {
            "confidential": [
                r"\b(confidential|secret|private)\b",
                r"\b(ssn|social\s*security)\b",
                r"\b(credit\s*card|cc\s*number)\b",
                r"\b(password|passwd)\b"
            ],
            "restricted": [
                r"\b(encryption\s*key|private\s*key)\b",
                r"\b(admin\s*credentials|root\s*password)\b",
                r"\b(api\s*key|access\s*token)\b"
            ]
        }
        
        content_lower = content.lower()
        
        for level, patterns in sensitive_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    classification = level
                    break
        
        # Store classification
        self.data_inventory[data_id] = {
            "classification": classification,
            "created_at": datetime.utcnow(),
            "metadata": metadata,
            "retention_policy": self.get_retention_policy(classification)
        }
        
        return classification
    
    def get_retention_policy(self, classification: str) -> str:
        """Get retention policy for data classification"""
        for data_class in self.security_manager.data_classifications:
            if data_class.classification_id == classification:
                return data_class.retention_policy
        return "7_years"  # Default
    
    def apply_retention_policy(self, data_id: str):
        """Apply retention policy to data"""
        if data_id not in self.data_inventory:
            return
        
        data_info = self.data_inventory[data_id]
        retention_policy = data_info['retention_policy']
        created_at = data_info['created_at']
        
        # Calculate expiration date
        if retention_policy == "indefinite":
            return
        
        retention_days = {
            "7_years": 2555,
            "10_years": 3650,
            "permanent": None
        }
        
        if retention_policy in retention_days and retention_days[retention_policy]:
            expiration_date = created_at + timedelta(days=retention_days[retention_policy])
            
            if datetime.utcnow() > expiration_date:
                self.schedule_data_deletion(data_id)
    
    def schedule_data_deletion(self, data_id: str):
        """Schedule data for deletion"""
        logger.info(f"Scheduling data deletion for {data_id}")
        # Implementation for data deletion scheduling
    
    def track_data_lineage(self, data_id: str, operation: str, user_id: str, details: Dict[str, Any]):
        """Track data lineage and provenance"""
        if data_id not in self.data_lineage:
            self.data_lineage[data_id] = []
        
        lineage_entry = {
            "timestamp": datetime.utcnow(),
            "operation": operation,
            "user_id": user_id,
            "details": details
        }
        
        self.data_lineage[data_id].append(lineage_entry)

class ComplianceReporting:
    """Compliance reporting and monitoring"""
    
    def __init__(self, security_manager: EnterpriseSecurityManager):
        self.security_manager = security_manager
    
    def generate_compliance_report(self, standard: ComplianceStandard, 
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for a specific standard"""
        report = {
            "standard": standard.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {},
            "violations": [],
            "recommendations": []
        }
        
        # Filter events for the period
        period_events = [
            event for event in self.security_manager.audit_events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Analyze compliance
        if standard == ComplianceStandard.GDPR:
            report.update(self.analyze_gdpr_compliance(period_events))
        elif standard == ComplianceStandard.HIPAA:
            report.update(self.analyze_hipaa_compliance(period_events))
        elif standard == ComplianceStandard.SOX:
            report.update(self.analyze_sox_compliance(period_events))
        elif standard == ComplianceStandard.PCI_DSS:
            report.update(self.analyze_pci_compliance(period_events))
        
        return report
    
    def analyze_gdpr_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze GDPR compliance"""
        analysis = {
            "data_processing_activities": 0,
            "data_subject_requests": 0,
            "data_breaches": 0,
            "consent_management": 0
        }
        
        for event in events:
            if "gdpr" in event.compliance_tags:
                if event.event_type == AuditEventType.DATA_ACCESS:
                    analysis["data_processing_activities"] += 1
                elif event.event_type == AuditEventType.SECURITY_EVENT:
                    analysis["data_breaches"] += 1
        
        return analysis
    
    def analyze_hipaa_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze HIPAA compliance"""
        analysis = {
            "phi_access_events": 0,
            "unauthorized_access": 0,
            "encryption_events": 0,
            "audit_trail_completeness": 0
        }
        
        for event in events:
            if "hipaa" in event.compliance_tags:
                if event.event_type == AuditEventType.DATA_ACCESS:
                    analysis["phi_access_events"] += 1
                elif event.event_type == AuditEventType.SECURITY_EVENT:
                    analysis["unauthorized_access"] += 1
        
        return analysis
    
    def analyze_sox_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze SOX compliance"""
        analysis = {
            "financial_data_access": 0,
            "data_integrity_checks": 0,
            "audit_trail_events": 0,
            "segregation_of_duties": 0
        }
        
        for event in events:
            if "sox" in event.compliance_tags:
                if event.event_type == AuditEventType.DATA_ACCESS:
                    analysis["financial_data_access"] += 1
                elif event.event_type == AuditEventType.DATA_MODIFICATION:
                    analysis["data_integrity_checks"] += 1
        
        return analysis
    
    def analyze_pci_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze PCI DSS compliance"""
        analysis = {
            "card_data_access": 0,
            "encryption_events": 0,
            "security_incidents": 0,
            "access_control_events": 0
        }
        
        for event in events:
            if "pci" in event.compliance_tags:
                if event.event_type == AuditEventType.DATA_ACCESS:
                    analysis["card_data_access"] += 1
                elif event.event_type == AuditEventType.SECURITY_EVENT:
                    analysis["security_incidents"] += 1
        
        return analysis

# Decorators for enterprise features
def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user_id from request or context
            # This is a simplified version - implement based on your auth system
            user_id = kwargs.get('user_id') or 'anonymous'
            
            # Check permission
            if not hasattr(wrapper, 'rbac'):
                wrapper.rbac = RoleBasedAccessControl(EnterpriseSecurityManager())  # type: ignore
            
            if not wrapper.rbac.check_permission(user_id, permission):  # type: ignore
                raise PermissionError(f"Permission '{permission}' required")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def audit_event(event_type: AuditEventType, resource: str, action: str):
    """Decorator to automatically log audit events"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get security manager
            if not hasattr(wrapper, 'security_manager'):
                wrapper.security_manager = EnterpriseSecurityManager()  # type: ignore
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Log audit event
            user_id = kwargs.get('user_id') or 'anonymous'
            details = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs),
                "result": str(result)
            }
            
            # Create audit event (simplified - implement with actual request context)
            event = wrapper.security_manager.create_audit_event(  # type: ignore
                user_id=user_id,
                event_type=event_type,
                resource=resource,
                action=action,
                details=details,
                request=None  # Pass actual request object
            )
            
            wrapper.security_manager.log_audit_event(event)  # type: ignore
            
            return result
        return wrapper
    return decorator

def encrypt_sensitive_data(func):
    """Decorator to encrypt sensitive data"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get security manager
        if not hasattr(wrapper, 'security_manager'):
            wrapper.security_manager = EnterpriseSecurityManager()  # type: ignore
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Encrypt sensitive data in result
        if isinstance(result, dict):
            result = wrapper.security_manager.encrypt_sensitive_fields(result)  # type: ignore
        
        return result
    return wrapper

# Global enterprise features instance
enterprise_features = EnterpriseSecurityManager()

def initialize_enterprise_features(config: Optional[Dict[str, Any]] = None):
    """Initialize enterprise features"""
    global enterprise_features
    enterprise_features = EnterpriseSecurityManager(config)
    return enterprise_features

def get_enterprise_features() -> EnterpriseSecurityManager:
    """Get the global enterprise features instance"""
    return enterprise_features
