"""Hugo Template Dependencies CLI Tool.

A modern Python CLI tool for analyzing Hugo template files and mapping dependencies
between templates, partials, and modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.console import Console as FileConsole
from rich.tree import Tree

from .analyzer.template_discovery import TemplateDiscovery
from .analyzer.template_parser import HugoTemplateParser
from .config.parser import HugoConfigParser
from .error_handling import ErrorHandler
from .graph.hugo_graph import HugoDependencyGraph
from .modules.resolver import HugoModuleResolver
from .output.dot_formatter import DOTFormatter
from .output.json_formatter import JSONFormatter
from .output.mermaid_formatter import MermaidFormatter
from .progress_reporting import (
    AnalysisPhase,
    ProgressReporter,
)

app = typer.Typer(
    name="hugo-deps",
    help="Analyze Hugo template dependencies and build maps of template relationships.",
    no_args_is_help=True,
)
console = Console()


def _build_partial_lookup(parsed_templates: dict, project_path: Path) -> dict:
    """Build a lookup table mapping partial reference names to template objects.

    Args:
        parsed_templates: Dictionary of template path -> HugoTemplate
        project_path: Path to the Hugo project root

    Returns:
        Dictionary mapping partial reference names to HugoTemplate objects

    """
    lookup = {}

    for template_path, template in parsed_templates.items():
        path = Path(template_path)

        # Find the layouts directory in the template path
        layouts_dir = None
        for i, part in enumerate(path.parts):
            if part == "layouts":
                layouts_dir = Path(*path.parts[: i + 1])
                break

        if not layouts_dir:
            # No layouts directory found, skip
            continue

        # Make path relative to the layouts directory
        try:
            relative_path = path.relative_to(layouts_dir)
        except ValueError:
            # Should not happen since we found layouts dir, but skip if it does
            continue

        # Create various possible reference formats
        # 1. Relative path from layouts/ (e.g., "_partials/calendar_icon.html")
        lookup[str(relative_path)] = template

        # 2. Without leading underscore directory (e.g., "partials/calendar_icon.html")
        parts = list(relative_path.parts)
        if parts and parts[0].startswith("_"):
            parts[0] = parts[0][1:]  # Remove leading underscore
            lookup[str(Path(*parts))] = template

        # 3. Just the filename (for partials in root of _partials/)
        if relative_path.parts and relative_path.parts[0] in ["_partials", "partials"]:
            # Store as: "calendar_icon.html"
            lookup[path.name] = template

            # Store as: "partials/subdir/name.html" for nested partials
            if len(relative_path.parts) > 2:
                # e.g., "_partials/recurrence/debug_output.html" -> "recurrence/debug_output.html"
                subpath = Path(*relative_path.parts[1:])
                lookup[str(subpath)] = template

    return lookup


@app.command()
def analyze(  # noqa: PLR0912, PLR0915, PLR0913
    project_path: Path = typer.Argument(
        Path.cwd(),
        help="Path to Hugo project directory (defaults to current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    format: str = typer.Option(
        "tree",
        "--format",
        "-f",
        help="Output format: tree, json, dot, mermaid",
        show_default=True,
    ),
    output_file: Path = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Save output to file (works with all formats)",
    ),
    include_modules: bool = typer.Option(
        True,
        "--include-modules/--no-modules",
        help="Include dependencies from Hugo modules",
        show_default=True,
    ),
    ignore_patterns: list[str] = typer.Option(
        [],
        "--ignore",
        help="Patterns to ignore (can be used multiple times)",
    ),
    show_progress: bool = typer.Option(
        True,
        "--progress/--no-progress",
        help="Show progress bars and statistics",
        show_default=True,
    ),
    less_verbose: bool = typer.Option(
        False,
        "--less-verbose",
        help="Reduce output but still show some progress and statistics",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Only output the generated graph (no progress, no stats, no messages)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with detailed progress and statistics",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug output showing detailed template processing and categorization",
    ),
) -> None:
    """Analyze Hugo template dependencies.

    This command scans the Hugo project at PROJECT_PATH and builds a dependency
    map of all template files, including partials, blocks, and module imports.

    Example:
        hugo-deps analyze ./my-hugo-site --format json --output-file deps.json
        hugo-deps analyze ./my-hugo-site --quiet --format tree
        hugo-deps analyze ./my-hugo-site --verbose --format mermaid

    """
    # Handle options - quiet overrides everything, less_verbose reduces output
    effective_show_progress = show_progress and not quiet and not less_verbose
    effective_verbose = verbose and not quiet
    effective_debug = debug and not quiet

    # Create status console for proper output routing
    # When using -o flag: status messages to stdout, content to file
    # When not using -o flag: status messages to stderr, content to stdout
    if output_file:
        status_console = (
            console  # Use regular console (stdout) when writing content to file
        )
    else:
        status_console = Console(
            file=sys.stderr,
        )  # Use stderr when content goes to stdout

    # Initialize error handler and progress reporter with status_console
    error_handler = ErrorHandler(console=status_console, verbose=effective_verbose)
    progress_reporter = ProgressReporter(
        console=status_console,
        show_progress=effective_show_progress,
    )

    if effective_verbose:
        status_console.print(
            f"[blue]🔍 Analyzing Hugo project at:[/blue] {project_path}",
        )
        status_console.print(f"[blue]📊 Output format:[/blue] {format}")
        status_console.print(f"[blue]📦 Include modules:[/blue] {include_modules}")
        status_console.print(
            f"[blue]⚙️  Progress bars:[/blue] {'enabled' if effective_show_progress else 'disabled'}",
        )
        status_console.print(
            f"[blue]🐛 Verbose mode:[/blue] {'enabled' if verbose else 'disabled'}",
        )
        status_console.print(
            f"[blue]🔬 Debug mode:[/blue] {'enabled' if debug else 'disabled'}",
        )

    try:
        # Initialize components

        # Start progress tracking for discovery phase
        progress_reporter.set_phase(
            AnalysisPhase.DISCOVERY,
            "🔍 Discovering Hugo templates",
        )

        # Discover local templates
        discovery = TemplateDiscovery()
        templates = discovery.discover_templates(project_path)

        # Discover module templates if enabled
        if include_modules:
            progress_reporter.set_phase(
                AnalysisPhase.RESOLUTION,
                "📦 Resolving Hugo modules",
            )
            module_resolver = HugoModuleResolver()
            modules = module_resolver.resolve_modules(project_path)

            # Add templates from each module with progress tracking
            progress_reporter.add_subtask(
                "modules",
                "Processing modules",
                len(modules),
            )
            for i, module in enumerate(modules):
                try:
                    progress_reporter.update_subtask("modules", i + 1, len(modules))
                    module_templates = module_resolver.discover_module_templates(module)
                    templates.extend(module_templates)
                except Exception as e:
                    error_handler.handle_dependency_resolution_error(
                        source_file=project_path,
                        target_dependency=str(module),
                        error=e,
                    )
            progress_reporter.complete_subtask("modules")

        if effective_verbose and not quiet and not less_verbose:
            status_console.print(
                f"[green]✅ Found {len(templates)} template files[/green]"
            )

        # Start comprehensive progress tracking for parsing and analysis
        progress_reporter.start_analysis(len(templates))
        progress_reporter.set_phase(AnalysisPhase.PARSING, "📄 Parsing template files")

        # Build dependency graph
        graph = HugoDependencyGraph()

        # Extract and set replacement mappings from Hugo config to handle module display names correctly
        try:
            config_parser = HugoConfigParser()
            hugo_config = config_parser.parse_hugo_config(project_path)
            replacement_mappings = config_parser.extract_module_replacements(
                hugo_config,
            )
            if replacement_mappings:
                graph.set_replacement_mappings(replacement_mappings)
                if effective_debug:
                    status_console.print(
                        f"[dim cyan]  Set {len(replacement_mappings)} replacement mappings[/dim cyan]",
                    )
        except Exception as e:
            # Non-critical error, continue without replacement mappings
            if effective_debug:
                status_console.print(
                    f"[dim yellow]  Warning: Could not extract replacement mappings: {e}[/dim yellow]",
                )

        parser = HugoTemplateParser()

        # First pass: parse all templates and add them to the graph
        parsed_templates = {}
        for i, template in enumerate(templates):
            try:
                # Update progress with current file
                progress_reporter.update_file_progress(i, len(templates))

                # Update current file being processed (only if not quiet and not less_verbose)
                if not quiet and not less_verbose:
                    progress_reporter.update_current_file(template.file_path)

                parsed = parser.parse_file(template.file_path)
                # Preserve the source information from the original template
                parsed.source = template.source
                graph.add_template(parsed)
                parsed_templates[str(parsed.file_path)] = parsed

                # Debug output: show template categorization
                if effective_debug:
                    status_console.print(
                        f"[dim cyan]  📄 Parsed:[/dim cyan] {parsed.file_path.name} "
                        f"[dim]→[/dim] [yellow]{parsed.template_type.value}[/yellow]",
                    )
                    if parsed.dependencies:
                        status_console.print(
                            f"[dim cyan]     Dependencies:[/dim cyan] {len(parsed.dependencies)}",
                        )
                        for dep in parsed.dependencies[:3]:  # Show first 3 dependencies
                            status_console.print(
                                f"[dim]       • {dep['type']}:[/dim] [green]{dep['target']}[/green] "
                                f"[dim](line {dep['line_number']})[/dim]",
                            )
                        if len(parsed.dependencies) > 3:
                            status_console.print(
                                f"[dim]       ... and {len(parsed.dependencies) - 3} more[/dim]",
                            )

            except Exception as e:
                # Enhanced error handling with context
                error_handler.handle_template_parsing_error(
                    file_path=template.file_path,
                    error=e,
                    line_number=getattr(e, "lineno", None),
                )
                continue

        # Create a lookup table for resolving partial names to actual templates
        # This maps partial reference names (e.g., "recurrence/debug_output.html") to template node IDs
        if effective_debug:
            status_console.print(
                "\n[bold cyan]🔍 Building partial lookup table...[/bold cyan]",
            )

        partial_lookup = _build_partial_lookup(parsed_templates, project_path)

        if effective_debug:
            status_console.print(
                f"[dim cyan]  Found {len(partial_lookup)} partial reference mappings[/dim cyan]",
            )
            # Show some example mappings
            for _i, (ref_name, template) in enumerate(list(partial_lookup.items())[:5]):
                status_console.print(
                    f'[dim]    • "{ref_name}" → {template.file_path.name}[/dim]',
                )
            if len(partial_lookup) > 5:
                status_console.print(
                    f"[dim]    ... and {len(partial_lookup) - 5} more mappings[/dim]",
                )
            status_console.print()

        # Second pass: resolve and add dependencies
        if effective_debug:
            status_console.print("[bold cyan]🔗 Resolving dependencies...[/bold cyan]")

        resolved_count = 0
        unresolved_count = 0

        for template_path, parsed in parsed_templates.items():
            try:
                # Add dependencies to graph
                if parsed.dependencies:
                    for dep in parsed.dependencies:
                        if dep["type"] in ["partial", "template", "include"]:
                            # Resolve target to actual template if possible
                            target_name = dep["target"]
                            resolved_target = partial_lookup.get(target_name)

                            if resolved_target:
                                # Use resolved template as target
                                graph.add_include_dependency(
                                    source=parsed,
                                    target=resolved_target,
                                    include_type=dep["type"],
                                    line_number=dep["line_number"],
                                    context=dep["context"],
                                )
                                resolved_count += 1

                                if effective_debug:
                                    status_console.print(
                                        f"[dim]  ✓ {parsed.file_path.name}[/dim] "
                                        f"[dim cyan]→[/dim cyan] [green]{target_name}[/green] "
                                        f"[dim](resolved)[/dim]",
                                    )
                            else:
                                # Target not found - create a placeholder node
                                graph.add_include_dependency(
                                    source=parsed,
                                    target=target_name,
                                    include_type=dep["type"],
                                    line_number=dep["line_number"],
                                    context=dep["context"],
                                )
                                unresolved_count += 1

                                if effective_debug:
                                    status_console.print(
                                        f"[dim]  ⚠ {parsed.file_path.name}[/dim] "
                                        f"[dim cyan]→[/dim cyan] [yellow]{target_name}[/yellow] "
                                        f"[dim](unresolved)[/dim]",
                                    )

                                error_handler.handle_dependency_resolution_error(
                                    source_file=parsed.file_path,
                                    target_dependency=target_name,
                                    error=ValueError(
                                        f"Could not resolve {dep['type']} reference: {target_name}",
                                    ),
                                )
            except Exception as e:
                # Enhanced error handling with context
                error_handler.handle_template_parsing_error(
                    file_path=Path(template_path),
                    error=e,
                    line_number=None,
                )
                continue

        if effective_debug:
            status_console.print(
                f"\n[bold cyan]📊 Dependency Resolution Summary:[/bold cyan]\n"
                f"[green]  ✓ Resolved:[/green] {resolved_count}\n"
                f"[yellow]  ⚠ Unresolved:[/yellow] {unresolved_count}\n",
            )

        # Create a lookup table for resolving partial names to actual templates
        # This maps partial reference names (e.g., "recurrence/debug_output.html") to template node IDs
        partial_lookup = _build_partial_lookup(parsed_templates, project_path)

        # Second pass: resolve and add dependencies
        for template_path, parsed in parsed_templates.items():
            try:
                # Add dependencies to graph
                if parsed.dependencies:
                    for dep in parsed.dependencies:
                        if dep["type"] in ["partial", "template", "include"]:
                            # Resolve target to actual template if possible
                            target_name = dep["target"]
                            resolved_target = partial_lookup.get(target_name)

                            if resolved_target:
                                # Use resolved template as target
                                graph.add_include_dependency(
                                    source=parsed,
                                    target=resolved_target,
                                    include_type=dep["type"],
                                    line_number=dep["line_number"],
                                    context=dep["context"],
                                )
                            else:
                                # Target not found - create a placeholder node
                                graph.add_include_dependency(
                                    source=parsed,
                                    target=target_name,
                                    include_type=dep["type"],
                                    line_number=dep["line_number"],
                                    context=dep["context"],
                                )
                                error_handler.handle_dependency_resolution_error(
                                    source_file=parsed.file_path,
                                    target_dependency=target_name,
                                    error=ValueError(
                                        f"Could not resolve {dep['type']} reference: {target_name}",
                                    ),
                                )
            except Exception as e:
                # Enhanced error handling with context
                error_handler.handle_template_parsing_error(
                    file_path=Path(template_path),
                    error=e,
                    line_number=None,
                )
                continue

        # Update progress with final stats
        progress_reporter.update_file_progress(len(templates), len(templates))

        # Graph building phase
        progress_reporter.set_phase(
            AnalysisPhase.GRAPH_BUILDING,
            "🕸️ Building dependency graph",
        )
        progress_reporter.update_graph_stats(
            graph.get_node_count(),
            graph.get_edge_count(),
        )
        progress_reporter.update_error_stats(
            error_handler.error_count,
            error_handler.warning_count,
        )

        # Output results
        progress_reporter.set_phase(
            AnalysisPhase.OUTPUT_FORMATTING,
            "📋 Formatting output",
        )

        # Helper function to write output to file or console
        def write_output(content: str, description: str = "Output") -> None:
            if output_file:
                # When using -o: content goes to file, status messages go to stdout
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                if not quiet:
                    status_console.print(
                        f"[green]{description} saved to:[/green] {output_file}",
                    )
            else:
                # When not using -o: status messages go to stderr, content to stdout
                if not quiet and description != "Output":
                    status_console.print(f"[blue]{description}:[/blue]")
                # Content always goes to stdout for piping/redirection
                print(content)

        if format == "tree":
            tree = Tree(f"📁 Hugo Project: {project_path.name}")

            # Add templates by type
            for template_type in [
                "layout",
                "partial",
                "single",
                "list",
                "baseof",
                "index",
            ]:
                type_templates = graph.get_templates_by_type(template_type)
                if type_templates:
                    type_dir = tree.add(f"📂 {template_type}s/")
                    for template in type_templates:
                        type_dir.add(f"📄 {template.display_name}")

            # For tree output, we need to capture the rich tree output
            if output_file:
                file_console = FileConsole(
                    file=open(output_file, "w", encoding="utf-8"),
                    width=80,
                )
                file_console.print(tree)
                file_console.file.close()
                if not quiet:
                    status_console.print(
                        f"[green]Tree output saved to:[/green] {output_file}"
                    )
            else:
                # Tree output goes to stdout (via regular console)
                print(tree)

        elif format == "mermaid":
            formatter = MermaidFormatter(graph)
            mermaid_output = formatter.format_with_styles()
            write_output(mermaid_output, "Mermaid Graph")

        elif format == "json":
            formatter = JSONFormatter(graph)
            if output_file:
                formatter.save_to_file(
                    output_file,
                    format_type="detailed",
                    validate_output=True,
                )
                if not quiet:
                    status_console.print(
                        f"[green]JSON output saved to:[/green] {output_file}"
                    )
            else:
                json_output = formatter.format_detailed()
                write_output(json_output, "JSON Output")

        elif format == "dot":
            formatter = DOTFormatter(graph)
            if output_file:
                formatter.save_to_file(str(output_file), format_type="clustered")
                if not quiet:
                    status_console.print(
                        f"[green]DOT output saved to:[/green] {output_file}"
                    )
            else:
                dot_output = formatter.format_clustered()
                write_output(dot_output, "DOT Output")

        else:
            error_handler.handle_configuration_error(
                f"Output format '{format}' is not supported",
                config_file=None,
            )

        # Print final statistics
        if effective_show_progress and not less_verbose:
            progress_reporter.print_statistics()

        if not quiet:
            progress_reporter.print_summary()

            # Print error summary if there were errors
            error_summary = error_handler.get_error_summary()
            if error_summary["total"] > 0:
                status_console.print(
                    f"\n[yellow]⚠[/yellow] Analysis completed with {error_summary['errors']} errors and {error_summary['warnings']} warnings.",
                )
            else:
                status_console.print(
                    f"\n[green]✓[/green] Analysis complete! Found {graph.get_node_count()} nodes and {graph.get_edge_count()} dependencies.",
                )

    except KeyboardInterrupt:
        status_console.print("\n[yellow]Analysis cancelled by user[/yellow]")
        raise
    except Exception as e:
        error_handler.handle_configuration_error(
            f"Analysis failed: {e}",
            config_file=None,
            error=e,
        )
        raise
    finally:
        # Clean up progress reporting
        progress_reporter.cancel()


@app.command()
def version() -> None:
    """Show version information."""
    console.print("hugo-deps version 0.0.1")


if __name__ == "__main__":
    app()
