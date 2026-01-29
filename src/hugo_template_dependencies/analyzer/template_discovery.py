"""Template discovery for Hugo projects.

This module provides functionality to discover Hugo template files
in a project directory and organize them by type.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType


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

    def discover_templates(self, project_path: Path) -> List[HugoTemplate]:
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
                    template_type=self._determine_template_type(template_file),
                )
                templates.append(template)

        return templates

    def _determine_template_type(self, file_path: Path) -> TemplateType:
        """Determine template type based on file path and name.

        Args:
            file_path: Path to template file

        Returns:
            TemplateType enum value
        """
        name = file_path.name.lower()
        parent_dir = file_path.parent.name.lower()

        # Check if file is under _partials directory (including nested subdirs)
        is_partial = "_partials" in file_path.parts or "partials" in file_path.parts

        if name == "baseof.html":
            return TemplateType.BASEOF
        elif name == "index.html":
            return TemplateType.INDEX
        elif is_partial or name.startswith("_"):
            return TemplateType.PARTIAL
        elif parent_dir in ["_shortcodes", "shortcodes"]:
            return TemplateType.SHORTCODE
        elif name.startswith("single"):
            return TemplateType.SINGLE
        elif name.startswith("list"):
            return TemplateType.LIST
        else:
            return TemplateType.LAYOUT
