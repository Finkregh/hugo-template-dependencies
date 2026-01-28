"""Hugo template parser for extracting dependencies.

This module provides functionality to parse Hugo template files and extract
dependency information like partial includes, template references, and block definitions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType


class HugoTemplateParser:
    """Parser for Hugo template files.

    This class parses Hugo template files and extracts dependency information
    including partial includes, template references, block definitions, and
    block usage patterns.

    The parser handles Hugo's template syntax while respecting comment blocks
    to avoid false dependencies.
    """

    def __init__(self) -> None:
        """Initialize the Hugo template parser."""
        # Regex patterns for Hugo template functions
        self.patterns = {
            "partial": re.compile(r'{{-\s*partial\s+"([^"]+)"\s*([^}]*)}}-?'),
            "template": re.compile(r'{{-\s*template\s+"([^"]+)"\s*([^}]*)}}-?'),
            "include": re.compile(r'{{-\s*include\s+"([^"]+)"\s*([^}]*)}}-?'),
            "block_def": re.compile(
                r'{{-\s*define\s+"([^"]+)"\s*}}-?(.*?){{-\s*end\s*}}-?', re.DOTALL
            ),
            "block_use": re.compile(
                r'{{-\s*block\s+"([^"]+)"\s*}}-?(.*?){{-\s*end\s*}}-?', re.DOTALL
            ),
            "range": re.compile(r"{{-\s*range\s+([^}]+)\s*}}-?"),
            "if": re.compile(r"{{-\s*if\s+([^}]+)\s*}}-?"),
            "with": re.compile(r"{{-\s*with\s+([^}]+)\s*}}-?"),
            "comment": re.compile(r"{{-\s*/\*.*?\*/\s*}}-?", re.DOTALL),
            "html_comment": re.compile(r"<!--.*?-->", re.DOTALL),
        }

    def parse_file(self, file_path: Path) -> HugoTemplate:
        """Parse a Hugo template file and extract dependencies.

        Args:
            file_path: Path to the Hugo template file

        Returns:
            HugoTemplate object with parsed dependencies
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")

        # Read file content
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Determine template type based on file path and name
        template_type = self._determine_template_type(file_path)

        # Create HugoTemplate object
        template = HugoTemplate(
            file_path=file_path,
            template_type=template_type,
            content=content,
            dependencies=[],
        )

        # Extract dependencies
        template.dependencies = self.extract_dependencies(content)

        return template

    def extract_dependencies(self, content: str) -> List[Dict]:
        """Extract dependencies from template content.

        Args:
            content: Template content to analyze

        Returns:
            List of dependency dictionaries
        """
        dependencies = []

        # Remove comments to avoid false dependencies
        content_no_comments = self._remove_comments(content)

        # Extract different types of dependencies
        dependencies.extend(self._extract_partials(content_no_comments))
        dependencies.extend(self._extract_templates(content_no_comments))
        dependencies.extend(self._extract_includes(content_no_comments))
        dependencies.extend(self._extract_blocks(content_no_comments))

        return dependencies

    def _remove_comments(self, content: str) -> str:
        """Remove Hugo and HTML comments from content.

        Args:
            content: Template content with comments

        Returns:
            Content without comments
        """
        # Remove Hugo comments first
        content = self.patterns["comment"].sub("", content)

        # Remove HTML comments
        content = self.patterns["html_comment"].sub("", content)

        return content

    def _extract_partials(self, content: str) -> List[Dict]:
        """Extract partial includes from content.

        Args:
            content: Template content

        Returns:
            List of partial dependencies
        """
        partials = []
        for match in self.patterns["partial"].finditer(content):
            partial_name = match.group(1)
            line_number = content[: match.start()].count("\n") + 1
            context = self._get_context(content, match.start(), match.end())

            partials.append(
                {
                    "type": "partial",
                    "target": partial_name,
                    "line_number": line_number,
                    "context": context,
                }
            )

        return partials

    def _extract_templates(self, content: str) -> List[Dict]:
        """Extract template references from content.

        Args:
            content: Template content

        Returns:
            List of template dependencies
        """
        templates = []
        for match in self.patterns["template"].finditer(content):
            template_name = match.group(1)
            line_number = content[: match.start()].count("\n") + 1
            context = self._get_context(content, match.start(), match.end())

            templates.append(
                {
                    "type": "template",
                    "target": template_name,
                    "line_number": line_number,
                    "context": context,
                }
            )

        return templates

    def _extract_includes(self, content: str) -> List[Dict]:
        """Extract include references from content.

        Args:
            content: Template content

        Returns:
            List of include dependencies
        """
        includes = []
        for match in self.patterns["include"].finditer(content):
            include_name = match.group(1)
            line_number = content[: match.start()].count("\n") + 1
            context = self._get_context(content, match.start(), match.end())

            includes.append(
                {
                    "type": "include",
                    "target": include_name,
                    "line_number": line_number,
                    "context": context,
                }
            )

        return includes

    def _extract_blocks(self, content: str) -> List[Dict]:
        """Extract block definitions and usage from content.

        Args:
            content: Template content

        Returns:
            List of block dependencies
        """
        blocks = []

        # Extract block definitions
        for match in self.patterns["block_def"].finditer(content):
            block_name = match.group(1)
            line_number = content[: match.start()].count("\n") + 1
            context = self._get_context(content, match.start(), match.end())

            blocks.append(
                {
                    "type": "block_definition",
                    "target": block_name,
                    "line_number": line_number,
                    "context": context,
                }
            )

        # Extract block usage
        for match in self.patterns["block_use"].finditer(content):
            block_name = match.group(1)
            line_number = content[: match.start()].count("\n") + 1
            context = self._get_context(content, match.start(), match.end())

            blocks.append(
                {
                    "type": "block_usage",
                    "target": block_name,
                    "line_number": line_number,
                    "context": context,
                }
            )

        return blocks

    def _determine_template_type(self, file_path: Path) -> TemplateType:
        """Determine template type based on file path and name.

        Args:
            file_path: Path to template file

        Returns:
            TemplateType enum value
        """
        name = file_path.name.lower()
        parent_dir = file_path.parent.name.lower()

        if name == "baseof.html":
            return TemplateType.BASEOF
        elif name == "index.html":
            return TemplateType.INDEX
        elif parent_dir == "_partials" or name.startswith("_"):
            return TemplateType.PARTIAL
        elif name.startswith("single"):
            return TemplateType.SINGLE
        elif name.startswith("list"):
            return TemplateType.LIST
        else:
            return TemplateType.LAYOUT

    def _get_context(
        self, content: str, start: int, end: int, context_chars: int = 50
    ) -> str:
        """Get context around a match for debugging.

        Args:
            content: Full content
            start: Match start position
            end: Match end position
            context_chars: Number of characters of context to include

        Returns:
            Context string around the match
        """
        context_start = max(0, start - context_chars)
        context_end = min(len(content), end + context_chars)

        context = content[context_start:context_end]
        # Add markers for match position
        match_start_in_context = start - context_start
        match_end_in_context = end - context_start

        return (
            context[:match_start_in_context]
            + ">>>"
            + context[match_start_in_context:match_end_in_context]
            + "<<<"
            + context[match_end_in_context:]
        )
