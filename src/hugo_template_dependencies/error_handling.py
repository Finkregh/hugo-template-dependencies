"""Enhanced error handling for Hugo template dependency analysis.

This module provides comprehensive error handling with context, suggestions,
and proper logging for the Hugo template dependency analyzer.
"""

from __future__ import annotations

import logging
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
    from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HugoAnalysisError(Exception):
    """Base exception for Hugo template analysis errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        suggestions: list[str] | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
    ) -> None:
        """Initialize Hugo analysis error.

        Args:
            message: Error message
            severity: Error severity level
            context: Additional context information
            suggestions: Recovery suggestions
            file_path: File where error occurred
            line_number: Line number where error occurred

        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.context = context or {}
        self.suggestions = suggestions or []
        self.file_path = file_path
        self.line_number = line_number


class TemplateParsingError(HugoAnalysisError):
    """Error during template file parsing."""

    def __init__(
        self,
        message: str,
        file_path: Path,
        line_number: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize template parsing error.

        Args:
            message: Error message
            file_path: Template file path
            line_number: Line number where error occurred
            context: Additional context information

        """
        # Generate specific suggestions based on error content
        suggestions = self._generate_parsing_suggestions(message, context)

        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            context=context,
            suggestions=suggestions,
            file_path=file_path,
            line_number=line_number,
        )

    def _generate_parsing_suggestions(
        self, message: str, context: dict[str, Any] | None,
    ) -> list[str]:
        """Generate specific suggestions based on the error message.

        Args:
            message: Error message
            context: Additional context information

        Returns:
            List of specific suggestions

        """
        suggestions = [
            "Check template syntax for Hugo-specific directives",
            "Verify all partial and template references are correct",
            "Ensure proper closing of template blocks",
            "Check for malformed HTML or Go template syntax",
        ]

        message_lower = message.lower()

        # Add specific suggestions based on error type
        if "partial" in message_lower:
            suggestions.insert(
                0,
                "Missing partial: Check if the partial file exists in layouts/partials/",
            )
            suggestions.insert(1, "Verify partial name spelling and path format")

        if "template" in message_lower and "not found" in message_lower:
            suggestions.insert(
                0, "Missing template: Check if the template file exists in layouts/",
            )
            suggestions.insert(
                1, "Verify template type (single, list, baseof) and path",
            )

        if "syntax" in message_lower or "parse" in message_lower:
            suggestions.insert(
                0, "Syntax error: Check Go template syntax ({{ }}, {{- -}}, etc.)",
            )
            suggestions.insert(
                1, "Ensure all Hugo functions and variables are correctly formatted",
            )

        if "end" in message_lower or "unclosed" in message_lower:
            suggestions.insert(
                0, "Unclosed block: Check for missing {{ end }} or {{- end -}}",
            )
            suggestions.insert(
                1, "Verify all {{ define }}, {{ block }}, {{ with }} blocks are closed",
            )

        if context and "line_content" in context:
            suggestions.insert(0, f"Line content: {context['line_content']}")

        return suggestions


class DependencyResolutionError(HugoAnalysisError):
    """Error during dependency resolution."""

    def __init__(
        self,
        message: str,
        source_file: Path | None = None,
        target_dependency: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize dependency resolution error.

        Args:
            message: Error message
            source_file: Source template file
            target_dependency: Target dependency that couldn't be resolved
            context: Additional context information

        """
        # Generate specific suggestions based on dependency type
        suggestions = self._generate_dependency_suggestions(target_dependency, context)

        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            context=context,
            suggestions=suggestions,
            file_path=source_file,
        )

    def _generate_dependency_suggestions(
        self, target_dependency: str | None, context: dict[str, Any] | None,
    ) -> list[str]:
        """Generate specific suggestions based on the dependency type.

        Args:
            target_dependency: Target dependency that couldn't be resolved
            context: Additional context information

        Returns:
            List of specific suggestions

        """
        suggestions = [
            "Verify the target template or partial exists",
            "Check module configuration and dependencies",
            "Ensure theme paths are correctly configured",
            "Validate Hugo module imports in go.mod",
        ]

        if target_dependency:
            dep_lower = target_dependency.lower()

            # Add specific suggestions based on dependency type
            if "partial" in dep_lower:
                suggestions.insert(
                    0,
                    f"Missing partial '{target_dependency}': Check layouts/partials/ directory",
                )
                suggestions.insert(
                    1, "Ensure partial name doesn't include .html extension in the call",
                )

            if "layouts/" in dep_lower or "theme/" in dep_lower:
                suggestions.insert(
                    0,
                    f"Missing layout '{target_dependency}': Check layouts/ directory structure",
                )
                suggestions.insert(
                    1, "Verify theme is properly configured and accessible",
                )

            if "module" in dep_lower:
                suggestions.insert(
                    0,
                    f"Missing module '{target_dependency}': Check go.mod and hugo.toml",
                )
                suggestions.insert(1, "Run 'hugo mod get' to download missing modules")

            # Add path-specific suggestions
            if target_dependency.startswith("partials/"):
                suggestions.insert(
                    0, f"Check if file exists: layouts/{target_dependency}.html",
                )
            elif "/" in target_dependency:
                suggestions.insert(
                    0, f"Check if file exists: layouts/{target_dependency}",
                )

        return suggestions


class FileAccessError(HugoAnalysisError):
    """Error during file access operations."""

    def __init__(
        self,
        message: str,
        file_path: Path,
        operation: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize file access error.

        Args:
            message: Error message
            file_path: File that couldn't be accessed
            operation: Operation being performed (read, write, etc.)
            context: Additional context information

        """
        suggestions = [
            "Check file permissions",
            "Verify the file path exists",
            "Ensure the directory is accessible",
            "Check if the file is locked by another process",
        ]

        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            context=(
                {**context, "operation": operation}
                if context
                else {"operation": operation}
            ),
            suggestions=suggestions,
            file_path=file_path,
        )


class ConfigurationError(HugoAnalysisError):
    """Error in project configuration."""

    def __init__(
        self,
        message: str,
        config_file: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_file: Configuration file path
            context: Additional context information

        """
        suggestions = [
            "Validate Hugo configuration file syntax",
            "Check module configuration in go.mod",
            "Verify theme configuration",
            "Ensure all required configuration fields are present",
        ]

        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            context=context,
            suggestions=suggestions,
            file_path=config_file,
        )


class ErrorHandler:
    """Enhanced error handler with logging and user-friendly output."""

    def __init__(self, console: Console | None = None, verbose: bool = False) -> None:
        """Initialize error handler.

        Args:
            console: Rich console for output
            verbose: Whether to enable verbose logging

        """
        self.console = console or Console()
        self.verbose = verbose
        self.error_count = 0
        self.warning_count = 0

        # Setup logging
        self._setup_logging(verbose)

    def _setup_logging(self, verbose: bool) -> None:
        """Setup logging configuration.

        Args:
            verbose: Whether to enable verbose logging

        """
        level = logging.DEBUG if verbose else logging.INFO

        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stderr),
            ],
        )

        self.logger = logging.getLogger(__name__)

    def handle_error(self, error: HugoAnalysisError, recover: bool = True) -> bool:
        """Handle an error with appropriate logging and user output.

        Args:
            error: The error to handle
            recover: Whether to attempt recovery

        Returns:
            True if error was handled successfully, False otherwise

        """
        # Log the error
        self._log_error(error)

        # Update counters
        if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            self.error_count += 1
        elif error.severity == ErrorSeverity.WARNING:
            self.warning_count += 1

        # Display user-friendly output
        self._display_error(error)

        # Attempt recovery if requested
        if recover:
            return self._attempt_recovery(error)

        return False

    def handle_template_parsing_error(
        self,
        file_path: Path,
        error: Exception,
        line_number: int | None = None,
    ) -> None:
        """Handle template parsing errors with context.

        Args:
            file_path: Template file path
            error: Original parsing error
            line_number: Line number where error occurred

        """
        context = {
            "original_error": str(error),
            "error_type": type(error).__name__,
        }

        parsing_error = TemplateParsingError(
            message=f"Failed to parse template: {error}",
            file_path=file_path,
            line_number=line_number,
            context=context,
        )

        self.handle_error(parsing_error, recover=True)

    def handle_dependency_resolution_error(
        self,
        source_file: Path,
        target_dependency: str,
        error: Exception,
    ) -> None:
        """Handle dependency resolution errors with context.

        Args:
            source_file: Source template file
            target_dependency: Target dependency that couldn't be resolved
            error: Original resolution error

        """
        context = {
            "original_error": str(error),
            "error_type": type(error).__name__,
            "target_dependency": target_dependency,
        }

        resolution_error = DependencyResolutionError(
            message=f"Failed to resolve dependency '{target_dependency}': {error}",
            source_file=source_file,
            target_dependency=target_dependency,
            context=context,
        )

        self.handle_error(resolution_error, recover=True)

    def handle_file_access_error(
        self,
        file_path: Path,
        operation: str,
        error: Exception,
    ) -> None:
        """Handle file access errors with context.

        Args:
            file_path: File that couldn't be accessed
            operation: Operation being performed
            error: Original file access error

        """
        context = {
            "original_error": str(error),
            "error_type": type(error).__name__,
            "operation": operation,
        }

        access_error = FileAccessError(
            message=f"Failed to {operation} file '{file_path}': {error}",
            file_path=file_path,
            operation=operation,
            context=context,
        )

        self.handle_error(access_error, recover=True)

    def handle_configuration_error(
        self,
        message: str,
        config_file: Path | None = None,
        error: Exception | None = None,
    ) -> None:
        """Handle configuration errors with context.

        Args:
            message: Error message
            config_file: Configuration file path
            error: Original configuration error

        """
        context = {}
        if error:
            context.update(
                {
                    "original_error": str(error),
                    "error_type": type(error).__name__,
                },
            )

        config_error = ConfigurationError(
            message=message,
            config_file=config_file,
            context=context,
        )

        self.handle_error(config_error, recover=False)

    def get_error_summary(self) -> dict[str, int]:
        """Get summary of errors handled.

        Returns:
            Dictionary with error counts by severity

        """
        return {
            "errors": self.error_count,
            "warnings": self.warning_count,
            "total": self.error_count + self.warning_count,
        }

    def _log_error(self, error: HugoAnalysisError) -> None:
        """Log error with appropriate level.

        Args:
            error: Error to log

        """
        log_message = f"{error.message}"
        if error.file_path:
            log_message += f" (file: {error.file_path})"
        if error.line_number:
            log_message += f" (line: {error.line_number})"

        if error.severity == ErrorSeverity.DEBUG:
            self.logger.debug(log_message)
        elif error.severity == ErrorSeverity.INFO:
            self.logger.info(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)

    def _display_error(self, error: HugoAnalysisError) -> None:
        """Display error to user with rich formatting and icons.

        Args:
            error: Error to display

        """
        # Choose icon and style based on severity
        if error.severity == ErrorSeverity.WARNING:
            icon = "⚠️"
            style = "yellow"
            title = "Warning"
        elif error.severity == ErrorSeverity.ERROR:
            icon = "❌"
            style = "red"
            title = "Error"
        elif error.severity == ErrorSeverity.CRITICAL:
            icon = "🔥"
            style = "bold red"
            title = "Critical Error"
        else:
            icon = "ℹ️"
            style = "white"
            title = "Info"

        # Build error message with icon
        message_lines = [f"{icon} {error.message}"]

        # Add file context if available
        if error.file_path:
            file_info = f"📁 File: {error.file_path}"
            if error.line_number:
                file_info += f":{error.line_number}"
            message_lines.append(file_info)

        # Add context information if verbose
        if self.verbose and error.context:
            message_lines.append("\n🔍 Context:")
            for key, value in error.context.items():
                message_lines.append(f"  • {key}: {value}")

        # Add suggestions if available
        if error.suggestions:
            message_lines.append("\n💡 Suggestions:")
            for suggestion in error.suggestions:
                message_lines.append(f"  • {suggestion}")

        full_message = "\n".join(message_lines)

        # Display error with enhanced panel
        self.console.print(
            Panel(
                full_message,
                title=f"[{style}]{icon} {title}[/{style}]",
                border_style=style,
                padding=(1, 2),
            ),
        )

    def _attempt_recovery(self, error: HugoAnalysisError) -> bool:
        """Attempt to recover from error.

        Args:
            error: Error to recover from

        Returns:
            True if recovery was successful, False otherwise

        """
        # Recovery strategies based on error type
        if isinstance(error, TemplateParsingError):
            return self._recover_from_parsing_error(error)
        if isinstance(error, DependencyResolutionError):
            return self._recover_from_dependency_error(error)
        if isinstance(error, FileAccessError):
            return self._recover_from_file_access_error(error)
        if isinstance(error, ConfigurationError):
            return self._recover_from_configuration_error(error)

        return False

    def _recover_from_parsing_error(self, error: TemplateParsingError) -> bool:
        """Attempt recovery from template parsing error.

        Args:
            error: Parsing error

        Returns:
            True if recovery was successful

        """
        self.logger.info(
            f"Attempting to recover from parsing error in {error.file_path}",
        )

        # For now, just log that we're skipping this file
        if error.file_path:
            self.logger.info(f"Skipping template file: {error.file_path}")

        return True  # Continue processing other files

    def _recover_from_dependency_error(self, error: DependencyResolutionError) -> bool:
        """Attempt recovery from dependency resolution error.

        Args:
            error: Dependency resolution error

        Returns:
            True if recovery was successful

        """
        self.logger.info("Attempting to recover from dependency resolution error")

        # For now, just log that we're skipping this dependency
        if error.context.get("target_dependency"):
            self.logger.info(
                f"Skipping unresolved dependency: {error.context['target_dependency']}",
            )

        return True  # Continue processing other dependencies

    def _recover_from_file_access_error(self, error: FileAccessError) -> bool:
        """Attempt recovery from file access error.

        Args:
            error: File access error

        Returns:
            True if recovery was successful

        """
        self.logger.info("Attempting to recover from file access error")

        # For now, just log that we're skipping this file
        if error.file_path:
            self.logger.info(f"Skipping inaccessible file: {error.file_path}")

        return True  # Continue processing other files

    def _recover_from_configuration_error(self, error: ConfigurationError) -> bool:
        """Attempt recovery from configuration error.

        Args:
            error: Configuration error

        Returns:
            True if recovery was successful

        """
        self.logger.info("Attempting to recover from configuration error")

        # Configuration errors are usually not recoverable
        self.logger.error("Configuration error requires manual intervention")

        return False  # Cannot recover from configuration errors
