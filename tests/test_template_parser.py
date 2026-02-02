"""Tests for the enhanced Hugo template parser."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from hugo_template_dependencies.analyzer.template_parser import (
    HugoTemplateParser,
)
from hugo_template_dependencies.graph.hugo_graph import TemplateType


class TestHugoTemplateParser:
    """Test cases for the enhanced Hugo template parser."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = HugoTemplateParser()

    def test_parse_basic_partial(self) -> None:
        """Test parsing basic partial includes."""
        content = '{{ partial "header.html" . }}'
        dependencies = self.parser.extract_dependencies(content)

        assert len(dependencies) == 1
        assert dependencies[0]["type"] == "partial"
        assert dependencies[0]["target"] == "header.html"
        assert dependencies[0]["line_number"] == 1
        assert not dependencies[0]["is_conditional"]

    def test_parse_template_with_comments(self) -> None:
        """Test parsing templates with Hugo and HTML comments."""
        content = """
        {{/* This is a comment with {{ partial "ignored.html" . }} */}}
        <!-- HTML comment with {{ template "also-ignored.html" . }} -->
        {{ partial "real-partial.html" . }}
        """
        dependencies = self.parser.extract_dependencies(content)

        # Should only find the real partial, not the ones in comments
        assert len(dependencies) == 1
        assert dependencies[0]["target"] == "real-partial.html"

    def test_parse_nested_hugo_comments(self) -> None:
        """Test parsing nested Hugo comments."""
        content = """
        {{/* Outer comment {{/* nested comment */}} still in comment */}}
        {{ partial "visible.html" . }}
        """
        dependencies = self.parser.extract_dependencies(content)

        assert len(dependencies) == 1
        assert dependencies[0]["target"] == "visible.html"

    def test_parse_range_blocks(self) -> None:
        """Test parsing range control flow."""
        content = """
        {{ range .Pages }}
            {{ partial "page-item.html" . }}
        {{ end }}
        """
        dependencies = self.parser.extract_dependencies(content)

        # Should find both the range and the conditional partial
        partial_deps = [d for d in dependencies if d["type"] == "partial"]
        range_deps = [d for d in dependencies if d["type"] == "range"]

        assert len(partial_deps) == 1
        assert len(range_deps) == 1
        assert partial_deps[0]["is_conditional"]  # Partial is inside range

    def test_parse_if_blocks(self) -> None:
        """Test parsing if/else control flow."""
        content = """
        {{ if .Params.show }}
            {{ partial "shown.html" . }}
        {{ else }}
            {{ partial "hidden.html" . }}
        {{ end }}
        """
        dependencies = self.parser.extract_dependencies(content)

        partial_deps = [d for d in dependencies if d["type"] == "partial"]
        if_deps = [d for d in dependencies if d["type"] == "if"]

        assert len(partial_deps) == 2
        assert len(if_deps) == 1

        # Both partials should be conditional
        for partial in partial_deps:
            assert partial["is_conditional"]

    def test_parse_with_blocks(self) -> None:
        """Test parsing with control flow."""
        content = """
        {{ with .Params.data }}
            {{ partial "data-display.html" . }}
        {{ end }}
        """
        dependencies = self.parser.extract_dependencies(content)

        partial_deps = [d for d in dependencies if d["type"] == "partial"]
        with_deps = [d for d in dependencies if d["type"] == "with"]

        assert len(partial_deps) == 1
        assert len(with_deps) == 1
        assert partial_deps[0]["is_conditional"]

    def test_parse_block_definitions(self) -> None:
        """Test parsing block definitions."""
        content = """
        {{ define "header" }}
            <h1>{{ .Title }}</h1>
            {{ partial "nav.html" . }}
        {{ end }}
        """
        dependencies = self.parser.extract_dependencies(content)

        block_deps = [d for d in dependencies if d["type"] == "block_definition"]
        partial_deps = [d for d in dependencies if d["type"] == "partial"]

        assert len(block_deps) == 1
        assert len(partial_deps) == 1
        assert block_deps[0]["target"] == "header"
        assert partial_deps[0]["is_conditional"]  # Inside block definition

    def test_parse_block_usage(self) -> None:
        """Test parsing block usage."""
        content = """
        {{ block "main" . }}
            <p>Default content</p>
        {{ end }}
        """
        dependencies = self.parser.extract_dependencies(content)

        block_deps = [d for d in dependencies if d["type"] == "block_usage"]

        assert len(block_deps) == 1
        assert block_deps[0]["target"] == "main"

    def test_parse_enhanced_context(self) -> None:
        """Test enhanced context extraction."""
        content = 'Some content before {{ partial "test.html" . }} some content after'
        dependencies = self.parser.extract_dependencies(content)

        assert len(dependencies) == 1
        context = dependencies[0]["context"]
        assert ">>>" in context
        assert "<<<" in context
        assert "test.html" in context

    def test_parse_multiline_templates(self) -> None:
        """Test parsing multiline template functions."""
        content = """
        {{ partial
           "multiline.html"
           (dict "param" "value") }}
        """
        dependencies = self.parser.extract_dependencies(content)

        assert len(dependencies) == 1
        assert dependencies[0]["target"] == "multiline.html"
        assert dependencies[0]["parameters"] == '(dict "param" "value")'

    def test_parse_template_with_parameters(self) -> None:
        """Test parsing templates with parameters."""
        content = '{{ template "pagination.html" (dict "context" . "items" .Pages) }}'
        dependencies = self.parser.extract_dependencies(content)

        assert len(dependencies) == 1
        assert dependencies[0]["type"] == "template"
        assert dependencies[0]["target"] == "pagination.html"
        assert "dict" in dependencies[0]["parameters"]

    def test_parse_file_nonexistent(self) -> None:
        """Test parsing non-existent file fails gracefully."""
        try:
            self.parser.parse_file(Path("/nonexistent/file.html"))
            msg = "Should have raised FileNotFoundError"
            raise AssertionError(msg)
        except FileNotFoundError as e:
            assert "Template file not found" in str(e)

    def test_parse_file_integration(self) -> None:
        """Test parsing a complete template file."""
        content = """{{/* Template with various dependencies */}}
<!DOCTYPE html>
<html>
<head>
    {{ partial "head.html" . }}
</head>
<body>
    {{ block "header" . }}
        {{ partial "default-header.html" . }}
    {{ end }}

    {{ if .Params.showSidebar }}
        {{ partial "sidebar.html" . }}
    {{ end }}

    <main>
        {{ range .Pages }}
            {{ template "page-summary.html" . }}
        {{ end }}
    </main>

    {{ with .Params.footer }}
        {{ partial "footer.html" . }}
    {{ end }}
</body>
</html>"""

        with NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)

        try:
            template = self.parser.parse_file(temp_path)

            assert template.template_type == TemplateType.TEMPLATE
            assert template.content == content
            assert len(template.dependencies) > 0

            # Check for expected dependencies
            partial_deps = [d for d in template.dependencies if d["type"] == "partial"]
            template_deps = [d for d in template.dependencies if d["type"] == "template"]
            block_deps = [d for d in template.dependencies if d["type"] == "block_usage"]
            control_deps = [d for d in template.dependencies if d["type"] in ["if", "range", "with"]]

            assert len(partial_deps) >= 3  # head.html, default-header.html, sidebar.html, footer.html
            assert len(template_deps) >= 1  # page-summary.html
            assert len(block_deps) >= 1  # header block
            assert len(control_deps) >= 3  # if, range, with

            # Verify conditional detection
            conditional_partials = [d for d in partial_deps if d["is_conditional"]]
            assert len(conditional_partials) >= 2  # sidebar and footer should be conditional

        finally:
            temp_path.unlink()

    def test_error_handling_malformed_syntax(self) -> None:
        """Test error handling for malformed template syntax."""
        # Test graceful handling - parser should not crash on malformed content
        malformed_content = "{{ partial incomplete"
        dependencies = self.parser.extract_dependencies(malformed_content)

        # Should return empty list rather than crashing
        assert isinstance(dependencies, list)

    def test_empty_content(self) -> None:
        """Test handling of empty content."""
        dependencies = self.parser.extract_dependencies("")
        assert dependencies == []

        dependencies = self.parser.extract_dependencies("   \n\t  ")
        assert dependencies == []
