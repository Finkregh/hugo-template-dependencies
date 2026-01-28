#!/usr/bin/env python3
"""Hugo Template Dependencies CLI Tool.

A modern Python CLI tool for analyzing Hugo template files and mapping dependencies
between templates, partials, and modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.tree import Tree

app = typer.Typer(
    name="hugo-deps",
    help="Analyze Hugo template dependencies and build maps of template relationships.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    project_path: Path = typer.Argument(
        Path.cwd(),
        help="Path to Hugo project directory (defaults to current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    output_format: str = typer.Option(
        "tree",
        "--output",
        "-o",
        help="Output format: tree, json, dot",
        show_default=True,
    ),
    include_modules: bool = typer.Option(
        True,
        "--include-modules/--no-modules",
        help="Include dependencies from Hugo modules",
        show_default=True,
    ),
    ignore_patterns: List[str] = typer.Option(
        [],
        "--ignore",
        help="Patterns to ignore (can be used multiple times)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Analyze Hugo template dependencies.

    This command scans the Hugo project at PROJECT_PATH and builds a dependency
    map of all template files, including partials, blocks, and module imports.

    Example:
        hugo-deps analyze ./my-hugo-site --output json --verbose
    """
    if verbose:
        console.print(f"[blue]Analyzing Hugo project at:[/blue] {project_path}")
        console.print(f"[blue]Output format:[/blue] {output_format}")
        console.print(f"[blue]Include modules:[/blue] {include_modules}")

    # TODO: Implement actual analysis logic
    tree = Tree(f"📁 Hugo Project: {project_path.name}")
    layouts_dir = tree.add("📂 layouts/")

    # Placeholder for now - will be replaced with actual template discovery
    layouts_dir.add("📄 baseof.html")
    layouts_dir.add("📄 index.html")
    partials = layouts_dir.add("📂 _partials/")
    partials.add("📄 header.html")
    partials.add("📄 footer.html")

    console.print(tree)

    if output_format == "tree":
        console.print("\n[green]✓[/green] Analysis complete!")
    else:
        console.print(
            f"\n[yellow]⚠[/yellow] Output format '{output_format}' not yet implemented"
        )


@app.command()
def version() -> None:
    """Show version information."""
    console.print("hugo-deps version 0.0.1")


if __name__ == "__main__":
    app()
