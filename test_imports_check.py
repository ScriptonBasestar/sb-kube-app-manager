#!/usr/bin/env python3
"""
Simple test to verify that all imports are working correctly.
"""

import sys
import traceback

def test_imports():
    """Test all main module imports"""
    try:
        # Test main CLI module
        from sbkube.cli import main
        print("✅ CLI module imports successfully")
        
        # Test exceptions module
        from sbkube.exceptions import SbkubeError
        print("✅ Exceptions module imports successfully")
        
        # Test utils.common module
        from sbkube.utils.common import common_click_options
        print("✅ Utils.common module imports successfully")
        
        # Test all commands
        from sbkube.commands import (
            build, delete, deploy, doctor, fix, history, init, prepare, 
            profiles, run, state, template, upgrade, validate, version
        )
        print("✅ All command modules import successfully")
        
        # Test models
        from sbkube.models.config_model import AppInfoScheme
        print("✅ Models import successfully")
        
        # Test logger
        from sbkube.utils.logger import logger
        print("✅ Logger imports successfully")
        
        print("\n🎉 All imports are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)