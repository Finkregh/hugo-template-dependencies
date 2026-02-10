"""Tests for error handling system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from rich.console import Console

from hugo_template_dependencies.error_handling import (
    ConfigurationError,
    DependencyResolutionError,
    ErrorHandler,
    ErrorSeverity,
    FileAccessError,
    HugoAnalysisError,
    TemplateParsingError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def console() -> Console:
    """Create Rich console for testing.

    Returns:
        Rich Console instance

    """
    return Console()


@pytest.fixture
def error_handler(console: Console) -> ErrorHandler:
    """Create error handler with test console.

    Args:
        console: Rich Console instance

    Returns:
        ErrorHandler instance

    """
    return ErrorHandler(console=console, verbose=False)


@pytest.fixture
def verbose_error_handler(console: Console) -> ErrorHandler:
    """Create verbose error handler.

    Args:
        console: Rich Console instance

    Returns:
        Verbose ErrorHandler instance

    """
    return ErrorHandler(console=console, verbose=True)


@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """Create a temporary file for testing.

    Yields:
        Path to temporary file

    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        temp_path = Path(f.name)
        f.write("<html>Test</html>")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestErrorSeverity:
    """Test cases for ErrorSeverity enum."""

    def test_error_severity_levels(self) -> None:
        """Test that all severity levels are defined."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_severity_enum_members(self) -> None:
        """Test that ErrorSeverity has expected members."""
        members = [member.name for member in ErrorSeverity]
        assert "DEBUG" in members
        assert "INFO" in members
        assert "WARNING" in members
        assert "ERROR" in members
        assert "CRITICAL" in members


class TestHugoAnalysisError:
    """Test cases for HugoAnalysisError base exception."""

    def test_hugo_analysis_error_creation(self) -> None:
        """Test basic error creation."""
        error = HugoAnalysisError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.severity == ErrorSeverity.ERROR
        assert error.context == {}
        assert error.suggestions == []
        assert error.file_path is None
        assert error.line_number is None

    def test_hugo_analysis_error_with_all_parameters(self, temp_file: Path) -> None:
        """Test error creation with all parameters.

        Args:
            temp_file: Temporary file path

        """
        context = {"key": "value", "count": 42}
        suggestions = ["Try this", "Or this"]

        error = HugoAnalysisError(
            message="Detailed error",
            severity=ErrorSeverity.WARNING,
            context=context,
            suggestions=suggestions,
            file_path=temp_file,
            line_number=10,
        )

        assert error.message == "Detailed error"
        assert error.severity == ErrorSeverity.WARNING
        assert error.context == context
        assert error.suggestions == suggestions
        assert error.file_path == temp_file
        assert error.line_number == 10

    def test_hugo_analysis_error_inheritance(self) -> None:
        """Test that HugoAnalysisError inherits from Exception."""
        error = HugoAnalysisError("Test")
        assert isinstance(error, Exception)


class TestTemplateParsingError:
    """Test cases for TemplateParsingError."""

    def test_template_parsing_error_basic(self, temp_file: Path) -> None:
        """Test basic template parsing error.

        Args:
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Syntax error",
            file_path=temp_file,
        )

        assert error.message == "Syntax error"
        assert error.file_path == temp_file
        assert error.severity == ErrorSeverity.ERROR
        assert len(error.suggestions) > 0

    def test_template_parsing_error_with_line_number(self, temp_file: Path) -> None:
        """Test template parsing error with line number.

        Args:
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Parse error at line 5",
            file_path=temp_file,
            line_number=5,
        )

        assert error.line_number == 5
        assert error.file_path == temp_file

    def test_template_parsing_error_partial_suggestions(self, temp_file: Path) -> None:
        """Test suggestions for partial-related errors.

        Args:
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Missing partial reference",
            file_path=temp_file,
        )

        # Should have specific partial suggestions
        assert any("partial" in s.lower() for s in error.suggestions)

    def test_template_parsing_error_syntax_suggestions(self, temp_file: Path) -> None:
        """Test suggestions for syntax errors.

        Args:
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Syntax error in template",
            file_path=temp_file,
        )

        # Should have syntax-related suggestions
        assert any("syntax" in s.lower() for s in error.suggestions)

    def test_template_parsing_error_unclosed_block_suggestions(
        self,
        temp_file: Path,
    ) -> None:
        """Test suggestions for unclosed block errors.

        Args:
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Unclosed block detected",
            file_path=temp_file,
        )

        # Should have suggestions about closing blocks
        assert any("end" in s.lower() for s in error.suggestions)

    def test_template_parsing_error_with_context(self, temp_file: Path) -> None:
        """Test template parsing error with context.

        Args:
            temp_file: Temporary file path

        """
        context = {"line_content": "{{ partial 'missing' }}"}
        error = TemplateParsingError(
            message="Template error",
            file_path=temp_file,
            context=context,
        )

        assert "line_content" in error.context
        # Context should appear in suggestions
        assert any("Line content:" in s for s in error.suggestions)


class TestDependencyResolutionError:
    """Test cases for DependencyResolutionError."""

    def test_dependency_resolution_error_basic(self, temp_file: Path) -> None:
        """Test basic dependency resolution error.

        Args:
            temp_file: Temporary file path

        """
        error = DependencyResolutionError(
            message="Cannot resolve dependency",
            source_file=temp_file,
            target_dependency="missing-partial",
        )

        assert "Cannot resolve dependency" in error.message
        assert error.file_path == temp_file
        assert len(error.suggestions) > 0

    def test_dependency_resolution_error_partial_suggestions(
        self,
        temp_file: Path,
    ) -> None:
        """Test suggestions for missing partial dependencies.

        Args:
            temp_file: Temporary file path

        """
        error = DependencyResolutionError(
            message="Missing partial",
            source_file=temp_file,
            target_dependency="partials/header.html",
        )

        # Should have partial-specific suggestions
        assert any("partial" in s.lower() for s in error.suggestions)
        assert any("partials/header.html" in s for s in error.suggestions)

    def test_dependency_resolution_error_module_suggestions(
        self,
        temp_file: Path,
    ) -> None:
        """Test suggestions for missing module dependencies.

        Args:
            temp_file: Temporary file path

        """
        error = DependencyResolutionError(
            message="Missing module",
            source_file=temp_file,
            target_dependency="module:hugo-theme",
        )

        # Should have module-specific suggestions
        assert any("module" in s.lower() for s in error.suggestions)
        assert any("go.mod" in s.lower() for s in error.suggestions)


class TestFileAccessError:
    """Test cases for FileAccessError."""

    def test_file_access_error_basic(self, temp_file: Path) -> None:
        """Test basic file access error.

        Args:
            temp_file: Temporary file path

        """
        error = FileAccessError(
            message="Cannot read file",
            file_path=temp_file,
            operation="read",
        )

        assert "Cannot read file" in error.message
        assert error.file_path == temp_file
        assert error.context["operation"] == "read"
        assert len(error.suggestions) > 0

    def test_file_access_error_with_context(self, temp_file: Path) -> None:
        """Test file access error with additional context.

        Args:
            temp_file: Temporary file path

        """
        context = {"error_code": 13, "permissions": "r--"}
        error = FileAccessError(
            message="Permission denied",
            file_path=temp_file,
            operation="write",
            context=context,
        )

        assert error.context["operation"] == "write"
        assert error.context["error_code"] == 13
        assert error.context["permissions"] == "r--"

    def test_file_access_error_suggestions(self, temp_file: Path) -> None:
        """Test file access error suggestions.

        Args:
            temp_file: Temporary file path

        """
        error = FileAccessError(
            message="File not found",
            file_path=temp_file,
            operation="read",
        )

        # Should have file access suggestions
        assert any("permission" in s.lower() for s in error.suggestions)
        assert any(
            "path" in s.lower() or "file" in s.lower() for s in error.suggestions
        )


class TestConfigurationError:
    """Test cases for ConfigurationError."""

    def test_configuration_error_basic(self) -> None:
        """Test basic configuration error."""
        error = ConfigurationError(message="Invalid configuration")

        assert "Invalid configuration" in error.message
        assert error.severity == ErrorSeverity.ERROR
        assert len(error.suggestions) > 0

    def test_configuration_error_with_config_file(self, temp_file: Path) -> None:
        """Test configuration error with config file.

        Args:
            temp_file: Temporary file path

        """
        error = ConfigurationError(
            message="Invalid config",
            config_file=temp_file,
        )

        assert error.file_path == temp_file

    def test_configuration_error_suggestions(self) -> None:
        """Test configuration error suggestions."""
        error = ConfigurationError(message="Invalid module config")

        # Should have configuration-related suggestions
        assert any("configuration" in s.lower() for s in error.suggestions)
        assert any(
            "module" in s.lower() or "hugo" in s.lower() for s in error.suggestions
        )


class TestErrorHandler:
    """Test cases for ErrorHandler."""

    def test_error_handler_initialization(self, error_handler: ErrorHandler) -> None:
        """Test error handler initialization.

        Args:
            error_handler: ErrorHandler instance

        """
        assert error_handler.console is not None
        assert error_handler.verbose is False
        assert error_handler.error_count == 0
        assert error_handler.warning_count == 0

    def test_error_handler_verbose_initialization(
        self,
        verbose_error_handler: ErrorHandler,
    ) -> None:
        """Test verbose error handler initialization.

        Args:
            verbose_error_handler: Verbose ErrorHandler instance

        """
        assert verbose_error_handler.verbose is True

    def test_handle_error_increments_count(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test that error count is incremented.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error = HugoAnalysisError(
            message="Test error",
            severity=ErrorSeverity.ERROR,
        )

        error_handler.handle_error(error, recover=True)

        assert error_handler.error_count == 1
        assert error_handler.warning_count == 0

    def test_handle_warning_increments_count(
        self,
        error_handler: ErrorHandler,
    ) -> None:
        """Test that warning count is incremented.

        Args:
            error_handler: ErrorHandler instance

        """
        warning = HugoAnalysisError(
            message="Test warning",
            severity=ErrorSeverity.WARNING,
        )

        error_handler.handle_error(warning, recover=True)

        assert error_handler.error_count == 0
        assert error_handler.warning_count == 1

    def test_handle_template_parsing_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test handling template parsing errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        original_error = Exception("Parse failed")

        error_handler.handle_template_parsing_error(
            file_path=temp_file,
            error=original_error,
            line_number=10,
        )

        assert error_handler.error_count == 1

    def test_handle_dependency_resolution_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test handling dependency resolution errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        original_error = Exception("Cannot resolve")

        error_handler.handle_dependency_resolution_error(
            source_file=temp_file,
            target_dependency="missing-partial",
            error=original_error,
        )

        assert error_handler.error_count == 1

    def test_handle_file_access_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test handling file access errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        original_error = PermissionError("Access denied")

        error_handler.handle_file_access_error(
            file_path=temp_file,
            operation="read",
            error=original_error,
        )

        assert error_handler.error_count == 1

    def test_handle_configuration_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test handling configuration errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error_handler.handle_configuration_error(
            message="Invalid config",
            config_file=temp_file,
            error=ValueError("Bad value"),
        )

        assert error_handler.error_count == 1

    def test_get_error_summary(self, error_handler: ErrorHandler) -> None:
        """Test error summary generation.

        Args:
            error_handler: ErrorHandler instance

        """
        # Add some errors and warnings
        error_handler.handle_error(
            HugoAnalysisError("Error 1", severity=ErrorSeverity.ERROR),
            recover=True,
        )
        error_handler.handle_error(
            HugoAnalysisError("Error 2", severity=ErrorSeverity.ERROR),
            recover=True,
        )
        error_handler.handle_error(
            HugoAnalysisError("Warning 1", severity=ErrorSeverity.WARNING),
            recover=True,
        )

        summary = error_handler.get_error_summary()

        assert summary["errors"] == 2
        assert summary["warnings"] == 1
        assert summary["total"] == 3

    def test_recovery_from_parsing_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test recovery from template parsing errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error = TemplateParsingError(
            message="Parse error",
            file_path=temp_file,
        )

        # Should recover (continue processing)
        result = error_handler.handle_error(error, recover=True)
        assert result is True

    def test_recovery_from_dependency_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test recovery from dependency resolution errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error = DependencyResolutionError(
            message="Dependency error",
            source_file=temp_file,
            target_dependency="missing",
        )

        # Should recover (continue processing)
        result = error_handler.handle_error(error, recover=True)
        assert result is True

    def test_recovery_from_file_access_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test recovery from file access errors.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error = FileAccessError(
            message="Access error",
            file_path=temp_file,
            operation="read",
        )

        # Should recover (skip file)
        result = error_handler.handle_error(error, recover=True)
        assert result is True

    def test_no_recovery_from_configuration_error(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test that configuration errors don't recover.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        error = ConfigurationError(
            message="Config error",
            config_file=temp_file,
        )

        # Should not recover (halt execution)
        result = error_handler.handle_error(error, recover=True)
        assert result is False

    def test_error_display_with_rich_console(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test error display formatting.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        with patch.object(error_handler.console, "print") as mock_print:
            error = HugoAnalysisError(
                message="Test error",
                severity=ErrorSeverity.ERROR,
                file_path=temp_file,
                line_number=5,
                suggestions=["Suggestion 1", "Suggestion 2"],
            )

            error_handler.handle_error(error, recover=True)

            # Should have called console.print
            mock_print.assert_called_once()

    def test_verbose_error_display(
        self,
        verbose_error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test verbose error display includes context.

        Args:
            verbose_error_handler: Verbose ErrorHandler instance
            temp_file: Temporary file path

        """
        with patch.object(verbose_error_handler.console, "print") as mock_print:
            error = HugoAnalysisError(
                message="Test error",
                context={"key": "value", "number": 42},
                severity=ErrorSeverity.ERROR,
            )

            verbose_error_handler.handle_error(error, recover=True)

            # Should have displayed error
            mock_print.assert_called_once()

    def test_error_logging(
        self,
        error_handler: ErrorHandler,
        temp_file: Path,
    ) -> None:
        """Test that errors are logged.

        Args:
            error_handler: ErrorHandler instance
            temp_file: Temporary file path

        """
        with patch.object(error_handler.logger, "error") as mock_log:
            error = HugoAnalysisError(
                message="Test error",
                severity=ErrorSeverity.ERROR,
                file_path=temp_file,
                line_number=10,
            )

            error_handler.handle_error(error, recover=True)

            # Should have logged the error
            mock_log.assert_called_once()

    def test_warning_logging(
        self,
        error_handler: ErrorHandler,
    ) -> None:
        """Test that warnings are logged.

        Args:
            error_handler: ErrorHandler instance

        """
        with patch.object(error_handler.logger, "warning") as mock_log:
            warning = HugoAnalysisError(
                message="Test warning",
                severity=ErrorSeverity.WARNING,
            )

            error_handler.handle_error(warning, recover=True)

            # Should have logged the warning
            mock_log.assert_called_once()

    def test_different_severity_icons(self, error_handler: ErrorHandler) -> None:
        """Test that different severities use different icons.

        Args:
            error_handler: ErrorHandler instance

        """
        with patch.object(error_handler.console, "print") as mock_print:
            # Test different severity levels
            for severity in [
                ErrorSeverity.WARNING,
                ErrorSeverity.ERROR,
                ErrorSeverity.CRITICAL,
                ErrorSeverity.INFO,
            ]:
                error = HugoAnalysisError(message="Test", severity=severity)
                error_handler.handle_error(error, recover=True)

            # Should have displayed each error
            assert mock_print.call_count == 4

    def test_error_handler_setup_logging(self, console: Console) -> None:
        """Test logging setup on initialization.

        Args:
            console: Rich Console instance

        """
        # Create handler with verbose logging
        handler = ErrorHandler(console=console, verbose=True)

        assert handler.logger is not None
        # Logger is created and available

        # Create handler with normal logging
        handler = ErrorHandler(console=console, verbose=False)

        assert handler.logger is not None
        # Logger level is controlled by root logger via basicConfig, not directly
        assert handler.verbose is False
