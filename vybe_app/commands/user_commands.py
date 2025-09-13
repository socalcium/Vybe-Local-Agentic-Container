"""
User management CLI commands
"""

import click
from flask import current_app
from ..models import User, db
from ..logger import log_error, log_info


def register_user_commands(app):
    """Register user management commands"""
    
    @app.cli.command('create-user')
    def create_user():
        """Creates a new user."""
        try:
            username = click.prompt('Enter username')
            password = click.prompt('Enter password', hide_input=True, confirmation_prompt=True)
            
            with app.app_context():
                if User.query.filter_by(username=username).first():
                    click.echo(f"Error: User '{username}' already exists.")
                    return
                
                user = User()
                user.username = username
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                click.echo(f"User '{username}' created successfully.")
                log_info(f"User created: {username}")
                
        except Exception as e:
            log_error(f"Error creating user: {e}")
            click.echo(f"Error creating user: {e}")
    
    @app.cli.command('list-users')
    def list_users():
        """List all users."""
        try:
            with app.app_context():
                users = User.query.all()
                if not users:
                    click.echo("No users found.")
                    return
                
                click.echo("Users:")
                for user in users:
                    status = "Active" if user.is_active else "Inactive"
                    click.echo(f"  {user.username} ({user.email or 'No email'}) - {status}")
                    
        except Exception as e:
            log_error(f"Error listing users: {e}")
            click.echo(f"Error listing users: {e}")
    
    @app.cli.command('delete-user')
    @click.argument('username')
    def delete_user(username):
        """Delete a user."""
        try:
            with app.app_context():
                user = User.query.filter_by(username=username).first()
                if not user:
                    click.echo(f"Error: User '{username}' not found.")
                    return
                
                if click.confirm(f"Are you sure you want to delete user '{username}'?"):
                    db.session.delete(user)
                    db.session.commit()
                    click.echo(f"User '{username}' deleted successfully.")
                    log_info(f"User deleted: {username}")
                else:
                    click.echo("Operation cancelled.")
                    
        except Exception as e:
            log_error(f"Error deleting user: {e}")
            click.echo(f"Error deleting user: {e}")
    
    @app.cli.command('reset-password')
    @click.argument('username')
    def reset_password(username):
        """Reset a user's password."""
        try:
            with app.app_context():
                user = User.query.filter_by(username=username).first()
                if not user:
                    click.echo(f"Error: User '{username}' not found.")
                    return
                
                new_password = click.prompt('Enter new password', hide_input=True, confirmation_prompt=True)
                user.set_password(new_password)
                db.session.commit()
                
                click.echo(f"Password for user '{username}' reset successfully.")
                log_info(f"Password reset for user: {username}")
                
        except Exception as e:
            # Don't expose sensitive error details in logs
            log_error(f"Error resetting password for user: {username}")
            click.echo("Error resetting password. Please check the logs for details.")
    
    @app.cli.command('generate-api-key')
    @click.argument('username')
    def generate_api_key(username):
        """Generate a new API key for a user."""
        try:
            with app.app_context():
                user = User.query.filter_by(username=username).first()
                if not user:
                    click.echo(f"Error: User '{username}' not found.")
                    return
                
                api_key = user.generate_api_key()
                click.echo(f"New API key for user '{username}': {api_key}")
                click.echo("Store this key securely - it won't be shown again.")
                log_info(f"API key generated for user: {username}")
                
        except Exception as e:
            # Don't expose sensitive error details in logs
            log_error(f"Error generating API key for user: {username}")
            click.echo("Error generating API key. Please check the logs for details.")
    
    @app.cli.command('revoke-api-key')
    @click.argument('username')
    def revoke_api_key(username):
        """Revoke a user's API key."""
        try:
            with app.app_context():
                user = User.query.filter_by(username=username).first()
                if not user:
                    click.echo(f"Error: User '{username}' not found.")
                    return
                
                if not user.api_key:
                    click.echo(f"User '{username}' has no API key to revoke.")
                    return
                
                if click.confirm(f"Are you sure you want to revoke the API key for user '{username}'?"):
                    user.revoke_api_key()
                    click.echo(f"API key for user '{username}' revoked successfully.")
                    log_info(f"API key revoked for user: {username}")
                else:
                    click.echo("Operation cancelled.")
                    
        except Exception as e:
            # Don't expose sensitive error details in logs
            log_error(f"Error revoking API key for user: {username}")
            click.echo("Error revoking API key. Please check the logs for details.")
