"""Test template parser logic for dependency extraction."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from hugo_template_dependencies.analyzer.template_parser import HugoTemplateParser
from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType


class TestHugoTemplateParser:
    """Test suite for HugoTemplateParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return HugoTemplateParser()

    def test_extract_partial_dependencies(self, parser):
        """Test extraction of partial dependencies from template content."""
        content = """{{ partial "header.html" . }}
        <main>
            {{ partial "components/sidebar.html" .Params }}
        </main>
        {{ partial "footer.html" . }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/single.html")
        template_node.template_type = TemplateType.SINGLE

        dependencies = parser.extract_dependencies(content)

        partial_deps = [dep for dep in dependencies if dep["type"] == "partial"]
        assert len(partial_deps) == 3

        # Check specific partial names
        partial_names = [dep["target"] for dep in partial_deps]
        assert "header.html" in partial_names
        assert "components/sidebar.html" in partial_names
        assert "footer.html" in partial_names

    def test_extract_partial_dependencies_with_assignments(self, parser):
        """Test extraction of partial dependencies with variable assignments."""
        content = """{{ $header = partial "header.html" . }}
        <main>
            {{- $sidebar = partial "components/sidebar.html" .Params -}}
            {{ $content := partial "content/main.html" . }}
        </main>
        {{ $footer := partial "footer.html" . }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/single.html")
        template_node.template_type = TemplateType.SINGLE

        dependencies = parser.extract_dependencies(content)

        partial_deps = [dep for dep in dependencies if dep["type"] == "partial"]
        assert len(partial_deps) == 4

        # Check specific partial names
        partial_names = [dep["target"] for dep in partial_deps]
        assert "header.html" in partial_names
        assert "components/sidebar.html" in partial_names
        assert "content/main.html" in partial_names
        assert "footer.html" in partial_names

    def test_extract_template_dependencies(self, parser):
        """Test extraction of template dependencies."""
        content = """{{ template "_internal/google_analytics.html" . }}
        {{ template "partials/head.html" . }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/baseof.html")
        template_node.template_type = TemplateType.BASEOF

        dependencies = parser.extract_dependencies(content)

        template_deps = [dep for dep in dependencies if dep["type"] == "template"]
        assert len(template_deps) == 2

        targets = [dep["target"] for dep in template_deps]
        assert "_internal/google_analytics.html" in targets
        assert "partials/head.html" in targets

    def test_extract_conditional_dependencies(self, parser):
        """Test extraction of dependencies within conditional blocks."""
        content = """{{ if .Site.GoogleAnalytics }}
            {{ partial "analytics.html" . }}
        {{ end }}
        {{ with .Params.sidebar }}
            {{ partial "sidebar.html" . }}
        {{ end }}
        {{ range .Pages }}
            {{ partial "article-summary.html" . }}
        {{ end }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/list.html")
        template_node.template_type = TemplateType.LIST

        dependencies = parser.extract_dependencies(content)

        partial_deps = [dep for dep in dependencies if dep.type == "partial"]
        assert len(partial_deps) == 3

        # Check that conditional dependencies are marked
        conditional_deps = [dep for dep in partial_deps if dep.is_conditional]
        assert len(conditional_deps) == 3  # All should be conditional

        # Check control flow dependencies
        control_deps = [dep for dep in dependencies if dep.type in ["if", "with", "range"]]
        assert len(control_deps) >= 3

    def test_extract_block_dependencies(self, parser):
        """Test extraction of block define/yield dependencies."""
        content = """{{ define "main" }}
        <h1>{{ .Title }}</h1>
        {{ block "content" . }}{{ end }}
        {{ block "sidebar" . }}
            Default sidebar content
        {{ end }}
        {{ end }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/single.html")
        template_node.template_type = TemplateType.SINGLE

        dependencies = parser.extract_dependencies(content)

        block_deps = [dep for dep in dependencies if dep.type == "block"]
        assert len(block_deps) == 3  # main, content, sidebar

        block_names = [dep.target for dep in block_deps]
        assert "main" in block_names
        assert "content" in block_names
        assert "sidebar" in block_names

    def test_extract_shortcode_dependencies(self, parser):
        """Test extraction of shortcode dependencies."""
        content = """{{ .Content }}
        {{< youtube w7Ft2ymGmfc >}}
        {{< figure src="image.jpg" title="A figure" >}}
        {{% alert type="warning" %}}
        This is a warning.
        {{% /alert %}}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/single.html")
        template_node.template_type = TemplateType.SINGLE

        dependencies = parser.extract_dependencies(content)

        shortcode_deps = [dep for dep in dependencies if dep.type == "shortcode"]
        assert len(shortcode_deps) == 3

        shortcode_names = [dep.target for dep in shortcode_deps]
        assert "youtube" in shortcode_names
        assert "figure" in shortcode_names
        assert "alert" in shortcode_names

    def test_line_number_tracking(self, parser):
        """Test that line numbers are correctly tracked for dependencies."""
        content = """Line 1
{{ partial "header.html" . }}
Line 3
{{ partial "footer.html" . }}"""

        template_node = Mock()
        template_node.file_path = Path("layouts/_default/single.html")
        template_node.template_type = TemplateType.SINGLE

        dependencies = parser.extract_dependencies(content)

        partial_deps = [dep for dep in dependencies if dep.type == "partial"]
        assert len(partial_deps) == 2

        # Check line numbers
        header_dep = next(dep for dep in partial_deps if dep.target == "header.html")
        footer_dep = next(dep for dep in partial_deps if dep.target == "footer.html")

        assert header_dep.line_number == 2
        assert footer_dep.line_number == 4

    def test_edge_cases_parsing(self, parser):
        """Test edge cases in template parsing."""
        # Test empty content
        dependencies = parser.extract_dependencies("", Mock())
        assert dependencies == []

        # Test content with no dependencies
        content = "<h1>Static content</h1>"
        dependencies = parser.extract_dependencies(content, Mock())
        assert dependencies == []

        # Test malformed Hugo syntax - should not crash
        content = '{{ partial "incomplete'
        dependencies = parser.extract_dependencies(content, Mock())
        # Should return empty list, not crash
        assert isinstance(dependencies, list)

        # Test nested quotes
        content = '{{ partial "path/with "quotes" in name.html" . }}'
        dependencies = parser.extract_dependencies(content, Mock())
        # Should handle gracefully
