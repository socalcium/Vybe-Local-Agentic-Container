#!/usr/bin/env python3
"""
Database Fix Script for Vybe
Fixes common database schema issues that prevent the app from starting
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_database():
    """Fix database schema issues"""
    print("🔧 Fixing Vybe database schema...")
    
    try:
        # Import the app and run migrations
        from vybe_app import create_app
        from vybe_app.models import db
        
        app = create_app()
        
        with app.app_context():
            print("📊 Running database migrations...")
            from vybe_app.utils.migrate_db import DatabaseMigrator
            migrator = DatabaseMigrator(app)
            
            # Run migrations
            success = migrator.run_all_migrations()
            
            if success:
                print("✅ Database migrations completed successfully!")
                
                # Verify the schema
                print("🔍 Verifying database schema...")
                migrator.verify_migrations()
                
                print("\n🎉 Database fix completed! You can now start Vybe.")
                return True
            else:
                print("❌ Database migrations failed!")
                return False
                
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        import traceback
        traceback.print_exc()
        return False

def backup_database():
    """Create a backup of the current database"""
    try:
        from vybe_app.config import Config
        user_data_dir = Config.get_user_data_dir()
        db_path = user_data_dir / "site.db"
        
        if db_path.exists():
            import shutil
            from datetime import datetime
            
            # Ensure backup directory exists
            backup_dir = user_data_dir / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_filename = f'site.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            backup_path = backup_dir / backup_filename
            
            # Verify source file is readable
            if not os.access(db_path, os.R_OK):
                print(f"⚠️  Cannot read database file: {db_path}")
                return False
            
            # Check available disk space (at least 2x database size)
            db_size = db_path.stat().st_size
            disk_usage = shutil.disk_usage(backup_dir)
            available_space = disk_usage.free
            
            if available_space < (db_size * 2):
                print(f"⚠️  Insufficient disk space for backup. Need {db_size * 2} bytes, have {available_space}")
                return False
            
            # Create backup with error handling
            try:
                shutil.copy2(db_path, backup_path)
                
                # Verify backup was created successfully
                if not backup_path.exists():
                    print(f"❌ Backup file was not created: {backup_path}")
                    return False
                
                # Verify backup size matches original
                backup_size = backup_path.stat().st_size
                if backup_size != db_size:
                    print(f"⚠️  Backup size mismatch. Original: {db_size}, Backup: {backup_size}")
                    # Don't fail, but warn user
                
                print(f"💾 Database backed up to: {backup_path}")
                return True
                
            except PermissionError as e:
                print(f"❌ Permission denied creating backup: {e}")
                return False
            except OSError as e:
                print(f"❌ File system error during backup: {e}")
                return False
            except Exception as e:
                print(f"❌ Unexpected error during backup: {e}")
                return False
        else:
            print("ℹ️  No existing database found to backup")
            return True
            
    except ImportError as e:
        print(f"❌ Could not import required modules for backup: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Could not backup database: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Vybe Database Fix Tool")
    print("=" * 40)
    
    # Create backup first
    print("\n1. Creating database backup...")
    backup_database()
    
    # Fix the database
    print("\n2. Fixing database schema...")
    success = fix_database()
    
    if success:
        print("\n🎉 Database fix completed successfully!")
        print("   You can now run: python run.py")
        return 0
    else:
        print("\n❌ Database fix failed!")
        print("   Please check the error messages above.")
        return 1

if __name__ == '__main__':
    exit(main())
