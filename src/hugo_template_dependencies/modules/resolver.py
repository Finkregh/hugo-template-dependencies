"""Hugo module resolver for template dependency analysis.

This module provides functionality to resolve Hugo module imports
and discover templates from imported modules.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from hugo_template_dependencies.analyzer.template_discovery import TemplateDiscovery
from hugo_template_dependencies.analyzer.template_parser import HugoTemplateParser
from hugo_template_dependencies.config.parser import HugoConfigParser
from hugo_template_dependencies.graph.hugo_graph import (
    HugoModule,
    HugoTemplate,
    TemplateType,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class HugoModuleResolver:
    """Resolver for Hugo module imports and template discovery.

    This class resolves Hugo module imports and discovers templates
    from imported modules for dependency analysis.
    """

    def __init__(self) -> None:
        """Initialize Hugo module resolver."""
        self.config_parser = HugoConfigParser()
        self.template_discovery = TemplateDiscovery()

    def resolve_modules(
        self,
        project_path: Path,
        config: dict[str, Any] | None = None,
    ) -> list[HugoModule]:
        """Resolve all Hugo module imports for a project.

        Uses Hugo configuration to resolve modules, NOT 'hugo mod graph'.
        Always gets latest versions from cachedir.

        Args:
            project_path: Path to Hugo project
            config: Optional pre-parsed Hugo config (will parse if not provided)

        Returns:
            List of resolved Hugo modules

        """
        # Parse config if not provided
        if config is None:
            try:
                config = self.config_parser.parse_hugo_config(project_path)
            except ValueError as e:
                logger.warning(f"Could not parse Hugo config: {e}")
                return []

        # Extract module imports and replacements
        module_imports = self.config_parser.extract_module_imports(config)
        replacements = self.config_parser.extract_module_replacements(config)

        logger.debug(f"Found {len(module_imports)} module imports")
        logger.debug(f"Found {len(replacements)} module replacements")

        if not module_imports:
            return []

        # Get cache directory
        try:
            cachedir = self.config_parser.get_cachedir(config)
            logger.debug(f"Using cachedir: {cachedir}")
        except ValueError as e:
            logger.warning(f"Could not get cachedir: {e}")
            cachedir = None

        # Resolve each module import
        modules = []
        for import_item in module_imports:
            module = self._resolve_module_import(
                import_item,
                project_path,
                cachedir,
                replacements,
            )
            if module:
                modules.append(module)

        logger.debug(f"Resolved {len(modules)} modules")
        return modules

    def _resolve_module_import(
        self,
        import_item: dict[str, Any],
        project_path: Path,
        cachedir: Path | None,
        replacements: dict[str, str],
    ) -> HugoModule | None:
        """Resolve a single module import.

        Args:
            import_item: Module import dictionary
            project_path: Hugo project path
            cachedir: Hugo cache directory
            replacements: Module replacement mappings

        Returns:
            Resolved Hugo module, or None if resolution fails

        """
        path = import_item.get("path")
        version = import_item.get("version")

        if not path:
            logger.debug("Module import missing 'path' field")
            return None

        logger.debug(f"Resolving module import: {path} (version: {version or 'none'})")

        # Resolve using config parser with replacements
        resolved_path = self.config_parser.resolve_module_path(
            import_item,
            project_path,
            cachedir,
            replacements,
        )

        if not resolved_path:
            logger.warning(f"Config parser returned None for module: {path}")
            return None

        if not resolved_path.exists():
            logger.warning(
                f"Config parser resolved path does not exist: {resolved_path}",
            )
            return None

        logger.debug(f"Successfully resolved {path}: {resolved_path}")
        return HugoModule(
            path=path,
            version=version,
            resolved_path=resolved_path,
        )

    def discover_module_templates(self, module: HugoModule) -> list[HugoTemplate]:
        """Discover templates in a Hugo module.

        Args:
            module: Hugo module to discover templates in

        Returns:
            List of Hugo templates from the module

        """
        logger.debug(f"Discovering templates in module: {module.path}")
        logger.debug(f"  Resolved path: {module.resolved_path}")

        if not module.resolved_path:
            logger.debug(f"  ✗ No resolved path for module {module.path}")
            return []

        if not module.resolved_path.exists():
            logger.debug(f"  ✗ Resolved path does not exist: {module.resolved_path}")
            return []

        # Look for layouts directory in module
        layouts_path = module.resolved_path / "layouts"
        logger.debug(f"  Looking for layouts at: {layouts_path}")

        if not layouts_path.exists():
            logger.debug(f"  ✗ Layouts directory does not exist: {layouts_path}")
            return []

        logger.debug(f"  ✓ Found layouts directory: {layouts_path}")
        logger.debug(f"  ✓ Found layouts directory: {layouts_path}")

        # Discover templates in module layouts
        templates = []
        template_files = list(layouts_path.rglob("*"))
        logger.debug(f"  Found {len(template_files)} files/dirs in layouts (recursive)")

        for template_file in template_files:
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
                logger.debug(f"    Adding template: {template_file.name}")
                template = HugoTemplate(
                    file_path=template_file,
                    template_type=HugoTemplateParser._determine_template_type(
                        template_file
                    ),
                    source=module.path,  # Add source information
                )
                templates.append(template)

        logger.debug(f"  Total templates discovered: {len(templates)}")
        return templates
