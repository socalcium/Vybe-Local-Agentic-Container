"""
Data Initialization Module
Provides default data and configurations for testing and demo purposes.
"""

import os
import json
from datetime import datetime
from ..logger import log_info, log_error
from ..models import db, AppSetting, SystemPrompt


def initialize_default_data():
    """Initialize the application with default data for testing"""
    try:
        # Use database transaction to ensure atomicity
        with db.session.begin():
            # Check if already initialized to prevent duplicate initialization
            init_marker = AppSetting.query.filter_by(key='_data_initialized').first()
            if init_marker:
                log_info("Default data already initialized, skipping...")
                return True
            
            log_info("Starting default data initialization...")
            
            # Initialize core data with proper transaction handling
            _init_default_settings()
            db.session.flush()  # Ensure settings are committed before continuing
            
            # Initialize default system prompts
            _init_default_system_prompts()
            db.session.flush()  # Ensure prompts are committed before continuing
            
            # Initialize default RAG data
            _init_default_rag_data()
            db.session.flush()  # Ensure RAG data is committed before continuing
            
            # Initialize agent memory system
            _init_agent_memory_system()
            db.session.flush()  # Ensure agent memory is committed before continuing
            
            # Mark initialization as complete
            init_marker = AppSetting()
            init_marker.key = '_data_initialized'
            init_marker.value = 'true'
            init_marker.description = 'Internal flag indicating default data initialization is complete'
            db.session.add(init_marker)
            db.session.flush()
            
        log_info("Default data initialization completed successfully")
        return True
        
    except Exception as e:
        log_error(f"Error initializing default data: {str(e)}")
        # Rollback will be automatic due to transaction context
        return False


def _init_default_settings():
    """Initialize default application settings"""
    try:
        default_settings = [
            {
                'key': 'theme_mode',
                'value': 'system',
                'description': 'Application theme mode (light, dark, system)'
            },
            {
                'key': 'default_model',
                'value': 'llama3.2:3b',
                'description': 'Default chat model'
            },
            {
                'key': 'max_tokens',
                'value': '2048',
                'description': 'Maximum tokens for responses'
            },
            {
                'key': 'temperature',
                'value': '0.7',
                'description': 'Model temperature setting'
            },
            {
                'key': 'workspace_path',
                'value': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'workspace'),
                'description': 'Default workspace directory'
            },
            {
                'key': 'rag_enabled',
                'value': 'true',
                'description': 'Enable RAG functionality'
            },
            {
                'key': 'web_search_enabled',
                'value': 'true',
                'description': 'Enable web search functionality'
            }
        ]
        
        for setting_data in default_settings:
            existing = AppSetting.query.filter_by(key=setting_data['key']).first()
            if not existing:
                setting = AppSetting()
                setting.key = setting_data['key']
                setting.value = setting_data['value']
                setting.description = setting_data['description']
                db.session.add(setting)
                log_info(f"Added default setting: {setting_data['key']} = {setting_data['value']}")
        
        db.session.commit()
        log_info("Default settings initialized successfully")
        
    except Exception as e:
        log_error(f"Error initializing default settings: {str(e)}")
        db.session.rollback()
        raise


def _init_default_system_prompts():
    """Initialize default system prompts"""
    try:
        default_prompts = [
            {
                'name': 'Default Assistant',
                'description': 'Standard helpful AI assistant prompt',
                'category': 'General',
                'content': 'You are a helpful, harmless, and honest AI assistant. Provide clear, accurate, and useful responses to user questions. Be concise but thorough when needed.'
            },
            {
                'name': 'Code Assistant',
                'description': 'Programming and development focused assistant',
                'category': 'Development',
                'content': 'You are an expert programming assistant. Help users with coding problems, debugging, code review, and software development best practices. Provide clear explanations and working code examples.'
            },
            {
                'name': 'Research Assistant',
                'description': 'Research and analysis focused assistant',
                'category': 'Research',
                'content': 'You are a research assistant skilled in finding, analyzing, and synthesizing information. Help users with research questions, provide well-sourced answers, and suggest relevant resources.'
            },
            {
                'name': 'Creative Writer',
                'description': 'Creative writing and content creation assistant',
                'category': 'Creative',
                'content': 'You are a creative writing assistant. Help users with storytelling, content creation, editing, and creative expression. Be imaginative while maintaining quality and coherence.'
            },
            {
                'name': 'Technical Writer',
                'description': 'Technical documentation and explanation assistant',
                'category': 'Technical',
                'content': 'You are a technical writing specialist. Help users create clear technical documentation, explain complex concepts simply, and improve technical communication.'
            }
        ]
    
        for prompt_data in default_prompts:
            existing = SystemPrompt.query.filter_by(name=prompt_data['name']).first()
            if not existing:
                prompt = SystemPrompt()
                prompt.name = prompt_data['name']
                prompt.description = prompt_data['description']
                prompt.category = prompt_data['category']
                prompt.content = prompt_data['content']
                prompt.created_at = datetime.utcnow()
                db.session.add(prompt)
                log_info(f"Added default system prompt: {prompt_data['name']}")
        
        db.session.commit()
        log_info("Default system prompts initialized successfully")
        
    except Exception as e:
        log_error(f"Error initializing default system prompts: {str(e)}")
        db.session.rollback()
        raise


def _init_default_rag_data():
    """Initialize default RAG data and sample documents"""
    try:
        # Create default RAG directories
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rag_data_path = os.path.join(app_root, 'rag_data')
        knowledge_base_path = os.path.join(rag_data_path, 'knowledge_base')
        
        os.makedirs(knowledge_base_path, exist_ok=True)
        
        # Create sample knowledge base files
        sample_docs = [
            {
                'filename': 'vybe_introduction.md',
                'title': 'Introduction to Vybe AI Assistant',
                'content': '''# Vybe AI Assistant

Vybe is a powerful AI assistant application built with Flask and modern web technologies. It provides:

## Key Features

- **Intelligent Chat**: Engage with various AI models through a clean, intuitive interface
- **RAG (Retrieval-Augmented Generation)**: Upload documents and web content to enhance AI responses
- **Web Search Integration**: Access real-time information from the web
- **Model Management**: Easy switching between different AI models
- **Theme Customization**: Light, dark, and system theme options
- **Mobile Responsive**: Works seamlessly across devices

## Getting Started

1. **Chat**: Start conversations with the AI using the main chat interface
2. **Upload Documents**: Use the RAG Manager to add your own knowledge base
3. **Customize Settings**: Adjust themes, models, and preferences in Settings
4. **Explore Features**: Try web search and different system prompts

Vybe makes AI interaction simple and powerful for both beginners and advanced users.
'''
            },
            {
                'filename': 'rag_system_guide.md',
                'title': 'RAG System User Guide',
                'content': '''# RAG System Guide

The Retrieval-Augmented Generation (RAG) system allows you to enhance AI responses with your own documents and knowledge.

## How RAG Works

1. **Document Upload**: Add text files, PDFs, or web content
2. **Automatic Processing**: Documents are chunked and indexed
3. **Intelligent Retrieval**: Relevant content is found based on your questions
4. **Enhanced Responses**: AI uses your documents to provide better answers

## Supported Content Types

- Text files (.txt, .md)
- PDF documents
- Web pages (via URL)
- Direct text input

## Best Practices

- Use descriptive filenames
- Organize content by topic
- Keep documents focused and relevant
- Regular review and updates

## Collection Management

- Create separate collections for different topics
- Use meaningful collection names
- Monitor document counts and status
- Remove outdated content regularly

The RAG system makes your AI assistant truly personalized with your own knowledge base.
'''
            },
            {
                'filename': 'troubleshooting.md',
                'title': 'Vybe Troubleshooting Guide',
                'content': '''# Troubleshooting Guide

Common issues and solutions for Vybe AI Assistant.

## Connection Issues

### LLM Backend Not Running
- **Problem**: "Model not available" or connection errors
- **Solution**: Check if llama-cpp-python backend is running (port 11435)

### ChromaDB Errors
- **Problem**: RAG functionality not working
- **Solution**: Check ChromaDB installation and permissions

## Performance Issues

### Slow Responses
- Try smaller models (e.g., llama3.2:3b instead of larger variants)
- Reduce max tokens in settings
- Close unused browser tabs

### High Memory Usage
- Use quantized models
- Limit concurrent requests
- Restart application if needed

## UI Issues

### Theme Not Loading
- Clear browser cache
- Check theme setting in Settings page
- Try switching themes

### Mobile Display Problems
- Update browser to latest version
- Clear browser data
- Check viewport settings

## Getting Help

1. Check application logs in the user data directory logs folder
2. Verify all dependencies are installed
3. Restart the application
4. Check system requirements

For persistent issues, check the application logs for detailed error messages.
'''
            }
        ]
        
        for doc in sample_docs:
            file_path = os.path.join(knowledge_base_path, doc['filename'])
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(doc['content'])
                log_info(f"Created sample document: {doc['filename']}")
        
        # Create README for the knowledge base
        readme_path = os.path.join(knowledge_base_path, 'README.md')
        if not os.path.exists(readme_path):
            readme_content = '''# Vybe Knowledge Base

This directory contains sample documents for the RAG system. You can:

1. Add your own documents here
2. Use the RAG Manager web interface to upload files
3. Load web content directly through the interface

## File Organization

- Keep files organized by topic
- Use descriptive filenames
- Supported formats: .txt, .md, .pdf
- Documents will be automatically processed when uploaded

## Getting Started

Use the RAG Manager in the web interface to:
- Upload new documents
- Manage collections
- View processed content
- Test retrieval functionality

Happy learning with Vybe!
'''
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            log_info("Created knowledge base README")
        
    except Exception as e:
        log_error(f"Error initializing RAG data: {str(e)}")


def check_initialization_status():
    """Check if default data has been initialized"""
    try:
        # Check if basic settings exist
        theme_setting = AppSetting.query.filter_by(key='theme_mode').first()
        
        # Check if system prompts exist
        prompts_count = SystemPrompt.query.count()
        
        # Check if knowledge base exists
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        knowledge_base_path = os.path.join(app_root, 'rag_data', 'knowledge_base')
        kb_exists = os.path.exists(knowledge_base_path)
        
        return {
            'settings_initialized': theme_setting is not None,
            'prompts_initialized': prompts_count > 0,
            'knowledge_base_initialized': kb_exists,
            'fully_initialized': theme_setting is not None and prompts_count > 0 and kb_exists
        }
        
    except Exception as e:
        log_error(f"Error checking initialization status: {str(e)}")
        return {
            'settings_initialized': False,
            'prompts_initialized': False,
            'knowledge_base_initialized': False,
            'fully_initialized': False
        }


def _init_agent_memory_system():
    """Initialize the agent memory system with ChromaDB collection"""
    try:
        from ..rag.vector_db import initialize_vector_db, ensure_agent_memory_collection
        from ..config import Config
        
        log_info("Initializing agent memory system...")
        
        # Initialize ChromaDB client
        db_path = Config.RAG_VECTOR_DB_PATH
        chroma_client = initialize_vector_db(db_path)
        
        if chroma_client:
            # Ensure agent memory collection exists
            try:
                if ensure_agent_memory_collection():
                    log_info("✅ Agent memory system initialized successfully")
                else:
                    log_error("❌ Failed to initialize agent memory collection")
            except Exception as e:
                log_error(f"❌ Failed to initialize agent memory collection: {e}")
        else:
            log_error("❌ Failed to initialize ChromaDB client for agent memory")
            
    except Exception as e:
        log_error(f"Error initializing agent memory system: {str(e)}")


def get_sample_chat_prompts():
    """Get sample prompts for testing the chat functionality"""
    return [
        "Using the RAG system, what are the key features of Vybe?",
        "Search the web for the latest news on Llama 3.2",
        "List the files in my workspace",
        "Help me understand how RAG collections work and how to use them effectively",
        "What's the difference between querying specific collections vs all collections?",
        "Create a new text file with a summary of today's AI news",
        "Search for recent developments in vector databases and save the findings",
        "What file management capabilities do you have available?",
        "How can I organize my knowledge base with multiple RAG collections?",
        "Search for Python best practices and save them to a reference file"
    ]

def get_default_sample_prompts():
    """Alias used by API layer; returns the same sample prompts."""
    return get_sample_chat_prompts()