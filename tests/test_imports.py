"""Import tests to ensure all core dependencies are available.
"""

import pytest


class TestCoreImports:
    """Test that all core dependencies can be imported."""

    def test_sbkube_imports(self):
        """Test that sbkube core modules can be imported."""

    def test_essential_dependencies(self):
        """Test that essential dependencies are available."""

    def test_test_dependencies(self):
        """Test that test dependencies are available."""
        try:
            import testcontainers  # noqa: F401
        except ImportError:
            pytest.skip("testcontainers optional for minimal test environment")

        try:
            import kubernetes  # noqa: F401
        except ImportError:
            pytest.skip("kubernetes optional for minimal test environment")
