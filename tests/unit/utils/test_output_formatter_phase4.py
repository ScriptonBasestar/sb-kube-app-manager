"""Tests for OutputFormatter Phase 4-5 features.

Phase 4: Advanced output formats (table, tree, error structuring)
Phase 5: Streaming output (progress, JSONL, parallel tasks)
"""

import json

import pytest

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from sbkube.utils.output_formatter import OutputFormat, OutputFormatter


class TestPhase4TableOutput:
    """Test Phase 4.1: Table output optimization."""

    def test_table_llm_format_basic(self) -> None:
        """LLM table format should be CSV-like with --- separator."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        data = [
            {"name": "app1", "status": "running", "version": "1.0.0"},
            {"name": "app2", "status": "pending", "version": "2.0.0"},
        ]

        result = formatter.table(data)

        assert "NAME  STATUS  VERSION" in result
        assert "---" in result
        assert "app1  running  1.0.0" in result
        assert "app2  pending  2.0.0" in result
        # Should not have Rich table decorations
        assert "┌" not in result
        assert "│" not in result

    def test_table_llm_format_with_title(self) -> None:
        """LLM table should include title as comment."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        data = [{"app": "nginx", "pods": "3"}]

        result = formatter.table(data, title="Running Applications")

        assert "# Running Applications" in result
        assert "APP  PODS" in result

    def test_table_llm_format_custom_headers(self) -> None:
        """LLM table should support custom header order."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        data = [{"name": "app1", "status": "running", "version": "1.0.0"}]

        result = formatter.table(data, headers=["status", "name"])

        lines = result.split("\n")
        assert lines[0] == "STATUS  NAME"
        assert "running  app1" in result

    def test_table_json_format(self) -> None:
        """JSON table should return structured data."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)
        data = [{"name": "app1", "status": "running"}]

        result = formatter.table(data, title="Apps")

        parsed = json.loads(result)
        assert parsed["title"] == "Apps"
        assert parsed["headers"] == ["name", "status"]
        assert len(parsed["rows"]) == 1

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_table_yaml_format(self) -> None:
        """YAML table should return structured data."""
        formatter = OutputFormatter(format_type=OutputFormat.YAML)
        data = [{"name": "app1"}]

        result = formatter.table(data)

        parsed = yaml.safe_load(result)
        assert "headers" in parsed
        assert "rows" in parsed

    def test_table_empty_data(self) -> None:
        """Empty table should return empty string."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.table([])

        assert result == ""


class TestPhase4TreeOutput:
    """Test Phase 4.2: Tree/chart data optimization."""

    def test_tree_llm_format_nested_dict(self) -> None:
        """LLM tree should use indented structure."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        data = {
            "deployment_history": [
                {"version": "v1.0.0", "date": "2025-11-01"},
                {"version": "v1.1.0", "date": "2025-11-05"},
            ]
        }

        result = formatter.tree(data, root_label="History")

        assert "deployment_history:" in result
        assert "version: v1.0.0" in result
        assert "date: 2025-11-01" in result
        # Should use indentation, not tree characters
        assert "├──" not in result
        assert "└──" not in result

    def test_tree_llm_format_list(self) -> None:
        """LLM tree should handle lists."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        data = ["v1.0.0", "v1.1.0", "v1.2.0"]

        result = formatter.tree(data, root_label="versions")

        assert "versions:" in result
        assert "- v1.0.0" in result
        assert "- v1.1.0" in result

    def test_tree_json_format(self) -> None:
        """JSON tree should return structured data."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)
        data = {"apps": {"app1": "running"}}

        result = formatter.tree(data, root_label="Status")

        parsed = json.loads(result)
        assert parsed["root"] == "Status"
        assert parsed["data"]["apps"]["app1"] == "running"


class TestPhase4ErrorFormatting:
    """Test Phase 4.3: Error message structuring."""

    def test_error_llm_format_basic(self) -> None:
        """LLM error should be structured with KEY: VALUE."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.error(
            error_type="ValidationError",
            message="Invalid config.yaml",
            code="CONFIG_001",
        )

        assert "ERROR: ValidationError" in result
        assert "MESSAGE: Invalid config.yaml" in result
        assert "CODE: CONFIG_001" in result

    def test_error_llm_format_with_suggestions(self) -> None:
        """LLM error should include suggestions list."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.error(
            error_type="ValidationError",
            message="Invalid YAML",
            suggestions=["Check YAML syntax", "Verify required fields"],
        )

        assert "SUGGESTIONS:" in result
        assert "- Check YAML syntax" in result
        assert "- Verify required fields" in result

    def test_error_llm_format_with_references(self) -> None:
        """LLM error should include documentation references."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.error(
            error_type="ConfigError",
            message="Missing field",
            references=["docs/config-schema.md", "docs/troubleshooting.md"],
        )

        assert "REFERENCES:" in result
        assert "- docs/config-schema.md" in result

    def test_error_json_format(self) -> None:
        """JSON error should return structured data."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)

        result = formatter.error(
            error_type="DeploymentError",
            message="Failed to deploy",
            code="DEPLOY_001",
            suggestions=["Check cluster"],
            references=["docs/deployment.md"],
        )

        parsed = result
        assert parsed["error"]["type"] == "DeploymentError"
        assert parsed["error"]["message"] == "Failed to deploy"
        assert parsed["error"]["code"] == "DEPLOY_001"
        assert len(parsed["error"]["suggestions"]) == 1
        assert len(parsed["error"]["references"]) == 1

    def test_error_human_format(self) -> None:
        """Human error should be readable with emoji."""
        formatter = OutputFormatter(format_type=OutputFormat.HUMAN)

        result = formatter.error(
            error_type="Error",
            message="Something went wrong",
            suggestions=["Try again"],
        )

        assert "❌" in result
        assert "Something went wrong" in result


class TestPhase5StreamingOutput:
    """Test Phase 5.2: Real-time log streaming (JSONL)."""

    def test_stream_llm_format_jsonl(self) -> None:
        """LLM stream should output JSONL (one JSON per line)."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        event = {
            "type": "log",
            "level": "info",
            "message": "Starting deployment",
        }

        result = formatter.stream(event)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["type"] == "log"
        assert parsed["level"] == "info"
        assert parsed["message"] == "Starting deployment"
        # Should not have newlines inside (JSONL format)
        assert "\n" not in result

    def test_stream_json_format_jsonl(self) -> None:
        """JSON stream should also output JSONL."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)
        event = {"type": "progress", "step": "prepare", "status": "running"}

        result = formatter.stream(event)

        parsed = json.loads(result)
        assert parsed["type"] == "progress"

    def test_stream_human_format(self) -> None:
        """Human stream should be simple text."""
        formatter = OutputFormatter(format_type=OutputFormat.HUMAN)
        event = {"type": "log", "level": "error", "message": "Build failed"}

        result = formatter.stream(event)

        assert "[ERROR]" in result
        assert "Build failed" in result

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_stream_yaml_format(self) -> None:
        """YAML stream should use document separator."""
        formatter = OutputFormatter(format_type=OutputFormat.YAML)
        event = {"type": "log", "message": "test"}

        result = formatter.stream(event)

        assert "---" in result


class TestPhase5ProgressOutput:
    """Test Phase 5.1: Progress bar replacement."""

    def test_progress_llm_format_jsonl(self) -> None:
        """LLM progress should be JSONL event."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.progress(
            task="download", current=50, total=100, status="running"
        )

        parsed = json.loads(result)
        assert parsed["type"] == "progress"
        assert parsed["task"] == "download"
        assert parsed["current"] == 50
        assert parsed["total"] == 100
        assert parsed["percentage"] == 50
        assert parsed["status"] == "running"

    def test_progress_json_format_jsonl(self) -> None:
        """JSON progress should be JSONL event."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)

        result = formatter.progress(task="build", current=3, total=5)

        parsed = json.loads(result)
        assert parsed["percentage"] == 60

    def test_progress_human_format(self) -> None:
        """Human progress should be simple text."""
        formatter = OutputFormatter(format_type=OutputFormat.HUMAN)

        result = formatter.progress(task="deploy", current=2, total=10)

        assert "deploy: 2/10 (20%)" in result

    def test_progress_zero_total(self) -> None:
        """Progress should handle zero total gracefully."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        result = formatter.progress(task="test", current=0, total=0)

        parsed = json.loads(result)
        assert parsed["percentage"] == 0


class TestPhase5ParallelTasksOutput:
    """Test Phase 5.3: Parallel task output."""

    def test_parallel_tasks_llm_format(self) -> None:
        """LLM parallel tasks should be structured list."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        tasks = {
            "app1": {"status": "running", "progress": 50},
            "app2": {"status": "completed", "progress": 100},
            "app3": {"status": "pending", "progress": 0},
        }

        result = formatter.parallel_tasks(tasks)

        assert "PARALLEL TASKS:" in result
        assert "- app1: running (50%)" in result
        assert "- app2: completed (100%)" in result
        assert "- app3: pending (0%)" in result

    def test_parallel_tasks_json_format(self) -> None:
        """JSON parallel tasks should be dict."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)
        tasks = {"app1": {"status": "running", "progress": 75}}

        result = formatter.parallel_tasks(tasks)

        assert result["parallel_tasks"]["app1"]["status"] == "running"
        assert result["parallel_tasks"]["app1"]["progress"] == 75

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_parallel_tasks_yaml_format(self) -> None:
        """YAML parallel tasks should be structured."""
        formatter = OutputFormatter(format_type=OutputFormat.YAML)
        tasks = {"app1": {"status": "completed", "progress": 100}}

        result = formatter.parallel_tasks(tasks)

        parsed = yaml.safe_load(result)
        assert "parallel_tasks" in parsed

    def test_parallel_tasks_human_format(self) -> None:
        """Human parallel tasks should have emoji status icons."""
        formatter = OutputFormatter(format_type=OutputFormat.HUMAN)
        tasks = {
            "app1": {"status": "completed", "progress": 100},
            "app2": {"status": "running", "progress": 50},
        }

        result = formatter.parallel_tasks(tasks)

        assert "Parallel Tasks:" in result
        assert "✅" in result or "🔄" in result


class TestPrintOutput:
    """Test print_output method enhancement."""

    def test_print_output_string(self, capsys) -> None:
        """print_output should handle string output."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)
        formatter.print_output("test output")

        captured = capsys.readouterr()
        assert "test output" in captured.out

    def test_print_output_dict_json(self, capsys) -> None:
        """print_output should convert dict to JSON."""
        formatter = OutputFormatter(format_type=OutputFormat.JSON)
        formatter.print_output({"status": "success", "count": 3})

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["status"] == "success"
        assert parsed["count"] == 3

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_print_output_dict_yaml(self, capsys) -> None:
        """print_output should convert dict to YAML."""
        formatter = OutputFormatter(format_type=OutputFormat.YAML)
        formatter.print_output({"status": "success"})

        captured = capsys.readouterr()
        assert "status:" in captured.out


class TestTokenSavings:
    """Test token savings validation."""

    def test_table_token_reduction(self) -> None:
        """LLM table should use significantly fewer tokens than rich format."""
        data = [
            {"name": f"app{i}", "status": "running", "version": f"{i}.0.0"}
            for i in range(10)
        ]

        llm_formatter = OutputFormatter(format_type=OutputFormat.LLM)
        llm_output = llm_formatter.table(data)

        # LLM output should be compact
        assert len(llm_output) < 500  # Rough token estimate
        assert "┌" not in llm_output  # No box drawing
        assert "│" not in llm_output
        assert "━" not in llm_output

    def test_error_token_reduction(self) -> None:
        """LLM error should be more compact than human format."""
        llm_formatter = OutputFormatter(format_type=OutputFormat.LLM)
        human_formatter = OutputFormatter(format_type=OutputFormat.HUMAN)

        llm_error = llm_formatter.error(
            error_type="Error",
            message="Failed",
            suggestions=["Fix it", "Try again"],
        )
        human_error = human_formatter.error(
            error_type="Error",
            message="Failed",
            suggestions=["Fix it", "Try again"],
        )

        # LLM should be shorter (no emoji, less decoration)
        assert len(llm_error) < len(human_error) + 50


class TestIntegrationScenarios:
    """Test real-world usage scenarios."""

    def test_deployment_progress_stream(self) -> None:
        """Test streaming deployment progress events."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        events = [
            {"type": "log", "level": "info", "message": "Starting deployment"},
            {"type": "progress", "step": "prepare", "status": "running"},
            {"type": "progress", "step": "prepare", "status": "completed"},
            {"type": "progress", "step": "build", "status": "running"},
        ]

        results = [formatter.stream(event) for event in events]

        # All should be valid JSONL
        for result in results:
            parsed = json.loads(result)
            assert "type" in parsed

    def test_multi_app_deployment_status(self) -> None:
        """Test parallel deployment status output."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        # Initial status
        tasks = {
            "nginx": {"status": "running", "progress": 0},
            "postgres": {"status": "pending", "progress": 0},
            "redis": {"status": "pending", "progress": 0},
        }
        status1 = formatter.parallel_tasks(tasks)

        # Updated status
        tasks["nginx"]["progress"] = 100
        tasks["nginx"]["status"] = "completed"
        tasks["postgres"]["status"] = "running"
        tasks["postgres"]["progress"] = 50
        status2 = formatter.parallel_tasks(tasks)

        assert "nginx: running (0%)" in status1
        assert "nginx: completed (100%)" in status2
        assert "postgres: running (50%)" in status2

    def test_error_with_recovery_suggestions(self) -> None:
        """Test error formatting with actionable suggestions."""
        formatter = OutputFormatter(format_type=OutputFormat.LLM)

        error = formatter.error(
            error_type="DeploymentError",
            message="PVC claim pending (storage class not found)",
            code="STORAGE_001",
            suggestions=[
                "kubectl get storageclass",
                "Check storage provisioner installation",
                "Verify PVC configuration",
            ],
            references=[
                "docs/troubleshooting/storage-issues.md",
                "docs/configuration/storage.md",
            ],
        )

        assert "ERROR: DeploymentError" in error
        assert "CODE: STORAGE_001" in error
        assert "SUGGESTIONS:" in error
        assert "kubectl get storageclass" in error
        assert "REFERENCES:" in error
        assert "docs/troubleshooting/storage-issues.md" in error
