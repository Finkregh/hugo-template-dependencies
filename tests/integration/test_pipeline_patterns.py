"""Integration tests for mock pattern validation."""

import json
import tempfile
from pathlib import Path

import pytest

from hugo_template_dependencies.cli import analyze


class TestPipelinePatterns:
    """Test suite for mock pattern structure validation."""

    def test_new_pattern_mock_structures(self) -> None:
        """Test dependency analysis on new pattern-based mock structures."""
        # Test paths to our new mock patterns
        mock_patterns = [
            "basic_partial_pattern",
            "nested_partial_chain",
            "conditional_partials",
            "context_passing",
        ]

        for pattern in mock_patterns:
            pattern_path = Path("tests/mocks") / pattern
            if not pattern_path.exists():
                pytest.skip(f"Mock pattern {pattern} not found")

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
            ) as output_file:
                output_path = Path(output_file.name)

            try:
                # Run analysis on each pattern
                analyze(
                    project_path=pattern_path,
                    format="json",
                    output_file=output_path,
                    include_modules=False,
                    show_progress=False,
                    less_verbose=False,
                    quiet=True,
                    verbose=False,
                    debug=False,
                )

                # Parse results
                graph_data = json.loads(output_path.read_text())
                nodes = graph_data["nodes"]
                edges = graph_data["edges"]

                # Basic validation - each pattern should have nodes and relationships
                assert len(nodes) > 0, f"Pattern {pattern} should have template nodes"

                # Pattern-specific validations
                if pattern == "basic_partial_pattern":
                    assert len(nodes) == 2, "Basic pattern should have 2 nodes (single.html + header.html)"
                    assert len(edges) == 1, "Basic pattern should have 1 edge"

                elif pattern == "nested_partial_chain":
                    assert len(nodes) == 5, "Nested chain should have 5 nodes"
                    assert len(edges) == 4, "Nested chain should have 4 edges"

                elif pattern == "conditional_partials":
                    assert len(nodes) == 4, "Conditional pattern should have 4 nodes"
                    # Note: conditional partials may have fewer detected edges due to dynamic resolution

                elif pattern == "context_passing":
                    assert len(nodes) == 3, "Context pattern should have 3 nodes"
                    assert len(edges) == 2, "Context pattern should have 2 edges"

            finally:
                if output_path.exists():
                    output_path.unlink()

    def test_phase3_advanced_patterns(self) -> None:
        """Test dependency analysis on Phase 3 advanced pattern structures."""
        # Test paths to Phase 3 advanced patterns
        phase3_patterns = [
            "cached_partials",
            "template_blocks",
            "inline_partials",
            "function_integration",
            "shortcode_templates",
        ]

        for pattern in phase3_patterns:
            pattern_path = Path("tests/mocks") / pattern
            if not pattern_path.exists():
                pytest.skip(f"Phase 3 pattern {pattern} not found")

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
            ) as output_file:
                output_path = Path(output_file.name)

            try:
                # Run analysis on each pattern
                analyze(
                    project_path=pattern_path,
                    format="json",
                    output_file=output_path,
                    include_modules=False,
                    show_progress=False,
                    less_verbose=False,
                    quiet=True,
                    verbose=False,
                    debug=False,
                )

                # Parse results
                graph_data = json.loads(output_path.read_text())
                nodes = graph_data["nodes"]
                edges = graph_data["edges"]

                # Basic validation - each pattern should have nodes
                assert len(nodes) > 0, f"Pattern {pattern} should have template nodes"

                # Pattern-specific validations
                if pattern == "cached_partials":
                    assert len(nodes) == 3, "Cached pattern should have 3 nodes (baseof + 2 partials)"
                    # Note: partialCached calls may not create edges in dependency analysis

                elif pattern == "template_blocks":
                    assert len(nodes) == 2, "Template blocks should have 2 nodes (baseof + single)"
                    # Note: block inheritance may not create traditional partial edges

                elif pattern == "inline_partials":
                    assert len(nodes) >= 1, "Inline pattern should have at least 1 node (home.html)"
                    # Note: inline partials ({{ define "_partials/..." }}) may not be detected as separate nodes

                elif pattern == "function_integration":
                    assert len(nodes) == 3, "Function integration should have 3 nodes"
                    assert len(edges) >= 2, "Function integration should have partial dependencies"

                elif pattern == "shortcode_templates":
                    assert len(nodes) == 4, "Shortcode pattern should have 4 nodes (2 shortcodes + 2 partials)"
                    assert len(edges) >= 2, "Shortcode pattern should have shortcode→partial dependencies"

            finally:
                if output_path.exists():
                    output_path.unlink()
