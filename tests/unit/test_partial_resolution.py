"""Test partial resolution and path normalization logic."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from hugo_template_dependencies.cli import _build_partial_lookup, _add_partial_lookup_entries


class TestPartialResolution:
    """Test suite for partial resolution logic."""

    @pytest.fixture
    def sample_partials(self):
        """Create sample partial templates for testing."""
        return [
            Path("layouts/_partials/header.html"),
            Path("layouts/_partials/footer.html"),
            Path("layouts/_partials/components/button.html"),
            Path("layouts/_partials/components/form.html"),
            Path("layouts/_partials/modules/navigation/menu.html"),
            Path("layouts/_partials/modules/navigation/breadcrumb.html"),
            Path("layouts/partials/calendar_icon.html"),  # Non-underscore partials dir
        ]

    def test_build_partial_lookup_basic(self, sample_partials):
        """Test basic partial lookup generation."""
        lookup = _build_partial_lookup(sample_partials)

        # Test basic lookup entries exist
        assert "header.html" in lookup
        assert "footer.html" in lookup
        assert "_partials/header.html" in lookup
        assert "_partials/footer.html" in lookup

        # Test resolution paths are correct
        assert lookup["header.html"] == Path("layouts/_partials/header.html")
        assert lookup["_partials/header.html"] == Path("layouts/_partials/header.html")

    def test_build_partial_lookup_nested_components(self, sample_partials):
        """Test lookup for nested component partials."""
        lookup = _build_partial_lookup(sample_partials)

        # Test nested component lookups
        assert "components/button.html" in lookup
        assert "components/form.html" in lookup
        assert "_partials/components/button.html" in lookup
        assert "_partials/components/form.html" in lookup

        # Test resolution paths
        expected_button = Path("layouts/_partials/components/button.html")
        assert lookup["components/button.html"] == expected_button
        assert lookup["_partials/components/button.html"] == expected_button

    def test_build_partial_lookup_deep_nesting(self, sample_partials):
        """Test lookup for deeply nested partials."""
        lookup = _build_partial_lookup(sample_partials)

        # Test deeply nested paths
        assert "modules/navigation/menu.html" in lookup
        assert "_partials/modules/navigation/menu.html" in lookup
        assert "navigation/menu.html" in lookup
        assert "navigation/breadcrumb.html" in lookup

    def test_build_partial_lookup_non_underscore_partials(self, sample_partials):
        """Test lookup for partials in non-underscore partials directory."""
        lookup = _build_partial_lookup(sample_partials)

        # Test non-underscore partials dir
        assert "calendar_icon.html" in lookup
        assert "partials/calendar_icon.html" in lookup
        expected_calendar = Path("layouts/partials/calendar_icon.html")
        assert lookup["calendar_icon.html"] == expected_calendar

    def test_partial_lookup_entries_generation(self):
        """Test the _add_partial_lookup_entries function directly."""
        lookup = {}
        partial_path = Path("layouts/_partials/components/forms/input.html")

        _add_partial_lookup_entries(lookup, partial_path)

        # Should create multiple lookup entries
        expected_entries = {
            "_partials/components/forms/input.html",
            "partials/components/forms/input.html",
            "components/forms/input.html",
            "forms/input.html",
            "input.html",
        }

        for entry in expected_entries:
            assert entry in lookup
            assert lookup[entry] == partial_path

    def test_partial_lookup_conflict_resolution(self):
        """Test how conflicts are handled in partial lookup."""
        # Create partials with name conflicts
        partials = [
            Path("layouts/_partials/header.html"),
            Path("layouts/_partials/components/header.html"),
        ]

        lookup = _build_partial_lookup(partials)

        # Both should be accessible by their full paths
        assert "_partials/header.html" in lookup
        assert "_partials/components/header.html" in lookup
        assert "components/header.html" in lookup

        # Short name should resolve to first one found
        assert "header.html" in lookup

    def test_edge_cases_partial_resolution(self):
        """Test edge cases in partial resolution."""
        # Test empty list
        lookup = _build_partial_lookup([])
        assert lookup == {}

        # Test single partial
        single_partial = [Path("layouts/_partials/single.html")]
        lookup = _build_partial_lookup(single_partial)
        assert "single.html" in lookup
        assert "_partials/single.html" in lookup
