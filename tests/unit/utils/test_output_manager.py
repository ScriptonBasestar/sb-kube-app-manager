"""
Unit tests for OutputManager.
"""

from io import StringIO
from unittest.mock import patch

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
        assert (
            OutputManager._strip_markup("[RGB(255,0,0)]Red Text[/RGB(255,0,0)]")
            == "Red Text"
        )

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
        # Ensure second call with no arguments is a no-op
        manager.finalize()

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    @patch("sbkube.utils.output_formatter.OutputFormatter.format_deployment_result")
    def test_finalize_llm_mode(self, mock_format_result, mock_print_output):
        """Test finalize() in LLM mode."""
        manager = OutputManager(format_type="llm")
        manager.print("Event 1", level="info")
        manager.print_error("Error event")

        mock_format_result.return_value = {"result": "ok"}

        manager.finalize(
            status="failed",
            summary={"processed": 2, "failed": 1},
            next_steps=["Fix errors", "Retry"],
            errors=["Error event"],
        )

        # finalize should call formatter.print_output
        assert mock_format_result.called
        called_kwargs = mock_format_result.call_args.kwargs
        assert called_kwargs["status"] == "failed"
        assert called_kwargs["summary"] == {"processed": 2, "failed": 1}
        assert mock_print_output.called
        assert manager._finalized

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    @patch("sbkube.utils.output_formatter.OutputFormatter.format_deployment_result")
    def test_finalize_llm_mode_defaults(self, mock_format_result, mock_print_output):
        """Test finalize() default inference when status/summary are omitted."""
        manager = OutputManager(format_type="llm")
        manager.print("Event 1", level="info")
        mock_format_result.return_value = {"result": "ok"}

        manager.finalize()

        assert mock_format_result.called
        kwargs = mock_format_result.call_args.kwargs
        assert kwargs["status"] == "success"
        assert kwargs["summary"]["events_recorded"] == 1
        assert kwargs["summary"]["deployments_recorded"] == 0
        assert kwargs["summary"]["errors"] == 0
        assert mock_print_output.called

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    @patch("sbkube.utils.output_formatter.OutputFormatter.format_deployment_result")
    def test_finalize_llm_mode_defaults_with_errors(
        self, mock_format_result, mock_print_output
    ):
        """Test finalize() infers failed status when errors are collected."""
        manager = OutputManager(format_type="llm")
        manager.print_error("Something went wrong")
        mock_format_result.return_value = {"result": "ok"}

        manager.finalize()

        kwargs = mock_format_result.call_args.kwargs
        assert kwargs["status"] == "failed"
        assert kwargs["summary"]["errors"] == 1
        assert mock_print_output.called

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

    def test_add_deployment(self):
        """Test add_deployment() method."""
        manager = OutputManager(format_type="llm")

        # Add deployment without version
        manager.add_deployment(name="app1", namespace="default", status="deployed")

        assert len(manager.deployments) == 1
        assert manager.deployments[0]["name"] == "app1"
        assert manager.deployments[0]["namespace"] == "default"
        assert manager.deployments[0]["status"] == "deployed"
        assert manager.deployments[0]["version"] == ""

        # Add deployment with version
        manager.add_deployment(
            name="app2", namespace="production", status="failed", version="1.2.3"
        )

        assert len(manager.deployments) == 2
        assert manager.deployments[1]["name"] == "app2"
        assert manager.deployments[1]["namespace"] == "production"
        assert manager.deployments[1]["status"] == "failed"
        assert manager.deployments[1]["version"] == "1.2.3"

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    def test_finalize_with_deployments(self, mock_print_output):
        """Test finalize() correctly passes deployments to formatter."""
        manager = OutputManager(format_type="llm")

        # Add some deployments
        manager.add_deployment(
            name="app1", namespace="default", status="deployed", version="1.0"
        )
        manager.add_deployment(name="app2", namespace="prod", status="skipped")

        # Add some events
        manager.print_error("Error message")

        # Finalize
        manager.finalize(
            status="success",
            summary={"deployed": 1, "skipped": 1},
            next_steps=["Verify pods"],
        )

        # Verify formatter was called
        assert mock_print_output.called
        call_args = mock_print_output.call_args
        result = call_args[0][0]

        # Check that result is a string (formatted output)
        assert isinstance(result, str)
        assert "app1" in result
        assert "app2" in result

    def test_error_message_accumulation(self):
        """Test that error messages are accumulated correctly."""
        manager = OutputManager(format_type="llm")

        # Print multiple errors
        manager.print_error("Error 1")
        manager.print_error("Error 2", error="Details 2")
        manager.print_error("[red]Error 3[/red]")  # With markup

        # Check error_messages accumulation
        assert len(manager.error_messages) == 3
        assert "Error 1" in manager.error_messages
        assert "Error 2" in manager.error_messages
        assert "Error 3" in manager.error_messages  # Markup stripped
        assert "[red]" not in manager.error_messages[2]

    def test_error_message_deduplication(self):
        """Test that duplicate error messages are not accumulated."""
        manager = OutputManager(format_type="llm")

        # Print same error twice
        manager.print_error("Duplicate error")
        manager.print_error("Duplicate error")

        # Should only have one entry
        assert len(manager.error_messages) == 1
        assert manager.error_messages[0] == "Duplicate error"

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    def test_finalize_with_auto_collected_errors(self, mock_print_output):
        """Test finalize() uses auto-collected errors when errors=None."""
        manager = OutputManager(format_type="llm")

        # Print errors
        manager.print_error("App not found: mongo")
        manager.print_error("Config file missing")

        # Finalize without passing errors parameter
        manager.finalize(
            status="failed",
            summary={"processed": 0},
            next_steps=["Fix issues"],
            # errors=None (default) - should use auto-collected
        )

        # Verify formatter was called
        assert mock_print_output.called
        call_args = mock_print_output.call_args
        result = call_args[0][0]

        # Check that auto-collected errors are in output
        assert isinstance(result, str)
        assert "App not found: mongo" in result
        assert "Config file missing" in result

    @patch("sbkube.utils.output_formatter.OutputFormatter.print_output")
    def test_finalize_with_explicit_errors_overrides(self, mock_print_output):
        """Test that explicit errors parameter overrides auto-collected."""
        manager = OutputManager(format_type="llm")

        # Print errors (should be ignored)
        manager.print_error("Auto-collected error 1")
        manager.print_error("Auto-collected error 2")

        # Finalize with explicit errors
        manager.finalize(
            status="failed",
            summary={"processed": 0},
            errors=["Explicit error only"],
        )

        # Verify formatter was called
        assert mock_print_output.called
        call_args = mock_print_output.call_args
        result = call_args[0][0]

        # Check that only explicit error is in output
        assert isinstance(result, str)
        assert "Explicit error only" in result
        assert "Auto-collected error 1" not in result
        assert "Auto-collected error 2" not in result
