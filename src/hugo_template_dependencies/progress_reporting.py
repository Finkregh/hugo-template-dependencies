"""Progress reporting for Hugo template dependency analysis.

This module provides comprehensive progress reporting with progress bars,
statistics, and time estimates for the Hugo template dependency analyzer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from typing_extensions import Self


class AnalysisPhase(Enum):
    """Analysis phases for progress tracking."""

    DISCOVERY = "discovery"
    PARSING = "parsing"
    RESOLUTION = "resolution"
    GRAPH_BUILDING = "graph_building"
    OUTPUT_FORMATTING = "output_formatting"
    COMPLETE = "complete"


@dataclass
class AnalysisStats:
    """Statistics for analysis progress."""

    total_files: int = 0
    processed_files: int = 0
    total_dependencies: int = 0
    resolved_dependencies: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    errors: int = 0
    warnings: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def files_per_second(self) -> float:
        """Get files processed per second."""
        if self.elapsed_time == 0:
            return 0.0
        return self.processed_files / self.elapsed_time

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_files == 0:
            return 100.0
        return (self.processed_files / self.total_files) * 100.0

    @property
    def estimated_remaining_time(self) -> float:
        """Get estimated remaining time in seconds."""
        if self.processed_files == 0 or self.total_files == 0:
            return 0.0

        rate = self.files_per_second
        if rate == 0:
            return 0.0

        remaining_files = self.total_files - self.processed_files
        return remaining_files / rate


class ProgressReporter:
    """Enhanced progress reporter with rich UI and statistics."""

    def __init__(
        self,
        console: Console | None = None,
        show_progress: bool = True,
    ) -> None:
        """Initialize progress reporter.

        Args:
            console: Rich console for output
            show_progress: Whether to show progress bars

        """
        self.console = console or Console()
        self.show_progress = show_progress
        self.stats = AnalysisStats()
        self.current_phase = AnalysisPhase.DISCOVERY
        self.tasks: dict[str, TaskID] = {}

        # Initialize progress display
        if self.show_progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
            )
        else:
            self.progress = None

    def start_analysis(self, total_files: int) -> None:
        """Start analysis progress tracking.

        Args:
            total_files: Total number of files to process

        """
        self.stats.total_files = total_files
        self.stats.start_time = time.time()
        self.current_phase = AnalysisPhase.DISCOVERY

        if self.show_progress and self.progress:
            self.progress.start()
            self._create_main_task()

        self._print_phase_header("Starting Hugo Template Analysis")

    def set_phase(self, phase: AnalysisPhase, description: str | None = None) -> None:
        """Set current analysis phase.

        Args:
            phase: New analysis phase
            description: Optional phase description

        """
        self.current_phase = phase

        if description:
            self._print_phase_header(description)
        else:
            self._print_phase_header(f"Phase: {phase.value.title()}")

    def update_current_file(self, file_path: Path | str) -> None:
        """Update the current file being processed.

        Args:
            file_path: Path of the current file being processed

        """
        if self.show_progress and self.progress and "main" in self.tasks:
            # Convert to relative path if possible for cleaner display
            if isinstance(file_path, Path) and file_path.is_absolute():
                try:
                    # Try to make it relative to current working directory
                    file_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    # If not relative, just use the name
                    file_path = file_path.name

            # Update progress description with current file
            self.progress.update(
                self.tasks["main"],
                description=f"📄 Processing: {file_path}",
            )

    def update_file_progress(self, processed: int, total: int | None = None) -> None:
        """Update file processing progress.

        Args:
            processed: Number of files processed
            total: Total number of files (optional)

        """
        self.stats.processed_files = processed
        if total is not None:
            self.stats.total_files = total

        # For large projects (>1000 files), update progress less frequently to improve performance
        if self.show_progress and self.progress and "main" in self.tasks:
            if total and total > 1000 and processed % 10 != 0 and processed != total:
                # Skip updates for large projects except every 10 files or final update
                return
            self.progress.update(self.tasks["main"], completed=processed, total=total)

    def increment_file_progress(self, increment: int = 1) -> None:
        """Increment file processing progress.

        Args:
            increment: Number of files to increment by

        """
        self.stats.processed_files += increment

        if self.show_progress and self.progress and "main" in self.tasks:
            self.progress.advance(self.tasks["main"], increment)

    def update_dependency_stats(self, total: int, resolved: int) -> None:
        """Update dependency resolution statistics.

        Args:
            total: Total number of dependencies found
            resolved: Number of dependencies resolved

        """
        self.stats.total_dependencies = total
        self.stats.resolved_dependencies = resolved

    def update_graph_stats(self, nodes: int, edges: int) -> None:
        """Update graph building statistics.

        Args:
            nodes: Number of nodes in graph
            edges: Number of edges in graph

        """
        self.stats.total_nodes = nodes
        self.stats.total_edges = edges

    def update_error_stats(self, errors: int, warnings: int) -> None:
        """Update error statistics.

        Args:
            errors: Number of errors
            warnings: Number of warnings

        """
        self.stats.errors = errors
        self.stats.warnings = warnings

    def add_subtask(self, name: str, description: str, total: int) -> TaskID:
        """Add a subtask for progress tracking.

        Args:
            name: Task name
            description: Task description
            total: Total items for task

        Returns:
            Task ID for the subtask

        """
        if self.show_progress and self.progress:
            task_id = self.progress.add_task(description, total=total)
            self.tasks[name] = task_id
            return task_id
        return TaskID(0)  # Dummy ID when progress is disabled

    def update_subtask(
        self,
        name: str,
        completed: int,
        total: int | None = None,
    ) -> None:
        """Update subtask progress.

        Args:
            name: Subtask name
            completed: Number of items completed
            total: Total number of items (optional)

        """
        if self.show_progress and self.progress and name in self.tasks:
            self.progress.update(self.tasks[name], completed=completed, total=total)

    def complete_subtask(self, name: str) -> None:
        """Mark subtask as complete.

        Args:
            name: Subtask name

        """
        if self.show_progress and self.progress and name in self.tasks:
            # Mark as complete by setting completed to total
            task_id = self.tasks[name]
            task = self.progress.tasks[task_id]
            self.progress.update(task_id, completed=task.total)

    def print_statistics(self) -> None:
        """Print current analysis statistics."""
        table = Table(
            title="Analysis Statistics",
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="white", width=15)
        table.add_column("Rate", style="green", width=15)

        # File statistics
        table.add_row(
            "Files Processed",
            f"{self.stats.processed_files:,}",
            f"{self.stats.completion_percentage:.1f}%",
        )
        table.add_row("Total Files", f"{self.stats.total_files:,}", "")

        # Dependency statistics
        if self.stats.total_dependencies > 0:
            dep_percentage = (
                self.stats.resolved_dependencies / self.stats.total_dependencies
            ) * 100
            table.add_row(
                "Dependencies Resolved",
                f"{self.stats.resolved_dependencies:,}",
                f"{dep_percentage:.1f}%",
            )
            table.add_row(
                "Total Dependencies",
                f"{self.stats.total_dependencies:,}",
                "",
            )

        # Graph statistics
        if self.stats.total_nodes > 0:
            table.add_row("Graph Nodes", f"{self.stats.total_nodes:,}", "")
            table.add_row("Graph Edges", f"{self.stats.total_edges:,}", "")

        # Error statistics
        if self.stats.errors > 0 or self.stats.warnings > 0:
            table.add_row("Errors", f"{self.stats.errors:,}", "red")
            table.add_row("Warnings", f"{self.stats.warnings:,}", "yellow")

        # Performance statistics
        table.add_row(
            "Elapsed Time",
            f"{self.stats.elapsed_time:.1f}s",
            f"{self.stats.files_per_second:.1f} files/s",
        )

        if self.stats.processed_files < self.stats.total_files:
            remaining = self.stats.estimated_remaining_time
            table.add_row("Est. Remaining", f"{remaining:.1f}s", "")

        self.console.print(table)

    def print_summary(self) -> None:
        """Print final analysis summary."""
        self.stats.end_time = time.time()
        self.current_phase = AnalysisPhase.COMPLETE

        # Create summary panel
        summary_text = Text()
        summary_text.append("Analysis Complete!\n\n", style="bold green")

        summary_text.append(
            f"Files Processed: {self.stats.processed_files:,}/{self.stats.total_files:,}\n",
            style="white",
        )
        summary_text.append(
            f"Dependencies Found: {self.stats.total_dependencies:,}\n",
            style="white",
        )
        summary_text.append(f"Graph Nodes: {self.stats.total_nodes:,}\n", style="white")
        summary_text.append(f"Graph Edges: {self.stats.total_edges:,}\n", style="white")

        if self.stats.errors > 0 or self.stats.warnings > 0:
            summary_text.append(f"\nErrors: {self.stats.errors:,}\n", style="red")
            summary_text.append(f"Warnings: {self.stats.warnings:,}\n", style="yellow")

        summary_text.append(
            f"\nTotal Time: {self.stats.elapsed_time:.1f}s\n",
            style="white",
        )
        summary_text.append(
            f"Processing Rate: {self.stats.files_per_second:.1f} files/s",
            style="green",
        )

        self.console.print(
            Panel(
                summary_text,
                title="[bold green]Analysis Summary[/]",
                border_style="green",
            ),
        )

    def cancel(self) -> None:
        """Cancel progress reporting."""
        if self.show_progress and self.progress:
            self.progress.stop()

    def __enter__(self) -> Self:
        """Context manager entry."""
        if self.show_progress and self.progress:
            self.progress.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if self.show_progress and self.progress:
            self.progress.stop()

    def _create_main_task(self) -> None:
        """Create main progress task."""
        if self.show_progress and self.progress:
            task_id = self.progress.add_task(
                "Analyzing Hugo templates...",
                total=self.stats.total_files,
            )
            self.tasks["main"] = task_id

    def _print_phase_header(self, description: str) -> None:
        """Print phase header.

        Args:
            description: Phase description

        """
        if not self.show_progress:
            return

        self.console.print(f"\n[bold blue]{description}[/bold blue]")
        if self.progress:
            self.console.print()  # Add spacing


class CancellableProgress:
    """Progress reporter that supports cancellation."""

    def __init__(self, reporter: ProgressReporter) -> None:
        """Initialize cancellable progress.

        Args:
            reporter: Base progress reporter

        """
        self.reporter = reporter
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel the analysis."""
        self._cancelled = True
        self.reporter.console.print("\n[yellow]Analysis cancelled by user[/yellow]")
        self.reporter.cancel()

    @property
    def is_cancelled(self) -> bool:
        """Check if analysis was cancelled."""
        return self._cancelled

    def check_cancellation(self) -> None:
        """Check for cancellation and raise if cancelled."""
        if self._cancelled:
            msg = "Analysis was cancelled"
            raise KeyboardInterrupt(msg)

    def update_file_progress(self, processed: int, total: int | None = None) -> None:
        """Update file progress with cancellation check."""
        self.check_cancellation()
        self.reporter.update_file_progress(processed, total)

    def increment_file_progress(self, increment: int = 1) -> None:
        """Increment file progress with cancellation check."""
        self.check_cancellation()
        self.reporter.increment_file_progress(increment)
