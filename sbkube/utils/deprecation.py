"""Deprecation warning helpers for CLI options."""

import click
from click.core import ParameterSource


def warn_deprecated_option(option_name: str, alternative: str) -> None:
    """Emit a standardized deprecation warning to stderr."""
    click.echo(
        f"WARNING: '{option_name}' is deprecated and will be removed in v1.0. "
        f"Use '{alternative}' instead.",
        err=True,
    )


def option_was_explicitly_set(ctx: click.Context, parameter_name: str) -> bool:
    """Return True if an option was explicitly provided by the caller."""
    source = ctx.get_parameter_source(parameter_name)
    return source in {
        ParameterSource.COMMANDLINE,
        ParameterSource.ENVIRONMENT,
        ParameterSource.PROMPT,
    }
