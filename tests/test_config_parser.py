"""Tests for the Hugo config parser module resolution functionality."""

import tempfile
from pathlib import Path

from hugo_template_dependencies.config.parser import HugoConfigParser


class TestHugoConfigParserModuleResolution:
    """Test cases for Hugo config parser module resolution."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = HugoConfigParser()

    def test_scan_cache_for_module_direct_match(self) -> None:
        """Test finding module with direct path@version match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create a direct match: module@version (using _ instead of / as in real cache)
            module_dir = cache_dir / "golang.foundata.com_hugo-theme-dev@v1.0.0"
            module_dir.mkdir()

            # Test direct match
            result = self.parser._scan_cache_for_module(
                cache_dir,
                "golang.foundata.com/hugo-theme-dev",
                "v1.0.0",
            )

            assert result == module_dir

    def test_scan_cache_for_module_no_preferred_version(self) -> None:
        """Test finding latest version when no preferred version specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create multiple versions
            v1_dir = cache_dir / "example.com_theme@v1.0.0"
            v2_dir = cache_dir / "example.com_theme@v2.0.0"
            v1_dir.mkdir()
            v2_dir.mkdir()

            result = self.parser._scan_cache_for_module(
                cache_dir,
                "example.com/theme",
                None,
            )

            # Should return the lexicographically latest version (v2.0.0)
            assert result == v2_dir

    def test_scan_cache_for_module_not_found(self) -> None:
        """Test behavior when module is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            result = self.parser._scan_cache_for_module(
                cache_dir,
                "nonexistent.com/theme",
                "v1.0.0",
            )

            assert result is None

    def test_scan_cache_for_module_version_selection(self) -> None:
        """Test version selection logic with multiple available versions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create multiple versions in different formats
            versions = [
                "example.com_theme@v1.0.0",
                "example.com_theme@v1.1.0",
                "example.com_theme@v2.0.0-beta",
                "example.com_theme@v2.0.0",
            ]

            for version in versions:
                (cache_dir / version).mkdir()

            # Test exact version match
            result = self.parser._scan_cache_for_module(
                cache_dir,
                "example.com/theme",
                "v1.1.0",
            )
            assert result is not None
            assert "v1.1.0" in result.name

            # Test latest version (no preferred)
            result = self.parser._scan_cache_for_module(
                cache_dir,
                "example.com/theme",
                None,
            )
            # Should get latest (lexicographically)
            assert result is not None
            assert "v2.0.0" in result.name

    def test_module_resolution_edge_cases(self) -> None:
        """Test edge cases in module resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Case 1: Empty cache directory
            result = self.parser._scan_cache_for_module(
                cache_dir,
                "any/module",
                "v1.0.0",
            )
            assert result is None

            # Case 2: Cache directory with non-module directories
            (cache_dir / "random-dir").mkdir()
            (cache_dir / "another-dir").mkdir()

            result = self.parser._scan_cache_for_module(
                cache_dir,
                "any/module",
                "v1.0.0",
            )
            assert result is None
