"""Unit tests for Hugo module resolution.

Tests the complete module resolution logic:
- Replacement handling
- Local relative path resolution
- Remote module resolution from cachedir
- Version handling (explicit, latest, with suffixes)
"""

from pathlib import Path

import pytest

from hugo_template_dependencies.config.parser import HugoConfigParser
from hugo_template_dependencies.graph.hugo_graph import HugoModule
from hugo_template_dependencies.modules.resolver import HugoModuleResolver


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create temporary Hugo project structure.

    Cleanup is automatic via tmp_path fixture.
    """
    project = tmp_path / "project"
    project.mkdir()

    # Create layouts directory
    layouts = project / "layouts"
    layouts.mkdir()
    (layouts / "index.html").write_text("<html>{{ .Content }}</html>")

    return project


@pytest.fixture
def temp_cache(tmp_path: Path) -> Path:
    """Create temporary Hugo cache directory structure.

    Cleanup is automatic via tmp_path fixture.
    """
    cache = tmp_path / "cache" / "modules" / "filecache" / "modules" / "pkg" / "mod"
    cache.mkdir(parents=True)
    return cache


@pytest.fixture
def mock_hugo_config() -> str:
    """Mock hugo config command output."""
    return """baseURL = "https://example.com"
cacheDir = "/tmp/test_cache"

[module]
  replacements = ["github.com/user/theme -> ../../.."]

  [[module.imports]]
    path = "github.com/user/theme"
    version = "v1.0.0"

  [[module.imports]]
    path = "github.com/other/module"
    version = "v2.1.0"
"""


class TestModuleReplacements:
    """Test module replacement resolution."""

    def test_replacement_as_local_path(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test replacement resolves to local relative path."""
        # Setup: Create parent theme WITHIN tmp_path scope
        # Use temp_project's tmp_path parent instead of going too far up
        # Create theme as a sibling to project within the tmp_path
        parent_theme = temp_project.parent / "theme"
        parent_theme.mkdir(parents=True, exist_ok=True)
        theme_layouts = parent_theme / "layouts"
        theme_layouts.mkdir(exist_ok=True)
        (theme_layouts / "baseof.html").write_text(
            '<html>{{ block "main" . }}{{ end }}</html>',
        )

        # Config with replacement (adjusted to ../theme since we changed structure)
        config = {
            "module": {
                "replacements": ["github.com/user/theme -> ../theme"],
                "imports": [{"path": "github.com/user/theme", "version": "v1.0.0"}],
            },
        }

        parser = HugoConfigParser()
        resolver = HugoModuleResolver()
        resolver.config_parser = parser

        # Extract replacements
        replacements = parser.extract_module_replacements(config)
        assert "github.com/user/theme" in replacements
        assert replacements["github.com/user/theme"] == "../theme"

        # Resolve module
        resolved = parser.resolve_module_path(
            {"path": "github.com/user/theme", "version": "v1.0.0"},
            temp_project,
            temp_cache,
            replacements,
        )

        assert resolved is not None
        assert resolved.exists()
        assert (resolved / "layouts" / "baseof.html").exists()

    def test_replacement_fallback_to_cache(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test replacement falls back to cachedir when local path doesn't exist."""
        # Setup: Create module in cache
        module_dir = temp_cache / "github.com" / "user" / "theme@v1.0.0"
        module_dir.mkdir(parents=True)
        layouts = module_dir / "layouts"
        layouts.mkdir()
        (layouts / "single.html").write_text("{{ .Content }}")

        # Config with replacement to nonexistent local path
        config = {
            "module": {
                "replacements": ["github.com/user/theme -> ../nonexistent"],
                "imports": [{"path": "github.com/user/theme", "version": "v1.0.0"}],
            },
        }

        parser = HugoConfigParser()
        replacements = parser.extract_module_replacements(config)

        # Should fall back to cache
        resolved = parser.resolve_module_path(
            {"path": "github.com/user/theme", "version": "v1.0.0"},
            temp_project,
            temp_cache,
            replacements,
        )

        assert resolved is not None
        assert resolved == module_dir
        assert (resolved / "layouts" / "single.html").exists()


class TestLocalModuleResolution:
    """Test local relative module resolution."""

    def test_relative_path_without_replacement(self, temp_project: Path) -> None:
        """Test resolving local module without replacement."""
        # Setup: Create sibling theme
        sibling_theme = temp_project.parent / "sibling-theme"
        sibling_theme.mkdir()
        layouts = sibling_theme / "layouts"
        layouts.mkdir()
        (layouts / "list.html").write_text("{{ range .Pages }}{{ end }}")

        parser = HugoConfigParser()

        resolved = parser.resolve_module_path(
            {"path": "../sibling-theme"},
            temp_project,
            None,  # No cachedir needed for local
            {},
        )

        assert resolved is not None
        assert resolved == sibling_theme
        assert (resolved / "layouts" / "list.html").exists()


class TestRemoteModuleResolution:
    """Test remote module resolution from cachedir."""

    def test_exact_version_match(self, temp_project: Path, temp_cache: Path) -> None:
        """Test resolving module with exact version."""
        # Setup: Create module at exact version
        module_dir = temp_cache / "github.com" / "foo" / "bar@v1.2.3"
        module_dir.mkdir(parents=True)
        layouts = module_dir / "layouts"
        layouts.mkdir()
        (layouts / "partial.html").write_text("{{ . }}")

        parser = HugoConfigParser()

        resolved = parser.resolve_module_path(
            {"path": "github.com/foo/bar", "version": "v1.2.3"},
            temp_project,
            temp_cache,
            {},
        )

        assert resolved is not None
        assert resolved == module_dir

    def test_version_suffix_stripping(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test version suffix like +vendor is handled."""
        # Hugo mod graph reports: github.com/foo/bar@v1.0.0+vendor
        # But cache has: github.com/foo/bar@v1.0.0

        module_dir = temp_cache / "github.com" / "foo" / "bar@v1.0.0"
        module_dir.mkdir(parents=True)
        layouts = module_dir / "layouts"
        layouts.mkdir()
        (layouts / "index.html").write_text("test")

        parser = HugoConfigParser()

        # Request with +vendor suffix
        resolved = parser.resolve_module_path(
            {"path": "github.com/foo/bar", "version": "v1.0.0+vendor"},
            temp_project,
            temp_cache,
            {},
        )

        assert resolved is not None
        assert resolved == module_dir

    def test_find_latest_version(self, temp_project: Path, temp_cache: Path) -> None:
        """Test finding latest version when no version specified."""
        # Create multiple versions - use 3-level structure matching real Hugo cache
        # Real structure: github.com/finkregh/hugo-theme-component-ical@v0.10.2
        for version in ["v1.0.0", "v1.1.0", "v2.0.0"]:
            module_dir = temp_cache / "github.com" / "foo" / f"bar@{version}"
            module_dir.mkdir(parents=True)
            (module_dir / "layouts").mkdir()

        parser = HugoConfigParser()

        resolved = parser.resolve_module_path(
            {"path": "github.com/foo/bar"},  # No version
            temp_project,
            temp_cache,
            {},
        )

        assert resolved is not None
        # Should get latest (lexicographic sort)
        assert "v2.0.0" in str(resolved)


class TestHierarchicalCacheStructure:
    """Test hierarchical cache directory handling."""

    def test_hierarchical_cache_format(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test resolving from hierarchical cache (domain/module@version)."""
        # Create hierarchical structure
        domain_dir = temp_cache / "golang.foundata.com"
        domain_dir.mkdir()
        module_dir = domain_dir / "hugo-theme-dev@v1.0.0"
        module_dir.mkdir()
        layouts = module_dir / "layouts"
        layouts.mkdir()
        (layouts / "baseof.html").write_text("base")

        parser = HugoConfigParser()

        resolved = parser.resolve_module_path(
            {"path": "golang.foundata.com/hugo-theme-dev", "version": "v1.0.0"},
            temp_project,
            temp_cache,
            {},
        )

        assert resolved is not None
        assert resolved == module_dir

    def test_flat_cache_format(self, temp_project: Path, temp_cache: Path) -> None:
        """Test resolving from flat cache (full/path@version)."""
        # Create flat structure
        module_dir = temp_cache / "github.com" / "user" / "repo@v1.0.0"
        module_dir.mkdir(parents=True)
        layouts = module_dir / "layouts"
        layouts.mkdir()
        (layouts / "test.html").write_text("test")

        parser = HugoConfigParser()

        resolved = parser.resolve_module_path(
            {"path": "github.com/user/repo", "version": "v1.0.0"},
            temp_project,
            temp_cache,
            {},
        )

        assert resolved is not None
        assert resolved == module_dir


class TestFullModuleResolution:
    """Test complete module resolution workflow."""

    def test_resolve_modules_with_replacements(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test full resolve_modules() workflow with replacements."""
        # Setup local replacement target
        parent_theme = temp_project.parent / "parent-theme"
        parent_theme.mkdir()
        parent_layouts = parent_theme / "layouts"
        parent_layouts.mkdir()
        (parent_layouts / "baseof.html").write_text("base")

        # Setup remote module in cache
        remote_module = temp_cache / "github.com" / "other" / "module@v1.0.0"
        remote_module.mkdir(parents=True)
        remote_layouts = remote_module / "layouts"
        remote_layouts.mkdir()
        (remote_layouts / "single.html").write_text("single")

        # Config
        config = {
            "cacheDir": str(temp_cache.parent.parent.parent.parent.parent),
            "module": {
                "replacements": ["github.com/user/theme -> ../parent-theme"],
                "imports": [
                    {"path": "github.com/user/theme", "version": "v1.0.0"},
                    {"path": "github.com/other/module", "version": "v1.0.0"},
                ],
            },
        }

        resolver = HugoModuleResolver()
        modules = resolver.resolve_modules(temp_project, config)

        assert len(modules) == 2

        # First module should resolve via replacement
        assert modules[0].path == "github.com/user/theme"
        assert modules[0].resolved_path == parent_theme

        # Second module should resolve from cache
        assert modules[1].path == "github.com/other/module"
        assert modules[1].resolved_path == remote_module

    def test_discover_templates_in_resolved_modules(self, temp_project: Path) -> None:
        """Test template discovery in resolved modules."""
        # Setup module with templates
        module_dir = temp_project.parent / "test-module"
        module_dir.mkdir()
        layouts = module_dir / "layouts"
        layouts.mkdir()

        # Create various templates
        (layouts / "_default").mkdir()
        (layouts / "_default" / "single.html").write_text("single")
        (layouts / "_default" / "list.html").write_text("list")
        (layouts / "_partials").mkdir()
        (layouts / "_partials" / "header.html").write_text("header")

        # Create module object
        module = HugoModule(
            path="../test-module",
            version=None,
            resolved_path=module_dir,
        )

        resolver = HugoModuleResolver()
        templates = resolver.discover_module_templates(module)

        assert len(templates) == 3
        template_names = {t.file_path.name for t in templates}
        assert "single.html" in template_names
        assert "list.html" in template_names
        assert "header.html" in template_names


class TestExampleSiteRealData:
    """Tests using real data from exampleSite Hugo config."""

    def test_examplesite_config_parsing(self) -> None:
        """Test parsing actual exampleSite config structure."""
        # Real config from ~/work/private/hugo-ical-templates/.github/exampleSite
        config = {
            "baseURL": "https://example.com",
            "module": {
                "noproxy": "none",
                "private": "*.*",
                "proxy": "direct",
                "replacements": [
                    "github.com/finkregh/hugo-theme-component-ical -> ../../..",
                ],
                "workspace": "off",
                "hugoversion": {},
                "imports": [
                    {"path": "../../..", "version": "refactor"},
                    {
                        "path": "golang.foundata.com/hugo-theme-dev",
                        "ignoreconfig": False,
                        "ignorevariables": False,
                    },
                ],
            },
        }

        parser = HugoConfigParser()

        # Test replacement extraction
        replacements = parser.extract_module_replacements(config)
        assert len(replacements) == 1
        assert "github.com/finkregh/hugo-theme-component-ical" in replacements
        assert (
            replacements["github.com/finkregh/hugo-theme-component-ical"] == "../../.."
        )

        # Test imports extraction
        imports = parser.extract_module_imports(config)
        assert len(imports) == 2
        assert imports[0]["path"] == "../../.."
        assert imports[0]["version"] == "refactor"
        assert imports[1]["path"] == "golang.foundata.com/hugo-theme-dev"

    def test_examplesite_module_resolution_logic(
        self,
        temp_project: Path,
        temp_cache: Path,
    ) -> None:
        """Test resolution logic matching exampleSite structure."""
        # Simulate exampleSite structure
        # exampleSite is at: project/.github/exampleSite
        # From exampleSite, ../../.. goes to parent of project
        github_dir = temp_project / ".github"
        github_dir.mkdir()
        examplesite = github_dir / "exampleSite"
        examplesite.mkdir()

        # Create theme root with layouts at actual ../../.. location
        # ../../.. from project/.github/exampleSite = temp_project.parent.parent.parent
        # But for testing, we create it at the resolved location
        theme_root = (examplesite / "../../..").resolve()
        theme_layouts = theme_root / "layouts" / "_partials"
        theme_layouts.mkdir(parents=True)
        (theme_layouts / "calendar_icon.html").write_text("icon")

        # Create hugo-theme-dev module in cache
        dev_module = temp_cache / "golang.foundata.com" / "hugo-theme-dev@v1.0.0"
        dev_module.mkdir(parents=True)
        dev_layouts = dev_module / "layouts" / "_partials"
        dev_layouts.mkdir(parents=True)
        (dev_layouts / "list.html").write_text("list")

        # Config simulating exampleSite
        config = {
            "module": {
                "replacements": [
                    "github.com/finkregh/hugo-theme-component-ical -> ../../..",
                ],
                "imports": [
                    {"path": "../../..", "version": "refactor"},
                    {"path": "golang.foundata.com/hugo-theme-dev"},
                ],
            },
        }

        parser = HugoConfigParser()
        replacements = parser.extract_module_replacements(config)

        # Resolve first import (../../..) - should NOT use replacement
        # It's already a relative path
        resolved1 = parser.resolve_module_path(
            {"path": "../../..", "version": "refactor"},
            examplesite,
            temp_cache,
            replacements,
        )

        assert resolved1 is not None
        assert resolved1 == theme_root
        assert (resolved1 / "layouts" / "_partials" / "calendar_icon.html").exists()

        # Resolve second import (golang.foundata.com/hugo-theme-dev)
        # No replacement, should use cache
        resolved2 = parser.resolve_module_path(
            {"path": "golang.foundata.com/hugo-theme-dev"},
            examplesite,
            temp_cache,
            replacements,
        )

        assert resolved2 is not None
        assert resolved2 == dev_module
        assert (resolved2 / "layouts" / "_partials" / "list.html").exists()
