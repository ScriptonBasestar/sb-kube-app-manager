"""
Unit tests for OutputManager.
"""

from io import StringIO
from unittest.mock import patch

import pytest

from sbkube.utils.output_manager import OutputManager


class TestOutputManager:
    """Tests for OutputManager class."""

    def test_init_human_mode(self):
        """Test OutputManager initialization in human mode."""
        manager = OutputManager(format_type="human")
        assert manager.format_type == "human"
        assert not manager.console.quiet
        assert manager.events == []
        assert not manager._finalized

    def test_init_llm_mode(self):
        """Test OutputManager initialization in LLM mode."""
        manager = OutputManager(format_type="llm")
        assert manager.format_type == "llm"
        assert manager.console.quiet
        assert manager.events == []
        assert not manager._finalized

    def test_strip_markup(self):
        """Test Rich markup removal."""
        # Test simple markup
        assert OutputManager._strip_markup("[bold]Hello[/bold]") == "Hello"
        assert OutputManager._strip_markup("[red]Error[/red]") == "Error"

        # Test complex composite markup (with spaces)
        assert (
            OutputManager._strip_markup("[bold cyan]━━━ Title ━━━[/bold cyan]")
            == "━━━ Title ━━━"
        )
        assert (
            OutputManager._strip_markup("[dim red]Critical Error[/dim red]")
            == "Critical Error"
        )

        # Test warnings
        assert (
            OutputManager._strip_markup("[yellow]Warning: test[/yellow]")
            == "Warning: test"
        )

        # Test markup with uppercase and numbers
        assert OutputManager._strip_markup("[RGB(255,0,0)]Red Text[/RGB(255,0,0)]") == "Red Text"

        # Test hex colors
        assert OutputManager._strip_markup("[#FF0000]Red[/#FF0000]") == "Red"

        # Test mixed content
        assert (
            OutputManager._strip_markup("[bold]Start[/bold] middle [cyan]end[/cyan]")
            == "Start middle end"
        )

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_human_mode(self, mock_stdout):
        """Test print() in human mode."""
        manager = OutputManager(format_type="human")
        manager.print("Test message", level="info")

        # In human mode, events should be empty (not collected)
        assert len(manager.events) == 0

    def test_print_llm_mode(self):
        """Test print() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print("Test message", level="info", extra="data")

        # In LLM mode, events should be collected
        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "message"
        assert manager.events[0]["level"] == "info"
        assert manager.events[0]["message"] == "Test message"
        assert manager.events[0]["extra"] == "data"

    def test_print_section_human_mode(self):
        """Test print_section() in human mode."""
        manager = OutputManager(format_type="human")
        manager.print_section("Test Section", meta="info")

        # Events should be empty in human mode
        assert len(manager.events) == 0

    def test_print_section_llm_mode(self):
        """Test print_section() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print_section("Test Section", meta="info")

        # Events should be collected
        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "section"
        assert manager.events[0]["title"] == "Test Section"
        assert manager.events[0]["meta"] == "info"

    def test_print_error_human_mode(self):
        """Test print_error() in human mode."""
        manager = OutputManager(format_type="human")
        manager.print_error("Error occurred", error="Details")

        assert len(manager.events) == 0

    def test_print_error_llm_mode(self):
        """Test print_error() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print_error("Error occurred", error="Details", code=500)

        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "error"
        assert manager.events[0]["level"] == "error"
        assert manager.events[0]["message"] == "Error occurred"
        assert manager.events[0]["error"] == "Details"
        assert manager.events[0]["code"] == 500

    def test_print_warning(self):
        """Test print_warning() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print_warning("Warning message", severity="high")

        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "warning"
        assert manager.events[0]["level"] == "warning"
        assert manager.events[0]["message"] == "Warning message"
        assert manager.events[0]["severity"] == "high"

    def test_print_success(self):
        """Test print_success() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print_success("Operation successful", operation="deploy")

        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "success"
        assert manager.events[0]["level"] == "success"
        assert manager.events[0]["message"] == "Operation successful"
        assert manager.events[0]["operation"] == "deploy"

    def test_print_list(self):
        """Test print_list() in LLM mode."""
        manager = OutputManager(format_type="llm")
        items = ["Item 1", "[bold]Item 2[/bold]", "[red]Item 3[/red]"]
        manager.print_list(items, title="Test List")

        assert len(manager.events) == 1
        assert manager.events[0]["type"] == "list"
        assert manager.events[0]["title"] == "Test List"
        assert manager.events[0]["items"] == ["Item 1", "Item 2", "Item 3"]

    def test_finalize_human_mode(self):
        """Test finalize() in human mode (should not output anything)."""
        manager = OutputManager(format_type="human")
        manager.print("Test", level="info")

        # finalize should be idempotent in human mode
        manager.finalize(
            status="success",
            summary={"count": 1},
            next_steps=["Step 1"],
        )

        assert manager._finalized

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    def test_finalize_llm_mode(self, mock_print_output):
        """Test finalize() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print("Event 1", level="info")
        manager.print_error("Error event")

        manager.finalize(
            status="failed",
            summary={"processed": 2, "failed": 1},
            next_steps=["Fix errors", "Retry"],
            errors=["Error event"],
        )

        # finalize should call formatter.print_output
        assert mock_print_output.called
        assert manager._finalized

    def test_finalize_idempotent(self):
        """Test that finalize() can be called multiple times safely."""
        manager = OutputManager(format_type="llm")
        manager.print("Test", level="info")

        manager.finalize(status="success", summary={})
        manager.finalize(status="success", summary={})  # Should not raise

        assert manager._finalized

    def test_get_console(self):
        """Test get_console() returns Rich Console."""
        manager = OutputManager(format_type="human")
        console = manager.get_console()

        assert console is not None
        assert hasattr(console, "print")

    def test_event_collection_multiple_events(self):
        """Test that multiple events are collected correctly in LLM mode."""
        manager = OutputManager(format_type="llm")

        manager.print("Message 1", level="info")
        manager.print_section("Section A")
        manager.print_error("Error 1", error="Details")
        manager.print_warning("Warning 1")
        manager.print_success("Success 1")
        manager.print_list(["a", "b"], title="List 1")

        assert len(manager.events) == 6
        assert manager.events[0]["type"] == "message"
        assert manager.events[1]["type"] == "section"
        assert manager.events[2]["type"] == "error"
        assert manager.events[3]["type"] == "warning"
        assert manager.events[4]["type"] == "success"
        assert manager.events[5]["type"] == "list"
