"""Tests for DOT output formatter."""

import tempfile
from pathlib import Path

import pytest

from hugo_template_dependencies.output.dot_formatter import DOTFormatter
from tests.conftest import MockGraph


@pytest.fixture
def dot_formatter(mock_graph: MockGraph) -> DOTFormatter:
    """Create DOT formatter with mock graph."""
    return DOTFormatter(mock_graph)


class TestDOTFormatter:
    """Test cases for DOT formatter."""

    def test_format_graph_basic(self, dot_formatter: DOTFormatter) -> None:
        """Test basic graph formatting."""
        result = dot_formatter.format_graph()

        # Check DOT structure
        assert result.startswith("digraph hugo_dependencies {")
        assert result.endswith("}")

        # Check for required elements
        assert "layout = dot;" in result
        assert "rankdir = TB;" in result
        assert "bgcolor=white;" in result

    def test_format_graph_with_subgraphs(self, dot_formatter: DOTFormatter) -> None:
        """Test graph formatting with subgraphs."""
        result = dot_formatter.format_graph(include_subgraphs=True)

        # Should contain subgraphs
        assert "subgraph" in result
        # Should contain cluster for "other" since mock nodes don't have proper file paths
        assert "cluster_other" in result

    def test_format_graph_without_subgraphs(self, dot_formatter: DOTFormatter) -> None:
        """Test graph formatting without subgraphs."""
        result = dot_formatter.format_graph(include_subgraphs=False)

        # Should not contain subgraphs
        assert "subgraph" not in result
        assert "cluster_" not in result

        # Should contain nodes directly
        assert "template1" in result
        assert "template2" in result
        assert "block1" in result

    def test_format_graph_with_styles(self, dot_formatter: DOTFormatter) -> None:
        """Test graph formatting with styles."""
        result = dot_formatter.format_graph(include_styles=True)

        # Should contain style definitions
        assert "fillcolor=" in result
        assert "color=" in result
        assert "shape=" in result

    def test_format_graph_without_styles(self, dot_formatter: DOTFormatter) -> None:
        """Test graph formatting without styles."""
        result = dot_formatter.format_graph(include_styles=False)

        # Should not contain style definitions
        assert "fillcolor=" not in result
        assert "color=" not in result

        # Should contain basic labels
        assert 'label="' in result

    def test_format_simple(self, dot_formatter: DOTFormatter) -> None:
        """Test simple format."""
        result = dot_formatter.format_simple()

        # Simple format should not have subgraphs or styles
        assert "subgraph" not in result
        assert "fillcolor=" not in result
        assert "color=" not in result

        # Should have basic structure
        assert "digraph hugo_dependencies {" in result
        assert "template1" in result
        assert "template2" in result

    def test_format_clustered(self, dot_formatter: DOTFormatter) -> None:
        """Test clustered format."""
        result = dot_formatter.format_clustered()

        # Clustered format should have subgraphs and styles
        assert "subgraph" in result
        assert "cluster_" in result
        assert "fillcolor=" in result
        assert "color=" in result

    def test_save_to_file_simple(self, dot_formatter: DOTFormatter) -> None:
        """Test saving simple format to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.dot"

            dot_formatter.save_to_file(str(file_path), format_type="simple")

            assert file_path.exists()

            # Load and verify content
            content = file_path.read_text()
            assert "digraph hugo_dependencies {" in content
            assert "subgraph" not in content

    def test_save_to_file_clustered(self, dot_formatter: DOTFormatter) -> None:
        """Test saving clustered format to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.dot"

            dot_formatter.save_to_file(str(file_path), format_type="clustered")

            assert file_path.exists()

            # Load and verify content
            content = file_path.read_text()
            assert "digraph hugo_dependencies {" in content
            assert "subgraph" in content

    def test_save_to_file_invalid_format(self, dot_formatter: DOTFormatter) -> None:
        """Test saving with invalid format type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "output.dot"

            with pytest.raises(ValueError, match="Invalid format_type"):
                dot_formatter.save_to_file(str(file_path), format_type="invalid")

    def test_get_node_style_config(self, dot_formatter: DOTFormatter) -> None:
        """Test node style configuration."""
        # Test template style
        style = dot_formatter._get_node_style_config(node_type="template")
        assert "shape=box" in style
        assert 'fillcolor="#e1f5fe"' in style
        assert 'color="#01579b"' in style

        # Test partial style
        style = dot_formatter._get_node_style_config(node_type="partial")
        assert "shape=ellipse" in style
        assert 'fillcolor="#FFE6E6"' in style
        assert 'color="#E24A4A"' in style

        # Test unknown style
        style = dot_formatter._get_node_style_config(node_type="unknown")
        assert "shape=box" in style
        assert 'fillcolor="#f5f5f5"' in style

    def test_get_edge_style_config(self, dot_formatter: DOTFormatter) -> None:
        """Test edge style configuration."""
        # Test includes style
        style = dot_formatter._get_edge_style_config(relationship="includes")
        assert 'color="#2196f3"' in style
        assert "style=solid" in style
        assert "arrowhead=normal" in style

        # Test defines style
        style = dot_formatter._get_edge_style_config(relationship="defines")
        assert 'color="#4caf50"' in style
        assert "style=bold" in style
        assert "arrowhead=diamond" in style

        # Test unknown style
        style = dot_formatter._get_edge_style_config(relationship="unknown")
        assert 'color="#9e9e9e"' in style
        assert "style=solid" in style

    def test_get_subgraph_style(self, dot_formatter: DOTFormatter) -> None:
        """Test subgraph style configuration."""
        # Test template subgraph style
        style = dot_formatter._get_subgraph_style(node_type="template")
        assert "filled" in style
        assert 'fillcolor="#e1f5fe"' in style

        # Test unknown subgraph style
        style = dot_formatter._get_subgraph_style(node_type="unknown")
        assert "filled" in style
        assert 'fillcolor="#f5f5f5"' in style

    def test_sanitize_id(self, dot_formatter: DOTFormatter) -> None:
        """Test ID sanitization."""
        # Test basic sanitization
        assert dot_formatter._sanitize_id(node_id="test/id") == "local_test_id"
        assert dot_formatter._sanitize_id(node_id="test.id") == "local_test"
        assert dot_formatter._sanitize_id(node_id="test-id") == "local_test_id"
        assert dot_formatter._sanitize_id(node_id="test id") == "local_test_id"
        assert dot_formatter._sanitize_id(node_id="test(id)") == "local_testid"

        # Test numeric start
        assert dot_formatter._sanitize_id(node_id="123test") == "local_123test"
        assert dot_formatter._sanitize_id(node_id="-test") == "local_test"

        # Test empty ID
        assert dot_formatter._sanitize_id(node_id="") == "local_"

        # Test all numeric
        result = dot_formatter._sanitize_id(node_id="123")
        assert result.startswith("local_node_")

    def test_get_node_label(self, dot_formatter: DOTFormatter) -> None:
        """Test node label generation."""
        # Test basic label
        data = {"display_name": "Test Template"}
        label = dot_formatter._get_node_label(node_id="test", data=data)
        assert label == "Test Template"

        # Test label with file path
        data = {"display_name": "Test Template", "file_path": "/path/to/test.html"}
        label = dot_formatter._get_node_label(node_id="test", data=data)
        assert "Test Template" in label
        assert "/path/to/test.html" in label

        # Test label without display name
        data = {"file_path": "/path/to/test.html"}
        label = dot_formatter._get_node_label(node_id="test", data=data)
        assert label == "test"

    def test_get_node_attributes(self, dot_formatter: DOTFormatter) -> None:
        """Test node attribute generation."""
        data = {"display_name": "Test", "file_path": "/path/to/test.html"}
        attributes = dot_formatter._get_node_attributes(node_type="template", data=data)

        # Should include both display name and file path in label
        assert 'label="Test\\n/path/to/test.html"' in attributes
        assert "shape=box" in attributes
        assert "style=filled" in attributes
        assert 'fillcolor="#e1f5fe"' in attributes
        assert 'tooltip="/path/to/test.html"' in attributes

    def test_get_edge_attributes(self, dot_formatter: DOTFormatter) -> None:
        """Test edge attribute generation."""
        data = {"line_number": 5, "context": "test context"}
        attributes = dot_formatter._get_edge_attributes(
            relationship="includes",
            data=data,
        )

        assert 'label="includes"' in attributes
        assert 'color="#2196f3"' in attributes
        assert "style=solid" in attributes
        assert 'xlabel="L5"' in attributes
        assert 'tooltip="test context"' in attributes

    def test_get_global_styles(self, dot_formatter: DOTFormatter) -> None:
        """Test global style generation."""
        styles = dot_formatter._get_global_styles()

        assert isinstance(styles, list)
        assert "bgcolor=white" in " ".join(styles)
        assert "pad=1" in " ".join(styles)
