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
    def format_history_result(
        self,
        status: str,
        summary: dict[str, Any],
        history: list[dict[str, Any]],
        next_steps: list[str],
        errors: list[str],
    ) -> str | dict:
        """
        Format deployment history output in the selected format.

        Args:
            status: Overall status ("success", "failed", "warning")
            summary: Summary information (filters, counters, metadata)
            history: History payload (list view, detail view, diff, etc.)
            next_steps: Suggested follow-up commands
            errors: Error messages

        Returns:
            Formatted output (str for human/llm, dict for json/yaml)
        """
        if self.format == OutputFormat.HUMAN:
            return "Human format (rendered directly in command)"
        if self.format == OutputFormat.LLM:
            return self._format_llm_history(status, summary, history, next_steps, errors)
        if self.format == OutputFormat.JSON:
            return self._format_json_history(status, summary, history, next_steps, errors)
        if self.format == OutputFormat.YAML:
            return self._format_yaml_history(status, summary, history, next_steps, errors)
        return ""

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
    def _format_llm_history(
        self,
        status: str,
        summary: dict[str, Any],
        history: list[dict[str, Any]],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format history result for LLM consumption."""
        def icon_for_state(state: str) -> str:
            mapping = {
                "success": "✅",
                "failed": "❌",
                "in_progress": "🔄",
                "pending": "⏳",
                "rolled_back": "↩️",
                "partially_failed": "⚠️",
            }
            return mapping.get(state, "•")

        lines: list[str] = []
        status_icon = icon_for_state(status)
        view = summary.get("view", "list")
        lines.append(f"HISTORY STATUS: {status} {status_icon}")

        if view == "list":
            total = summary.get("total", len(history))
            returned = summary.get("returned", len(history))
            limit = summary.get("limit")
            lines.append(f"TOTAL DEPLOYMENTS: {total}")
            if limit:
                lines.append(f"LIMIT: {limit} (showing {returned})")
            filters = summary.get("filters") or {}
            filter_items = [
                f"{key}={value}"
                for key, value in filters.items()
                if value not in (None, "", "any")
            ]
            if filter_items:
                lines.append(f"FILTERS: {', '.join(filter_items)}")
            status_counts = summary.get("status_counts") or {}
            if status_counts:
                formatted_counts = ", ".join(
                    f"{name}:{status_counts[name]}" for name in sorted(status_counts)
                )
                lines.append(f"STATUS COUNTS: {formatted_counts}")
            if history:
                lines.append("")
                lines.append("RECENT DEPLOYMENTS:")
                for entry in history:
                    entry_status = entry.get("status", "unknown")
                    entry_icon = entry.get("status_icon") or icon_for_state(entry_status)
                    apps_info = entry.get("apps", {})
                    success_count = apps_info.get("success", 0)
                    total_count = apps_info.get("total", 0)
                    timestamp = entry.get("timestamp")
                    lines.append(
                        f"- {entry.get('deployment_id', 'unknown')} | {timestamp} | "
                        f"{entry.get('cluster', '-')}/{entry.get('namespace', '-')} | "
                        f"{entry_status} {entry_icon} ({success_count}/{total_count} apps)"
                    )
                    if entry.get("error_message"):
                        lines.append(f"  error: {entry['error_message']}")
        elif view == "detail":
            entry = history[0] if history else {}
            entry_status = entry.get("status", status)
            entry_icon = icon_for_state(entry_status)
            lines.append(f"DEPLOYMENT ID: {entry.get('deployment_id', 'unknown')} {entry_icon}")
            lines.append(f"TIMESTAMP: {entry.get('timestamp')}")
            lines.append(
                f"CONTEXT: {entry.get('cluster', '-')}/{entry.get('namespace', '-')}"
            )
            if entry.get("config_dir"):
                lines.append(f"CONFIG DIR: {entry['config_dir']}")
            if entry.get("error_message"):
                lines.append(f"ERROR: {entry['error_message']}")

            apps = entry.get("apps") or []
            if apps:
                lines.append("")
                lines.append(f"APPS ({len(apps)}):")
                for app in apps:
                    app_status = app.get("status", "unknown")
                    app_icon = app.get("status_icon") or icon_for_state(app_status)
                    namespace = app.get("namespace")
                    ns_str = f" ({namespace})" if namespace else ""
                    lines.append(
                        f"- {app.get('name', 'unknown')} [{app.get('type', '?')}] "
                        f"{app_status} {app_icon}{ns_str}"
                    )
                    if app.get("error_message"):
                        lines.append(f"  error: {app['error_message']}")

            resources = entry.get("resources") or []
            if resources:
                lines.append("")
                lines.append(f"RESOURCES ({len(resources)}):")
                for resource in resources[:10]:
                    ns_str = f"/{resource['namespace']}" if resource.get("namespace") else ""
                    lines.append(
                        f"- {resource.get('action', '').upper()} "
                        f"{resource.get('kind', '?')}{ns_str}/{resource.get('name', '?')}"
                    )
                if len(resources) > 10:
                    lines.append(f"... {len(resources) - 10} more")

            helm = entry.get("helm_releases") or []
            if helm:
                lines.append("")
                lines.append(f"HELM RELEASES ({len(helm)}):")
                for release in helm[:10]:
                    lines.append(
                        f"- {release.get('release_name', '?')} "
                        f"rev {release.get('revision')} "
                        f"status {release.get('status')}"
                    )
                if len(helm) > 10:
                    lines.append(f"... {len(helm) - 10} more")
        elif view == "diff":
            entry = history[0] if history else {}
            dep1 = entry.get("deployment1", {})
            dep2 = entry.get("deployment2", {})
            lines.append(
                f"COMPARE: {dep1.get('id', '?')} ({dep1.get('status')}) → "
                f"{dep2.get('id', '?')} ({dep2.get('status')})"
            )
            lines.append(
                f"TIMESTAMP: {dep1.get('timestamp')} → {dep2.get('timestamp')}"
            )
            lines.append(
                f"APPS: {dep1.get('app_count', 0)} → {dep2.get('app_count', 0)}"
            )
            apps_diff = entry.get("apps_diff") or {}
            diff_parts = []
            for key in ("added", "removed", "modified"):
                items = apps_diff.get(key) or []
                if items:
                    diff_parts.append(f"{key}:{len(items)}")
            if diff_parts:
                lines.append(f"APP CHANGES: {', '.join(diff_parts)}")
            config_changes = entry.get("config_changes") or []
            if config_changes:
                lines.append("")
                lines.append("CONFIG CHANGES:")
                lines.extend(config_changes[:10])
                if len(config_changes) > 10:
                    lines.append(f"... {len(config_changes) - 10} more")
        elif view == "values-diff":
            entry = history[0] if history else {}
            lines.append(
                f"VALUES DIFF: {entry.get('deployment1_id', '?')} → {entry.get('deployment2_id', '?')}"
            )
            summary_counts = entry.get("summary", {})
            if summary_counts:
                formatted_counts = ", ".join(
                    f"{key}:{summary_counts[key]}" for key in ("added", "removed", "modified", "unchanged") if key in summary_counts
                )
                lines.append(f"HELM RELEASES: {formatted_counts}")
            releases = entry.get("releases") or []
            if releases:
                lines.append("")
                lines.append("CHANGES:")
                for release in releases[:10]:
                    status = release.get("status")
                    lines.append(f"- {release.get('name')}: {status}")
                if len(releases) > 10:
                    lines.append(f"... {len(releases) - 10} more")

        if next_steps:
            lines.append("")
            lines.append("NEXT STEPS:")
            lines.extend(next_steps)

        if errors:
            lines.append("")
            lines.append("ERRORS:")
            for error in errors:
                lines.append(f"- {error}")
        else:
            lines.append("")
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
    def _format_json_history(
        self,
        status: str,
        summary: dict[str, Any],
        history: list[dict[str, Any]],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format history result as JSON."""
        result = {
            "status": status,
            "summary": summary,
            "history": history,
            "next_steps": next_steps or [],
            "errors": errors or [],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _format_yaml_history(
        self,
        status: str,
        summary: dict[str, Any],
        history: list[dict[str, Any]],
        next_steps: list[str] | None,
        errors: list[str] | None,
    ) -> str:
        """Format history result as YAML."""
        if yaml is None:
            return self._format_json_history(status, summary, history, next_steps, errors)
        result = {
            "status": status,
            "summary": summary,
            "history": history,
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
