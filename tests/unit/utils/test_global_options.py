"""Tests for global CLI options decorator."""

import click
from click.testing import CliRunner

from sbkube.utils.global_options import global_options


def _make_test_command():
    """Create a minimal test command with @global_options."""

    @click.command(name="test-cmd")
    @click.option("--name", default="world")
    @global_options
    @click.pass_context
    def test_cmd(ctx, name):
        ctx.ensure_object(dict)
        fmt = ctx.obj.get("format", "human")
        click.echo(f"format={fmt} name={name}")

    return test_cmd


def _make_test_group():
    """Create a group + subcommand to test group-level propagation."""

    @click.group()
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["human", "llm", "json", "yaml"]),
        default="human",
    )
    @click.option("-v", "--verbose", count=True)
    @click.option(
        "--log-level",
        "log_level",
        type=click.Choice(["info", "debug", "verbose", "warn"]),
        default=None,
    )
    @click.pass_context
    def grp(ctx, output_format, verbose, log_level):
        ctx.ensure_object(dict)
        ctx.obj["format"] = output_format
        ctx.obj["verbose"] = verbose

    @grp.command(name="sub")
    @global_options
    @click.pass_context
    def sub(ctx):
        fmt = ctx.obj.get("format", "human")
        verbose = ctx.obj.get("verbose", 0)
        click.echo(f"format={fmt} verbose={verbose}")

    return grp


class TestGlobalOptionsStandalone:
    """Test @global_options on standalone commands."""

    def test_default_values(self):
        runner = CliRunner()
        result = runner.invoke(_make_test_command(), [], obj={"format": "human"})
        assert result.exit_code == 0
        assert "format=human" in result.output

    def test_format_override(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(), ["--format", "llm"], obj={"format": "human"}
        )
        assert result.exit_code == 0
        assert "format=llm" in result.output

    def test_format_json(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(), ["--format", "json"], obj={"format": "human"}
        )
        assert result.exit_code == 0
        assert "format=json" in result.output

    def test_verbose_flag(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(), ["-v"], obj={"format": "human"}
        )
        assert result.exit_code == 0

    def test_log_level_debug(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(), ["--log-level", "debug"], obj={"format": "human"}
        )
        assert result.exit_code == 0

    def test_log_level_warn(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(), ["--log-level", "warn"], obj={"format": "human"}
        )
        assert result.exit_code == 0

    def test_command_specific_option_preserved(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(),
            ["--name", "test", "--format", "json"],
            obj={"format": "human"},
        )
        assert result.exit_code == 0
        assert "name=test" in result.output
        assert "format=json" in result.output


class TestGlobalOptionsConflict:
    """Test --log-level and -v conflict detection."""

    def test_log_level_and_verbose_conflict(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(),
            ["--log-level", "debug", "-v"],
            obj={"format": "human"},
        )
        assert result.exit_code == 2
        assert "--log-level and -v/--verbose cannot be used together" in result.output

    def test_log_level_and_vv_conflict(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(),
            ["--log-level", "info", "-vv"],
            obj={"format": "human"},
        )
        assert result.exit_code == 2

    def test_log_level_without_verbose_no_conflict(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_command(),
            ["--log-level", "info"],
            obj={"format": "human"},
        )
        assert result.exit_code == 0


class TestGlobalOptionsGroupPropagation:
    """Test format/verbose propagation from group to subcommand."""

    def test_group_format_inherited(self):
        runner = CliRunner()
        result = runner.invoke(_make_test_group(), ["--format", "json", "sub"])
        assert result.exit_code == 0
        assert "format=json" in result.output

    def test_subcommand_format_overrides_group(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_test_group(), ["--format", "json", "sub", "--format", "llm"]
        )
        assert result.exit_code == 0
        assert "format=llm" in result.output

    def test_subcommand_format_without_group(self):
        runner = CliRunner()
        result = runner.invoke(_make_test_group(), ["sub", "--format", "yaml"])
        assert result.exit_code == 0
        assert "format=yaml" in result.output

    def test_subcommand_verbose_sets_ctx_obj(self):
        runner = CliRunner()
        result = runner.invoke(_make_test_group(), ["sub", "-v"])
        assert result.exit_code == 0
        assert "verbose=1" in result.output

    def test_subcommand_log_level_sets_verbose(self):
        runner = CliRunner()
        result = runner.invoke(_make_test_group(), ["sub", "--log-level", "verbose"])
        assert result.exit_code == 0
        assert "verbose=2" in result.output
