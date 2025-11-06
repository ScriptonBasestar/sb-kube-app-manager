"""Import tests to ensure all core dependencies are available."""


class TestCoreImports:
    """Test that all core dependencies can be imported."""

    def test_sbkube_imports(self) -> None:
        """Test that sbkube core modules can be imported."""
        # Core modules
        import sbkube.cli  # noqa: F401
        import sbkube.commands.deploy  # noqa: F401
        import sbkube.models.config_model  # noqa: F401
        import sbkube.utils.common  # noqa: F401

    def test_essential_dependencies(self) -> None:
        """Test that essential dependencies are available."""
        import click  # noqa: F401
        import pydantic  # noqa: F401
        import rich  # noqa: F401
        import yaml  # noqa: F401
