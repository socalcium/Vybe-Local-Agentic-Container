"""
Basic Test Suite for Vybe Application
Simple tests that verify core functionality without full app setup
"""

import unittest
import sys
import os
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BasicFunctionalityTest(unittest.TestCase):
    """Test basic functionality without full app setup"""
    
    def test_import_models(self):
        """Test that core models can be imported"""
        try:
            from vybe_app.models import db, User, AppSetting
            self.assertTrue(True, "Models imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import models: {e}")
    
    def test_import_utils(self):
        """Test that utility modules can be imported"""
        try:
            from vybe_app.utils.resource_cleanup import ResourceCleanupManager
            from vybe_app.logger import log_info
            self.assertTrue(True, "Utils imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import utils: {e}")
    
    def test_cache_functionality(self):
        """Test AppSetting cache functionality independently"""
        try:
            from vybe_app.models import AppSetting
            
            # Test cache methods exist
            self.assertTrue(hasattr(AppSetting, 'get_cached'))
            self.assertTrue(hasattr(AppSetting, 'invalidate_cache'))
            self.assertTrue(hasattr(AppSetting, 'save_and_invalidate_cache'))
            
            # Test cache invalidation doesn't crash
            AppSetting.invalidate_cache()
            AppSetting.invalidate_cache('test_key')
            
            self.assertTrue(True, "Cache functionality works")
        except Exception as e:
            self.fail(f"Cache functionality failed: {e}")
    
    def test_security_functions(self):
        """Test that security functions exist and work"""
        try:
            from vybe_app.models import optimize_query_performance
            
            # Test function exists and can be called
            result = optimize_query_performance()
            self.assertIsInstance(result, bool)
            
            self.assertTrue(True, "Security functions work")
        except Exception as e:
            self.fail(f"Security functions failed: {e}")
    
    def test_accessibility_manager(self):
        """Test that accessibility features can be imported"""
        try:
            # Test that the accessibility file exists
            accessibility_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'vybe_app', 'static', 'js', 'accessibility.js'
            )
            self.assertTrue(os.path.exists(accessibility_path), "Accessibility script exists")
            
            # Test that it contains expected functionality
            with open(accessibility_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('AccessibilityManager', content)
                self.assertIn('announce', content)
                self.assertIn('trapFocus', content)
                
            self.assertTrue(True, "Accessibility features available")
        except Exception as e:
            self.fail(f"Accessibility features failed: {e}")
    
    def test_base_css_accessibility(self):
        """Test that base CSS includes accessibility features"""
        try:
            base_css_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'vybe_app', 'static', 'css', 'base.css'
            )
            self.assertTrue(os.path.exists(base_css_path), "Base CSS exists")
            
            with open(base_css_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('.sr-only', content)
                self.assertIn('prefers-reduced-motion', content)
                self.assertIn('prefers-contrast', content)
                self.assertIn('skip-link', content)
                
            self.assertTrue(True, "CSS accessibility features available")
        except Exception as e:
            self.fail(f"CSS accessibility features failed: {e}")
    
    def test_template_accessibility(self):
        """Test that templates include accessibility features"""
        try:
            index_template_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'vybe_app', 'templates', 'index.html'
            )
            self.assertTrue(os.path.exists(index_template_path), "Index template exists")
            
            with open(index_template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('aria-label', content)
                self.assertIn('role=', content)
                self.assertIn('skip-link', content)
                self.assertIn('sr-only', content)
                
            self.assertTrue(True, "Template accessibility features available")
        except Exception as e:
            self.fail(f"Template accessibility features failed: {e}")


class PerformanceTest(unittest.TestCase):
    """Test performance characteristics"""
    
    def test_file_operations(self):
        """Test basic file operations"""
        try:
            # Test temporary file creation
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("test content")
                temp_path = f.name
            
            # Test file reading
            with open(temp_path, 'r') as f:
                content = f.read()
                self.assertEqual(content, "test content")
            
            # Cleanup
            os.unlink(temp_path)
            
            self.assertTrue(True, "File operations work")
        except Exception as e:
            self.fail(f"File operations failed: {e}")
    
    def test_memory_basic(self):
        """Test basic memory operations"""
        try:
            import gc
            
            # Create some objects
            test_objects = []
            for i in range(1000):
                test_objects.append({'id': i, 'data': f'test_{i}'})
            
            # Verify objects exist
            self.assertEqual(len(test_objects), 1000)
            
            # Clear and garbage collect
            test_objects.clear()
            gc.collect()
            
            self.assertTrue(True, "Memory operations work")
        except Exception as e:
            self.fail(f"Memory operations failed: {e}")


def run_basic_tests():
    """Run basic tests without full app setup"""
    print("Running Basic Vybe Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [BasicFunctionalityTest, PerformanceTest]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Basic Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")
    print(f"{'='*50}")
    
    # Print details for failures/errors
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_basic_tests()
    sys.exit(0 if success else 1)
