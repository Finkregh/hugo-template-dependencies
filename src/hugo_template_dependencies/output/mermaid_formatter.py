"""Mermaid formatter for Hugo dependency graphs.

This module provides functionality to convert Hugo dependency graphs
into Mermaid diagram format for visualization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hugo_template_dependencies.graph.base import GraphBase


class MermaidFormatter:
    """Convert Hugo dependency graphs to Mermaid diagram format.

    This class takes a dependency graph and converts it to Mermaid
    syntax suitable for display in documentation or web interfaces.
    """

    def __init__(self, graph: GraphBase) -> None:
        """Initialize Mermaid formatter.

        Args:
            graph: The dependency graph to format

        """
        self.graph = graph

    def format_graph(
        self,
        direction: str = "TD",
        include_metadata: bool = False,
    ) -> str:
        """Format the graph as Mermaid diagram.

        Args:
            direction: Graph direction ('TD' for top-down, 'LR' for left-right)
            include_metadata: Whether to include metadata in node labels

        Returns:
            Mermaid diagram string

        """
        # Add ELK layout configuration for better rendering
        mermaid_lines = [f"graph {direction}"]

        # Add nodes with proper labeling
        nodes = self._get_formatted_nodes(include_metadata)
        mermaid_lines.extend(nodes)

        # Add edges with relationships
        edges = self._get_formatted_edges()
        mermaid_lines.extend(edges)

        # Add subgraphs by type if requested
        subgraphs = self._get_subgraphs()
        mermaid_lines.extend(subgraphs)

        return "\n".join(mermaid_lines)

    def _get_formatted_nodes(self, include_metadata: bool) -> list[str]:
        """Get formatted node definitions.

        Args:
            include_metadata: Whether to include metadata in node labels

        Returns:
            List of formatted node definitions

        """
        nodes = []

        for node_id, data in self.graph.graph.nodes(data=True):
            label = self._get_node_label(node_id, data, include_metadata)
            node_type = data.get("type", "unknown")

            # Style nodes based on type
            style = self._get_node_style(node_type)
            nodes.append(f'    {self._sanitize_id(node_id, data)}["{label}"]{style}')

        return nodes

    def _get_formatted_edges(self) -> list[str]:
        """Get formatted edge definitions.

        Returns:
            List of formatted edge definitions

        """
        edges = []

        for source, target, data in self.graph.graph.edges(data=True):
            relationship = data.get("relationship", "depends on")
            edge_label = self._get_edge_label(relationship)

            # Get node data for proper sanitization
            source_data = self.graph.graph.nodes.get(source, {})
            target_data = self.graph.graph.nodes.get(target, {})

            source_id = self._sanitize_id(source, source_data)
            target_id = self._sanitize_id(target, target_data)

            if edge_label:
                edges.append(f"    {source_id} -->|{edge_label}| {target_id}")
            else:
                edges.append(f"    {source_id} --> {target_id}")

        return edges

    def _get_subgraphs(self) -> list[str]:
        """Get formatted subgraph definitions by template source.

        Returns:
            List of formatted subgraph definitions grouped by source

        """
        from collections import defaultdict

        subgraphs = []
        source_groups = defaultdict(list)

        # Group nodes by source
        for node_id, data in self.graph.graph.nodes(data=True):
            source = data.get("source", "unknown")
            source_groups[source].append((node_id, data))

        # Create subgraphs for each source
        for source, nodes in source_groups.items():
            if len(source_groups) <= 1:
                # Skip subgraphs if there's only one source
                break

            # Format source name for display
            # Try to get display name from HugoDependencyGraph if available
            try:
                from hugo_template_dependencies.graph.hugo_graph import HugoDependencyGraph

                if isinstance(self.graph, HugoDependencyGraph):
                    source_display = self.graph.get_display_name_for_source(source)
                else:
                    raise AttributeError  # Use fallback
            except (AttributeError, ImportError):
                # Fallback for graphs without replacement support
                if source == "local":
                    source_display = "Local Templates"
                elif source == "unknown":
                    source_display = "Unknown Source"
                else:
                    source_display = f"Module: {source}"

            # Create meaningful subgraph ID based on display name
            try:
                from hugo_template_dependencies.graph.hugo_graph import HugoDependencyGraph

                if isinstance(self.graph, HugoDependencyGraph):
                    display_name = self.graph.get_display_name_for_source(source)
                    # Extract module name from "Module: hugo-theme-component-ical"
                    if display_name.startswith("Module: "):
                        module_name = display_name[8:]  # Remove "Module: " prefix
                        subgraph_id = self._sanitize_id(module_name, None)
                    elif display_name == "Local Templates":
                        subgraph_id = "local_templates"
                    else:
                        subgraph_id = self._sanitize_id(source, None)
                else:
                    subgraph_id = self._sanitize_id(f"source_{source}", None)
            except (AttributeError, ImportError):
                subgraph_id = self._sanitize_id(f"source_{source}", None)
            subgraphs.append(f'    subgraph {subgraph_id} ["{source_display}"]')

            # Add nodes to subgraph
            for node_id, data in nodes:
                sanitized_id = self._sanitize_id(node_id, data)
                subgraphs.append(f"        {sanitized_id}")

            # End subgraph
            subgraphs.append("    end")
            subgraphs.append("")  # Add blank line for readability

        return subgraphs

    def _get_node_label(
        self,
        node_id: str,
        data: dict[str, Any],
        include_metadata: bool,
    ) -> str:
        """Get label for a node.

        Args:
            node_id: Node identifier
            data: Node data
            include_metadata: Whether to include metadata

        Returns:
            Formatted node label

        """
        display_name = data.get("display_name", node_id)

        if include_metadata:
            metadata_parts = []
            if "file_path" in data:
                metadata_parts.append(f"Path: {data['file_path']}")
            if "template_type" in data:
                metadata_parts.append(f"Type: {data['template_type']}")

            if metadata_parts:
                metadata_str = "\\n" + "\\n".join(metadata_parts)
                return f"{display_name}{metadata_str}"

        return display_name

    def _get_node_style(self, node_type: str) -> str:
        """Get styling for a node based on its type.

        Args:
            node_type: Type of node

        Returns:
            Style string for node

        """
        styles = {
            "template": ":::template",
            "partial": ":::partial",
            "block": ":::block",
            "module": ":::module",
            "unknown": "",
        }
        return styles.get(node_type, "")

    def _get_edge_label(self, relationship: str) -> str:
        """Get label for an edge based on relationship type.

        Args:
            relationship: Type of relationship

        Returns:
            Label string for edge (without pipes)

        """
        labels = {
            "includes": "includes",
            "defines": "defines",
            "uses": "uses",
            "depends on": "",
        }
        return labels.get(relationship, "")

    def _sanitize_id(self, node_id: str, node_data: dict[str, Any] | None = None) -> str:
        """Sanitize node ID for Mermaid compatibility.

        Creates meaningful IDs by extracting relative path context with source prefixes:
        - For local templates: "local_" prefix (e.g., "local_baseof")
        - For module templates: module name prefix (e.g., "hugo_theme_dev_baseof")

        Examples:
            "/path/to/layouts/meetings/single.html" → "local_meetings_single" (if local)
            "/module/layouts/_partials/header.html" → "theme_partials_header" (if module)

        Args:
            node_id: Original node identifier (often a full file path)
            node_data: Optional node data containing source information

        Returns:
            Sanitized node ID with source prefix and meaningful path context

        """
        import os
        from pathlib import Path

        # Handle module node IDs that start with "module:"
        if node_id.startswith("module:"):
            module_path = node_id[7:]  # Remove "module:" prefix
            # Extract module name (last part of path)
            if "/" in module_path:
                module_name = module_path.split("/")[-1]
            else:
                module_name = module_path
            # Sanitize module name
            sanitized = module_name.replace("-", "_").replace(".", "_")
            return f"mod_{sanitized}"

        # Handle block node IDs that start with "block:"
        if node_id.startswith("block:"):
            block_name = node_id[6:]  # Remove "block:" prefix
            sanitized = block_name.replace("-", "_").replace(" ", "_")
            return f"blk_{sanitized}"

        # Extract source information
        source_prefix = "local"
        if node_data:
            source = node_data.get("source", "local")
            if source == "local":
                source_prefix = "local"
            else:
                # Try to use graph's method to get proper display name, handling replacements
                # Check if this is a HugoDependencyGraph with the method we need
                if hasattr(self.graph, "get_display_name_for_source"):
                    try:
                        display_name = self.graph.get_display_name_for_source(source)  # type: ignore[attr-defined]
                        if display_name.startswith("Module: "):
                            # Extract module name from "Module: hugo-theme-dev" format
                            module_name = display_name[8:]  # Remove "Module: " prefix
                        else:
                            module_name = source
                    except Exception:
                        # Fallback if method fails
                        module_name = source
                else:
                    # Fallback: extract from source path
                    if "/" in source:
                        module_name = source.split("/")[-1]
                    else:
                        module_name = source

                # Sanitize module name
                source_prefix = module_name.replace("-", "_").replace(".", "_")

        # For template files, extract meaningful path
        meaningful_path = None
        try:
            path_obj = Path(node_id)
            parts = list(path_obj.parts)  # Convert to list for easier manipulation

            # Find layouts directory to get relative path
            if "layouts" in parts:
                layouts_index = parts.index("layouts")
                # Get path relative to layouts directory
                relative_parts = parts[layouts_index + 1 :]
                if relative_parts:
                    meaningful_path = "/".join(relative_parts)
                else:
                    meaningful_path = path_obj.name
            else:
                # Fallback: use just the filename with parent directory for context
                if len(parts) >= 2:
                    meaningful_path = f"{parts[-2]}/{parts[-1]}"
                else:
                    meaningful_path = path_obj.name

        except (ValueError, IndexError):
            meaningful_path = node_id

        # Ensure we have a meaningful path
        if meaningful_path is None:
            meaningful_path = node_id

        # Remove file extension for cleaner display
        if "." in meaningful_path:
            meaningful_path = os.path.splitext(meaningful_path)[0]

        # Replace path separators and problematic characters
        sanitized_path = meaningful_path.replace("/", "_").replace("\\", "_")
        sanitized_path = sanitized_path.replace("-", "_").replace(" ", "_")
        sanitized_path = sanitized_path.replace("(", "").replace(")", "")
        sanitized_path = sanitized_path.replace("[", "").replace("]", "")
        sanitized_path = sanitized_path.replace(":", "_").replace("@", "_")

        # Handle leading underscores from paths like "_partials/file"
        while sanitized_path.startswith("_"):
            sanitized_path = sanitized_path[1:]

        # Combine source prefix with path
        full_id = f"{source_prefix}_{sanitized_path}"

        # Ensure it starts with a letter or underscore
        if full_id and full_id[0].isdigit():
            full_id = f"n_{full_id}"

        # Handle edge cases
        if not full_id or full_id.isspace():
            full_id = f"{source_prefix}_unknown"

        return full_id

    def format_with_styles(self) -> str:
        """Format graph with CSS style definitions.

        Returns:
            Complete Mermaid diagram with styling

        """
        # Add ELK layout directive at the beginning
        elk_directive = """%%{
  init: {
    "layout": "elk"
  }
}%%

"""

        mermaid_content = self.format_graph(include_metadata=False)
        legend = """
    subgraph Legend
        Template:::template
        Partial:::partial
        block:::block
        module:::block
    end
"""
        styles = """
classDef template fill:#00af00,stroke:#01579b,stroke-width:2px
classDef partial fill:#af0000,stroke:#4a148c,stroke-width:2px
classDef block fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
classDef module fill:#fff3e0,stroke:#e65100,stroke-width:2px
"""

        return f"{elk_directive}{mermaid_content}\n{legend}{styles}"
