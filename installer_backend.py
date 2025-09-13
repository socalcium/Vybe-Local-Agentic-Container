import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_app_base_path():
    """Gets the base path of the application."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe
        return Path(sys.executable).parent
    else:
        # Running as a script
        return Path(__file__).parent

def run_command(command, description):
    """Runs a command and logs its output."""
    logging.info(f"Starting: {description}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                logging.info(line.strip())
        process.wait()
        if process.returncode == 0:
            logging.info(f"Finished: {description}")
            return True
        else:
            logging.error(f"Error during: {description}. Return code: {process.returncode}")
            return False
    except Exception as e:
        logging.error(f"Exception during: {description}. Error: {e}")
        return False

def create_python_environment():
    """Creates a Python virtual environment."""
    app_path = get_app_base_path()
    venv_path = app_path / 'vybe-env-311-fixed'
    
    if venv_path.exists():
        logging.info("Python virtual environment already exists.")
        # Verify it's working
        venv_python = venv_path / 'Scripts' / 'python.exe'
        if venv_python.exists():
            logging.info("Virtual environment verification passed.")
            return True
        else:
            logging.warning("Virtual environment exists but python.exe missing. Recreating...")
            import shutil
            shutil.rmtree(venv_path)
    
    python_exe = sys.executable # Use the python that runs this script
    logging.info(f"Creating virtual environment using: {python_exe}")
    command = [python_exe, "-m", "venv", str(venv_path)]
    
    if run_command(command, "Creating Python virtual environment"):
        # Verify the creation was successful
        venv_python = venv_path / 'Scripts' / 'python.exe'
        if venv_python.exists():
            logging.info("Virtual environment created and verified successfully.")
            return True
        else:
            logging.error("Virtual environment creation reported success but python.exe not found.")
            return False
    else:
        return False

def install_dependencies():
    """Installs dependencies from requirements.txt into the venv."""
    app_path = get_app_base_path()
    venv_python = app_path / 'vybe-env-311-fixed' / 'Scripts' / 'python.exe'
    requirements_file = app_path / 'requirements.txt'

    if not venv_python.exists() or not requirements_file.exists():
        logging.error("Virtual environment or requirements.txt not found.")
        return False

    command = [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)]
    return run_command(command, "Installing Python dependencies")

def install_playwright():
    """Installs Playwright browser components."""
    app_path = get_app_base_path()
    venv_python = app_path / 'vybe-env-311-fixed' / 'Scripts' / 'python.exe'
    
    if not venv_python.exists():
        logging.error("Virtual environment not found.")
        return False
        
    command = [str(venv_python), "-m", "playwright", "install"]
    return run_command(command, "Installing Playwright browser components")

def main():
    """Main function to run the setup tasks."""
    try:
        logging.info("Starting Vybe first-time setup...")
        logging.info(f"Python executable: {sys.executable}")
        logging.info(f"Python version: {sys.version}")
        
        app_path = get_app_base_path()
        logging.info(f"Application path: {app_path}")
        
        # Create necessary directories
        directories = [
            app_path / 'instance',
            app_path / 'rag_data' / 'chroma_db',
            app_path / 'rag_data' / 'knowledge_base'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {directory}")
        
        # Setup environment file if it doesn't exist
        env_file = app_path / '.env'
        env_example = app_path / '.env.example'
        
        if not env_file.exists() and env_example.exists():
            import shutil
            shutil.copy2(env_example, env_file)
            logging.info("Created .env file from .env.example")
        
        if not create_python_environment():
            logging.error("Failed to create Python virtual environment")
            sys.exit(1)
            
        if not install_dependencies():
            logging.error("Failed to install Python dependencies")
            sys.exit(1)
            
        if not install_playwright():
            logging.warning("Failed to install Playwright browsers (non-critical)")
            # Don't exit for Playwright failure as it's not critical
            
        logging.info("Vybe first-time setup completed successfully.")
        # Create a flag file to indicate setup is complete
        flag_file = get_app_base_path() / 'instance' / 'setup_complete.flag'
        flag_file.touch()
        logging.info(f"Setup complete flag created: {flag_file}")
        
    except Exception as e:
        logging.error(f"Critical error during setup: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
