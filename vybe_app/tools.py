from datetime import datetime
from typing import Dict, Any
import logging

# Import controller classes for lazy instantiation
from vybe_app.core.stable_diffusion_controller import stable_diffusion_controller
from vybe_app.core.edge_tts_controller import EdgeTTSController
from vybe_app.core.audio_io import transcribe_audio
from vybe_app.core.video_generator import VideoGeneratorController

logger = logging.getLogger(__name__)

def get_current_datetime():
    """Returns the current date and time in a human-readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def web_search(query):
    """Search the web for information using Brave Search API.
    
    Args:
        query (str): The search query to perform
        
    Returns:
        str: Formatted search results as a string
    """
    from flask import current_app
    from .core.search_tools import search_brave, search_web_fallback
    from .config import Config
    
    try:
        # Check if Brave API key is configured
        if hasattr(Config, 'BRAVE_SEARCH_API_KEY') and Config.BRAVE_SEARCH_API_KEY:
            results = search_brave(query)
        else:
            results = search_web_fallback(query)
        
        if not results:
            return "No search results found for the query."
        
        # Format results for the AI
        formatted_results = []
        for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
            title = result.get('title', 'No Title')
            snippet = result.get('snippet', 'No description available')
            link = result.get('link', '#')
            
            formatted_results.append(f"{i}. **{title}**\n   {snippet}\n   Source: {link}")
        
        search_summary = f"Web search results for '{query}':\n\n" + "\n\n".join(formatted_results)
        
        # Add note about configuration if using fallback
        if not (hasattr(Config, 'BRAVE_SEARCH_API_KEY') and Config.BRAVE_SEARCH_API_KEY):
            search_summary += "\n\n*Note: Real web search is not configured. Configure BRAVE_SEARCH_API_KEY for live web search.*"
        
        return search_summary
        
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def save_to_scratchpad(content):
    """Save information to AI's persistent scratchpad/working memory.
    
    Args:
        content (str): The content to save to scratchpad
        
    Returns:
        str: Success message confirming the save
    """
    from flask import current_app
    from .models import db, AIScratchpad
    
    try:
        # Get or create the global scratchpad entry
        scratchpad = AIScratchpad.query.filter_by(session_id='global_scratchpad').first()
        
        if scratchpad:
            scratchpad.content = content
            scratchpad.last_updated = datetime.utcnow()
        else:
            scratchpad = AIScratchpad(
                session_id='global_scratchpad',
                content=content
            )
            db.session.add(scratchpad)
        
        db.session.commit()
        return f"Successfully saved to scratchpad: {content[:50]}..." if len(content) > 50 else f"Successfully saved to scratchpad: {content}"
        
    except Exception as e:
        db.session.rollback()
        return f"Error saving to scratchpad: {str(e)}"

def read_scratchpad():
    """Read information from AI's persistent scratchpad/working memory.
    
    Returns:
        str: The content from scratchpad or empty message
    """
    from flask import current_app
    from .models import AIScratchpad
    
    try:
        scratchpad = AIScratchpad.query.filter_by(session_id='global_scratchpad').first()
        
        if scratchpad and scratchpad.content:
            return scratchpad.content
        else:
            return "Scratchpad is empty."
            
    except Exception as e:
        return f"Error reading scratchpad: {str(e)}"

def ai_query_rag_collections(query, collection_names=None):
    """Query specific RAG collections or all available collections based on context.
    
    Args:
        query (str): The natural language query to ask the RAG system
        collection_names (list[str], optional): List of specific collection names to query.
                                              If None or empty, queries all collections.
    
    Returns:
        str: Combined relevant chunks of text as a single string
    """
    from flask import current_app
    from .rag.vector_db import retrieve_relevant_chunks
    
    try:
        # Get the ChromaDB client from the app instance
        chroma_client = getattr(current_app, 'chroma_client', None)
        if not chroma_client:
            return "Error: RAG system is not initialized."
        
        # Get available collections
        try:
            available_collections = [col.name for col in chroma_client.list_collections()]
        except Exception as e:
            return f"Error: Unable to list RAG collections: {str(e)}"
        
        if not available_collections:
            return "No RAG collections are currently available."
        
        # Determine which collections to query
        if collection_names:
            # Filter to only valid collections
            target_collections = [name for name in collection_names if name in available_collections]
            if not target_collections:
                return f"Error: None of the specified collections {collection_names} exist. Available collections: {available_collections}"
        else:
            # Query all collections
            target_collections = available_collections
        
        # Query each target collection
        all_results = []
        for collection_name in target_collections:
            try:
                results = retrieve_relevant_chunks(chroma_client, collection_name, query, n_results=3)
                if results:
                    # Add explicit collection context to each result
                    collection_results = [f"[From collection '{collection_name}']: {result}" for result in results]
                    all_results.extend(collection_results)
            except Exception as e:
                print(f"Error querying collection {collection_name}: {e}")
                continue
        
        if not all_results:
            queried_collections = ", ".join(target_collections)
            return f"No relevant information found in the queried collections: {queried_collections}"
        
        # Combine and return results
        combined_results = "\n\n".join(all_results)
        collection_info = f"Searched {len(target_collections)} collection(s): {', '.join(target_collections)}"
        
        return f"{collection_info}\n\n{combined_results}"
        
    except Exception as e:
        return f"Error querying RAG collections: {str(e)}"


def ai_generate_image(prompt: str, 
                     negative_prompt: str = "", 
                     steps: int = 20,
                     cfg_scale: float = 7.0,
                     width: int = 512,
                     height: int = 512,
                     sampler_name: str = "Euler a",
                     seed: int = -1) -> str:
    """Generate an image using Stable Diffusion.
    
    Args:
        prompt (str): The positive prompt describing what to generate
        negative_prompt (str, optional): What to avoid in the image
        steps (int, optional): Number of sampling steps (default: 20)
        cfg_scale (float, optional): Classifier Free Guidance scale (default: 7.0)
        width (int, optional): Image width in pixels (default: 512)
        height (int, optional): Image height in pixels (default: 512)  
        sampler_name (str, optional): Sampling method (default: "Euler a")
        seed (int, optional): Random seed for reproducibility (default: -1 for random)
        
    Returns:
        str: Success message with path to generated image or error message
    """
    from flask import current_app
    
    try:
        # Get the Stable Diffusion controller from the app
        sd_controller = stable_diffusion_controller
        if not sd_controller:
            return "Error: Stable Diffusion controller is not available."
        
        # Check if SD is installed and running, start if needed
        if not sd_controller.is_running():
            if not sd_controller.start():
                return "Error: Failed to start Stable Diffusion WebUI. Please check the logs and ensure it's properly installed."
        
        # Generate the image
        image_path = sd_controller.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            sampler_name=sampler_name,
            seed=seed
        )
        
        if image_path:
            return f"✅ Image generated successfully! Saved to: {image_path}\n\nPrompt: {prompt}"
        else:
            return "❌ Failed to generate image. Please try again."
            
    except Exception as e:
        return f"❌ Error generating image: {str(e)}"


def ai_speak_text(text: str, voice: str = 'en-US-AriaNeural', rate: str = '+0%', pitch: str = '+0Hz') -> str:
    """Convert text to speech using Edge TTS.
    
    Args:
        text: The text to convert to speech
        voice: Voice name to use (default: 'en-US-AriaNeural')
        rate: Speech rate (default: '+0%')
        pitch: Speech pitch (default: '+0Hz')
        
    Returns:
        str: Status message about the speech synthesis
    """
    try:
        from flask import current_app
        
        if not text.strip():
            return "❌ Error: Text cannot be empty."
        
        # Get EdgeTTS controller from current app
        tts_controller = EdgeTTSController()
        
        if not tts_controller or not tts_controller.available:
            return "❌ Error: Edge TTS is not available."
        
        # Generate speech
        audio_file = tts_controller.synthesize_speech(text, voice, rate, pitch)
        
        if audio_file:
            text_preview = text[:100] + ('...' if len(text) > 100 else '')
            return f"🔊 Speech generated successfully!\n\nText: \"{text_preview}\"\nVoice: {voice}\nAudio file: {audio_file}\nCharacters spoken: {len(text)}"
        else:
            return f"❌ Failed to generate speech using Edge TTS"
            
    except Exception as e:
        return f"❌ Error in text-to-speech: {str(e)}"


def ai_transcribe_audio(file_path: str, language: str = 'en') -> str:
    """Transcribe audio file to text using whisper.cpp.
    
    Args:
        file_path: Path to the audio file to transcribe
        language: Language code for transcription (default: 'en')
        
    Returns:
        str: The transcribed text or error message
    """
    try:
        from .core.audio_io import transcribe_audio
        from flask import current_app
        from pathlib import Path
        
        # Validate file path
        audio_path = Path(file_path)
        if not audio_path.exists():
            return f"❌ Error: Audio file not found: {file_path}"
        
        # Check file extension
        valid_extensions = {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}
        if audio_path.suffix.lower() not in valid_extensions:
            return f"❌ Error: Unsupported audio format. Supported formats: {', '.join(valid_extensions)}"
        
        # Perform transcription using the imported function
        result = transcribe_audio(str(audio_path), None)
        
        if result['success']:
            text = result.get('text', '').strip()
            if text:
                return f"🎤 Transcription completed successfully!\n\nFile: {file_path}\nTranscribed text: \"{text}\"\n\nLanguage: {result.get('language', 'unknown')}"
            else:
                return f"⚠️ Transcription completed but no text was detected in the audio file: {file_path}"
        else:
            error = result.get('error', 'Unknown error')
            return f"❌ Failed to transcribe audio: {error}"
            
    except Exception as e:
        return f"❌ Error in audio transcription: {str(e)}"

# Home Assistant AI Tools
from .core.home_assistant_controller import HomeAssistantController

def list_home_assistant_entities():
    controller = HomeAssistantController()
    entities = controller.get_entities()
    if entities is None:
        return "Home Assistant is not configured or unreachable."
    return [e["entity_id"] for e in entities]

def get_entity_state(entity_id: str):
    controller = HomeAssistantController()
    state = controller.get_entity_state(entity_id)
    if state is None:
        return f"Entity {entity_id} not found or Home Assistant not configured."
    return state.get("state", "Unknown")

def call_ha_service(entity_id: str, service: str, data: dict):
    controller = HomeAssistantController()
    domain = entity_id.split(".")[0]
    result = controller.call_service(domain, service, data)
    if result is None:
        return f"Failed to call service {service} for {entity_id}."
    return result


def ai_store_agent_memory(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store information in long-term agent memory
    
    Args:
        parameters: Dict containing:
            - content: The memory content to store
            - memory_id: Unique identifier for this memory
            - metadata: Optional metadata (agent_id, task_type, success, etc.)
    
    Returns:
        Dict with storage result
    """
    try:
        from .rag.vector_db import store_agent_memory
        from .config import Config
        import chromadb
        
        content = parameters.get('content')
        memory_id = parameters.get('memory_id')
        metadata = parameters.get('metadata', {})
        
        if not content or not memory_id:
            return {"success": False, "error": "Content and memory_id are required"}
        
        # Initialize ChromaDB client
        db_path = Config.RAG_VECTOR_DB_PATH
        client = chromadb.PersistentClient(path=db_path)
        
        # Store the memory
        success = store_agent_memory(memory_id, content, metadata)
        
        if success:
            return {
                "success": True,
                "message": f"Memory stored successfully: {memory_id}",
                "memory_id": memory_id
            }
        else:
            return {"success": False, "error": "Failed to store memory"}
            
    except Exception as e:
        logger.error(f"Failed to store agent memory: {e}")
        return {"success": False, "error": str(e)}


def ai_retrieve_agent_memories(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant memories from long-term agent memory
    
    Args:
        parameters: Dict containing:
            - query: Query to search for relevant memories
            - agent_id: Optional filter by specific agent
            - memory_type: Optional filter by memory type
            - n_results: Number of results to return (default: 5)
    
    Returns:
        Dict with retrieved memories
    """
    try:
        from .rag.vector_db import retrieve_agent_memories
        from .config import Config
        import chromadb
        
        query = parameters.get('query')
        if not query:
            return {"success": False, "error": "Query is required"}
        
        agent_id = parameters.get('agent_id')
        memory_type = parameters.get('memory_type')
        n_results = parameters.get('n_results', 5)
        
        # Initialize ChromaDB client
        db_path = Config.RAG_VECTOR_DB_PATH
        client = chromadb.PersistentClient(path=db_path)
        
        # Retrieve memories
        memories = retrieve_agent_memories(query, agent_id, memory_type, n_results)
        
        return {
            "success": True,
            "memories": memories,
            "count": len(memories),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve agent memories: {e}")
        return {"success": False, "error": str(e)}


def ai_get_memory_stats(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get statistics about agent memory system
    
    Args:
        parameters: Dict containing:
            - agent_id: Optional filter by specific agent
    
    Returns:
        Dict with memory statistics
    """
    try:
        from .rag.vector_db import get_agent_memory_stats
        from .config import Config
        import chromadb
        
        agent_id = parameters.get('agent_id')
        
        # Initialize ChromaDB client
        db_path = Config.RAG_VECTOR_DB_PATH
        client = chromadb.PersistentClient(path=db_path)
        
        # Get stats
        stats = get_agent_memory_stats(client, agent_id)
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {"success": False, "error": str(e)}


def ai_execute_python(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute Python code in a secure environment
    
    Args:
        parameters: Dict containing:
            - code: Python code to execute
            - session_id: Optional session ID for persistent workspace
            - context: Optional context variables to pass to the code
            - security: Optional security settings
    
    Returns:
        Dict with execution results
    """
    try:
        from .core.code_interpreter import get_code_interpreter, SecuritySettings
        
        code = parameters.get('code')
        if not code:
            return {"success": False, "error": "No code provided"}
        
        session_id = parameters.get('session_id')
        context = parameters.get('context', {})
        security_config = parameters.get('security', {})
        
        # Create security settings
        security_settings = SecuritySettings(
            allow_file_io=security_config.get('allow_file_io', True),
            allow_network=security_config.get('allow_network', False),
            allow_subprocess=security_config.get('allow_subprocess', False),
            max_execution_time=security_config.get('max_execution_time', 30.0),
            max_memory_mb=security_config.get('max_memory_mb', 512)
        )
        
        # Get interpreter
        interpreter = get_code_interpreter(session_id, security_settings)
        
        # Execute code
        result = interpreter.execute_code(code, context)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "plots": result.plots,
            "files_created": result.files_created,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "workspace_dir": interpreter.workspace_dir,
            "session_id": interpreter.session_id
        }
        
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return {"success": False, "error": str(e)}


def ai_generate_video(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a video from a text prompt using ComfyUI video generation.
    
    Args:
        parameters: Dict containing:
            - prompt: Description of the video to generate
        
    Returns:
        Dict: Result with success status and message
    """
    from flask import current_app
    
    try:
        prompt = parameters.get('prompt')
        if not prompt:
            return {"success": False, "error": "No prompt provided"}
            
        video_controller = VideoGeneratorController()
        job_manager = getattr(current_app, 'job_manager', None)
        
        if not video_controller:
            return {"success": False, "error": "Video generation service is not available. Please ensure ComfyUI is properly configured."}
        
        if not job_manager:
            return {"success": False, "error": "Job manager is not available. Cannot queue video generation task."}
        
        # Ensure the video service is running
        if not video_controller.is_running():
            success, message = video_controller.start()
            if not success:
                return {"success": False, "error": f"Failed to start video generation service: {message}"}
        
        # Queue the video generation job
        success, message = video_controller.generate_video(prompt, job_manager)
        
        if success:
            return {
                "success": True, 
                "message": f"✅ Video generation started: {message}",
                "detail": "🎬 Your video will be available in the Video Portal gallery once processing is complete."
            }
        else:
            return {"success": False, "error": f"❌ Failed to start video generation: {message}"}
            
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        return {"success": False, "error": f"Error generating video: {str(e)}"}


def ai_write_file(filename: str, content: str) -> dict:
    """
    A placeholder for a tool that writes content to a file.
    In the future, this will handle file operations and return status.
    """
    print(f"--- AI is writing to {filename} ---")
    # In a real implementation, you would write the content to the file.
    # For now, we'll just simulate success.
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"File {filename} written successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
