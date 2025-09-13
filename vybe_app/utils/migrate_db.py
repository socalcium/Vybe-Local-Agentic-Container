"""
Enhanced Database Migration Utility for Vybe Application
Handles database schema updates and migrations with version tracking and rollback support
"""

import os
import sys
from datetime import datetime
from flask import current_app
from sqlalchemy import text, inspect, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Optional, Tuple
import json

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vybe_app import create_app
from vybe_app.models import db


class DatabaseMigrator:
    """Enhanced database migration handler with version tracking and rollback support"""
    
    # Migration definitions with version tracking
    MIGRATIONS = [
        {
            'version': '1.0.0',
            'name': 'create_migration_tracking',
            'description': 'Create migration tracking table',
            'up_sql': '''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(20) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    rollback_sql TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_migrations_version ON schema_migrations(version);
                CREATE INDEX IF NOT EXISTS idx_migrations_applied_at ON schema_migrations(applied_at);
            ''',
            'down_sql': 'DROP TABLE IF EXISTS schema_migrations;'
        },
        {
            'version': '1.1.0',
            'name': 'create_feedback_table',
            'description': 'Create feedback table with comprehensive fields',
            'up_sql': '''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    feedback_type VARCHAR(50) NOT NULL DEFAULT 'general',
                    subject VARCHAR(256),
                    message TEXT NOT NULL,
                    rating INTEGER,
                    status VARCHAR(50) DEFAULT 'pending',
                    priority VARCHAR(20) DEFAULT 'medium',
                    category VARCHAR(100),
                    metadata_json TEXT,
                    browser_info TEXT,
                    session_id VARCHAR(128),
                    ip_address VARCHAR(45),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by INTEGER,
                    reviewed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES user(id),
                    FOREIGN KEY (reviewed_by) REFERENCES user(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at);
                CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
                CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
                CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
            ''',
            'down_sql': 'DROP TABLE IF EXISTS feedback;'
        },
        {
            'version': '1.2.0',
            'name': 'enhance_app_setting_table',
            'description': 'Add missing columns to app_setting table',
            'up_sql': '''
                -- Add description column if it doesn't exist
                ALTER TABLE app_setting ADD COLUMN description VARCHAR(200);
                
                -- Add created_at column if it doesn't exist  
                ALTER TABLE app_setting ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;
                
                -- Add updated_at column if it doesn't exist
                ALTER TABLE app_setting ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_appsetting_key_updated ON app_setting(key, updated_at);
                CREATE INDEX IF NOT EXISTS idx_appsetting_created_updated ON app_setting(created_at, updated_at);
            ''',
            'down_sql': '''
                ALTER TABLE app_setting DROP COLUMN IF EXISTS description;
                ALTER TABLE app_setting DROP COLUMN IF EXISTS created_at;
                ALTER TABLE app_setting DROP COLUMN IF EXISTS updated_at;
                DROP INDEX IF EXISTS idx_appsetting_key_updated;
                DROP INDEX IF EXISTS idx_appsetting_created_updated;
            '''
        },
        {
            'version': '1.3.0',
            'name': 'enhance_system_prompt_table',
            'description': 'Add missing columns to system_prompt table',
            'up_sql': '''
                -- Add is_default column if it doesn't exist
                ALTER TABLE system_prompt ADD COLUMN is_default BOOLEAN DEFAULT FALSE;
                
                -- Add updated_at column if it doesn't exist
                ALTER TABLE system_prompt ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_sysprompt_default ON system_prompt(is_default);
                CREATE INDEX IF NOT EXISTS idx_sysprompt_updated ON system_prompt(updated_at);
            ''',
            'down_sql': '''
                ALTER TABLE system_prompt DROP COLUMN IF EXISTS is_default;
                ALTER TABLE system_prompt DROP COLUMN IF EXISTS updated_at;
                DROP INDEX IF EXISTS idx_sysprompt_default;
                DROP INDEX IF EXISTS idx_sysprompt_updated;
            '''
        }
    ]
    
    def __init__(self, app=None):
        self.app = app or create_app()
        
    def check_table_exists(self, table_name):
        """Check if a table exists in the database"""
        with self.app.app_context():
            inspector = inspect(db.engine)
            if inspector is not None:
                return table_name in inspector.get_table_names()
            return False
    
    def check_column_exists(self, table_name, column_name):
        """Check if a column exists in a table"""
        with self.app.app_context():
            try:
                inspector = inspect(db.engine)
                if inspector is not None:
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    return column_name in columns
                return False
            except Exception:
                return False

    def ensure_migration_tracking_table(self):
        """Ensure the migration tracking table exists"""
        with self.app.app_context():
            try:
                # Check if migration table exists
                if not self.check_table_exists('schema_migrations'):
                    print("📊 Creating migration tracking table...")
                    migration = self.MIGRATIONS[0]  # First migration creates the tracking table
                    db.session.execute(text(migration['up_sql']))  # type: ignore
                    db.session.commit()
                    print("✅ Migration tracking table created")
                return True
            except Exception as e:
                print(f"❌ Failed to create migration tracking table: {str(e)}")
                db.session.rollback()
                return False

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        with self.app.app_context():
            try:
                if not self.check_table_exists('schema_migrations'):
                    return []
                
                result = db.session.execute(text("SELECT version FROM schema_migrations ORDER BY applied_at"))  # type: ignore
                return [row[0] for row in result.fetchall()]
            except Exception:
                return []

    def record_migration(self, migration: Dict):
        """Record a migration as applied"""
        with self.app.app_context():
            try:
                db.session.execute(text('''
                    INSERT INTO schema_migrations (version, name, description, rollback_sql)
                    VALUES (:version, :name, :description, :rollback_sql)
                '''), {  # type: ignore
                    'version': migration['version'],
                    'name': migration['name'],
                    'description': migration['description'],
                    'rollback_sql': migration['down_sql']
                })
                db.session.commit()
                return True
            except Exception as e:
                print(f"❌ Failed to record migration {migration['version']}: {str(e)}")
                db.session.rollback()
                return False

    def apply_migration(self, migration: Dict):
        """Apply a single migration with proper transaction handling"""
        with self.app.app_context():
            try:
                print(f"🔄 Applying migration {migration['version']}: {migration['name']}")
                
                # Execute migration SQL
                for statement in migration['up_sql'].split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            db.session.execute(text(statement))  # type: ignore
                        except Exception as e:
                            # Some ALTER TABLE statements might fail if column already exists
                            # This is expected behavior for some migrations
                            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                                print(f"   ℹ️  Skipping: {str(e)}")
                                continue
                            else:
                                raise e
                
                # Record migration as applied (only for tracking table migration)
                if migration['name'] != 'create_migration_tracking':
                    self.record_migration(migration)
                
                db.session.commit()
                print(f"✅ Migration {migration['version']} completed successfully")
                return True
                
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"❌ Migration {migration['version']} failed: {str(e)}")
                return False
            except Exception as e:
                db.session.rollback()
                print(f"❌ Migration {migration['version']} failed with unexpected error: {str(e)}")
                return False

    def rollback_migration(self, version: str):
        """Rollback a specific migration"""
        with self.app.app_context():
            try:
                # Get rollback SQL from migration tracking table
                result = db.session.execute(text('''
                    SELECT rollback_sql FROM schema_migrations WHERE version = :version
                '''), {'version': version})  # type: ignore
                
                row = result.fetchone()
                if not row:
                    print(f"❌ Migration {version} not found in tracking table")
                    return False
                
                rollback_sql = row[0]
                if not rollback_sql:
                    print(f"❌ No rollback SQL available for migration {version}")
                    return False
                
                print(f"🔄 Rolling back migration {version}")
                
                # Execute rollback SQL
                for statement in rollback_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        db.session.execute(text(statement))  # type: ignore
                
                # Remove migration record
                db.session.execute(text('''
                    DELETE FROM schema_migrations WHERE version = :version
                '''), {'version': version})  # type: ignore
                
                db.session.commit()
                print(f"✅ Migration {version} rolled back successfully")
                return True
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Rollback of migration {version} failed: {str(e)}")
                return False

    def run_all_migrations(self):
        """Run all pending migrations"""
        with self.app.app_context():
            try:
                # Ensure migration tracking table exists first
                if not self.ensure_migration_tracking_table():
                    return False
                
                # Get applied migrations
                applied_versions = self.get_applied_migrations()
                
                # Run pending migrations
                success = True
                for migration in self.MIGRATIONS:
                    if migration['version'] not in applied_versions:
                        if not self.apply_migration(migration):
                            success = False
                            break
                    else:
                        print(f"ℹ️  Migration {migration['version']} already applied, skipping")
                
                if success:
                    print("🎉 All migrations completed successfully!")
                else:
                    print("❌ Migration process stopped due to errors")
                
                return success
                
            except Exception as e:
                print(f"❌ Migration process failed: {str(e)}")
                return False

    def get_migration_status(self) -> Dict:
        """Get current migration status"""
        with self.app.app_context():
            try:
                applied_versions = self.get_applied_migrations()
                all_versions = [m['version'] for m in self.MIGRATIONS]
                
                pending_migrations = []
                applied_migrations = []
                
                for migration in self.MIGRATIONS:
                    if migration['version'] in applied_versions:
                        applied_migrations.append({
                            'version': migration['version'],
                            'name': migration['name'],
                            'description': migration['description']
                        })
                    else:
                        pending_migrations.append({
                            'version': migration['version'],
                            'name': migration['name'],
                            'description': migration['description']
                        })
                
                return {
                    'total_migrations': len(self.MIGRATIONS),
                    'applied_count': len(applied_migrations),
                    'pending_count': len(pending_migrations),
                    'applied_migrations': applied_migrations,
                    'pending_migrations': pending_migrations,
                    'current_version': applied_versions[-1] if applied_versions else None
                }
                
            except Exception as e:
                return {'error': str(e)}
    
    def run_migration(self, migration_name, migration_sql):
        """Run a single migration with proper transaction handling"""
        with self.app.app_context():
            try:
                # Start transaction
                db.session.execute(text(migration_sql))  # type: ignore
                db.session.commit()
                print(f"✅ Migration '{migration_name}' completed successfully")
                return True
            except SQLAlchemyError as e:
                # Rollback on any error
                db.session.rollback()
                print(f"❌ Migration '{migration_name}' failed: {str(e)}")
                return False
            except Exception as e:
                # Rollback on any unexpected error
                db.session.rollback()
                print(f"❌ Migration '{migration_name}' failed with unexpected error: {str(e)}")
                return False
    
    def migrate_feedback_table(self):
        """Create the feedback table if it doesn't exist"""
        if self.check_table_exists('feedback'):
            print("ℹ️  Feedback table already exists, skipping migration")
            return True
        
        print("📊 Creating feedback table...")
        
        migration_sql = """
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feedback_type VARCHAR(50) NOT NULL DEFAULT 'general',
            subject VARCHAR(256),
            message TEXT NOT NULL,
            rating INTEGER,
            status VARCHAR(50) DEFAULT 'pending',
            priority VARCHAR(20) DEFAULT 'medium',
            category VARCHAR(100),
            metadata_json TEXT,
            browser_info TEXT,
            session_id VARCHAR(128),
            ip_address VARCHAR(45),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_by INTEGER,
            reviewed_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (reviewed_by) REFERENCES user(id)
        );
        
        CREATE INDEX idx_feedback_created_at ON feedback(created_at);
        CREATE INDEX idx_feedback_status ON feedback(status);
        CREATE INDEX idx_feedback_type ON feedback(feedback_type);
        """
        
        return self.run_migration("create_feedback_table", migration_sql)
    
    def migrate_config_enhancements(self):
        """Add security-related configuration columns if needed"""
        config_table_exists = self.check_table_exists('configuration')
        
        if not config_table_exists:
            print("ℹ️  Configuration table doesn't exist yet, will be created by SQLAlchemy")
            return True
        
        # Check for new columns that might be needed
        security_columns = [
            ('is_sensitive', 'BOOLEAN DEFAULT FALSE'),
            ('requires_restart', 'BOOLEAN DEFAULT FALSE'),
            ('data_type', 'VARCHAR(50) DEFAULT "string"'),
            ('category', 'VARCHAR(100) DEFAULT "general"'),
            ('updated_by', 'INTEGER'),
            ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for column_name, column_def in security_columns:
            if not self.check_column_exists('configuration', column_name):
                migration_sql = f"ALTER TABLE configuration ADD COLUMN {column_name} {column_def};"
                self.run_migration(f"add_config_{column_name}", migration_sql)
        
        return True
    
    def migrate_user_enhancements(self):
        """Add security enhancements to user table"""
        if not self.check_table_exists('user'):
            print("ℹ️  User table doesn't exist yet, will be created by SQLAlchemy")
            return True
        
        # Security columns for user table
        security_columns = [
            ('last_password_change', 'DATETIME'),
            ('failed_login_attempts', 'INTEGER DEFAULT 0'),
            ('locked_until', 'DATETIME'),
            ('password_reset_token', 'VARCHAR(128)'),
            ('password_reset_expires', 'DATETIME'),
            ('email_verified', 'BOOLEAN DEFAULT FALSE'),
            ('email_verification_token', 'VARCHAR(128)')
        ]
        
        for column_name, column_def in security_columns:
            if not self.check_column_exists('user', column_name):
                migration_sql = f"ALTER TABLE user ADD COLUMN {column_name} {column_def};"
                self.run_migration(f"add_user_{column_name}", migration_sql)
        
        return True
    
    def migrate_app_setting_table(self):
        """Add missing columns to app_setting table"""
        if not self.check_table_exists('app_setting'):
            print("ℹ️  AppSetting table doesn't exist yet, will be created by SQLAlchemy")
            return True
        
        # Check for missing description column
        if not self.check_column_exists('app_setting', 'description'):
            print("📊 Adding description column to app_setting table...")
            migration_sql = "ALTER TABLE app_setting ADD COLUMN description VARCHAR(200);"
            self.run_migration("add_app_setting_description", migration_sql)
        
        # Check for missing created_at column
        if not self.check_column_exists('app_setting', 'created_at'):
            print("📊 Adding created_at column to app_setting table...")
            migration_sql = "ALTER TABLE app_setting ADD COLUMN created_at DATETIME;"
            self.run_migration("add_app_setting_created_at", migration_sql)
        
        # Check for missing updated_at column
        if not self.check_column_exists('app_setting', 'updated_at'):
            print("📊 Adding updated_at column to app_setting table...")
            migration_sql = "ALTER TABLE app_setting ADD COLUMN updated_at DATETIME;"
            self.run_migration("add_app_setting_updated_at", migration_sql)
        
        print("ℹ️  AppSetting table migration completed")
        return True
    
    def migrate_system_prompt_table(self):
        """Add missing columns to system_prompt table"""
        if not self.check_table_exists('system_prompt'):
            print("ℹ️  SystemPrompt table doesn't exist yet, will be created by SQLAlchemy")
            return True
        
        # Check for missing is_default column
        if not self.check_column_exists('system_prompt', 'is_default'):
            print("📊 Adding is_default column to system_prompt table...")
            migration_sql = "ALTER TABLE system_prompt ADD COLUMN is_default BOOLEAN DEFAULT FALSE;"
            self.run_migration("add_system_prompt_is_default", migration_sql)
        
        # Check for missing updated_at column
        if not self.check_column_exists('system_prompt', 'updated_at'):
            print("📊 Adding updated_at column to system_prompt table...")
            migration_sql = "ALTER TABLE system_prompt ADD COLUMN updated_at DATETIME;"
            self.run_migration("add_system_prompt_updated_at", migration_sql)
        
        print("ℹ️  SystemPrompt table migration completed")
        return True

    def backup_database(self):
        """Create a backup of the database before migrations"""
        if not self.app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite:'):
            print("⚠️  Database backup only supported for SQLite databases")
            return False
        
        try:
            import shutil
            db_path = self.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if not os.path.exists(db_path):
                print("ℹ️  Database file doesn't exist yet, skipping backup")
                return True
            
            backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_path)
            print(f"💾 Database backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Database backup failed: {str(e)}")
            return False
    
    def verify_migrations(self):
        """Verify that all required tables and columns exist"""
        print("🔍 Verifying database schema...")
        
        required_tables = {
            'user': ['id', 'username', 'email', 'password_hash', 'created_at'],
            'feedback': ['id', 'user_id', 'message', 'status', 'created_at'],
            'message': ['id', 'user_message', 'ai_response', 'timestamp'],
            'chat_session': ['id', 'title', 'timestamp', 'messages_json'],
            'system_prompt': ['id', 'name', 'content', 'created_at']
        }
        
        all_good = True
        
        for table_name, required_columns in required_tables.items():
            if not self.check_table_exists(table_name):
                print(f"❌ Missing table: {table_name}")
                all_good = False
                continue
            
            for column_name in required_columns:
                if not self.check_column_exists(table_name, column_name):
                    print(f"❌ Missing column: {table_name}.{column_name}")
                    all_good = False
        
        if all_good:
            print("✅ Database schema verification passed!")
        else:
            print("❌ Database schema verification failed!")
        
        return all_good


def main():
    """Main migration script"""
    print("🚀 Vybe Database Migration Tool")
    print("=" * 40)
    
    migrator = DatabaseMigrator()
    
    # Create backup
    print("\n1. Creating database backup...")
    migrator.backup_database()
    
    # Run migrations
    print("\n2. Running migrations...")
    success = migrator.run_all_migrations()
    
    # Verify schema
    print("\n3. Verifying database schema...")
    migrator.verify_migrations()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("   You can now start the Vybe application.")
    else:
        print("\n⚠️  Migration completed with errors.")
        print("   Please check the error messages above.")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
