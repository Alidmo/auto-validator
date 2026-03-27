import sys

# Ensure UTF-8 output on Windows so Rich unicode (arrows, boxes, etc.) works
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click

from auto_validator.cli.commands.run import run_command
from auto_validator.cli.commands.discover import discover_command
from auto_validator.cli.commands.metrics import metrics_group
from auto_validator.cli.commands.listener import listener_group
from auto_validator.cli.commands.closer import closer_group
from auto_validator.cli.commands.projects import projects_group


@click.group()
@click.option("--dry-run/--no-dry-run", default=None, help="Override DRY_RUN env var")
@click.pass_context
def cli(ctx: click.Context, dry_run: bool | None) -> None:
    """Auto-Validator: Autonomous business idea validation agent."""
    if dry_run is not None:
        # Override the setting at runtime
        from auto_validator import config
        config.settings.dry_run = dry_run


cli.add_command(run_command)
cli.add_command(discover_command)
cli.add_command(metrics_group)
cli.add_command(listener_group)
cli.add_command(closer_group)
cli.add_command(projects_group)


if __name__ == "__main__":
    cli()
