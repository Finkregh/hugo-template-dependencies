"""JSON formatter for Hugo dependency graphs.

This module provides functionality to convert Hugo dependency graphs
into JSON format for machine-readable output and integration with other tools.
Follows JSON Graph Format standard with nodes/edges structure.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import jsonschema

if TYPE_CHECKING:
    from hugo_template_dependencies.graph.base import GraphBase


class JSONFormatter:
    """Convert Hugo dependency graphs to JSON format.

    This class takes a dependency graph and converts it to structured JSON
    suitable for machine processing, API integration, and data analysis.
    Follows JSON Graph Format standard with proper schema validation.
    """

    # Hugo template JSON schema definition
    HUGO_JSON_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "required": ["nodes", "edges", "metadata"],
        "properties": {
            "schema_version": {"type": "string"},
            "generated_at": {"type": "string", "format": "date-time"},
            "graph_type": {"type": "string"},
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "type"],
                    "properties": {
                        "id": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "partial",
                                "layout",
                                "baseof",
                                "single",
                                "list",
                                "index",
                                "template",
                                "shortcode",
                                "block",
                                "unknown",
                            ],
                        },
                        "name": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["source", "target", "relationship"],
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "relationship": {
                            "type": "string",
                            "enum": [
                                "includes",
                                "defines",
                                "uses",
                                "depends on",
                                "extends",
                            ],
                        },
                        "metadata": {"type": "object"},
                    },
                },
            },
            "metadata": {
                "type": "object",
                "required": ["generator", "totalNodes", "totalEdges"],
                "properties": {
                    "generator": {"type": "string"},
                    "totalNodes": {"type": "integer"},
                    "totalEdges": {"type": "integer"},
                    "analysis_date": {"type": "string"},
                    "hugo_version": {"type": "string"},
                    "project_path": {"type": "string"},
                },
            },
            "statistics": {"type": "object"},
        },
    }

    def __init__(self, graph: GraphBase) -> None:
        """Initialize JSON formatter.

        Args:
            graph: The dependency graph to format

        """
        self.graph = graph
        self._schema_validator = jsonschema.Draft7Validator(
            self.HUGO_JSON_SCHEMA,
        )

    def format_graph(
        self,
        *,
        include_metadata: bool = True,
        include_statistics: bool = True,
        schema_version: str = "1.0",
    ) -> str:
        """Format the graph as JSON.

        Args:
            include_metadata: Whether to include detailed metadata for nodes and edges
            include_statistics: Whether to include graph statistics
            schema_version: JSON schema version for compatibility

        Returns:
            JSON string representing the graph

        """
        graph_data: dict[str, Any] = {
            "schema_version": schema_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "graph_type": "hugo_template_dependencies",
        }

        # Add nodes
        graph_data["nodes"] = self._get_formatted_nodes(
            include_metadata=include_metadata,
        )

        # Add edges
        graph_data["edges"] = self._get_formatted_edges(
            include_metadata=include_metadata,
        )

        # Add statistics if requested
        if include_statistics:
            graph_data["statistics"] = self._get_graph_statistics()

        # Add metadata with Hugo-specific information
        graph_data["metadata"] = self._get_hugo_metadata()

        return json.dumps(graph_data, indent=2, ensure_ascii=False)

    def format_simple(self) -> str:
        """Format graph in simple JSON format with basic structure.

        Returns:
            Simplified JSON string with just nodes and edges

        """
        simple_data: dict[str, Any] = {
            "nodes": [
                {
                    "id": node_id,
                    "type": data.get("type", "unknown"),
                    "name": data.get("display_name", node_id),
                }
                for node_id, data in self.graph.graph.nodes(data=True)
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "relationship": data.get("relationship", "depends on"),
                }
                for source, target, data in self.graph.graph.edges(data=True)
            ],
            "metadata": {
                "generator": "hugo-deps",
                "totalNodes": self.graph.get_node_count(),
                "totalEdges": self.graph.get_edge_count(),
            },
        }

        return json.dumps(simple_data, indent=2, ensure_ascii=False)

    def format_detailed(self) -> str:
        """Format graph in detailed JSON format with full metadata.

        Returns:
            Detailed JSON string with complete node and edge information

        """
        return self.format_graph(
            include_metadata=True,
            include_statistics=True,
            schema_version="1.0-detailed",
        )

    def validate_json_schema(self, *, json_data: dict[str, Any]) -> dict[str, Any]:
        """Validate JSON data against the Hugo dependencies schema.

        Args:
            json_data: JSON data to validate

        Returns:
            Validation result with errors and warnings

        """
        errors = []
        warnings = []

        try:
            # Validate against schema
            validation_errors = sorted(
                self._schema_validator.iter_errors(json_data),
                key=lambda e: e.path,
            )
            for error in validation_errors:
                error_path = (
                    " -> ".join(str(p) for p in error.path) if error.path else "root"
                )
                errors.append(
                    f"Schema validation error at '{error_path}': {error.message}",
                )
        except Exception as e:  # noqa: BLE001
            errors.append(f"Schema validation failed: {e}")

        # Additional consistency checks
        warnings.extend(self._consistency_checks(json_data=json_data))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _consistency_checks(self, *, json_data: dict[str, Any]) -> list[str]:
        """Perform consistency checks on the JSON data.

        Args:
            json_data: JSON data to check

        Returns:
            List of warnings

        """
        warnings = []

        # Check for circular references
        if "edges" in json_data and "nodes" in json_data:
            node_ids = {node.get("id") for node in json_data["nodes"] if "id" in node}
            for i, edge in enumerate(json_data["edges"]):
                source = edge.get("source")
                target = edge.get("target")
                if source and source not in node_ids:
                    warnings.append(
                        f"Edge {i} references non-existent source node: {source}",
                    )
                if target and target not in node_ids:
                    warnings.append(
                        f"Edge {i} references non-existent target node: {target}",
                    )

        return warnings

    def _get_hugo_metadata(self) -> dict[str, Any]:
        """Get Hugo-specific metadata for JSON output.

        Returns:
            Dictionary containing Hugo-specific metadata

        """
        base_metadata = self.graph.get_metadata()

        # Ensure required metadata fields
        hugo_metadata = {
            "generator": "hugo-deps",
            "totalNodes": self.graph.get_node_count(),
            "totalEdges": self.graph.get_edge_count(),
            "analysis_date": datetime.now(timezone.utc).isoformat(),
        }

        # Add any additional metadata from the graph
        hugo_metadata.update(base_metadata)

        return hugo_metadata

    def save_to_file(
        self,
        file_path: Path,
        format_type: str = "detailed",
        *,
        validate_output: bool = True,
    ) -> None:
        """Save JSON output to file.

        Args:
            file_path: Path to save the JSON file
            format_type: Type of format ('simple', 'detailed', or 'custom')
            validate_output: Whether to validate the JSON output before saving

        Raises:
            ValueError: If format_type is invalid or validation fails
            OSError: If file cannot be written

        """
        # Generate JSON based on format type
        try:
            if format_type == "simple":
                json_output = self.format_simple()
            elif format_type == "detailed":
                json_output = self.format_detailed()
            elif format_type == "custom":
                json_output = self.format_graph(
                    include_metadata=True,
                    include_statistics=False,
                )
            else:
                msg = f"Invalid format_type: {format_type}. Use 'simple', 'detailed', or 'custom'"
                raise ValueError(msg)
        except Exception as e:
            msg = f"Failed to generate JSON output: {e}"
            raise ValueError(msg) from e

        # Validate output if requested
        if validate_output:
            try:
                json_data = json.loads(json_output)
                validation_result = self.validate_json_schema(json_data=json_data)
                if not validation_result["valid"]:
                    error_msg = "JSON validation failed:\n"
                    for error in validation_result["errors"]:
                        error_msg += f"  - {error}\n"
                    if validation_result["warnings"]:
                        error_msg += "Warnings:\n"
                        for warning in validation_result["warnings"]:
                            error_msg += f"  - {warning}\n"
                    raise ValueError(error_msg.rstrip())
            except json.JSONDecodeError as e:
                msg = f"Generated JSON is invalid: {e}"
                raise ValueError(msg) from e

        # Write to file with error handling
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                f.write(json_output)
        except OSError as e:
            msg = f"Failed to write JSON to file {file_path}: {e}"
            raise OSError(msg) from e

    def _get_formatted_nodes(self, *, include_metadata: bool) -> list[dict[str, Any]]:
        """Get formatted node data for JSON output.

        Args:
            include_metadata: Whether to include detailed metadata

        Returns:
            List of formatted node objects

        """
        nodes = []

        for node_id, data in self.graph.graph.nodes(data=True):
            node_data: dict[str, Any] = {
                "id": node_id,
                "type": data.get("type", "unknown"),
                "name": data.get("display_name", node_id),
                "source": data.get("source", "unknown"),  # Add source information
            }

            if include_metadata:
                # Add Hugo template-specific metadata
                metadata = {}

                # Standard Hugo template metadata
                hugo_fields = [
                    "file_path",
                    "template_type",
                    "line_number",
                    "content_type",
                ]
                for field in hugo_fields:
                    if field in data:
                        value = data[field]
                        if isinstance(value, Path):
                            metadata[field] = str(value)
                        else:
                            metadata[field] = value

                # Add all additional attributes as metadata
                for key, value in data.items():
                    if key not in ["type", "display_name", *hugo_fields]:
                        # Convert Path objects to strings for JSON serialization
                        if isinstance(value, Path):
                            metadata[key] = str(value)
                        elif hasattr(value, "__dict__"):
                            # Handle complex objects by converting to string representation
                            metadata[key] = str(value)
                        else:
                            metadata[key] = value

                if metadata:
                    node_data["metadata"] = metadata

            nodes.append(node_data)

        return nodes

    def _get_formatted_edges(self, *, include_metadata: bool) -> list[dict[str, Any]]:
        """Get formatted edge data for JSON output.

        Args:
            include_metadata: Whether to include detailed metadata

        Returns:
            List of formatted edge objects

        """
        edges = []

        for source, target, data in self.graph.graph.edges(data=True):
            edge_data: dict[str, Any] = {
                "source": source,
                "target": target,
                "relationship": data.get("relationship", "depends on"),
            }

            if include_metadata:
                # Add Hugo template-specific metadata
                metadata = {}

                # Standard Hugo relationship metadata
                hugo_fields = ["line_number", "context", "include_type", "block_name"]
                for field in hugo_fields:
                    if field in data:
                        metadata[field] = data[field]

                # Add all additional attributes as metadata
                for key, value in data.items():
                    if key not in ["relationship", *hugo_fields]:
                        if isinstance(value, Path):
                            metadata[key] = str(value)
                        else:
                            metadata[key] = value

                if metadata:
                    edge_data["metadata"] = metadata

            edges.append(edge_data)

        return edges

    def _get_graph_statistics(self) -> dict[str, Any]:
        """Get graph statistics for JSON output.

        Returns:
            Dictionary containing graph statistics

        """
        stats: dict[str, int | bool] = {
            "total_nodes": self.graph.get_node_count(),
            "total_edges": self.graph.get_edge_count(),
            "has_cycles": self.graph.has_cycles(),
        }

        # Node type statistics
        node_types = {}
        for _, data in self.graph.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        stats["node_types"] = node_types

        # Edge relationship statistics
        edge_relationships = {}
        for _, _, data in self.graph.graph.edges(data=True):
            relationship = data.get("relationship", "unknown")
            edge_relationships[relationship] = (
                edge_relationships.get(relationship, 0) + 1
            )
        stats["edge_relationships"] = edge_relationships

        # Cycle information
        if stats["has_cycles"]:
            cycles = self.graph.get_cycles()
            stats["cycle_count"] = len(cycles)
            stats["cycles"] = cycles

        return stats
