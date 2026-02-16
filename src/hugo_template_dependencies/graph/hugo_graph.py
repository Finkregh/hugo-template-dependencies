"""Hugo template dependency graph builder.

This module provides HugoDependencyGraph class that extends GraphBase
to build dependency graphs specifically for Hugo template files. It handles
template files, partials, blocks, and module imports.

The graph builder integrates with template parser and module resolver to create a complete
dependency graph showing relationships between Hugo template files across themes and modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


import networkx as nx

from hugo_template_dependencies.graph.base import GraphBase


class HugoDependencyGraph(GraphBase):
    """Hugo template specific graph builder extending generic base.

    This class builds dependency graphs for Hugo templates by parsing
    template files, resolving includes, and creating nodes and edges that represent
    dependency relationships.

    The graph supports:
    - Template file nodes with path and type information
    - Partial and template include relationships
    - Block definition and usage relationships
    - Module import dependencies
    - Metadata tracking for analysis and visualization

    Example:
        >>>
        >> graph = HugoDependencyGraph()
        >> template_file = HugoTemplate(Path("layouts/index.html"))
        >> graph.add_template(template_file)
        >> graph.get_node_count()
        1

    """

    def __init__(self) -> None:
        """Initialize the Hugo dependency graph."""
        super().__init__()
        self.templates: dict[str, HugoTemplate] = {}
        self.modules: dict[str, HugoModule] = {}
        self.replacement_mappings: dict[str, str] = (
            {}
        )  # replacement_path -> original_module

    def set_replacement_mappings(self, replacements: dict[str, str]) -> None:
        """Store Hugo module replacement mappings for display purposes.

        Args:
            replacements: Dictionary mapping original module paths to replacement paths

        """
        # Create reverse mapping: replacement_path -> original_module
        self.replacement_mappings = {v: k for k, v in replacements.items()}

    def get_display_name_for_source(self, source: str) -> str:
        """Get user-friendly display name for a template source.

        Args:
            source: Source identifier (local, module path, or replacement path)

        Returns:
            User-friendly display name for the source

        """
        if source == "local":
            return "Local Templates"
        if source == "unknown":
            return "Unknown Source"
        if source in self.replacement_mappings:
            # This is a replacement path like "../../.." - get original module name
            original_module = self.replacement_mappings[source]
            if "/" in original_module:
                module_name = original_module.split("/")[-1]  # Extract basename
                return f"Module: {module_name}"
            return f"Module: {original_module}"
        # Regular module path like golang.foundata.com/hugo-theme-dev
        return f"Module: {source}"

    def add_node(self, node_id: str, node_type: str, **attributes: object) -> None:
        """Add a node to graph with Hugo specific attributes.

        Args:
            node_id: Unique identifier for node
            node_type: Type of node ('template', 'partial', 'module')
            **attributes: Additional node attributes

        """
        self.graph.add_node(node_id, type=node_type, **attributes)
        self._nodes[node_id] = attributes

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        **attributes: object,
    ) -> None:
        """Add an edge to graph with Hugo specific attributes.

        Args:
            source: Source node identifier
            target: Target node identifier
            relationship: Type of relationship ('includes', 'extends', 'defines', 'uses')
            **attributes: Additional edge attributes

        """
        self.graph.add_edge(
            u_of_edge=source,
            v_of_edge=target,
            relationship=relationship,
            **attributes,
        )

    def add_template(self, template: HugoTemplate) -> None:
        """Add Hugo template as node to graph.

        Args:
            template: HugoTemplate object to add to graph

        """
        # Add template node
        self.add_node(
            template.node_id,
            template.template_type.value,
            file_path=str(template.file_path),
            template_type=template.template_type.value,
            display_name=template.display_name,
            source=template.source,
        )

        # Store template reference
        self.templates[template.node_id] = template

    def add_module(self, module: HugoModule) -> None:
        """Add Hugo module as node to graph.

        Args:
            module: HugoModule object to add to graph

        """
        # Add module node
        self.add_node(
            module.node_id,
            "module",
            module_path=module.path,
            version=module.version,
            display_name=module.display_name,
        )

        # Store module reference
        self.modules[module.node_id] = module

    def add_include_dependency(
        self,
        source: HugoTemplate,
        target: HugoTemplate | str,
        include_type: str,
        line_number: int | None = None,
        context: str | None = None,
    ) -> None:
        """Add include relationship as edge between Hugo templates.

        Args:
            source: Source template that includes the target
            target: Target template being included (can be HugoTemplate or string name)
            include_type: Type of include ('partial', 'template', 'include')
            line_number: Optional line number where include occurs
            context: Optional context string around include

        """
        # Ensure source template is in graph
        if source.node_id not in self.templates:
            self.add_template(source)

        # Handle string target (partial/template names)
        if isinstance(target, str):
            target_id = target
        else:
            # Ensure target template is in graph
            if target.node_id not in self.templates:
                self.add_template(target)
            target_id = target.node_id

        # Add include edge
        self.add_edge(
            source.node_id,
            target_id,
            "includes",
            include_type=include_type,
            line_number=line_number,
            context=context,
            relationship_type="dependency",
        )

    def add_block_dependency(
        self,
        source: HugoTemplate,
        block_name: str,
        block_type: str = "usage",
        line_number: int | None = None,
    ) -> None:
        """Add block relationship as edge.

        Args:
            source: Source template using or defining the block
            block_name: Name of the block
            block_type: Type of block relationship ('definition', 'usage')
            line_number: Optional line number where block occurs

        """
        # Ensure source template is in graph
        if source.node_id not in self.templates:
            self.add_template(source)

        # Create block node
        block_id = f"block:{block_name}"
        self.add_node(
            block_id,
            "block",
            block_name=block_name,
            display_name=f"Block: {block_name}",
        )

        # Add block relationship
        relationship = "defines" if block_type == "definition" else "uses"
        self.add_edge(
            source.node_id,
            block_id,
            relationship,
            line_number=line_number,
            relationship_type="block_relationship",
        )

    def get_templates_by_type(self, template_type: str) -> list[HugoTemplate]:
        """Get all templates of a specific type.

        Args:
            template_type: The type of templates to retrieve

        Returns:
            List of HugoTemplate objects matching specified type

        """
        return [
            template
            for template in self.templates.values()
            if template.template_type.value == template_type
        ]

    def get_template_dependency_chain(self, start_template: str) -> list[str]:
        """Get dependency chain starting from a specific template.

        Args:
            start_template: Node ID of the starting template

        Returns:
            List of node IDs in dependency order

        """
        if start_template not in self.graph.nodes:
            return []

        # Use DFS to build dependency chain
        visited = set()
        chain = []

        def dfs(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            chain.append(node)

            # Follow include relationships
            for successor in self.graph.successors(node):
                edge_data = self.graph.edges[node, successor]
                if edge_data.get("relationship") == "includes":
                    dfs(successor)

        dfs(start_template)
        return chain

    def get_dependency_cycles(self) -> list[list[str]]:
        """Get all dependency cycles in the graph.

        Returns:
            List of cycles, where each cycle is a list of node IDs

        """
        if not self.has_cycles():
            return []

        cycles = []
        try:
            # Use NetworkX cycle detection
            cycles.extend(list(cycle) for cycle in nx.simple_cycles(self.graph))
        except (nx.NetworkXError, ValueError, RuntimeError):
            # Fallback: manual cycle detection for directed graph issues
            cycles = self._detect_cycles_manually()

        return cycles

    def _detect_cycles_manually(self) -> list[list[str]]:
        """Manually detect cycles using DFS approach.

        Returns:
            List of cycles, where each cycle is a list of node IDs

        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = [*path[cycle_start:], node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Follow include relationships
            for successor in self.graph.successors(node):
                edge_data = self.graph.edges[node, successor]
                if edge_data.get("relationship") == "includes":
                    dfs(successor, path.copy())

            rec_stack.discard(node)

        for node in self.graph.nodes():
            if node not in visited:
                dfs(node, [])

        return cycles


class TemplateType(Enum):
    """Hugo template types."""

    TEMPLATE = "template"
    PARTIAL = "partial"
    SHORTCODE = "shortcode"
    # Legacy types - to be phased out
    LAYOUT = "layout"
    SINGLE = "single"
    LIST = "list"
    BASEOF = "baseof"
    INDEX = "index"


@dataclass
class HugoTemplate:
    """Represents a Hugo template file."""

    file_path: Path
    template_type: TemplateType
    content: str | None = None
    dependencies: list[Any] | None = None
    source: str = (
        "local"  # Source: "local" or module path like "golang.foundata.com/hugo-theme-dev"
    )

    @property
    def node_id(self) -> str:
        """Get unique node identifier for this template."""
        return str(self.file_path)

    @property
    def display_name(self) -> str:
        """Display name showing relative path from layouts directory.

        For files in layouts/, shows path relative to layouts/ directory.
        For files outside layouts/, shows full relative path from project root.

        Examples:
            layouts/meetings/list.html → meetings/list.html
            layouts/_default/single.html → _default/single.html
            layouts/_partials/header.html → _partials/header.html
            content/posts/example.md → content/posts/example.md

        Returns:
            String representing the display path for this template

        """
        # Find layouts directory in the path
        try:
            parts = self.file_path.parts
            if "layouts" in parts:
                layouts_index = parts.index("layouts")
                # Return path relative to layouts directory
                relative_parts = parts[layouts_index + 1 :]
                return "/".join(relative_parts)
            # File not in layouts, return relative path from project root
            return str(self.file_path)
        except (ValueError, IndexError):
            # Fallback to current behavior for edge cases
            return self.file_path.name


@dataclass
class HugoModule:
    """Represents a Hugo module import."""

    path: str
    version: str | None = None
    resolved_path: Path | None = None

    @property
    def node_id(self) -> str:
        """Get unique node identifier for this module."""
        return f"module:{self.path}"

    @property
    def display_name(self) -> str:
        """Get display name for this module."""
        return f"{self.path}@{self.version or 'latest'}"
