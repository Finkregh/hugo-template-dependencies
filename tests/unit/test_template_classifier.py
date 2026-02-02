"""Test template classification logic."""

import pytest
from pathlib import Path

from hugo_template_dependencies.analyzer.template_parser import HugoTemplateParser
from hugo_template_dependencies.graph.hugo_graph import TemplateType


class TestTemplateClassification:
    """Test suite for template type classification."""

    def test_partial_in_partials_directory(self):
        """Test detection of partials in _partials directory."""
        path = Path("layouts/_partials/header.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.PARTIAL

    def test_partial_in_nested_partials_directory(self):
        """Test detection of nested partials in _partials subdirectories."""
        path = Path("layouts/_partials/components/button.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.PARTIAL

    def test_underscore_prefixed_file_outside_partials(self):
        """Test that underscore-prefixed files outside _partials are not partials."""
        path = Path("layouts/_default/_meta.html")
        result = HugoTemplateParser._determine_template_type(path)
        # Files with underscores outside _partials directories are regular templates
        assert result == TemplateType.TEMPLATE

    def test_shortcode_template(self):
        """Test detection of shortcode templates."""
        path = Path("layouts/shortcodes/youtube.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.SHORTCODE

    def test_shortcode_in_nested_directory(self):
        """Test detection of shortcodes in nested directories."""
        path = Path("layouts/_shortcodes/nested/video.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.SHORTCODE

    def test_regular_template_defaults_to_template(self):
        """Test that unrecognized templates default to TEMPLATE type."""
        path = Path("layouts/_default/single.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.TEMPLATE

    def test_index_template_defaults_to_template(self):
        """Test that index templates are classified as TEMPLATE."""
        path = Path("layouts/index.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.TEMPLATE

    def test_baseof_template_defaults_to_template(self):
        """Test that baseof templates are classified as TEMPLATE."""
        path = Path("layouts/_default/baseof.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.TEMPLATE

    def test_list_template_defaults_to_template(self):
        """Test that list templates are classified as TEMPLATE."""
        path = Path("layouts/_default/list.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.TEMPLATE

    def test_deeply_nested_partial(self):
        """Test deeply nested partials are correctly classified."""
        path = Path("layouts/_partials/modules/forms/contact/fields.html")
        result = HugoTemplateParser._determine_template_type(path)
        assert result == TemplateType.PARTIAL
