"""Abstract base classes for graph builders and renderers.

This module provides foundation for building dependency graphs using NetworkX.
The abstract base classes ensure consistent interfaces while allowing for
specialized implementations for different types of dependency analysis.
"""

from abc import ABC, abstractmethod
from typing import Any

import networkx as nx


class GraphBase(ABC):
    """Abstract base class for graph builders.

    This class provides a common interface for building dependency graphs
    using NetworkX. Subclasses must implement abstract methods to
    define how nodes and edges are added to graph.

    The class maintains a NetworkX DiGraph internally and provides
    utility methods for common graph operations like filtering nodes
    by type and creating subgraphs.

    Attributes:
        graph: The underlying NetworkX directed graph
        _nodes: Dictionary storing node metadata
        _metadata: Dictionary storing graph-level metadata

    Example:
        >>> class MyGraph(GraphBase):
        ...     def add_node(self, node_id: str, node_type: str, **attributes):
        ...         self.graph.add_node(node_id, type=node_type, **attributes)
        ...         self._nodes[node_id] = attributes
        ...
        ...     def add_edge(self, source: str, target: str, relationship: str, **attributes):
        ...         self.graph.add_edge(source, target, relationship=relationship, **attributes)
        >>>
        >>> graph = MyGraph()
        >>> graph.add_node("node1", "file", path="/path/to/file")
        >>> graph.add_node("node2", "file", path="/path/to/other")
        >>> graph.add_edge("node1", "node2", "includes")
    """

    def __init__(self) -> None:
        """Initialize graph builder with an empty directed graph."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, Any] = {}
        self._metadata: dict[str, Any] = {}

    @abstractmethod
    def add_node(self, node_id: str, node_type: str, **attributes: object) -> None:
        """Add a node to graph.

        Args:
            node_id: Unique identifier for node
            node_type: Type/category of node (e.g., 'file', 'repository')
            **attributes: Additional attributes to store with node
        """

    @abstractmethod
    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        **attributes: object,
    ) -> None:
        """Add an edge to graph.

        Args:
            source: Source node identifier
            target: Target node identifier
            relationship: Type of relationship (e.g., 'includes', 'depends_on')
            **attributes: Additional attributes to store with edge
        """

    def get_graph(self) -> nx.DiGraph:
        """Get underlying NetworkX graph.

        Returns:
            The NetworkX directed graph containing all nodes and edges
        """
        return self.graph

    def get_nodes_by_type(self, node_type: str) -> list[str]:
        """Get all nodes of a specific type.

        Args:
            node_type: The type of nodes to retrieve

        Returns:
            List of node identifiers matching specified type
        """
        return [
            node_id
            for node_id, data in self.graph.nodes(data=True)
            if data.get("type") == node_type
        ]

    def get_subgraph_by_attribute(self, attribute: str, value: str) -> nx.DiGraph:
        """Get subgraph containing nodes with specific attribute value.

        Args:
            attribute: The attribute name to filter by
            value: The attribute value to match

        Returns:
            A subgraph containing only nodes with the specified attribute value
        """
        nodes = [
            node_id
            for node_id, data in self.graph.nodes(data=True)
            if data.get(attribute) == value
        ]
        # Create a new DiGraph from subgraph to maintain type consistency
        subgraph = self.graph.subgraph(nodes)
        return nx.DiGraph(subgraph)

    def get_node_count(self) -> int:
        """Get total number of nodes in graph.

        Returns:
            Number of nodes in graph
        """
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        """Get total number of edges in graph.

        Returns:
            Number of edges in graph
        """
        return self.graph.number_of_edges()

    def has_cycles(self) -> bool:
        """Check if graph contains any cycles.

        Returns:
            True if graph contains cycles, False otherwise
        """
        return not nx.is_directed_acyclic_graph(self.graph)

    def get_cycles(self) -> list[list[str]]:
        """Get all cycles in graph.

        Returns:
            List of cycles, where each cycle is a list of node identifiers
        """
        try:
            return list(nx.simple_cycles(self.graph))
        except nx.NetworkXError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        """Get graph-level metadata.

        Returns:
            Dictionary containing graph metadata
        """
        return self._metadata.copy()

    def set_metadata(self, key: str, value: object) -> None:
        """Set graph-level metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value
