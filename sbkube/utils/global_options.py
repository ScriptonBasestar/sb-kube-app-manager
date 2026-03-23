"""Global CLI options decorator for all sbkube subcommands.

Provides --format, --log-level, and -v/--verbose options that can be used
at both group level (sbkube --format llm apply) and subcommand level
(sbkube apply --format llm).
"""

import functools
import logging

import click

from sbkube.utils.logger import LogLevel, logger

LOG_LEVEL_MAP: dict[str, LogLevel] = {
    "debug": LogLevel.DEBUG,
    "verbose": LogLevel.VERBOSE,
    "info": LogLevel.INFO,
    "warn": LogLevel.WARNING,
}


def _resolve_options(ctx: click.Context) -> None:
    """Resolve format and log-level from subcommand + group options.

    Priority: subcommand explicit > group explicit > default.
    Conflict: --log-level + -v both explicit → UsageError.
    """
    ctx.ensure_object(dict)

    # --- Format resolution ---
    sub_format_source = ctx.get_parameter_source("output_format")
    if sub_format_source == click.core.ParameterSource.COMMANDLINE:
        ctx.obj["format"] = ctx.params["output_format"]
    elif ctx.obj.get("format") is None:
        ctx.obj["format"] = ctx.params.get("output_format") or "human"

    # --- Log-level / verbose resolution ---
    log_level_source = ctx.get_parameter_source("log_level")
    verbose_source = ctx.get_parameter_source("verbose")

    log_level_explicit = log_level_source == click.core.ParameterSource.COMMANDLINE
    verbose_explicit = (
        verbose_source == click.core.ParameterSource.COMMANDLINE
        and ctx.params.get("verbose", 0) > 0
    )

    if log_level_explicit and verbose_explicit:
        raise click.UsageError(
            "--log-level and -v/--verbose cannot be used together. "
            "Use one or the other."
        )

    if log_level_explicit:
        level = LOG_LEVEL_MAP[ctx.params["log_level"]]
        logger.set_level(level)
        if level <= LogLevel.DEBUG:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            )
        ctx.obj["verbose"] = 2 if level <= LogLevel.VERBOSE else (1 if level <= LogLevel.INFO else 0)
    elif verbose_explicit:
        verbose_count = ctx.params["verbose"]
        if verbose_count >= 2:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            )
            logger.set_level(LogLevel.VERBOSE)
        elif verbose_count >= 1:
            logger.set_level(LogLevel.INFO)
        ctx.obj["verbose"] = verbose_count
    # else: inherit from group (already in ctx.obj)


def global_options(func):
    """Decorator adding --format, --log-level, -v/--verbose to a subcommand.

    Usage::

        @click.command(name="apply")
        @global_options
        @click.pass_context
        def cmd(ctx, ...):
            # ctx.obj["format"] and ctx.obj["verbose"] are resolved
            pass
    """

    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["human", "llm", "json", "yaml"], case_sensitive=False),
        default=None,
        help="Output format (human/llm/json/yaml). Overrides group-level --format.",
    )
    @click.option(
        "--log-level",
        "log_level",
        type=click.Choice(["info", "debug", "verbose", "warn"], case_sensitive=False),
        default=None,
        help="Log level. Cannot be used with -v/--verbose.",
    )
    @click.option(
        "-v",
        "--verbose",
        count=True,
        help="Logging verbosity (-v: info, -vv: verbose). Cannot be used with --log-level.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        _resolve_options(ctx)
        # Remove decorator-managed params from kwargs so they don't
        # conflict with the wrapped function's signature
        kwargs.pop("output_format", None)
        kwargs.pop("log_level", None)
        kwargs.pop("verbose", None)
        return func(*args, **kwargs)

    return wrapper
