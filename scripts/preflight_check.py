#!/usr/bin/env python3
"""
Preflight checker for Vybe: verifies presence of a high-context (>= REQUIRED_MIN_CONTEXT_TOKENS) model
and optionally triggers a download of the default recommended high-context model.
"""
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from vybe_app import create_app
from vybe_app.core.model_sources_manager import get_model_sources_manager
from vybe_app.config import Config


def main(download_if_missing: bool = False) -> int:
    """Main preflight check with comprehensive error handling"""
    try:
        app = create_app()
        with app.app_context():
            try:
                hard_min = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
            except (AttributeError, ValueError) as e:
                print(f"[WARN] Could not read REQUIRED_MIN_CONTEXT_TOKENS: {e}")
                hard_min = 32768  # Safe fallback
                
            try:
                msm = get_model_sources_manager()
                candidates = msm.get_available_models(min_context=hard_min)
                downloaded = [m for m in candidates if m.get('downloaded')]
            except Exception as e:
                print(f"[WARN] Could not check available models: {e}")
                candidates = []
                downloaded = []
                
            if downloaded:
                print(f"[OK] High-context model present: {downloaded[0].get('filename')}")
                return 0
                
            print("[WARN] No high-context model found.")
            if not download_if_missing:
                if candidates:
                    print(f"Recommended: {candidates[0].get('filename')} (~{candidates[0].get('size_mb')} MB)\nURL: {candidates[0].get('download_url')}")
                return 1
                
            # Attempt download via FirstLaunchManager with comprehensive error handling
            try:
                from vybe_app.core.first_launch_manager import first_launch_manager
                print("[INFO] Attempting to download default high-context model...")
                ok = first_launch_manager.download_model(first_launch_manager.default_model)
                if ok:
                    print("[OK] Downloaded default high-context model.")
                    return 0
                else:
                    print("[ERR] Download failed - model may not be available or network issues.")
                    print("[HELP] Try running with internet connection or manually download models.")
                    return 2
            except ImportError as e:
                print(f"[ERR] Cannot import first_launch_manager: {e}")
                print("[HELP] Check if vybe_app.core.first_launch_manager module exists.")
                print("[HELP] Running in offline mode with fallback configuration.")
                return 3
            except AttributeError as e:
                print(f"[ERR] FirstLaunchManager missing required methods: {e}")
                print("[HELP] Module may be corrupted. Try reinstalling the application.")
                return 3
            except Exception as e:
                print(f"[ERR] Preflight download failed with unexpected error: {e}")
                print("[HELP] Check logs for more details or try manual model download.")
                print("[HELP] Application can still run in offline mode.")
                return 3
                
    except Exception as e:
        print(f"[CRITICAL] Preflight check failed to initialize: {e}")
        print("[HELP] Database or application context initialization failed.")
        print("[HELP] Try running the application repair tool or check file permissions.")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == '__main__':
    dl = False
    if len(sys.argv) > 1:
        dl = sys.argv[1].lower() in ('1','true','yes','download','--download')
    sys.exit(main(download_if_missing=dl))


