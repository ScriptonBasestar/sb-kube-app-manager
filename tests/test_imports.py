"""
Import tests to ensure all core dependencies are available.
"""

import pytest


class TestCoreImports:
    """Test that all core dependencies can be imported."""
    
    def test_sbkube_imports(self):
        """Test that sbkube core modules can be imported."""
        import sbkube
        import sbkube.cli
        import sbkube.commands
        import sbkube.models
        import sbkube.state
        import sbkube.utils
        
    def test_essential_dependencies(self):
        """Test that essential dependencies are available."""
        import sqlalchemy
        import click
        import yaml
        import git
        import jinja2
        import rich
        
    def test_test_dependencies(self):
        """Test that test dependencies are available."""
        import pytest
        import faker
        try:
            import testcontainers
        except ImportError:
            pytest.skip("testcontainers optional for minimal test environment")
            
        try:
            import kubernetes
        except ImportError:
            pytest.skip("kubernetes optional for minimal test environment")