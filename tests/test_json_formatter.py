"""Tests for JSON output formatter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hugo_template_dependencies.output.json_formatter import JSONFormatter
from tests.conftest import MockGraph


@pytest.fixture
def json_formatter(mock_graph: MockGraph) -> JSONFormatter:
    """Create JSON formatter with mock graph."""
    return JSONFormatter(mock_graph)


class TestJSONFormatter:
    """Test cases for JSON formatter."""

    def test_format_graph_basic(self, json_formatter: JSONFormatter) -> None:
        """Test basic graph formatting."""
        result = json_formatter.format_graph()

        # Should be valid JSON
        data = json.loads(result)

        # Check structure
        assert "schema_version" in data
        assert "generated_at" in data
        assert "graph_type" in data
        assert "nodes" in data
        assert "edges" in data
        assert "statistics" in data
        assert "metadata" in data

        assert data["graph_type"] == "hugo_template_dependencies"
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    def test_format_graph_without_metadata(self, json_formatter: JSONFormatter) -> None:
        """Test graph formatting without metadata."""
        result = json_formatter.format_graph(include_metadata=False)

        data = json.loads(result)

        # Check nodes structure
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "name" in node
            assert "metadata" not in node

        # Check edges structure
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "relationship" in edge
            assert "metadata" not in edge

    def test_format_graph_with_metadata(self, json_formatter: JSONFormatter) -> None:
        """Test graph formatting with metadata."""
        result = json_formatter.format_graph(include_metadata=True)

        data = json.loads(result)

        # Check nodes have metadata
        for node in data["nodes"]:
            assert "metadata" in node
            if node["id"] == "template1":
                assert "file_path" in node["metadata"]
                assert node["metadata"]["file_path"] == "/path/to/template1.html"

    def test_format_simple(self, json_formatter: JSONFormatter) -> None:
        """Test simple format."""
        result = json_formatter.format_simple()

        data = json.loads(result)

        # Simple format should have nodes, edges, and basic metadata
        assert "nodes" in data
        assert "edges" in data
        assert "schema_version" not in data
        assert "statistics" not in data
        assert "metadata" in data

        # Check node structure
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "name" in node
            assert "metadata" not in node

    def test_format_detailed(self, json_formatter: JSONFormatter) -> None:
        """Test detailed format."""
        result = json_formatter.format_detailed()

        data = json.loads(result)

        # Detailed format should have everything
        assert "schema_version" in data
        assert data["schema_version"] == "1.0-detailed"
        assert "nodes" in data
        assert "edges" in data
        assert "statistics" in data
        assert "metadata" in data

    def test_validate_json_schema_valid(self, json_formatter: JSONFormatter) -> None:
        """Test JSON schema validation with valid data."""
        valid_data = {
            "schema_version": "1.0",
            "nodes": [
                {"id": "node1", "type": "template", "name": "Node 1"},
                {"id": "node2", "type": "partial", "name": "Node 2"},
            ],
            "edges": [
                {"source": "node1", "target": "node2", "relationship": "includes"},
            ],
            "metadata": {
                "generator": "hugo-deps",
                "totalNodes": 2,
                "totalEdges": 1,
            },
        }

        result = json_formatter.validate_json_schema(json_data=valid_data)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_json_schema_missing_fields(
        self,
        json_formatter: JSONFormatter,
    ) -> None:
        """Test JSON schema validation with missing required fields."""
        invalid_data = {
            "schema_version": "1.0",
            "nodes": [],
            # Missing "edges" field
        }

        result = json_formatter.validate_json_schema(json_data=invalid_data)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("edges" in error for error in result["errors"])

    def test_validate_json_schema_invalid_nodes(
        self,
        json_formatter: JSONFormatter,
    ) -> None:
        """Test JSON schema validation with invalid nodes."""
        invalid_data = {
            "schema_version": "1.0",
            "nodes": [
                {"type": "template", "name": "Node 1"},  # Missing "id"
            ],
            "edges": [],
        }

        result = json_formatter.validate_json_schema(json_data=invalid_data)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("id" in error for error in result["errors"])

    def test_validate_json_schema_orphaned_edges(
        self,
        json_formatter: JSONFormatter,
    ) -> None:
        """Test JSON schema validation with edges referencing non-existent nodes."""
        data_with_orphans = {
            "schema_version": "1.0",
            "nodes": [
                {"id": "node1", "type": "template", "name": "Node 1"},
            ],
            "edges": [
                {
                    "source": "node1",
                    "target": "nonexistent",
                    "relationship": "includes",
                },
            ],
            "metadata": {
                "generator": "hugo-deps",
                "totalNodes": 1,
                "totalEdges": 1,
            },
        }

        result = json_formatter.validate_json_schema(json_data=data_with_orphans)

        # Should be valid but with warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("nonexistent" in warning for warning in result["warnings"])

    def test_save_to_file_simple(self, json_formatter: JSONFormatter) -> None:
        """Test saving simple format to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.json"

            json_formatter.save_to_file(
                file_path,
                format_type="simple",
                validate_output=False,
            )

            assert file_path.exists()

            # Load and verify content
            with file_path.open() as f:
                data = json.load(f)

            assert "nodes" in data
            assert "edges" in data
            assert "schema_version" not in data

    def test_save_to_file_detailed(self, json_formatter: JSONFormatter) -> None:
        """Test saving detailed format to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.json"

            json_formatter.save_to_file(
                file_path,
                format_type="detailed",
                validate_output=True,
            )

            assert file_path.exists()

            # Load and verify content
            with file_path.open() as f:
                data = json.load(f)

            assert "schema_version" in data
            assert data["schema_version"] == "1.0-detailed"
            assert "statistics" in data
            assert "metadata" in data

    def test_save_to_file_invalid_format(self, json_formatter: JSONFormatter) -> None:
        """Test saving with invalid format type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.json"

            with pytest.raises(ValueError, match="Invalid format_type"):
                json_formatter.save_to_file(file_path, format_type="invalid")

    def test_save_to_file_with_validation_failure(
        self,
        json_formatter: JSONFormatter,
    ) -> None:
        """Test saving with validation failure."""
        # Mock the format method to return invalid JSON
        with patch.object(
            json_formatter, "format_detailed", return_value="{invalid json"
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = Path(temp_dir) / "output.json"

                with pytest.raises(ValueError, match="Generated JSON is invalid"):
                    json_formatter.save_to_file(
                        file_path,
                        format_type="detailed",
                        validate_output=True,
                    )

    def test_get_graph_statistics(self, json_formatter: JSONFormatter) -> None:
        """Test graph statistics generation."""
        result = json_formatter.format_graph(include_statistics=True)
        data = json.loads(result)

        stats = data["statistics"]

        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "has_cycles" in stats
        assert "node_types" in stats
        assert "edge_relationships" in stats

        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert "template" in stats["node_types"]
        assert "partial" in stats["node_types"]
        assert "block" in stats["node_types"]
        assert stats["node_types"]["template"] == 1
        assert stats["node_types"]["partial"] == 1
        assert stats["node_types"]["block"] == 1
