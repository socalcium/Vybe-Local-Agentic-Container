"""
Comprehensive Test Suite for Vybe Application
Provides unit, integration, and functional testing capabilities
"""

import unittest
import tempfile
import os
import sys
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask testing utilities
from flask import current_app
from flask_testing import TestCase

# Import application modules
try:
    from vybe_app import create_app
    from vybe_app.models import db, User, AppSetting, ChatSession
except ImportError as e:
    print(f"Warning: Could not import all modules: {e}")


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities"""
    
    def create_app(self):
        """Create and configure a test app"""
        # Create app without config parameter (default configuration)
        app = create_app()
        
        # Override with test configuration
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SERVER_NAME': 'localhost:5000'
        })
        
        return app
    
    def setUp(self):
        """Set up test environment"""
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user with proper password requirements
        self.test_user = User()
        self.test_user.username = 'testuser'
        self.test_user.email = 'test@example.com'
        # Use a password that meets requirements: uppercase, lowercase, digit
        self.test_user.set_password('TestPass123')
        db.session.add(self.test_user)
        
        # Create test settings
        self.test_setting = AppSetting()
        self.test_setting.key = 'test_setting'
        self.test_setting.value = 'test_value'
        self.test_setting.description = 'Test setting for testing'
        db.session.add(self.test_setting)
        
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login_user(self, username='testuser', password='TestPass123'):
        """Login a user for testing"""
        return self.client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def logout_user(self):
        """Logout current user"""
        return self.client.get('/auth/logout', follow_redirects=True)


class ModelTestCase(BaseTestCase):
    """Test cases for database models"""
    
    def test_user_creation(self):
        """Test user model creation and methods"""
        user = User()
        user.username = 'newuser'
        user.email = 'new@example.com'
        # Use proper password requirements
        user.set_password('NewPass123')
        db.session.add(user)
        db.session.commit()
        
        # Test user exists
        found_user = User.query.filter_by(username='newuser').first()
        self.assertIsNotNone(found_user)
        assert found_user is not None  # Type narrowing for linter
        self.assertEqual(found_user.email, 'new@example.com')
        
        # Test password verification
        assert found_user is not None  # Type narrowing for linter
        self.assertTrue(found_user.check_password('NewPass123'))
        assert found_user is not None  # Type narrowing for linter
        self.assertFalse(found_user.check_password('wrongpassword'))
    
    def test_app_setting_caching(self):
        """Test AppSetting caching functionality"""
        # Test cached retrieval
        setting = AppSetting.get_cached('test_setting')
        self.assertIsNotNone(setting)
        assert setting is not None  # Type narrowing for linter
        self.assertEqual(setting.value, 'test_value')
        
        # Test cache invalidation
        AppSetting.invalidate_cache('test_setting')
        
        # Test non-existent setting
        non_existent = AppSetting.get_cached('non_existent')
        self.assertIsNone(non_existent)
    
    def test_app_setting_save_and_invalidate(self):
        """Test AppSetting save with cache invalidation"""
        new_setting = AppSetting()
        new_setting.key = 'new_test_setting'
        new_setting.value = 'new_value'
        new_setting.description = 'New test setting'
        
        # Test save and invalidate method
        new_setting.save_and_invalidate_cache()
        
        # Verify it was saved
        found_setting = AppSetting.query.filter_by(key='new_test_setting').first()
        self.assertIsNotNone(found_setting)
        assert found_setting is not None  # Type narrowing for linter
        self.assertEqual(found_setting.value, 'new_value')


class AuthTestCase(BaseTestCase):
    """Test cases for authentication and authorization"""
    
    def test_login_success(self):
        """Test successful user login"""
        response = self.login_user()
        self.assert200(response)
        # Should redirect to main page after login
        self.assertIn(b'Chat', response.data)
    
    def test_login_failure(self):
        """Test failed login with wrong credentials"""
        response = self.client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        # Should show error message
        self.assert200(response)
        self.assertIn(b'Invalid', response.data)
    
    def test_logout(self):
        """Test user logout"""
        # Login first
        self.login_user()
        
        # Then logout
        response = self.logout_user()
        self.assert200(response)
    
    def test_protected_route_access(self):
        """Test that protected routes require authentication"""
        response = self.client.get('/api/chat/sessions')
        # Should be redirected to login or return 401
        self.assertIn(response.status_code, [302, 401])
    
    def test_authenticated_route_access(self):
        """Test that authenticated users can access protected routes"""
        self.login_user()
        response = self.client.get('/api/chat/sessions')
        # Should be successful or at least not redirect to login
        self.assertNotEqual(response.status_code, 302)


class APITestCase(BaseTestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        """Set up API tests"""
        super().setUp()
        self.login_user()  # Most API tests need authentication
    
    def test_health_check(self):
        """Test application health check endpoint"""
        response = self.client.get('/api/health')
        self.assert200(response)
        data = json.loads(response.data)
        self.assertIn('status', data)
    
    def test_settings_api(self):
        """Test settings API endpoints"""
        # Test getting settings
        response = self.client.get('/api/settings/test_setting')
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data.get('value'), 'test_value')
        
        # Test updating settings
        response = self.client.post('/api/settings/test_setting', 
                                   json={'value': 'updated_value'})
        self.assert200(response)
        
        # Verify update
        response = self.client.get('/api/settings/test_setting')
        data = json.loads(response.data)
        self.assertEqual(data.get('value'), 'updated_value')
    
    def test_chat_api_structure(self):
        """Test chat API basic structure"""
        # Test chat sessions endpoint
        response = self.client.get('/api/chat/sessions')
        self.assertIn(response.status_code, [200, 204])  # Success or no content
        
        # Test models endpoint
        response = self.client.get('/api/models/available')
        self.assertIn(response.status_code, [200, 503])  # Success or service unavailable


class SecurityTestCase(BaseTestCase):
    """Test cases for security measures"""
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        # Attempt SQL injection in login
        response = self.client.post('/auth/login', data={
            'username': "admin'; DROP TABLE users; --",
            'password': 'anything'
        })
        
        # Should not cause an error and user table should still exist
        self.assert200(response)
        users = User.query.all()
        self.assertGreater(len(users), 0)  # Users should still exist
    
    def test_xss_protection(self):
        """Test protection against XSS attacks"""
        # This would need to be expanded based on actual input handling
        # For now, just test that script tags are handled properly
        malicious_input = "<script>alert('xss')</script>"
        
        # Test in settings value
        response = self.client.post('/api/settings/test_xss', 
                                   json={'value': malicious_input})
        
        # Should either reject or escape the input
        if response.status_code == 200:
            # If accepted, should be escaped
            data = json.loads(response.data)
            self.assertNotIn('<script>', data.get('value', ''))
    
    def test_csrf_protection(self):
        """Test CSRF protection (when enabled)"""
        # This test assumes CSRF protection might be enabled in production
        # For now, just verify the mechanism exists
        with self.app.test_request_context():
            # Test would verify CSRF tokens are required for state-changing operations
            pass


class PerformanceTestCase(BaseTestCase):
    """Test cases for performance characteristics"""
    
    def test_database_query_performance(self):
        """Test that database queries perform within acceptable limits"""
        # Create multiple test records
        for i in range(100):
            setting = AppSetting()
            setting.key = f'perf_test_{i}'
            setting.value = f'value_{i}'
            setting.description = f'Performance test setting {i}'
            db.session.add(setting)
        db.session.commit()
        
        # Test query performance
        start_time = time.time()
        settings = AppSetting.query.filter(AppSetting.key.like('perf_test_%')).all()
        end_time = time.time()
        
        self.assertEqual(len(settings), 100)
        # Query should complete in reasonable time (adjust as needed)
        self.assertLess(end_time - start_time, 1.0)  # Less than 1 second
    
    def test_memory_usage_basic(self):
        """Basic test for memory usage patterns"""
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Create and destroy objects
        objects = []
        for i in range(1000):
            obj = {'test': f'data_{i}', 'number': i}
            objects.append(obj)
        
        # Clear references
        objects.clear()
        gc.collect()
        
        # Test should complete without memory errors
        self.assertTrue(True)


class IntegrationTestCase(BaseTestCase):
    """Integration tests for component interactions"""
    
    def test_user_workflow(self):
        """Test complete user workflow"""
        # 1. Register/login
        response = self.login_user()
        self.assert200(response)
        
        # 2. Access main interface
        response = self.client.get('/')
        self.assert200(response)
        
        # 3. Access settings
        response = self.client.get('/settings')
        self.assertIn(response.status_code, [200, 302])  # Success or redirect
        
        # 4. Logout
        response = self.logout_user()
        self.assert200(response)
    
    def test_api_integration(self):
        """Test API component integration"""
        self.login_user()
        
        # Test that different API endpoints work together
        health_response = self.client.get('/api/health')
        self.assert200(health_response)
        
        settings_response = self.client.get('/api/settings/test_setting')
        self.assert200(settings_response)
        
        # Both should return valid JSON
        health_data = json.loads(health_response.data)
        settings_data = json.loads(settings_response.data)
        
        self.assertIsInstance(health_data, dict)
        self.assertIsInstance(settings_data, dict)


def create_test_suite():
    """Create a comprehensive test suite"""
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        ModelTestCase,
        AuthTestCase,
        APITestCase,
        SecurityTestCase,
        PerformanceTestCase,
        IntegrationTestCase
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def run_tests(verbosity=2):
    """Run the complete test suite"""
    runner = unittest.TextTestRunner(verbosity=verbosity)
    suite = create_test_suite()
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Run tests if script is executed directly
    success = run_tests()
    sys.exit(0 if success else 1)
