"""Mermaid formatter for Hugo dependency graphs.

This module provides functionality to convert Hugo dependency graphs
into Mermaid diagram format for visualization.
"""

from __future__ import annotations

from typing import Any

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
            nodes.append(f'    {self._sanitize_id(node_id)}["{label}"]{style}')

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

            source_id = self._sanitize_id(source)
            target_id = self._sanitize_id(target)

            if edge_label:
                edges.append(f"    {source_id} -->|{edge_label}| {target_id}")
            else:
                edges.append(f"    {source_id} --> {target_id}")

        return edges

    def _get_subgraphs(self) -> list[str]:
        """Get formatted subgraph definitions by node type.

        Returns:
            List of formatted subgraph definitions
        """
        subgraphs = []
        node_types = {}

        # Group nodes by type
        for node_id, data in self.graph.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            if node_type not in node_types:
                node_types[node_type] = []
            node_types[node_type].append(node_id)

        # Create subgraphs for each type
        for node_type, nodes in node_types.items():
            if len(nodes) > 1:  # Only create subgraph if multiple nodes
                subgraphs.append(f'    subgraph "{node_type.title()}"')
                for node_id in nodes:
                    sanitized_id = self._sanitize_id(node_id)
                    subgraphs.append(f"        {sanitized_id}")
                subgraphs.append("    end")

        return subgraphs

    def _get_node_label(self, node_id: str, data: dict[str, Any], include_metadata: bool) -> str:
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

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for Mermaid compatibility.

        Creates shorter, more readable IDs by extracting filename
        and ensuring uniqueness.

        Args:
            node_id: Original node identifier (often a full file path)

        Returns:
            Sanitized node ID
        """
        import os

        # Extract filename from path
        if "/" in node_id:
            filename = os.path.basename(node_id)
        else:
            filename = node_id

        # Remove file extension for cleaner display
        if "." in filename:
            filename = os.path.splitext(filename)[0]

        # Replace problematic characters and make it a valid identifier
        sanitized = filename.replace("-", "_").replace(" ", "_")
        sanitized = sanitized.replace("(", "").replace(")", "")
        sanitized = sanitized.replace("[", "").replace("]", "")

        # Ensure it starts with a letter
        if sanitized and sanitized[0].isdigit():
            sanitized = f"n_{sanitized}"

        # Handle edge cases
        if not sanitized or sanitized.isspace():
            sanitized = "unknown_node"

        return sanitized

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

        styles = """
classDef template fill:#e1f5fe,stroke:#01579b,stroke-width:2px
classDef partial fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
classDef block fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
classDef module fill:#fff3e0,stroke:#e65100,stroke-width:2px
"""

        return f"{elk_directive}{mermaid_content}\n{styles}"
