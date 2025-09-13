#!/usr/bin/env python3
"""
Test script to validate imports are working correctly
"""

try:
    print("Testing Plugin API imports...")
    from vybe_app.core.plugin_manager import PluginType, PluginStatus
    print("✅ PluginType and PluginStatus imported successfully")
    print(f"   PluginType values: {[t.value for t in PluginType]}")
    print(f"   PluginStatus values: {[s.value for s in PluginStatus]}")
except Exception as e:
    print(f"❌ Plugin imports failed: {e}")

try:
    print("\nTesting RAG API imports...")
    from vybe_app.utils.data_initializer import get_sample_chat_prompts
    print("✅ get_sample_chat_prompts imported successfully")
except Exception as e:
    print(f"❌ RAG imports failed: {e}")

try:
    print("\nTesting Settings API imports...")
    from vybe_app.core.home_assistant_controller import HomeAssistantController
    from vybe_app.core.setup_manager import setup_manager
    print("✅ HomeAssistantController and setup_manager imported successfully")
except Exception as e:
    print(f"❌ Settings imports failed: {e}")

try:
    print("\nTesting RPG API imports...")
    from vybe_app.core.rpg_engine import rpg_engine
    print("✅ rpg_engine imported successfully")
except Exception as e:
    print(f"❌ RPG imports failed: {e}")

print("\nImport validation complete!")
