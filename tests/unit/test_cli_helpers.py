"""Tests for CLI helper functions."""

from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass


class TestCLIHelpers:
    """Test CLI helper functions."""

    def test_write_output_to_file(self) -> None:
        """Test write_output function with file output."""
        from hugo_template_dependencies.cli import analyze

        # Create temporary files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as output_file:
            output_path = Path(output_file.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir)

            # Create minimal Hugo project structure
            layouts_dir = temp_project / "layouts"
            layouts_dir.mkdir()

            # Create a simple template
            index_template = layouts_dir / "index.html"
            index_template.write_text("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1></body>
</html>""")

            try:
                # Run analysis with file output
                analyze(
                    project_path=temp_project,
                    format="json",
                    output_file=output_path,
                    include_modules=False,
                    show_progress=False,
                    less_verbose=False,
                    quiet=True,
                    verbose=False,
                    debug=False,
                )

                # Verify file was created and contains content
                assert output_path.exists()
                content = output_path.read_text()
                assert len(content) > 0
                assert "nodes" in content  # Basic JSON structure check
                assert "edges" in content

            finally:
                output_path.unlink(missing_ok=True)

    @patch("sys.stdout", new_callable=StringIO)
    def test_write_output_to_stdout(self, mock_stdout: StringIO) -> None:
        """Test write_output function with stdout output."""
        from hugo_template_dependencies.cli import analyze

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir)

            # Create minimal Hugo project structure
            layouts_dir = temp_project / "layouts"
            layouts_dir.mkdir()

            # Create a simple template
            index_template = layouts_dir / "index.html"
            index_template.write_text("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1></body>
</html>""")

            # Run analysis without output file (should go to stdout)
            # Note: typer.Option with None default accepts None at runtime despite type hint
            analyze(
                project_path=temp_project,
                format="json",
                output_file=None,  # type: ignore[arg-type]  # type: ignore[arg-type]
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=False,  # Not quiet so content gets printed
                verbose=False,
                debug=False,
            )

            # Verify content was written to stdout
            output = mock_stdout.getvalue()
            assert len(output) > 0
            assert "nodes" in output
            assert "edges" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_write_output_quiet_mode(self, mock_stdout: StringIO) -> None:
        """Test write_output function in quiet mode."""
        from hugo_template_dependencies.cli import analyze

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir)

            # Create minimal Hugo project structure
            layouts_dir = temp_project / "layouts"
            layouts_dir.mkdir()

            # Create a simple template
            index_template = layouts_dir / "index.html"
            index_template.write_text("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1></body>
</html>""")

            # Run analysis in quiet mode
            analyze(
                project_path=temp_project,
                format="json",
                output_file=None,  # type: ignore[arg-type]
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=True,  # Quiet mode
                verbose=False,
                debug=False,
            )

            # In quiet mode, no output should go to stdout (correct behavior)
            output = mock_stdout.getvalue()
            # Quiet mode should suppress output
            assert len(output) == 0

    @patch("sys.stdout", new_callable=StringIO)
    def test_mermaid_format_output(self, mock_stdout: StringIO) -> None:
        """Test that Mermaid format generates proper output to stdout."""
        from hugo_template_dependencies.cli import analyze

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir)

            # Create minimal Hugo project structure
            layouts_dir = temp_project / "layouts"
            layouts_dir.mkdir()
            partials_dir = layouts_dir / "_partials"
            partials_dir.mkdir()

            # Create templates with dependencies
            index_template = layouts_dir / "index.html"
            index_template.write_text("""<!DOCTYPE html>
<html>
<head>{{ partial "head.html" . }}</head>
<body><h1>{{ .Title }}</h1></body>
</html>""")

            head_partial = partials_dir / "head.html"
            head_partial.write_text("""<title>{{ .Title }}</title>
<meta charset="utf-8">""")

            # Run analysis with Mermaid format
            analyze(
                project_path=temp_project,
                format="mermaid",
                output_file=None,  # type: ignore[arg-type]
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=False,
                verbose=False,
                debug=False,
            )

            # Verify Mermaid content was written to stdout
            output = mock_stdout.getvalue()
            assert len(output) > 0
            assert "graph TD" in output or "flowchart TD" in output  # Mermaid syntax
            assert "-->" in output  # Mermaid dependency arrows
            assert "index.html" in output
            assert "head.html" in output

    def test_internal_template_detection(self) -> None:
        """Test detection of deprecated _internal templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir)

            # Create Hugo project structure
            layouts_dir = temp_project / "layouts"
            layouts_dir.mkdir()
            partials_dir = layouts_dir / "_partials"
            partials_dir.mkdir()

            # Create template using deprecated _internal templates
            head_partial = partials_dir / "head.html"
            head_partial.write_text("""<title>{{ .Title }}</title>
{{ template "_internal/opengraph.html" . }}
{{ template "_internal/twitter_cards.html" . }}
<meta charset="utf-8">""")

            # Create main template
            index_template = layouts_dir / "index.html"
            index_template.write_text("""<!DOCTYPE html>
<html>
<head>{{ partial "head.html" . }}</head>
<body><h1>{{ .Title }}</h1></body>
</html>""")

            # Run analysis - should detect _internal templates but not fail
            from hugo_template_dependencies.cli import analyze

            # Use file output to avoid stdout capture complexity
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as output_file:
                output_path = Path(output_file.name)

            try:
                analyze(
                    project_path=temp_project,
                    format="json",
                    output_file=output_path,
                    include_modules=False,
                    show_progress=False,
                    less_verbose=False,
                    quiet=True,  # Suppress error display for test
                    verbose=False,
                    debug=False,
                )

                # Analysis should complete successfully despite _internal template references
                assert output_path.exists()
                content = output_path.read_text()
                assert len(content) > 0
                assert "nodes" in content

                # The graph should still be generated with placeholder nodes for _internal templates
                import json

                graph_data = json.loads(content)
                nodes = graph_data["nodes"]
                node_ids = [node["id"] for node in nodes]

                # Should have the main templates
                assert any("index.html" in node_id for node_id in node_ids)
                assert any("head.html" in node_id for node_id in node_ids)

            finally:
                output_path.unlink(missing_ok=True)
