"""Integration tests for end-to-end dependency analysis pipeline."""

import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import json

from hugo_template_dependencies.cli import analyze_dependencies


class TestIntegrationPipeline:
    """Test suite for complete dependency analysis pipeline."""

    @pytest.fixture
    def temp_hugo_project(self):
        """Create a temporary Hugo project for testing."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create directory structure
        layouts_dir = temp_dir / "layouts"
        partials_dir = layouts_dir / "_partials"
        components_dir = partials_dir / "components"
        shortcodes_dir = layouts_dir / "shortcodes"
        default_dir = layouts_dir / "_default"

        layouts_dir.mkdir(parents=True)
        partials_dir.mkdir(parents=True)
        components_dir.mkdir(parents=True)
        shortcodes_dir.mkdir(parents=True)
        default_dir.mkdir(parents=True)

        # Create test templates
        templates = {
            # Base template
            default_dir / "baseof.html": """<!DOCTYPE html>
<html>
<head>
    {{ partial "head.html" . }}
</head>
<body>
    {{ partial "header.html" . }}
    <main>
        {{ block "main" . }}{{ end }}
    </main>
    {{ partial "footer.html" . }}
</body>
</html>""",
            # Single page template
            default_dir / "single.html": """{{ define "main" }}
<article>
    <h1>{{ .Title }}</h1>
    {{ .Content }}
    {{ if .Params.show_related }}
        {{ partial "components/related-posts.html" . }}
    {{ end }}
</article>
{{ end }}""",
            # List page template
            default_dir / "list.html": """{{ define "main" }}
<section class="posts">
    {{ range .Pages }}
        {{ partial "components/post-summary.html" . }}
    {{ end }}
</section>
{{ end }}""",
            # Head partial
            partials_dir / "head.html": """<meta charset="utf-8">
<title>{{ .Title }}</title>
{{ partial "analytics.html" . }}""",
            # Header partial
            partials_dir / "header.html": """<header>
    {{ partial "components/navigation.html" . }}
</header>""",
            # Footer partial
            partials_dir / "footer.html": """<footer>
    {{ partial "components/copyright.html" . }}
</footer>""",
            # Analytics partial
            partials_dir / "analytics.html": """{{ if .Site.GoogleAnalytics }}
<script async src="https://www.googletagmanager.com/gtag/js?id={{ .Site.GoogleAnalytics }}"></script>
{{ end }}""",
            # Component partials
            components_dir / "navigation.html": """<nav>
    {{ range .Site.Menus.main }}
        <a href="{{ .URL }}">{{ .Name }}</a>
    {{ end }}
</nav>""",
            components_dir / "copyright.html": """<p>&copy; {{ now.Year }} {{ .Site.Title }}</p>""",
            components_dir / "post-summary.html": """<article class="summary">
    <h2><a href="{{ .Permalink }}">{{ .Title }}</a></h2>
    {{ .Summary }}
    {{ partial "components/post-meta.html" . }}
</article>""",
            components_dir / "post-meta.html": """<div class="meta">
    <time>{{ .Date.Format "2006-01-02" }}</time>
    {{ if .Params.tags }}
        {{ partial "components/tags.html" . }}
    {{ end }}
</div>""",
            components_dir / "tags.html": """<ul class="tags">
    {{ range .Params.tags }}
        <li><a href="/tags/{{ . | urlize }}">{{ . }}</a></li>
    {{ end }}
</ul>""",
            components_dir / "related-posts.html": """<section class="related">
    <h3>Related Posts</h3>
    {{ range first 3 .Site.RegularPages.Related . }}
        {{ partial "components/post-summary.html" . }}
    {{ end }}
</section>""",
            # Shortcode
            shortcodes_dir / "youtube.html": """<div class="youtube">
    <iframe src="https://www.youtube.com/embed/{{ .Get 0 }}"></iframe>
</div>""",
        }

        # Write all template files
        for template_path, content in templates.items():
            template_path.write_text(content)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_complete_analysis_pipeline(self, temp_hugo_project):
        """Test the complete dependency analysis pipeline."""
        # Run analysis on the test project
        result = analyze_dependencies(
            layouts_dir=temp_hugo_project / "layouts", output_format="json", output_file=None, debug=False
        )

        # Parse the JSON result
        graph_data = json.loads(result)

        # Verify nodes exist
        node_ids = [node["id"] for node in graph_data["nodes"]]

        # Check that all expected templates are found
        expected_templates = [
            "_default/baseof.html",
            "_default/single.html",
            "_default/list.html",
            "_partials/head.html",
            "_partials/header.html",
            "_partials/footer.html",
            "_partials/analytics.html",
            "_partials/components/navigation.html",
            "_partials/components/copyright.html",
            "_partials/components/post-summary.html",
            "_partials/components/post-meta.html",
            "_partials/components/tags.html",
            "_partials/components/related-posts.html",
            "shortcodes/youtube.html",
        ]

        for template in expected_templates:
            # Node IDs use full paths from layouts/
            full_path = str(temp_hugo_project / "layouts" / template)
            assert any(full_path in node_id for node_id in node_ids), f"Template {template} not found"

    def test_dependency_resolution_accuracy(self, temp_hugo_project):
        """Test that all dependencies are correctly resolved."""
        result = analyze_dependencies(
            layouts_dir=temp_hugo_project / "layouts", output_format="json", output_file=None, debug=False
        )

        graph_data = json.loads(result)
        edges = graph_data["edges"]

        # Check specific dependency relationships
        # baseof.html should depend on head.html, header.html, footer.html
        baseof_edges = [edge for edge in edges if "baseof.html" in edge["source"]]

        assert len(baseof_edges) >= 3, "baseof.html should have at least 3 dependencies"

        # header.html should depend on components/navigation.html
        header_edges = [
            edge for edge in edges if "header.html" in edge["source"] and "navigation.html" in edge["target"]
        ]

        assert len(header_edges) >= 1, "header.html should depend on navigation.html"

    def test_conditional_dependencies_detected(self, temp_hugo_project):
        """Test that conditional dependencies are properly detected."""
        result = analyze_dependencies(
            layouts_dir=temp_hugo_project / "layouts", output_format="json", output_file=None, debug=False
        )

        graph_data = json.loads(result)
        edges = graph_data["edges"]

        # Look for conditional dependencies (should have metadata indicating this)
        conditional_edges = [
            edge
            for edge in edges
            if edge.get("style") == "dashed"  # Conditional edges are typically dashed
        ]

        # We have several conditional dependencies in our test templates
        assert len(conditional_edges) > 0, "Should detect conditional dependencies"

    def test_mermaid_output_format(self, temp_hugo_project):
        """Test Mermaid format output generation."""
        result = analyze_dependencies(
            layouts_dir=temp_hugo_project / "layouts", output_format="mermaid", output_file=None, debug=False
        )

        # Check Mermaid syntax
        assert result.startswith("graph TD"), "Mermaid output should start with 'graph TD'"
        assert "-->" in result, "Mermaid output should contain dependency arrows"

        # Check that sanitized node IDs are present
        assert "baseof_html" in result or "baseof.html" in result, "baseof template should be in output"

    def test_dot_output_format(self, temp_hugo_project):
        """Test DOT format output generation."""
        result = analyze_dependencies(
            layouts_dir=temp_hugo_project / "layouts", output_format="dot", output_file=None, debug=False
        )

        # Check DOT syntax
        assert result.startswith("digraph"), "DOT output should start with 'digraph'"
        assert "->" in result, "DOT output should contain dependency arrows"
        assert result.endswith("}\n"), "DOT output should end with closing brace"

    def test_error_handling_invalid_project(self):
        """Test error handling with invalid project structure."""
        # Test with non-existent directory
        with pytest.raises((FileNotFoundError, ValueError)):
            analyze_dependencies(
                layouts_dir=Path("/non/existent/path"), output_format="json", output_file=None, debug=False
            )

    def test_empty_project_handling(self):
        """Test handling of empty project (no templates)."""
        temp_dir = Path(tempfile.mkdtemp())
        layouts_dir = temp_dir / "layouts"
        layouts_dir.mkdir(parents=True)

        try:
            result = analyze_dependencies(layouts_dir=layouts_dir, output_format="json", output_file=None, debug=False)

            graph_data = json.loads(result)
            assert graph_data["nodes"] == [], "Empty project should have no nodes"
            assert graph_data["edges"] == [], "Empty project should have no edges"

        finally:
            shutil.rmtree(temp_dir)

    def test_cli_integration(self, temp_hugo_project):
        """Test CLI integration with the analysis pipeline."""
        # Test running the CLI command directly
        cmd = ["uv", "run", "hugo-tpldeps", "analyze", "--format", "json", str(temp_hugo_project / "layouts")]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_hugo_project)

        assert result.returncode == 0, f"CLI command failed: {result.stderr}"

        # Verify JSON output
        graph_data = json.loads(result.stdout)
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) > 0, "Should find template nodes"
