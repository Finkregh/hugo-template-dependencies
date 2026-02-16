"""Hugo template parser for extracting dependencies.

This module provides functionality to parse Hugo template files and extract
dependency information like partial includes, template references, and block definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ParsedDependency:
    """Represents a parsed template dependency with context."""

    type: str
    target: str
    line_number: int
    context: str
    is_conditional: bool = False
    error_message: str | None = None


@dataclass
class ParseContext:
    """Tracks parsing context for accurate line numbers and nesting."""

    content: str
    current_position: int = 0
    line_number: int = 1
    in_comment_block: bool = False
    nesting_level: int = 0


class HugoTemplateParser:
    """Parser for Hugo template files.

    This class parses Hugo template files and extracts dependency information
    including partial includes, template references, block definitions, and
    comprehensive Hugo syntax patterns.

    The parser handles Hugo's template syntax while respecting comment blocks
    to avoid false dependencies and provides accurate line tracking and context.
    """

    def __init__(self) -> None:
        """Initialize the Hugo template parser."""
        # Enhanced regex patterns for comprehensive Hugo template functions
        # Using more robust patterns that handle optional whitespace and various formats
        self.patterns = {
            # Core template functions - Fixed to handle := variable assignments
            "partial": re.compile(
                r'{{\s*-?\s*(?:\$\w+\s*:?=\s*)?partial\s*"([^"]+)"\s*([^}]*?)\s*-?\s*}}',
            ),
            "template": re.compile(
                r'{{\s*-?\s*(?:\$\w+\s*:?=\s*)?template\s+"([^"]+)"\s*([^}]*?)\s*-?\s*}}',
            ),
            "include": re.compile(
                r'{{\s*-?\s*(?:\$\w+\s*:?=\s*)?include\s+"([^"]+)"\s*([^}]*?)\s*-?\s*}}',
            ),
            # Block definitions and usage with improved multiline support
            "block_def": re.compile(
                r'{{\s*-?\s*define\s+"([^"]+)"\s*-?\s*}}(.*?){{\s*-?\s*end\s*-?\s*}}',
                re.DOTALL | re.MULTILINE,
            ),
            "block_use": re.compile(
                r'{{\s*-?\s*block\s+"([^"]+)"(?:\s+([^}]*?))?\s*-?\s*}}(.*?){{\s*-?\s*end\s*-?\s*}}',
                re.DOTALL | re.MULTILINE,
            ),
            # Control flow patterns
            "range": re.compile(r"{{\s*-?\s*range\s+([^}]+?)\s*-?\s*}}"),
            "if": re.compile(r"{{\s*-?\s*if\s+([^}]+?)\s*-?\s*}}"),
            "else_if": re.compile(r"{{\s*-?\s*else\s+if\s+([^}]+?)\s*-?\s*}}"),
            "else": re.compile(r"{{\s*-?\s*else\s*-?\s*}}"),
            "with": re.compile(r"{{\s*-?\s*with\s+([^}]+?)\s*-?\s*}}"),
            "end": re.compile(r"{{\s*-?\s*end\s*-?\s*}}"),
            # Comments - order matters for proper removal
            "comment": re.compile(r"{{\s*/\*.*?\*/\s*}}", re.DOTALL),
            "html_comment": re.compile(r"<!--.*?-->", re.DOTALL),
        }

    def parse_file(self, file_path: Path) -> HugoTemplate:
        """Parse a Hugo template file and extract dependencies.

        Args:
            file_path: Path to the Hugo template file

        Returns:
            HugoTemplate object with parsed dependencies

        Raises:
            FileNotFoundError: If the template file does not exist

        """
        # Early exit: Guard against non-existent files
        if not file_path.exists():
            error_msg = f"Template file not found: {file_path}"
            raise FileNotFoundError(error_msg)

        try:
            # Parse content at boundary - trusted state after this point
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            error_msg = f"Failed to read template file {file_path}: {e}"
            raise ValueError(error_msg) from e

        # Determine template type based on file path and name
        template_type = self._determine_template_type(file_path)

        # Create HugoTemplate object with parsed dependencies
        template = HugoTemplate(
            file_path=file_path,
            template_type=template_type,
            content=content,
            dependencies=[],
        )

        # Extract dependencies using enhanced parser
        template.dependencies = self.extract_dependencies(content)

        return template

    def extract_dependencies(self, content: str) -> list[dict]:
        """Extract dependencies from template content with enhanced Hugo syntax support.

        Args:
            content: Template content to analyze

        Returns:
            List of dependency dictionaries with enhanced context information

        """
        # Early exit: Guard against empty content
        if not content.strip():
            return []

        try:
            # Create parsing context for accurate tracking
            ParseContext(content=content)

            # Remove comments to avoid false dependencies (Parse Don't Validate)
            content_no_comments = self._remove_comments_enhanced(content)

            dependencies = []

            # Extract different types of dependencies with conditional context tracking
            dependencies.extend(self._extract_partials_enhanced(content_no_comments))
            dependencies.extend(self._extract_templates_enhanced(content_no_comments))
            dependencies.extend(self._extract_includes_enhanced(content_no_comments))
            dependencies.extend(self._extract_blocks_enhanced(content_no_comments))
            dependencies.extend(
                self._extract_control_flow_dependencies(content_no_comments),
            )

            return dependencies

        except Exception as e:
            # Fail fast with descriptive error - don't try to patch bad data
            error_msg = f"Failed to extract dependencies from content: {e}"
            raise ValueError(error_msg) from e

    def _remove_comments_enhanced(self, content: str) -> str:
        """Remove Hugo and HTML comments from content with enhanced nested handling.

        Args:
            content: Template content with comments

        Returns:
            Content without comments, preserving accurate line tracking

        Raises:
            ValueError: If malformed comment syntax is encountered

        """
        # Early exit: Guard against empty content
        if not content:
            return content

        try:
            result = content

            # Remove Hugo comments first ({{/* ... */}}) - handles nesting
            result = self._remove_nested_hugo_comments(result)

            # Remove HTML comments (<!-- ... -->)
            return self.patterns["html_comment"].sub("", result)

        except re.error as e:
            # Fail fast if regex fails
            error_msg = f"Failed to remove comments due to malformed syntax: {e}"
            raise ValueError(error_msg) from e

    def _remove_nested_hugo_comments(self, content: str) -> str:
        """Remove nested Hugo comments while preserving line structure.

        Args:
            content: Content that may contain nested Hugo comments

        Returns:
            Content with Hugo comments removed, preserving line breaks

        """
        # Hugo comments can be nested, so we need to handle them carefully
        result = []
        i = 0
        length = len(content)

        while i < length:
            # Look for Hugo comment start
            if i <= length - 4 and content[i : i + 4] == "{{/*":
                # Find matching end, accounting for nesting
                comment_start = i
                nesting_level = 1
                i += 4

                while i <= length - 4 and nesting_level > 0:
                    if content[i : i + 4] == "{{/*":
                        nesting_level += 1
                        i += 4
                    elif content[i : i + 4] == "*/}}":
                        nesting_level -= 1
                        i += 4
                    else:
                        i += 1

                # Replace comment with newlines to preserve line numbers
                comment_content = content[comment_start:i]
                newlines = comment_content.count("\n")
                result.append("\n" * newlines)
            else:
                result.append(content[i])
                i += 1

        return "".join(result)

    def _extract_partials_enhanced(self, content: str) -> list[dict]:
        """Extract partial includes from content with enhanced context tracking.

        Args:
            content: Template content without comments

        Returns:
            List of partial dependencies with enhanced metadata

        """
        partials = []

        for match in self.patterns["partial"].finditer(content):
            partial_name = match.group(1)
            partial_params = match.group(2).strip() if match.group(2) else ""

            # Get accurate line number and context
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            # Check if this partial is inside conditional block
            is_conditional = self._is_in_conditional_block(content, match.start())

            partials.append(
                {
                    "type": "partial",
                    "target": partial_name,
                    "line_number": line_number,
                    "context": context,
                    "parameters": partial_params,
                    "is_conditional": is_conditional,
                },
            )

        return partials

    def _extract_templates_enhanced(self, content: str) -> list[dict]:
        """Extract template references from content with enhanced context tracking.

        Args:
            content: Template content without comments

        Returns:
            List of template dependencies with enhanced metadata

        """
        templates = []

        for match in self.patterns["template"].finditer(content):
            template_name = match.group(1)
            template_params = match.group(2).strip() if match.group(2) else ""

            # Get accurate line number and context
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            # Check if this template is inside conditional block
            is_conditional = self._is_in_conditional_block(content, match.start())

            templates.append(
                {
                    "type": "template",
                    "target": template_name,
                    "line_number": line_number,
                    "context": context,
                    "parameters": template_params,
                    "is_conditional": is_conditional,
                },
            )

        return templates

    def _extract_includes_enhanced(self, content: str) -> list[dict]:
        """Extract include references from content with enhanced context tracking.

        Args:
            content: Template content without comments

        Returns:
            List of include dependencies with enhanced metadata

        """
        includes = []

        for match in self.patterns["include"].finditer(content):
            include_name = match.group(1)
            include_params = match.group(2).strip() if match.group(2) else ""

            # Get accurate line number and context
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            # Check if this include is inside conditional block
            is_conditional = self._is_in_conditional_block(content, match.start())

            includes.append(
                {
                    "type": "include",
                    "target": include_name,
                    "line_number": line_number,
                    "context": context,
                    "parameters": include_params,
                    "is_conditional": is_conditional,
                },
            )

        return includes

    def _extract_blocks_enhanced(self, content: str) -> list[dict]:
        """Extract block definitions and usage from content with enhanced context tracking.

        Args:
            content: Template content without comments

        Returns:
            List of block dependencies with enhanced metadata

        """
        blocks = []

        # Extract block definitions with enhanced tracking
        for match in self.patterns["block_def"].finditer(content):
            block_name = match.group(1)
            block_content = match.group(2) if len(match.groups()) >= 2 else ""  # noqa: PLR2004 needs_refactoring

            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())
            is_conditional = self._is_in_conditional_block(content, match.start())

            blocks.append(
                {
                    "type": "block_definition",
                    "target": block_name,
                    "line_number": line_number,
                    "context": context,
                    "is_conditional": is_conditional,
                    "block_content": block_content.strip() if block_content else "",
                },
            )

        # Extract block usage with enhanced tracking
        for match in self.patterns["block_use"].finditer(content):
            block_name = match.group(1)
            block_params = (
                match.group(2).strip()
                if len(match.groups()) >= 2 and match.group(2)  # noqa: PLR2004 needs_refactoring
                else ""
            )
            block_content = match.group(3) if len(match.groups()) >= 3 else ""  # noqa: PLR2004 needs_refactoring

            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())
            is_conditional = self._is_in_conditional_block(content, match.start())

            blocks.append(
                {
                    "type": "block_usage",
                    "target": block_name,
                    "line_number": line_number,
                    "context": context,
                    "is_conditional": is_conditional,
                    "parameters": block_params,
                    "block_content": block_content.strip() if block_content else "",
                },
            )

        return blocks

    def _extract_control_flow_dependencies(self, content: str) -> list[dict]:
        """Extract control flow dependencies (range, if, with, etc.) that may affect template dependencies.

        Args:
            content: Template content without comments

        Returns:
            List of control flow dependencies

        """
        control_flows = []

        # Extract range statements
        for match in self.patterns["range"].finditer(content):
            range_expr = match.group(1)
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            control_flows.append(
                {
                    "type": "range",
                    "target": range_expr,
                    "line_number": line_number,
                    "context": context,
                    "is_conditional": False,  # range itself creates conditional context
                },
            )

        # Extract if statements
        for match in self.patterns["if"].finditer(content):
            if_expr = match.group(1)
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            control_flows.append(
                {
                    "type": "if",
                    "target": if_expr,
                    "line_number": line_number,
                    "context": context,
                    "is_conditional": self._is_in_conditional_block(
                        content,
                        match.start(),
                    ),
                },
            )

        # Extract with statements
        for match in self.patterns["with"].finditer(content):
            with_expr = match.group(1)
            line_number = self._get_accurate_line_number(content, match.start())
            context = self._get_enhanced_context(content, match.start(), match.end())

            control_flows.append(
                {
                    "type": "with",
                    "target": with_expr,
                    "line_number": line_number,
                    "context": context,
                    "is_conditional": self._is_in_conditional_block(
                        content,
                        match.start(),
                    ),
                },
            )

        return control_flows

    def _get_accurate_line_number(self, content: str, position: int) -> int:
        """Get accurate line number for a position in content.

        Args:
            content: Full content
            position: Character position in content

        Returns:
            Line number (1-based)

        """
        return content[:position].count("\n") + 1

    def _get_enhanced_context(
        self,
        content: str,
        start: int,
        end: int,
        context_chars: int = 80,
    ) -> str:
        """Get enhanced context around a match with better formatting.

        Args:
            content: Full content
            start: Match start position
            end: Match end position
            context_chars: Number of characters of context to include on each side

        Returns:
            Enhanced context string around the match with clear markers

        """
        # Calculate safe context boundaries
        context_start = max(0, start - context_chars)
        context_end = min(len(content), end + context_chars)

        # Extract context and the matched text
        before_match = content[context_start:start]
        matched_text = content[start:end]
        after_match = content[end:context_end]

        # Clean up context - replace multiple whitespace with single space, preserve important line breaks
        before_clean = re.sub(r"\s+", " ", before_match).strip()
        after_clean = re.sub(r"\s+", " ", after_match).strip()

        # Build enhanced context with clear markers
        return f"...{before_clean} >>>{matched_text}<<< {after_clean}...".strip()

    def _is_in_conditional_block(self, content: str, position: int) -> bool:
        """Check if a position is inside a conditional block (if, range, with, define, block, etc.).

        Args:
            content: Full content
            position: Position to check

        Returns:
            True if position is inside a conditional block

        """
        # Look for all opening and closing statements throughout the content
        # and determine if position is inside any unmatched opening

        all_openings = []
        all_closings = []

        # Find all conditional opening patterns
        for pattern_name in ["if", "range", "with"]:
            for match in self.patterns[pattern_name].finditer(content):
                all_openings.append(match.start())

        # Find block definition openings (these are more complex patterns)
        # Look for {{ define "name" }} patterns
        define_pattern = re.compile(r'{{\s*-?\s*define\s+"[^"]+"\s*-?\s*}}')
        for match in define_pattern.finditer(content):
            all_openings.append(match.start())

        # Find block usage openings ({{ block "name" }})
        block_pattern = re.compile(r'{{\s*-?\s*block\s+"[^"]+"\s*[^}]*?\s*-?\s*}}')
        for match in block_pattern.finditer(content):
            all_openings.append(match.start())

        # Find all {{ end }} statements
        for match in self.patterns["end"].finditer(content):
            all_closings.append(match.start())

        # Count openings and closings before this position
        openings_before = sum(1 for pos in all_openings if pos < position)
        closings_before = sum(1 for pos in all_closings if pos < position)

        # If there are more openings than closings before this position,
        # we're inside a conditional block
        return openings_before > closings_before

    @staticmethod
    def _determine_template_type(file_path: Path) -> TemplateType:
        """Determine template type based on Hugo's official classification system.

        Hugo Template Classification Rules:
        - Files in layouts/ (not in special subdirs) → TEMPLATE
        - Files in layouts/_partials/ or layouts/partials/ → PARTIAL
        - Files in layouts/_shortcodes/ → SHORTCODE

        NO special classification for baseof.html, index.html, single.html, list.html
        - These are all regular templates with naming conventions

        Args:
            file_path: Path to the template file

        Returns:
            TemplateType enum value for mermaid styling and graph classification

        """
        # Check for partials directory (both _partials and partials supported)
        is_partial = "_partials" in file_path.parts or "partials" in file_path.parts

        # Check for shortcodes directory
        is_shortcode = (
            "_shortcodes" in file_path.parts or "shortcodes" in file_path.parts
        )

        if is_partial:
            return TemplateType.PARTIAL
        if is_shortcode:
            return TemplateType.SHORTCODE
        # All files in layouts/ (not in special subdirs) are regular templates
        # This includes baseof.html, home.html, single.html, list.html, etc.
        return TemplateType.TEMPLATE

    def _get_context(
        self,
        content: str,
        start: int,
        end: int,
        context_chars: int = 50,
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
