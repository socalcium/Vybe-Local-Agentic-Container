"""
Unit Tests for Backend Model System
Tests the new VRAM-tiered backend model configuration
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vybe_app.core.manager_model import ManagerModel
from vybe_app.core.model_sources_manager import ModelSourcesManager


class TestBackendModelSystem(unittest.TestCase):
    """Test the new backend model tier system"""
    
    def setUp(self):
        """Set up test environment"""
        self.manager = ManagerModel()
        self.sources = ModelSourcesManager(Path("test_models"))
    
    def test_available_orchestrator_models(self):
        """Test that backend models are properly configured"""
        models = self.manager.get_available_orchestrator_models()
        
        # Should have 4 tiers
        self.assertEqual(len(models), 4)
        
        # Check that all models have required fields
        for model in models:
            self.assertIn('name', model)
            self.assertIn('tier', model)
            self.assertIn('backend_vram_usage', model)
            self.assertIn('remaining_vram', model)
            self.assertIn('uncensored', model)
            self.assertIn('n_ctx', model)
            
        # Check tier progression
        tiers = [model['tier'] for model in models]
        self.assertEqual(tiers, [1, 2, 3, 4])
    
    def test_tier_1_8gb_model(self):
        """Test Tier 1 (8GB GPU) model configuration"""
        models = self.manager.get_available_orchestrator_models()
        tier_1 = models[0]
        
        self.assertEqual(tier_1['tier'], 1)
        self.assertEqual(tier_1['name'], 'dolphin-2.6-phi-2-2.7b')
        self.assertEqual(tier_1['backend_vram_usage'], '2.5GB')
        self.assertEqual(tier_1['remaining_vram'], '5.5GB')
        self.assertTrue(tier_1['uncensored'])
        self.assertEqual(tier_1['n_ctx'], 32768)
    
    def test_tier_2_10gb_model(self):
        """Test Tier 2 (10GB GPU) model configuration"""
        models = self.manager.get_available_orchestrator_models()
        tier_2 = models[1]
        
        self.assertEqual(tier_2['tier'], 2)
        self.assertEqual(tier_2['name'], 'dolphin-2.8-mistral-7b-v02')
        self.assertEqual(tier_2['backend_vram_usage'], '3.5GB')
        self.assertEqual(tier_2['remaining_vram'], '6.5GB')
        self.assertTrue(tier_2['uncensored'])
    
    def test_tier_3_16gb_model(self):
        """Test Tier 3 (16GB GPU) model configuration"""
        models = self.manager.get_available_orchestrator_models()
        tier_3 = models[2]
        
        self.assertEqual(tier_3['tier'], 3)
        self.assertEqual(tier_3['name'], 'hermes-2-pro-llama-3-8b')
        self.assertEqual(tier_3['backend_vram_usage'], '4.5GB')
        self.assertEqual(tier_3['remaining_vram'], '11.5GB')
        self.assertTrue(tier_3['uncensored'])
    
    def test_hardware_tier_calculation(self):
        """Test hardware tier calculation with VRAM detection"""
        # Test different tier calculations
        tier_8gb = self.manager._calculate_hardware_tier(8, 16 * (1024**3), 'nvidia')
        tier_16gb = self.manager._calculate_hardware_tier(8, 32 * (1024**3), 'nvidia')
        
        # Should return valid tier names (either VRAM-based or fallback)
        self.assertIsInstance(tier_8gb, str)
        self.assertIsInstance(tier_16gb, str)
        
        # If VRAM detection works, should get tier_X_Xgb format
        # If not, should get fallback format
        valid_tiers = ['tier_1_8gb', 'tier_2_10gb', 'tier_3_16gb', 'tier_4_24gb_plus',
                      'high_end_no_vram', 'mid_range_gpu', 'mid_range_cpu', 'budget_cpu', 'mobile']
        self.assertIn(tier_8gb, valid_tiers)
        self.assertIn(tier_16gb, valid_tiers)
    
    def test_model_sources_tier_system(self):
        """Test model sources manager with new tier system"""
        # Test getting backend-optimized models
        backend_model = self.sources.get_recommended_model(
            hardware_tier='tier_2_10gb', 
            uncensored_preferred=True, 
            backend_optimized=True
        )
        
        if backend_model:
            self.assertTrue(backend_model.get('backend_optimized', False))
            self.assertTrue(backend_model.get('uncensored', False))
    
    def test_concurrent_capacity_descriptions(self):
        """Test that concurrent capacity descriptions are meaningful"""
        models = self.manager.get_available_orchestrator_models()
        
        for model in models:
            capacity = model['concurrent_capacity']
            # Should mention frontend models and additional capabilities
            self.assertIn('Frontend:', capacity)
            
            # Higher tiers should support more concurrent operations
            if model['tier'] >= 3:
                self.assertTrue(
                    'SD XL' in capacity or 'image generation' in capacity,
                    f"Tier {model['tier']} should support image generation"
                )
    
    def test_all_models_have_large_context(self):
        """Test that all backend models have large context windows"""
        models = self.manager.get_available_orchestrator_models()
        
        for model in models:
            self.assertGreaterEqual(
                model['n_ctx'], 32768,
                f"Model {model['name']} should have at least 32K context"
            )
    
    def test_all_models_are_uncensored(self):
        """Test that all backend models are uncensored for maximum capability"""
        models = self.manager.get_available_orchestrator_models()
        
        for model in models:
            self.assertTrue(
                model['uncensored'],
                f"Backend model {model['name']} should be uncensored"
            )


if __name__ == '__main__':
    unittest.main()
