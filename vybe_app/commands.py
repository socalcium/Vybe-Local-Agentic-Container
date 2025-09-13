"""
Commands module - handles CLI commands for Vybe AI Assistant.
Refactored to use modular structure for better maintainability.
"""

from .commands import register_user_commands, register_file_commands


def register_commands(app):
    """Register all CLI commands"""
    register_user_commands(app)
    register_file_commands(app)