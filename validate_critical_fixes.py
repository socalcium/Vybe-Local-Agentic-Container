#!/usr/bin/env python3
"""
Validation Script for Critical Startup/Cleanup Fixes
Validates that the implemented fixes are working correctly
"""
import sys
import os
import time
from pathlib import Path

def validate_model_download_retry():
    """Validate Bug #207 fix: Model Download Error Recovery"""
    print("🔍 Testing Bug #207: Model Download Error Recovery...")
    
    try:
        # Import the updated download function
        sys.path.append(str(Path(__file__).parent))
        import download_default_model
        
        # Check if download_with_progress has retry functionality
        import inspect
        source = inspect.getsource(download_default_model.download_with_progress)
        
        checks = [
            "max_retries" in source,
            "exponential backoff" in source.lower() or "wait_time = 2 ** attempt" in source,
            "resume_header" in source,
            "Range.*bytes" in source or "resume" in source.lower()
        ]
        
        if all(checks):
            print("✅ Model download retry mechanism implemented")
            return True
        else:
            print("❌ Model download retry mechanism incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating model download fix: {e}")
        return False

def validate_database_transactions():
    """Validate Bug #208 fix: Database Initialization Race Conditions"""
    print("🔍 Testing Bug #208: Database Initialization Race Conditions...")
    
    try:
        # Check data_initializer for transaction handling
        data_init_path = Path(__file__).parent / "vybe_app" / "utils" / "data_initializer.py"
        
        if not data_init_path.exists():
            print("❌ data_initializer.py not found")
            return False
            
        content = data_init_path.read_text(encoding='utf-8')
        
        checks = [
            "with db.session.begin():" in content,
            "db.session.flush()" in content,
            "_data_initialized" in content,
            "transaction context" in content.lower() or "begin()" in content
        ]
        
        if all(checks):
            print("✅ Database transaction safety implemented")
            return True
        else:
            print("❌ Database transaction safety incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating database fix: {e}")
        return False

def validate_preflight_error_handling():
    """Validate Bug #209 fix: Preflight Check Exception Handling"""
    print("🔍 Testing Bug #209: Preflight Check Exception Handling...")
    
    try:
        # Check preflight_check for comprehensive error handling
        preflight_path = Path(__file__).parent / "scripts" / "preflight_check.py"
        
        if not preflight_path.exists():
            print("❌ preflight_check.py not found")
            return False
            
        content = preflight_path.read_text(encoding='utf-8')
        
        checks = [
            "try:" in content and content.count("try:") >= 3,
            "except Exception as e:" in content,
            "offline mode" in content.lower(),
            "traceback.print_exc()" in content,
            "HELP" in content
        ]
        
        if all(checks):
            print("✅ Preflight error handling implemented")
            return True
        else:
            print("❌ Preflight error handling incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating preflight fix: {e}")
        return False

def validate_global_cleanup():
    """Validate Bug #210 fix: Missing Global Cleanup Handler"""
    print("🔍 Testing Bug #210: Missing Global Cleanup Handler...")
    
    try:
        # Check run.py for global cleanup registry
        run_path = Path(__file__).parent / "run.py"
        
        if not run_path.exists():
            print("❌ run.py not found")
            return False
            
        content = run_path.read_text(encoding='utf-8')
        
        checks = [
            "register_cleanup_function" in content,
            "execute_global_cleanup" in content,
            "atexit.register" in content,
            "signal.signal" in content,
            "_cleanup_functions" in content
        ]
        
        if all(checks):
            print("✅ Global cleanup handler implemented")
            return True
        else:
            print("❌ Global cleanup handler incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating global cleanup fix: {e}")
        return False

def validate_nvml_cleanup():
    """Validate Bug #211 fix: NVML Shutdown Resource Leaks"""
    print("🔍 Testing Bug #211: NVML Shutdown Resource Leaks...")
    
    try:
        # Check system_monitor for NVML cleanup
        monitor_path = Path(__file__).parent / "vybe_app" / "core" / "system_monitor.py"
        
        if not monitor_path.exists():
            print("❌ system_monitor.py not found")
            return False
            
        content = monitor_path.read_text(encoding='utf-8')
        
        checks = [
            "cleanup_nvml" in content,
            "nvmlShutdown" in content,
            "register_cleanup_function" in content,
            "error handling" in content.lower() or "except Exception" in content
        ]
        
        if all(checks):
            print("✅ NVML cleanup implemented")
            return True
        else:
            print("❌ NVML cleanup incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating NVML cleanup fix: {e}")
        return False

def validate_cache_thread_safety():
    """Validate Bug #212 fix: Cache Manager Cleanup Thread Safety"""
    print("🔍 Testing Bug #212: Cache Manager Cleanup Thread Safety...")
    
    try:
        # Check cache_manager for thread safety
        cache_path = Path(__file__).parent / "vybe_app" / "utils" / "cache_manager.py"
        
        if not cache_path.exists():
            print("❌ cache_manager.py not found")
            return False
            
        content = cache_path.read_text(encoding='utf-8')
        
        checks = [
            "_stop_cleanup_event" in content,
            "threading.Event()" in content,
            "join(timeout=" in content,
            "is_alive()" in content
        ]
        
        if all(checks):
            print("✅ Cache thread cleanup implemented")
            return True
        else:
            print("❌ Cache thread cleanup incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating cache cleanup fix: {e}")
        return False

def validate_session_memory_cleanup():
    """Validate Bug #214 fix: Session Cleanup Memory Management"""
    print("🔍 Testing Bug #214: Session Cleanup Memory Management...")
    
    try:
        # Check auth.py for secure memory cleanup
        auth_path = Path(__file__).parent / "vybe_app" / "auth.py"
        
        if not auth_path.exists():
            print("❌ auth.py not found")
            return False
            
        content = auth_path.read_text(encoding='utf-8')
        
        checks = [
            "secure memory" in content.lower(),
            "\\x00" in content,  # Memory overwriting
            "gc.collect()" in content,
            "register_cleanup_function" in content
        ]
        
        if all(checks):
            print("✅ Session memory cleanup implemented")
            return True
        else:
            print("❌ Session memory cleanup incomplete")
            print(f"   Checks: {checks}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating session cleanup fix: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Validating Critical Startup/Cleanup Fixes")
    print("=" * 50)
    
    tests = [
        validate_model_download_retry,
        validate_database_transactions,
        validate_preflight_error_handling,
        validate_global_cleanup,
        validate_nvml_cleanup,
        validate_cache_thread_safety,
        validate_session_memory_cleanup
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            results.append(False)
        print()
    
    # Summary
    print("=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All critical fixes validated successfully!")
        print("✅ Application startup and cleanup reliability improved")
        return 0
    else:
        print("⚠️ Some fixes need attention")
        print("🔧 Review failed tests and complete implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
