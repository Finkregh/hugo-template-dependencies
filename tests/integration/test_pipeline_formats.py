"""Integration tests for output format functionality."""

import json
import subprocess
import tempfile
from pathlib import Path

from hugo_template_dependencies.cli import analyze


class TestPipelineFormats:
    """Test suite for output format generation and CLI integration."""

    def test_json_output_format(self, temp_hugo_project) -> None:
        """Test JSON format output generation."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            analyze(
                project_path=temp_hugo_project,
                format="json",
                output_file=output_path,
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=True,
                verbose=False,
                debug=False,
            )

            # Parse JSON output
            result = json.loads(output_path.read_text())

            # Verify JSON structure
            assert "nodes" in result, "JSON output should have 'nodes' key"
            assert "edges" in result, "JSON output should have 'edges' key"
            assert isinstance(result["nodes"], list), "Nodes should be a list"
            assert isinstance(result["edges"], list), "Edges should be a list"

            # Verify node structure
            if result["nodes"]:
                node = result["nodes"][0]
                assert "id" in node, "Nodes should have 'id' field"
                assert "type" in node, "Nodes should have 'type' field"

            # Verify edge structure
            if result["edges"]:
                edge = result["edges"][0]
                assert "source" in edge, "Edges should have 'source' field"
                assert "target" in edge, "Edges should have 'target' field"
        finally:
            # Clean up
            if output_path.exists():
                output_path.unlink()

    def test_mermaid_output_format(self, temp_hugo_project) -> None:
        """Test Mermaid format output generation."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            analyze(
                project_path=temp_hugo_project,
                format="mermaid",
                output_file=output_path,
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=True,
                verbose=False,
                debug=False,
            )

            result = output_path.read_text()

            # Check Mermaid syntax (may have header with %%{...}%%)
            assert "graph TD" in result, "Mermaid output should contain 'graph TD'"
            assert "-->" in result, "Mermaid output should contain dependency arrows"

            # Check that sanitized node IDs are present
            assert (
                "baseof_html" in result or "baseof.html" in result
            ), "baseof template should be in output"
        finally:
            # Clean up
            if output_path.exists():
                output_path.unlink()

    def test_dot_output_format(self, temp_hugo_project: Path) -> None:
        """Test DOT format output generation."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".dot",
            delete=False,
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            analyze(
                project_path=temp_hugo_project,
                format="dot",
                output_file=output_path,
                include_modules=False,
                show_progress=False,
                less_verbose=False,
                quiet=True,
                verbose=False,
                debug=False,
            )

            result = output_path.read_text()

            # Check DOT syntax
            assert "digraph" in result, "DOT output should contain 'digraph'"
            assert "->" in result, "DOT output should contain dependency arrows"
            assert result.rstrip().endswith(
                "}",
            ), "DOT output should end with closing brace"
        finally:
            # Clean up
            if output_path.exists():
                output_path.unlink()

    def test_cli_integration(self, temp_hugo_project) -> None:
        """Test CLI integration with the analysis pipeline."""
        # Test running the CLI command directly
        cmd = [
            "uv",
            "run",
            "hugo-template-dependencies",
            "analyze",
            "--format",
            "json",
            str(temp_hugo_project),
        ]

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=temp_hugo_project,
        )

        assert result.returncode == 0, f"CLI command failed: {result.stderr}"

        # Verify JSON output
        graph_data = json.loads(result.stdout)
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) > 0, "Should find template nodes"
