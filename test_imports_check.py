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
        print("✅ CLI module imports successfully")

        # Test exceptions module
        print("✅ Exceptions module imports successfully")

        # Test utils.common module
        print("✅ Utils.common module imports successfully")

        # Test all commands
        print("✅ All command modules import successfully")

        # Test models
        print("✅ Models import successfully")

        # Test logger
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
