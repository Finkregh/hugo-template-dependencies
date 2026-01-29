"""Graphviz DOT formatter for Hugo dependency graphs.

This module provides functionality to convert Hugo dependency graphs
into DOT format for Graphviz visualization and rendering.
"""

from __future__ import annotations

from typing import Any

from hugo_template_dependencies.graph.base import GraphBase


class DOTFormatter:
    """Convert Hugo dependency graphs to Graphviz DOT format.

    This class takes a dependency graph and converts it to DOT syntax
    suitable for rendering with Graphviz tools like dot, neato, or fdp.
    """

    def __init__(self, graph: GraphBase) -> None:
        """Initialize DOT formatter.

        Args:
            graph: The dependency graph to format
        """
        self.graph = graph

    def format_graph(
        self,
        graph_type: str = "digraph",
        layout: str = "dot",
        rankdir: str = "TB",
        include_subgraphs: bool = True,
        include_styles: bool = True,
    ) -> str:
        """Format the graph as DOT.

        Args:
            graph_type: Type of graph ('digraph' or 'graph')
            layout: Graphviz layout engine to use
            rankdir: Graph direction ('TB', 'LR', 'BT', 'RL')
            include_subgraphs: Whether to create subgraphs by template type
            include_styles: Whether to include styling attributes

        Returns:
            DOT format string
        """
        dot_lines = []

        # Graph header
        dot_lines.append(f"{graph_type} hugo_dependencies {{")
        dot_lines.append(f"    layout = {layout};")
        dot_lines.append(f"    rankdir = {rankdir};")
        # Note: Global node/edge styles are applied via individual node attributes
        # to avoid empty global declarations that cause DOT syntax errors
        dot_lines.append("")

        # Add global styling if requested
        if include_styles:
            dot_lines.extend(self._get_global_styles())
            dot_lines.append("")

        # Add subgraphs by type if requested
        if include_subgraphs:
            subgraphs = self._get_subgraphs(include_styles)
            for subgraph in subgraphs:
                dot_lines.extend(subgraph)
                dot_lines.append("")
        else:
            # Add nodes directly
            nodes = self._get_formatted_nodes(include_styles)
            dot_lines.extend(nodes)
            dot_lines.append("")

        # Add edges
        edges = self._get_formatted_edges(include_styles)
        dot_lines.extend(edges)
        dot_lines.append("")

        # Graph footer
        dot_lines.append("}")

        return "\n".join(dot_lines)

    def format_simple(self) -> str:
        """Format graph in simple DOT format without styling.

        Returns:
            Simple DOT format string
        """
        return self.format_graph(
            include_subgraphs=False,
            include_styles=False,
        )

    def format_clustered(self) -> str:
        """Format graph with clustered subgraphs by template type.

        Returns:
            Clustered DOT format string
        """
        return self.format_graph(
            include_subgraphs=True,
            include_styles=True,
        )

    def save_to_file(
        self,
        file_path: str,
        format_type: str = "clustered",
    ) -> None:
        """Save DOT output to file.

        Args:
            file_path: Path to save the DOT file
            format_type: Type of format ('simple', 'clustered', or 'custom')

        Raises:
            ValueError: If format_type is invalid
            OSError: If file cannot be written
        """
        # Generate DOT based on format type
        if format_type == "simple":
            dot_output = self.format_simple()
        elif format_type == "clustered":
            dot_output = self.format_clustered()
        elif format_type == "custom":
            dot_output = self.format_graph(include_subgraphs=True, include_styles=False)
        else:
            raise ValueError(f"Invalid format_type: {format_type}. Use 'simple', 'clustered', or 'custom'")

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(dot_output)

    def _get_formatted_nodes(self, include_styles: bool) -> list[str]:
        """Get formatted node definitions.

        Args:
            include_styles: Whether to include styling attributes

        Returns:
            List of formatted node definitions
        """
        nodes = []

        for node_id, data in self.graph.graph.nodes(data=True):
            label = self._get_node_label(node_id, data)
            node_type = data.get("type", "unknown")

            if include_styles:
                attributes = self._get_node_attributes(node_type, data)
                attributes_str = f" [{attributes}]" if attributes else ""
            else:
                attributes_str = f' [label="{label}"]'

            sanitized_id = self._sanitize_id(node_id)
            nodes.append(f"    {sanitized_id}{attributes_str};")

        return nodes

    def _get_formatted_edges(self, include_styles: bool) -> list[str]:
        """Get formatted edge definitions.

        Args:
            include_styles: Whether to include styling attributes

        Returns:
            List of formatted edge definitions
        """
        edges = []

        for source, target, data in self.graph.graph.edges(data=True):
            relationship = data.get("relationship", "depends on")

            if include_styles:
                attributes = self._get_edge_attributes(relationship, data)
                attributes_str = f" [{attributes}]" if attributes else ""
            else:
                attributes_str = f' [label="{relationship}"]'

            source_id = self._sanitize_id(source)
            target_id = self._sanitize_id(target)

            edges.append(f"    {source_id} -> {target_id}{attributes_str};")

        return edges

    def _get_subgraphs(self, include_styles: bool = True) -> list[list[str]]:
        """Get formatted subgraph definitions by template directory and type.

        Args:
            include_styles: Whether to include styling attributes

        Returns:
            List of subgraph definitions, each as a list of lines
        """
        subgraphs = []
        node_groups = {}

        # Group nodes by directory and type
        for node_id, data in self.graph.graph.nodes(data=True):
            file_path = data.get("file_path", "")
            node_type = data.get("type", "unknown")

            # Determine group based on file path or type
            if "layouts/" in file_path:
                if "partials/" in file_path:
                    group_key = "partials"
                    group_name = "Partials"
                elif "shortcodes/" in file_path:
                    group_key = "shortcodes"
                    group_name = "Shortcodes"
                elif (
                    "_default/" in file_path
                    or "baseof" in file_path
                    or "single" in file_path
                    or "list" in file_path
                    or "index" in file_path
                ):
                    group_key = "layouts"
                    group_name = "Layouts"
                else:
                    group_key = "layouts"
                    group_name = "Layouts"
            elif node_type == "module":
                group_key = "modules"
                group_name = "Modules"
            else:
                group_key = "other"
                group_name = "Other"

            if group_key not in node_groups:
                node_groups[group_key] = {"name": group_name, "nodes": []}

            node_groups[group_key]["nodes"].append((node_id, data))

        # Create subgraphs for each group
        for group_key, group_data in node_groups.items():
            if len(group_data["nodes"]) > 0:
                subgraph_lines = []
                subgraph_lines.append(f'    subgraph "cluster_{group_key}" {{')
                subgraph_lines.append(f'        label = "{group_data["name"]}";')

                if include_styles:
                    # Use appropriate style based on group type
                    subgraph_style = self._get_cluster_style_for_group(group_key)
                    subgraph_lines.append(f"        style = filled;")
                    fillcolor = subgraph_style.split('fillcolor="')[1].split('"')[0]
                    subgraph_lines.append(f'        fillcolor = "{fillcolor}";')

                # Add nodes to subgraph
                for node_id, data in group_data["nodes"]:
                    node_type = data.get("type", "unknown")
                    label = self._get_node_label(node_id, data)
                    if include_styles:
                        attributes = self._get_node_attributes(node_type, data)
                        attributes_str = f" [{attributes}]" if attributes else ""
                    else:
                        attributes_str = f' [label="{label}"]'
                    sanitized_id = self._sanitize_id(node_id)
                    subgraph_lines.append(f"        {sanitized_id}{attributes_str};")

                subgraph_lines.append("    }")
                subgraphs.append(subgraph_lines)

        return subgraphs

    def _get_node_label(self, node_id: str, data: dict[str, Any]) -> str:
        """Get label for a node.

        Args:
            node_id: Node identifier
            data: Node data

        Returns:
            Formatted node label
        """
        display_name = data.get("display_name", node_id)

        # Only include file path if display_name is explicitly provided and different
        file_path = data.get("file_path")
        if "display_name" in data and file_path and str(file_path) != display_name:
            return f"{display_name}\\n{file_path}"

        return display_name

    def _get_node_attributes(self, node_type: str, data: dict[str, Any]) -> str:
        """Get DOT attributes for a node based on its type.

        Args:
            node_type: Type of node
            data: Node data

        Returns:
            DOT attributes string
        """
        node_id = data.get("id", "")
        label = self._get_node_label(node_id, data)

        # Base attributes
        attributes = [f'label="{label}"']

        # Type-specific styling
        style_config = self._get_node_style_config(node_type)
        attributes.extend(style_config)

        # Add font attributes for all nodes
        attributes.extend(['fontname="Arial"', "fontsize=10"])

        # Add tooltip if file path is available
        if "file_path" in data:
            attributes.append(f'tooltip="{data["file_path"]}"')

        return ", ".join(attributes)

    def _get_edge_attributes(self, relationship: str, data: dict[str, Any]) -> str:
        """Get DOT attributes for an edge based on relationship type.

        Args:
            relationship: Type of relationship
            data: Edge data

        Returns:
            DOT attributes string
        """
        attributes = [f'label="{relationship}"']

        # Relationship-specific styling
        style_config = self._get_edge_style_config(relationship)
        attributes.extend(style_config)

        # Add font attributes for all edges
        attributes.extend(['fontname="Arial"', "fontsize=8"])

        # Add line number if available
        if "line_number" in data:
            attributes.append(f'xlabel="L{data["line_number"]}"')

        # Add tooltip if context is available
        if "context" in data:
            context = data["context"][:50] + "..." if len(data["context"]) > 50 else data["context"]
            attributes.append(f'tooltip="{context}"')

        return ", ".join(attributes)

    def _get_node_style_config(self, node_type: str) -> list[str]:
        """Get style configuration for a node type.

        Args:
            node_type: Type of node

        Returns:
            List of style attributes
        """
        styles = {
            # Layout templates - box shape with blue tint
            "layout": ["shape=box", "style=filled", 'fillcolor="#E6F3FF"', 'color="#4A90E2"'],
            "baseof": ["shape=box", "style=filled", 'fillcolor="#E6F3FF"', 'color="#4A90E2"'],
            "single": ["shape=box", "style=filled", 'fillcolor="#E6F3FF"', 'color="#4A90E2"'],
            "list": ["shape=box", "style=filled", 'fillcolor="#E6F3FF"', 'color="#4A90E2"'],
            "index": ["shape=box", "style=filled", 'fillcolor="#E6F3FF"', 'color="#4A90E2"'],
            # Partial templates - ellipse shape with red tint
            "partial": ["shape=ellipse", "style=filled", 'fillcolor="#FFE6E6"', 'color="#E24A4A"'],
            # Shortcode templates - diamond shape with green tint
            "shortcode": ["shape=diamond", "style=filled", 'fillcolor="#E6FFE6"', 'color="#4AE24A"'],
            # Block definitions - diamond shape with green tint
            "block": ["shape=diamond", "style=filled", 'fillcolor="#E8F5E8"', 'color="#2E7D32"'],
            # Module imports - folder shape with orange tint
            "module": ["shape=folder", "style=filled", 'fillcolor="#FFF3E0"', 'color="#E65100"'],
            # Generic template fallback
            "template": ["shape=box", "style=filled", 'fillcolor="#e1f5fe"', 'color="#01579b"'],
            # Unknown type
            "unknown": ["shape=box", "style=filled", 'fillcolor="#f5f5f5"', 'color="#616161"'],
        }
        return styles.get(node_type, styles["template"])

    def _get_edge_style_config(self, relationship: str) -> list[str]:
        """Get style configuration for an edge relationship.

        Args:
            relationship: Type of relationship

        Returns:
            List of style attributes
        """
        styles = {
            "includes": ['color="#2196f3"', "style=solid", "arrowhead=normal"],
            "extends": ['color="#ff9800"', "style=dashed", "arrowhead=empty"],
            "defines": ['color="#4caf50"', "style=bold", "arrowhead=diamond"],
            "uses": ['color="#9c27b0"', "style=dotted", "arrowhead=normal"],
            "depends on": ['color="#607d8b"', "style=solid", "arrowhead=normal"],
            "imports": ['color="#795548"', "style=bold", "arrowhead=vee"],
            "unknown": ['color="#9e9e9e"', "style=solid", "arrowhead=normal"],
        }
        return styles.get(relationship, styles["unknown"])

    def _get_subgraph_style(self, node_type: str) -> str:
        """Get style for subgraph based on node type.

        Args:
            node_type: Type of nodes in subgraph

        Returns:
            Subgraph style string
        """
        styles = {
            # Layout templates cluster
            "layout": 'filled, fillcolor="#E6F3FF"',
            "baseof": 'filled, fillcolor="#E6F3FF"',
            "single": 'filled, fillcolor="#E6F3FF"',
            "list": 'filled, fillcolor="#E6F3FF"',
            "index": 'filled, fillcolor="#E6F3FF"',
            # Partial templates cluster
            "partial": 'filled, fillcolor="#FFE6E6"',
            # Shortcode templates cluster
            "shortcode": 'filled, fillcolor="#E6FFE6"',
            # Block definitions cluster
            "block": 'filled, fillcolor="#E8F5E8"',
            # Module imports cluster
            "module": 'filled, fillcolor="#FFF3E0"',
            # Generic template fallback
            "template": 'filled, fillcolor="#e1f5fe"',
            # Unknown type
            "unknown": 'filled, fillcolor="#f5f5f5"',
        }
        return styles.get(node_type, styles["unknown"])

    def _get_cluster_style_for_group(self, group_key: str) -> str:
        """Get appropriate subgraph style for a group.

        Args:
            group_key: The group identifier

        Returns:
            Subgraph style string
        """
        styles = {
            "layouts": 'filled, fillcolor="#E6F3FF"',
            "partials": 'filled, fillcolor="#FFE6E6"',
            "shortcodes": 'filled, fillcolor="#E6FFE6"',
            "modules": 'filled, fillcolor="#FFF3E0"',
            "other": 'filled, fillcolor="#f5f5f5"',
        }
        return styles.get(group_key, styles["other"])

    def _get_global_styles(self) -> list[str]:
        """Get global graph styling.

        Returns:
            List of global style definitions
        """
        return [
            "    // Global settings",
            "    bgcolor=white;",
            "    pad=1.0;",
            "    nodesep=0.8;",
            "    ranksep=1.0;",
            "    // Default attributes are set in graph header",
        ]

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for DOT compatibility.

        Args:
            node_id: Original node identifier

        Returns:
            Sanitized node ID
        """
        # Store original first character check before replacement
        starts_with_dash = node_id.startswith("-")

        # Replace problematic characters
        sanitized = node_id.replace("/", "_").replace(".", "_").replace("-", "_")
        sanitized = sanitized.replace(" ", "_").replace("(", "").replace(")", "")
        sanitized = sanitized.replace(":", "_").replace("@", "_")

        # Handle empty or all-numeric IDs first
        if not sanitized:
            return "empty"
        elif sanitized.replace("_", "").isdigit():
            sanitized = f"node_{hash(node_id) % 10000}"

        # Ensure it starts with a letter or underscore
        elif sanitized and sanitized[0].isdigit():
            sanitized = f"n_{sanitized}"
        elif starts_with_dash and sanitized.startswith("_"):
            sanitized = f"n_{sanitized}"

        return sanitized
