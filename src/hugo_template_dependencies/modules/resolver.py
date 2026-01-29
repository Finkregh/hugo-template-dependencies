"""Hugo module resolver for template dependency analysis.

This module provides functionality to resolve Hugo module imports
and discover templates from imported modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hugo_template_dependencies.config.parser import HugoConfigParser
from hugo_template_dependencies.analyzer.template_discovery import TemplateDiscovery
from hugo_template_dependencies.graph.hugo_graph import HugoModule, HugoTemplate


class HugoModuleResolver:
    """Resolver for Hugo module imports and template discovery.

    This class resolves Hugo module imports and discovers templates
    from imported modules for dependency analysis.
    """

    def __init__(self) -> None:
        """Initialize Hugo module resolver."""
        self.config_parser = HugoConfigParser()
        self.template_discovery = TemplateDiscovery()

    def resolve_modules(self, project_path: Path) -> List[HugoModule]:
        """Resolve Hugo modules from project configuration.

        Args:
            project_path: Path to Hugo project

        Returns:
            List of resolved Hugo modules
        """
        modules = []

        try:
            # Parse Hugo configuration
            config = self.config_parser.parse_hugo_config(project_path)

            # Extract module imports
            module_imports = self.config_parser.extract_module_imports(config)

            # Get cache directory
            cachedir = self.config_parser.get_cachedir(config)

            # Resolve each module import
            for import_item in module_imports:
                module = self._resolve_module_import(import_item, project_path, cachedir)
                if module:
                    modules.append(module)

        except Exception as e:
            # Log error but continue with local templates only
            print(f"Warning: Failed to resolve modules: {e}")

        return modules

    def discover_module_templates(self, module: HugoModule) -> List[HugoTemplate]:
        """Discover templates in a Hugo module.

        Args:
            module: Hugo module to discover templates in

        Returns:
            List of Hugo templates from the module
        """
        if not module.resolved_path or not module.resolved_path.exists():
            return []

        # Look for layouts directory in module
        layouts_path = module.resolved_path / "layouts"
        if not layouts_path.exists():
            return []

        # Discover templates in module layouts
        templates = []
        for template_file in layouts_path.rglob("*"):
            if template_file.is_file() and template_file.suffix in {
                ".html",
                ".xml",
                ".json",
                ".svg",
                ".js",
                ".css",
                ".txt",
                ".rss",
                ".atom",
                ".mjs",
                ".cjs",
            }:
                template = HugoTemplate(
                    file_path=template_file,
                    template_type=self._determine_template_type(template_file),
                )
                templates.append(template)

        return templates

    def _resolve_module_import(
        self, import_item: Dict[str, Any], project_path: Path, cachedir: Optional[Path]
    ) -> Optional[HugoModule]:
        """Resolve a single module import.

        Args:
            import_item: Module import dictionary
            project_path: Hugo project path
            cachedir: Hugo cache directory

        Returns:
            Resolved Hugo module or None if not found
        """
        path = import_item.get("path")
        version = import_item.get("version")

        if not path:
            return None

        # Resolve module path
        resolved_path = self.config_parser.resolve_module_path(import_item, project_path, cachedir)

        if not resolved_path or not resolved_path.exists():
            return None

        return HugoModule(
            path=path,
            version=version,
            resolved_path=resolved_path,
        )

    def _determine_template_type(self, file_path: Path) -> str:
        """Determine template type based on file path and name.

        Args:
            file_path: Path to template file

        Returns:
            Template type string
        """
        name = file_path.name.lower()
        parent_dir = file_path.parent.name.lower()

        if name == "baseof.html":
            return "baseof"
        elif name == "index.html":
            return "index"
        elif parent_dir == "_partials" or name.startswith("_"):
            return "partial"
        elif name.startswith("single"):
            return "single"
        elif name.startswith("list"):
            return "list"
        else:
            return "layout"
