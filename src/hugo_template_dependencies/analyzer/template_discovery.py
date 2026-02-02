"""Template discovery for Hugo projects.

This module provides functionality to discover Hugo template files
in a project directory and organize them by type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType
from hugo_template_dependencies.analyzer.template_parser import HugoTemplateParser

if TYPE_CHECKING:
    from pathlib import Path


class TemplateDiscovery:
    """Discover Hugo template files in a project.

    This class scans a Hugo project directory and finds all template
    files, categorizing them by type and organizing them for analysis.
    """

    def __init__(self) -> None:
        """Initialize template discovery."""
        self.template_extensions = {
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
        }

    def discover_templates(self, project_path: Path) -> list[HugoTemplate]:
        """Discover all template files in a Hugo project.

        Args:
            project_path: Path to Hugo project directory

        Returns:
            List of HugoTemplate objects

        """
        templates = []

        # Look for layouts directory
        layouts_path = project_path / "layouts"
        if not layouts_path.exists():
            return templates

        # Discover all template files
        for template_file in layouts_path.rglob("*"):
            if template_file.is_file() and template_file.suffix in self.template_extensions:
                template = HugoTemplate(
                    file_path=template_file,
                    template_type=HugoTemplateParser._determine_template_type(template_file),
                )
                templates.append(template)

        return templates
