"""Tests for template discovery functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from hugo_template_dependencies.analyzer.template_discovery import TemplateDiscovery
from hugo_template_dependencies.graph.hugo_graph import HugoTemplate

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_hugo_project() -> Generator[Path, None, None]:
    """Create a temporary Hugo project structure for testing.

    Yields:
        Path to temporary Hugo project directory

    """
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        layouts_path = project_path / "layouts"
        layouts_path.mkdir()

        yield project_path


@pytest.fixture
def discovery() -> TemplateDiscovery:
    """Create TemplateDiscovery instance.

    Returns:
        TemplateDiscovery instance

    """
    return TemplateDiscovery()


class TestTemplateDiscovery:
    """Test cases for template discovery."""

    def test_discover_templates_empty_project(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test template discovery in empty project.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        templates = discovery.discover_templates(temp_hugo_project)

        assert isinstance(templates, list)
        assert len(templates) == 0

    def test_discover_templates_html_files(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of HTML template files.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create test templates
        (layouts_path / "index.html").write_text("<html>{{ .Content }}</html>")
        (layouts_path / "single.html").write_text("<html>{{ .Title }}</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 2
        assert all(isinstance(t, HugoTemplate) for t in templates)

        # Check file paths
        file_names = [t.file_path.name for t in templates]
        assert "index.html" in file_names
        assert "single.html" in file_names

    def test_discover_templates_multiple_extensions(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of templates with different extensions.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create templates with different extensions
        (layouts_path / "feed.xml").write_text("<xml>{{ .Content }}</xml>")
        (layouts_path / "data.json").write_text('{"title": "{{ .Title }}"}')
        (layouts_path / "image.svg").write_text("<svg>Content</svg>")
        (layouts_path / "script.js").write_text("console.log('test');")
        (layouts_path / "style.css").write_text("body { color: red; }")
        (layouts_path / "readme.txt").write_text("Text file")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 6

        extensions = [t.file_path.suffix for t in templates]
        assert ".xml" in extensions
        assert ".json" in extensions
        assert ".svg" in extensions
        assert ".js" in extensions
        assert ".css" in extensions
        assert ".txt" in extensions

    def test_discover_templates_nested_directories(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of templates in nested directory structures.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create nested structure
        partials_path = layouts_path / "_partials"
        partials_path.mkdir()
        (partials_path / "header.html").write_text("<header>Header</header>")

        nested_path = partials_path / "nested" / "deep"
        nested_path.mkdir(parents=True)
        (nested_path / "component.html").write_text("<div>Component</div>")

        default_path = layouts_path / "_default"
        default_path.mkdir()
        (default_path / "baseof.html").write_text("<html>Base</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 3

        # Check nested files are discovered
        relative_paths = [str(t.file_path.relative_to(layouts_path)) for t in templates]
        assert "_partials/header.html" in relative_paths
        assert "_partials/nested/deep/component.html" in relative_paths
        assert "_default/baseof.html" in relative_paths

    def test_discover_templates_excludes_non_template_files(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test that non-template files are excluded.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create template and non-template files
        (layouts_path / "template.html").write_text("<html>Template</html>")
        (layouts_path / "readme.md").write_text("# README")
        (layouts_path / "config.yaml").write_text("config: value")
        (layouts_path / "script.py").write_text("print('test')")
        (layouts_path / ".hidden").write_text("hidden file")

        templates = discovery.discover_templates(temp_hugo_project)

        # Should only find the HTML file
        assert len(templates) == 1
        assert templates[0].file_path.name == "template.html"

    def test_discover_templates_excludes_directories(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test that directories are excluded from results.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create subdirectories
        (layouts_path / "partials").mkdir()
        (layouts_path / "shortcodes").mkdir()

        # Create one template file
        (layouts_path / "index.html").write_text("<html>Index</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        # Should only find the file, not directories
        assert len(templates) == 1
        assert all(t.file_path.is_file() for t in templates)

    def test_discover_templates_no_layouts_directory(
        self,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery when layouts directory doesn't exist.

        Args:
            discovery: TemplateDiscovery instance

        """
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            # Don't create layouts directory

            templates = discovery.discover_templates(project_path)

            assert isinstance(templates, list)
            assert len(templates) == 0

    def test_discover_templates_template_types(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test that discovered templates have correct types.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create different template types
        (layouts_path / "baseof.html").write_text("<html>Baseof</html>")
        (layouts_path / "index.html").write_text("<html>Index</html>")
        (layouts_path / "single.html").write_text("<html>Single</html>")

        partials_path = layouts_path / "_partials"
        partials_path.mkdir()
        (partials_path / "header.html").write_text("<header>Header</header>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 4

        # Check template types are assigned
        for template in templates:
            assert hasattr(template, "template_type")
            assert template.template_type is not None

    def test_discover_templates_with_partials(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of partial templates.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create partials directory
        partials_path = layouts_path / "_partials"
        partials_path.mkdir()

        (partials_path / "header.html").write_text("<header>Header</header>")
        (partials_path / "footer.html").write_text("<footer>Footer</footer>")
        (partials_path / "nav.html").write_text("<nav>Navigation</nav>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 3

        # All should be from _partials directory
        for template in templates:
            assert "_partials" in str(template.file_path)

    def test_discover_templates_with_shortcodes(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of shortcode templates.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create shortcodes directory
        shortcodes_path = layouts_path / "shortcodes"
        shortcodes_path.mkdir()

        (shortcodes_path / "youtube.html").write_text("<div>YouTube</div>")
        (shortcodes_path / "image.html").write_text("<img src='test'>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 2

        # Check shortcode files are discovered
        for template in templates:
            assert "shortcodes" in str(template.file_path)

    def test_discover_templates_mixed_structure(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery in complex mixed directory structure.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create complex structure
        (layouts_path / "index.html").write_text("<html>Index</html>")

        default_path = layouts_path / "_default"
        default_path.mkdir()
        (default_path / "single.html").write_text("<html>Single</html>")
        (default_path / "list.html").write_text("<html>List</html>")

        partials_path = layouts_path / "_partials"
        partials_path.mkdir()
        (partials_path / "header.html").write_text("<header>Header</header>")

        nested_partials = partials_path / "components"
        nested_partials.mkdir()
        (nested_partials / "card.html").write_text("<div>Card</div>")

        shortcodes_path = layouts_path / "shortcodes"
        shortcodes_path.mkdir()
        (shortcodes_path / "alert.html").write_text("<div>Alert</div>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 6

        # Verify all expected files are found
        file_names = [t.file_path.name for t in templates]
        assert "index.html" in file_names
        assert "single.html" in file_names
        assert "list.html" in file_names
        assert "header.html" in file_names
        assert "card.html" in file_names
        assert "alert.html" in file_names

    def test_template_extensions_configuration(
        self,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test that template extensions are properly configured.

        Args:
            discovery: TemplateDiscovery instance

        """
        # Check default extensions
        assert ".html" in discovery.template_extensions
        assert ".xml" in discovery.template_extensions
        assert ".json" in discovery.template_extensions
        assert ".svg" in discovery.template_extensions
        assert ".js" in discovery.template_extensions
        assert ".css" in discovery.template_extensions
        assert ".txt" in discovery.template_extensions
        assert ".rss" in discovery.template_extensions
        assert ".atom" in discovery.template_extensions
        assert ".mjs" in discovery.template_extensions
        assert ".cjs" in discovery.template_extensions

    def test_discover_templates_with_special_characters(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of templates with special characters in names.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create templates with special characters (valid filesystem names)
        (layouts_path / "page-template.html").write_text("<html>Page</html>")
        (layouts_path / "template_with_underscores.html").write_text(
            "<html>Underscores</html>",
        )
        (layouts_path / "template.2.html").write_text("<html>Version 2</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 3

        file_names = [t.file_path.name for t in templates]
        assert "page-template.html" in file_names
        assert "template_with_underscores.html" in file_names
        assert "template.2.html" in file_names

    def test_discover_templates_real_world_mock(
        self,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery using actual mock templates from tests/mocks.

        Args:
            discovery: TemplateDiscovery instance

        """
        # Use the real mock directory from the project
        mock_path = Path(__file__).parent / "mocks" / "basic_partial_pattern"

        if mock_path.exists():
            templates = discovery.discover_templates(mock_path)

            # Should find templates in the mock directory
            assert len(templates) >= 1
            assert all(isinstance(t, HugoTemplate) for t in templates)

    def test_discover_templates_preserves_file_paths(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test that file paths are correctly preserved.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        template_path = layouts_path / "test.html"
        template_path.write_text("<html>Test</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 1
        assert templates[0].file_path == template_path
        assert templates[0].file_path.is_absolute()

    def test_discover_templates_empty_files(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of empty template files.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        # Create empty template files
        (layouts_path / "empty.html").write_text("")
        (layouts_path / "nonempty.html").write_text("<html>Content</html>")

        templates = discovery.discover_templates(temp_hugo_project)

        # Should find both empty and non-empty files
        assert len(templates) == 2

    def test_discover_templates_rss_and_atom_feeds(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of RSS and Atom feed templates.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        (layouts_path / "feed.rss").write_text("<rss>Feed</rss>")
        (layouts_path / "atom.atom").write_text("<feed>Atom</feed>")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 2

        extensions = [t.file_path.suffix for t in templates]
        assert ".rss" in extensions
        assert ".atom" in extensions

    def test_discover_templates_js_variants(
        self,
        temp_hugo_project: Path,
        discovery: TemplateDiscovery,
    ) -> None:
        """Test discovery of JavaScript template variants.

        Args:
            temp_hugo_project: Temporary Hugo project path
            discovery: TemplateDiscovery instance

        """
        layouts_path = temp_hugo_project / "layouts"

        (layouts_path / "script.js").write_text("console.log('test');")
        (layouts_path / "module.mjs").write_text("export default {};")
        (layouts_path / "common.cjs").write_text("module.exports = {};")

        templates = discovery.discover_templates(temp_hugo_project)

        assert len(templates) == 3

        extensions = [t.file_path.suffix for t in templates]
        assert ".js" in extensions
        assert ".mjs" in extensions
        assert ".cjs" in extensions
