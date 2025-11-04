"""
Output formatter for LLM-friendly and structured output.

This module provides utilities to format command outputs in different modes:
- human: Rich Console output (default)
- llm: LLM-friendly compact text output
- json: Structured JSON output
- yaml: Structured YAML output
"""

import json
import os
from enum import Enum
from typing import Any

from rich.console import Console

try:
    import yaml
except ImportError:
    yaml = None  # YAML support is optional


class OutputFormat(str, Enum):
    """Supported output formats."""

    HUMAN = "human"
    LLM = "llm"
    JSON = "json"
    YAML = "yaml"


class OutputFormatter:
    """Format command outputs for different consumers (humans, LLMs, machines)."""

    def __init__(self, format_type: OutputFormat | str = OutputFormat.HUMAN):
        """
        Initialize output formatter.

        Args:
            format_type: Output format (human, llm, json, yaml)
        """
        if isinstance(format_type, str):
            format_type = OutputFormat(format_type)
        self.format = format_type
        self.console = Console() if format_type == OutputFormat.HUMAN else None

    @classmethod
    def from_env_or_cli(
        cls,
        cli_format: str | None = None,
        env_var: str = "SBKUBE_OUTPUT_FORMAT",
    ) -> "OutputFormatter":
        """
        Create formatter from CLI option or environment variable.

        Priority: CLI option > Environment variable > Default (human)

        Args:
            cli_format: CLI-specified format (--format option)
            env_var: Environment variable name to check

        Returns:
            OutputFormatter instance
        """
        format_str = cli_format or os.environ.get(env_var, "human")
        try:
            return cls(format_type=OutputFormat(format_str.lower()))
        except ValueError:
            # Invalid format, fallback to human
            return cls(format_type=OutputFormat.HUMAN)

    def format_deployment_result(
        self,
        status: str,
        summary: dict[str, Any],
        deployments: list[dict[str, Any]],
        next_steps: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> str | dict:
        """
        Format deployment result in the selected format.

        Args:
            status: Overall status ("success", "failed", "partial")
            summary: Summary dict (charts_deployed, duration_seconds, etc.)
            deployments: List of deployment dicts (name, namespace, status, version)
            next_steps: Optional next steps/commands
            errors: Optional error messages

        Returns:
            Formatted output (str for human/llm, dict for json/yaml)
        """
        if self.format == OutputFormat.HUMAN:
            return self._format_human_deployment(
                status, summary, deployments, next_steps, errors
            )
        elif self.format == OutputFormat.LLM:
            return self._format_llm_deployment(
                status, summary, deployments, next_steps, errors
            )
        elif self.format == OutputFormat.JSON:
            return self._format_json_deployment(
                status, summary, deployments, next_steps, errors
            )
        elif self.format == OutputFormat.YAML:
            return self._format_yaml_deployment(
                status, summary, deployments, next_steps, errors
            )

    def _format_human_deployment(
        self,
        status: str,
        summary: dict,
        deployments: list[dict],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format deployment result for human (Rich Console)."""
        # This will be integrated with existing Rich Console output
        # For now, return a placeholder
        return "Human format (use Rich Console directly in commands)"

    def _format_llm_deployment(
        self,
        status: str,
        summary: dict,
        deployments: list[dict],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format deployment result for LLM (compact, readable text)."""
        lines = []

        # Status line
        status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
        lines.append(f"STATUS: {status} {status_icon}")

        # Summary
        charts_count = summary.get("charts_deployed", 0)
        duration = summary.get("duration_seconds", 0)
        lines.append(f"DEPLOYED: {charts_count} charts in {duration:.1f}s")
        lines.append("")

        # Deployments
        if deployments:
            lines.append("APPLICATIONS:")
            for dep in deployments:
                name = dep.get("name", "unknown")
                namespace = dep.get("namespace", "default")
                dep_status = dep.get("status", "unknown")
                version = dep.get("version", "")
                version_str = f" v{version}" if version else ""
                lines.append(f"- {name} ({namespace}): {dep_status}{version_str}")
            lines.append("")

        # Next steps
        if next_steps:
            lines.append("NEXT STEPS:")
            for step in next_steps:
                lines.append(step)
            lines.append("")

        # Errors
        if errors:
            lines.append("ERRORS:")
            for error in errors:
                lines.append(f"- {error}")
        else:
            lines.append("ERRORS: none")

        return "\n".join(lines)

    def _format_json_deployment(
        self,
        status: str,
        summary: dict,
        deployments: list[dict],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format deployment result as JSON."""
        result = {
            "status": status,
            "summary": summary,
            "deployments": deployments,
            "next_steps": next_steps or [],
            "errors": errors or [],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _format_yaml_deployment(
        self,
        status: str,
        summary: dict,
        deployments: list[dict],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format deployment result as YAML."""
        if yaml is None:
            # Fallback to JSON if PyYAML not available
            return self._format_json_deployment(
                status, summary, deployments, next_steps, errors
            )

        result = {
            "status": status,
            "summary": summary,
            "deployments": deployments,
            "next_steps": next_steps or [],
            "errors": errors or [],
        }
        return yaml.dump(result, allow_unicode=True, default_flow_style=False)

    def print_output(self, output: str | dict):
        """
        Print formatted output.

        Args:
            output: Formatted output (str or dict)
        """
        if isinstance(output, dict):
            # JSON or YAML dict → convert to string
            if self.format == OutputFormat.JSON:
                print(json.dumps(output, indent=2, ensure_ascii=False))
            elif self.format == OutputFormat.YAML and yaml:
                print(yaml.dump(output, allow_unicode=True, default_flow_style=False))
            else:
                print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(output)


def get_output_format_from_context(ctx: Any) -> OutputFormat:
    """
    Extract output format from Click context.

    Args:
        ctx: Click context

    Returns:
        OutputFormat enum value
    """
    # Try to get format from context params
    if hasattr(ctx, "params") and "format" in ctx.params:
        format_str = ctx.params["format"]
        if format_str:
            try:
                return OutputFormat(format_str)
            except ValueError:
                pass

    # Try environment variable
    env_format = os.environ.get("SBKUBE_OUTPUT_FORMAT")
    if env_format:
        try:
            return OutputFormat(env_format.lower())
        except ValueError:
            pass

    # Default to human
    return OutputFormat.HUMAN
