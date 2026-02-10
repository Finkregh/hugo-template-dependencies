"""Shared test fixtures and utilities for hugo-template-dependencies tests.

This module provides common test fixtures used across multiple test files,
including mock graph implementations for formatter testing and temporary
Hugo projects for integration testing.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from hugo_template_dependencies.graph.base import GraphBase


class MockGraph(GraphBase):
    """Mock graph for testing output formatters.

    This mock graph provides a simple test structure with templates, partials,
    and blocks that can be used to test various output formatters without
    requiring a full Hugo project setup.

    The graph includes:
    - Two template nodes (template and partial types)
    - One block node
    - Two edges representing includes and defines relationships
    """

    def __init__(self) -> None:
        super().__init__()
        # Add some test data
        self.graph.add_node(
            "template1",
            type="template",
            display_name="Template 1",
            file_path="/path/to/template1.html",
        )
        self.graph.add_node(
            "template2",
            type="partial",
            display_name="Partial 1",
            file_path="/path/to/partial1.html",
        )
        self.graph.add_node(
            "block1",
            type="block",
            display_name="Block 1",
            block_name="content",
        )

        self.graph.add_edge(
            "template1",
            "template2",
            relationship="includes",
            line_number=5,
            context='{{ partial "partial1.html" . }}',
        )
        self.graph.add_edge(
            "template1",
            "block1",
            relationship="defines",
            line_number=10,
        )

        self._nodes = {
            "template1": {
                "type": "template",
                "display_name": "Template 1",
                "file_path": "/path/to/template1.html",
            },
            "template2": {
                "type": "partial",
                "display_name": "Partial 1",
                "file_path": "/path/to/partial1.html",
            },
            "block1": {
                "type": "block",
                "display_name": "Block 1",
                "block_name": "content",
            },
        }

    def add_node(self, node_id: str, node_type: str, **attributes: object) -> None:
        """Add a node to mock graph."""
        self.graph.add_node(node_id, type=node_type, **attributes)

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        **attributes: object,
    ) -> None:
        """Add an edge to mock graph."""
        self.graph.add_edge(source, target, relationship=relationship, **attributes)


@pytest.fixture
def mock_graph() -> MockGraph:
    """Create a mock graph for testing.

    Returns:
        MockGraph: A pre-populated mock graph with test data

    """
    return MockGraph()


@pytest.fixture
def temp_hugo_project():
    """Create a temporary Hugo project for integration testing.

    Creates a complete Hugo project structure with layouts, partials,
    components, and shortcodes for comprehensive integration testing.

    Yields:
        Path: Path to the temporary Hugo project directory

    """
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
        default_dir
        / "baseof.html": """<!DOCTYPE html>
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
        default_dir
        / "single.html": """{{ define "main" }}
<article>
    <h1>{{ .Title }}</h1>
    {{ .Content }}
    {{ if .Params.show_related }}
        {{ partial "components/related-posts.html" . }}
    {{ end }}
</article>
{{ end }}""",
        # List page template
        default_dir
        / "list.html": """{{ define "main" }}
<section class="posts">
    {{ range .Pages }}
        {{ partial "components/post-summary.html" . }}
    {{ end }}
</section>
{{ end }}""",
        # Head partial
        partials_dir
        / "head.html": """<meta charset="utf-8">
<title>{{ .Title }}</title>
{{ partial "analytics.html" . }}""",
        # Header partial
        partials_dir
        / "header.html": """<header>
    {{ partial "components/navigation.html" . }}
</header>""",
        # Footer partial
        partials_dir
        / "footer.html": """<footer>
    {{ partial "components/copyright.html" . }}
</footer>""",
        # Analytics partial
        partials_dir
        / "analytics.html": """{{ if .Site.GoogleAnalytics }}
<script async src="https://www.googletagmanager.com/gtag/js?id={{ .Site.GoogleAnalytics }}"></script>
{{ end }}""",
        # Component partials
        components_dir
        / "navigation.html": """<nav>
    {{ range .Site.Menus.main }}
        <a href="{{ .URL }}">{{ .Name }}</a>
    {{ end }}
</nav>""",
        components_dir
        / "copyright.html": """<p>&copy; {{ now.Year }} {{ .Site.Title }}</p>""",
        components_dir
        / "post-summary.html": """<article class="summary">
    <h2><a href="{{ .Permalink }}">{{ .Title }}</a></h2>
    {{ .Summary }}
    {{ partial "components/post-meta.html" . }}
</article>""",
        components_dir
        / "post-meta.html": """<div class="meta">
    <time>{{ .Date.Format "2006-01-02" }}</time>
    {{ if .Params.tags }}
        {{ partial "components/tags.html" . }}
    {{ end }}
</div>""",
        components_dir
        / "tags.html": """<ul class="tags">
    {{ range .Params.tags }}
        <li><a href="/tags/{{ . | urlize }}">{{ . }}</a></li>
    {{ end }}
</ul>""",
        components_dir
        / "related-posts.html": """<section class="related">
    <h3>Related Posts</h3>
    {{ range first 3 .Site.RegularPages.Related . }}
        {{ partial "components/post-summary.html" . }}
    {{ end }}
</section>""",
        # Shortcode
        shortcodes_dir
        / "youtube.html": """<div class="youtube">
    <iframe src="https://www.youtube.com/embed/{{ .Get 0 }}"></iframe>
</div>""",
    }

    # Write all template files
    for template_path, content in templates.items():
        template_path.write_text(content)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)
