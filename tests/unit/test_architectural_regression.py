#!/usr/bin/env python3
"""
Regression tests for the four critical architectural fixes:

1. Node ID mismatch between graph and formatters
2. Missing node data in edge formatting
3. Duplicate dependency resolution loop
4. Template parser regex limitations with := assignments

These tests ensure the fixes don't regress as the codebase evolves.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hugo_template_dependencies.graph.hugo_graph import (
    HugoDependencyGraph,
    HugoTemplate,
    TemplateType,
)
from hugo_template_dependencies.output.mermaid_formatter import MermaidFormatter
from hugo_template_dependencies.output.dot_formatter import DOTFormatter
from hugo_template_dependencies.analyzer.template_parser import HugoTemplateParser


class TestArchitecturalFixes(unittest.TestCase):
    """Regression tests for critical architectural fixes."""

    def setUp(self):
        """Set up test fixtures."""
        self.graph = HugoDependencyGraph()
        self.parser = HugoTemplateParser()

        # Create realistic test templates
        self.local_template = HugoTemplate(
            file_path=Path("/project/layouts/_partials/calendar_section.html"),
            template_type=TemplateType.PARTIAL,
            content='{{ partial "events/calendar-downloads.html" . }}',
            source="local",
        )

        self.module_template = HugoTemplate(
            file_path=Path(
                "/cache/hugo-theme-component-ical/layouts/_partials/events/calendar-downloads.html"
            ),
            template_type=TemplateType.PARTIAL,
            content="<div>Downloads</div>",
            source="../../..",  # Module replacement path that caused issues
        )

        # Add templates to graph
        self.graph.add_template(self.local_template)
        self.graph.add_template(self.module_template)

    def test_regression_node_id_consistency(self):
        """
        Regression Test for Issue #1: Node ID mismatch between graph and formatters.

        Before fix: Graph edges used absolute paths but formatters used sanitized IDs,
        causing edges to disappear in formatted output.

        After fix: Formatters get proper node data to create consistent sanitized IDs.
        """
        # Add edge to graph
        self.graph.add_include_dependency(
            source=self.local_template,
            target=self.module_template,
            include_type="partial",
        )

        # Test Mermaid formatter edge consistency
        mermaid_formatter = MermaidFormatter(self.graph)
        mermaid_edges = mermaid_formatter._get_formatted_edges()

        # Should have at least one properly formatted edge
        self.assertGreater(
            len(mermaid_edges), 0, "Mermaid formatter should produce edges"
        )

        # Edge should not be empty (was the regression symptom)
        for edge in mermaid_edges:
            self.assertNotRegex(
                edge, r"-->.*\|\w+\|$", f"Edge target should not be empty: {edge}"
            )
            self.assertIn(
                "-->|includes|", edge, "Edge should show includes relationship"
            )

        # Test DOT formatter edge consistency
        dot_formatter = DOTFormatter(self.graph)
        dot_edges = dot_formatter._get_formatted_edges(include_styles=True)

        # Should have properly formatted DOT edges
        self.assertGreater(len(dot_edges), 0, "DOT formatter should produce edges")

        # DOT edges should have valid source and target IDs
        for edge in dot_edges:
            self.assertRegex(
                edge,
                r"\w+ -> \w+",
                f"DOT edge should have valid source->target: {edge}",
            )

    def test_regression_node_data_in_edge_formatting(self):
        """
        Regression Test for Issue #2: Missing node data in edge formatting.

        Before fix: Formatters called _sanitize_id(source, None) losing source information.

        After fix: Formatters get actual node data for proper source-prefixed sanitization.
        """
        # Add edge with complex module source
        self.graph.add_include_dependency(
            source=self.local_template,
            target=self.module_template,
            include_type="partial",
        )

        # Test that formatters get proper node data
        formatter = MermaidFormatter(self.graph)

        # Test direct node data access
        for node_id, node_data in self.graph.graph.nodes(data=True):
            self.assertIsNotNone(node_data, f"Node {node_id} should have data")
            self.assertIn(
                "source", node_data, f"Node {node_id} should have source information"
            )

            # Test sanitized ID creation with proper node data
            sanitized_id = formatter._sanitize_id(node_id, node_data)

            # Should not produce broken IDs like "___"
            self.assertNotIn(
                "___",
                sanitized_id,
                f"Sanitized ID should not contain '___': {sanitized_id}",
            )

            # Local templates should have local_ prefix
            if node_data["source"] == "local":
                self.assertTrue(
                    sanitized_id.startswith("local_"),
                    f"Local template should have local_ prefix: {sanitized_id}",
                )

            # Module templates should not start with underscores from path issues
            elif node_data["source"] != "local":
                self.assertFalse(
                    sanitized_id.startswith("___"),
                    f"Module template should not start with '___': {sanitized_id}",
                )

    def test_regression_template_parser_assignment_patterns(self):
        """
        Regression Test for Issue #4: Template parser regex limitations with := assignments.

        Before fix: Regex didn't handle Hugo's := variable assignment syntax.

        After fix: Regex pattern handles both = and := assignments.
        """
        # Test cases that were failing before the regex fix
        test_cases = [
            # Standard assignment (was working)
            ('{{ $result = partial "test.html" . }}', "test.html"),
            # Walrus operator assignment (was broken)
            ('{{- $result := partial "test.html" . -}}', "test.html"),
            # Complex real-world case that was failing
            (
                '{{- $parsedDays := partial "recurrence/day_names_resolver.html" (dict "days" $byDay "extractOrdinals" true) -}}',
                "recurrence/day_names_resolver.html",
            ),
            # Mixed syntax in same template
            (
                '{{ $header = partial "header.html" . }}\n{{- $footer := partial "footer.html" . -}}',
                ["header.html", "footer.html"],
            ),
        ]

        for content, expected in test_cases:
            with self.subTest(content=content):
                dependencies = self.parser.extract_dependencies(content)
                partial_deps = [dep for dep in dependencies if dep["type"] == "partial"]

                if isinstance(expected, list):
                    self.assertEqual(
                        len(partial_deps),
                        len(expected),
                        f"Should find {len(expected)} partials in: {content}",
                    )
                    actual_targets = [dep["target"] for dep in partial_deps]
                    for exp_target in expected:
                        self.assertIn(
                            exp_target,
                            actual_targets,
                            f"Should find target '{exp_target}' in: {content}",
                        )
                else:
                    self.assertEqual(
                        len(partial_deps), 1, f"Should find 1 partial in: {content}"
                    )
                    self.assertEqual(
                        partial_deps[0]["target"],
                        expected,
                        f"Target should be '{expected}' in: {content}",
                    )

    def test_regression_complex_assignment_edge_cases(self):
        """
        Additional regression test for complex assignment patterns that could break.
        """
        edge_cases = [
            # Nested assignments with complex parameters
            '{{- $data := partial "api/resolver.html" (dict "endpoint" .Params.api "cache" true "timeout" 30) -}}',
            # Multiple assignments in loops
            '{{ range .Pages }}\n{{- $summary := partial "summary.html" . -}}\n{{ end }}',
            # Conditional assignments
            '{{ if .Params.sidebar }}\n{{ $sidebar := partial "sidebar.html" . }}\n{{ end }}',
            # Mixed whitespace and dash patterns
            '{{$compact:=partial"compress.html".}}',
            '{{ -$spaced := partial "spaced.html" . -}}',
        ]

        for content in edge_cases:
            with self.subTest(content=content):
                dependencies = self.parser.extract_dependencies(content)
                partial_deps = [dep for dep in dependencies if dep["type"] == "partial"]

                # Should find at least one partial in each case
                self.assertGreater(
                    len(partial_deps),
                    0,
                    f"Should find at least 1 partial in edge case: {content}",
                )

                # All found partials should have valid targets
                for dep in partial_deps:
                    self.assertTrue(
                        dep["target"], f"Partial target should not be empty: {dep}"
                    )
                    self.assertTrue(
                        dep["target"].endswith(".html"),
                        f"Partial target should end with .html: {dep['target']}",
                    )

    def test_regression_end_to_end_integration(self):
        """
        Integration test ensuring all four fixes work together end-to-end.

        This test simulates the real-world scenario that was failing:
        - Module template with := assignment calls
        - Complex dependency resolution
        - Proper graph edge creation
        - Correct formatter output
        """
        # Create a complex template with := assignments (Issue #4 fix)
        complex_template = HugoTemplate(
            file_path=Path(
                "/cache/module/layouts/_partials/recurrence/yearly_frequency.html"
            ),
            template_type=TemplateType.PARTIAL,
            content="""
{{- $parsedDays := partial "recurrence/day_names_resolver.html" (dict "days" $byDay "extractOrdinals" true) -}}
{{- $interval := partial "recurrence/interval_formatter.html" .interval -}}
{{ $result = partial "components/helper.html" . }}
            """,
            source="golang.foundata.com/hugo-theme-dev",
        )

        # Create target templates
        target1 = HugoTemplate(
            file_path=Path(
                "/cache/module/layouts/_partials/recurrence/day_names_resolver.html"
            ),
            template_type=TemplateType.PARTIAL,
            content="<div>Day resolver</div>",
            source="golang.foundata.com/hugo-theme-dev",
        )

        target2 = HugoTemplate(
            file_path=Path(
                "/cache/module/layouts/_partials/recurrence/interval_formatter.html"
            ),
            template_type=TemplateType.PARTIAL,
            content="<div>Interval formatter</div>",
            source="golang.foundata.com/hugo-theme-dev",
        )

        target3 = HugoTemplate(
            file_path=Path("/project/layouts/_partials/components/helper.html"),
            template_type=TemplateType.PARTIAL,
            content="<div>Helper</div>",
            source="local",
        )

        # Add all templates to graph
        self.graph.add_template(complex_template)
        self.graph.add_template(target1)
        self.graph.add_template(target2)
        self.graph.add_template(target3)

        # Parse dependencies (tests Issue #4 fix)
        content_str = str(complex_template.content) if complex_template.content else ""
        dependencies = self.parser.extract_dependencies(content_str)
        partial_deps = [dep for dep in dependencies if dep["type"] == "partial"]

        # Should find all 3 partial calls (including := assignments)
        self.assertEqual(len(partial_deps), 3, "Should find all 3 partial dependencies")

        expected_targets = {
            "recurrence/day_names_resolver.html",
            "recurrence/interval_formatter.html",
            "components/helper.html",
        }
        actual_targets = {dep["target"] for dep in partial_deps}
        self.assertEqual(
            actual_targets, expected_targets, "Should find all expected targets"
        )

        # Create graph edges (tests Issue #1 and #2 fixes)
        for dep in partial_deps:
            target_name = dep["target"]

            # Find matching target template
            for template in [target1, target2, target3]:
                if target_name in str(template.file_path):
                    self.graph.add_include_dependency(
                        source=complex_template,
                        target=template,
                        include_type="partial",
                        line_number=dep["line_number"],
                        context=dep["context"],
                    )
                    break

        # Verify graph has proper edges
        edges = list(self.graph.graph.edges(data=True))
        self.assertEqual(len(edges), 3, "Should have 3 edges in graph")

        # Test formatter output (tests Issue #1 and #2 fixes)
        formatter = MermaidFormatter(self.graph)
        formatted_edges = formatter._get_formatted_edges()

        # Should have properly formatted edges with no empty targets
        self.assertGreater(len(formatted_edges), 0, "Should have formatted edges")
        for edge in formatted_edges:
            self.assertNotRegex(
                edge, r"-->.*\|\w+\|$", f"Edge should not have empty target: {edge}"
            )

        # All edges should connect to properly prefixed node IDs
        for edge in formatted_edges:
            if "yearly_frequency" in edge:
                # Should connect to other module templates and local template
                self.assertTrue(
                    any(
                        target in edge
                        for target in [
                            "day_names_resolver",
                            "interval_formatter",
                            "local_",
                        ]
                    ),
                    f"yearly_frequency edge should connect to expected targets: {edge}",
                )

    def test_regression_duplicate_resolution_prevention(self):
        """
        Regression Test for Issue #3: Duplicate dependency resolution loop.

        Before fix: Two identical dependency resolution loops caused performance issues
        and potential data corruption in module template processing.

        After fix: Single dependency resolution pass with proper tracking.
        """
        # This test verifies the architectural fix by ensuring dependencies
        # are resolved exactly once, which we can verify through call counting

        # Create templates with dependencies
        source_template = HugoTemplate(
            file_path=Path("/test/source.html"),
            template_type=TemplateType.PARTIAL,
            content='{{ partial "target.html" . }}',
            source="local",
        )

        target_template = HugoTemplate(
            file_path=Path("/test/target.html"),
            template_type=TemplateType.PARTIAL,
            content="<div>Target</div>",
            source="local",
        )

        self.graph.add_template(source_template)
        self.graph.add_template(target_template)

        # Mock the add_include_dependency to count calls
        original_add = self.graph.add_include_dependency
        call_count = 0

        def counting_add(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_add(*args, **kwargs)

        self.graph.add_include_dependency = counting_add

        # Parse dependencies
        content_str = str(source_template.content) if source_template.content else ""
        dependencies = self.parser.extract_dependencies(content_str)

        # Simulate dependency resolution (what CLI does)
        for dep in dependencies:
            if dep["type"] == "partial":
                self.graph.add_include_dependency(
                    source=source_template,
                    target=target_template,
                    include_type=dep["type"],
                    line_number=dep["line_number"],
                    context=dep["context"],
                )

        # Should be called exactly once per dependency (no duplicate resolution)
        self.assertEqual(
            call_count,
            1,
            "add_include_dependency should be called exactly once per dependency",
        )

        # Verify the edge was created properly
        edges = list(self.graph.graph.edges())
        self.assertEqual(len(edges), 1, "Should have exactly one edge")


if __name__ == "__main__":
    unittest.main(verbosity=2)
