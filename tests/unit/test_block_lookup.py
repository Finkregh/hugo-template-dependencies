"""Tests for block definition lookup functionality."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from hugo_template_dependencies.cli import _build_block_lookup
from hugo_template_dependencies.graph.hugo_graph import HugoTemplate, TemplateType

if TYPE_CHECKING:
    pass


class TestBlockLookup:
    """Test block definition lookup functionality added for RenderImageSimple fix."""

    def test_build_block_lookup_basic(self) -> None:
        """Test basic block lookup table construction."""
        template1 = HugoTemplate(
            file_path=Path("/layouts/render-image.html"),
            template_type=TemplateType.PARTIAL,
            dependencies=[
                {
                    "type": "block_definition",
                    "target": "RenderImageSimple",
                    "line_number": 1,
                    "context": '{{- define "RenderImageSimple" -}}',
                }
            ],
        )

        template2 = HugoTemplate(
            file_path=Path("/layouts/component.html"),
            template_type=TemplateType.PARTIAL,
            dependencies=[
                {
                    "type": "block_definition",
                    "target": "ComponentBox",
                    "line_number": 5,
                    "context": '{{- define "ComponentBox" -}}',
                },
                {
                    "type": "partial",
                    "target": "header.html",
                    "line_number": 10,
                    "context": '{{ partial "header.html" . }}',
                },
            ],
        )

        parsed_templates = {
            str(template1.file_path): template1,
            str(template2.file_path): template2,
        }

        block_lookup = _build_block_lookup(parsed_templates)

        # Verify block lookup table
        assert "RenderImageSimple" in block_lookup
        assert "ComponentBox" in block_lookup
        assert block_lookup["RenderImageSimple"] == template1
        assert block_lookup["ComponentBox"] == template2

        # Verify non-block dependencies are not in lookup
        assert "header.html" not in block_lookup

    def test_build_block_lookup_empty(self) -> None:
        """Test block lookup table with no block definitions."""
        template = HugoTemplate(
            file_path=Path("/layouts/simple.html"),
            template_type=TemplateType.SINGLE,
            dependencies=[
                {
                    "type": "partial",
                    "target": "header.html",
                    "line_number": 1,
                    "context": '{{ partial "header.html" . }}',
                }
            ],
        )

        parsed_templates = {str(template.file_path): template}
        block_lookup = _build_block_lookup(parsed_templates)

        assert len(block_lookup) == 0

    def test_build_block_lookup_multiple_blocks_single_template(self) -> None:
        """Test multiple block definitions in a single template."""
        template = HugoTemplate(
            file_path=Path("/layouts/_partials/multi-blocks.html"),
            template_type=TemplateType.PARTIAL,
            dependencies=[
                {
                    "type": "block_definition",
                    "target": "FirstBlock",
                    "line_number": 1,
                    "context": '{{- define "FirstBlock" -}}',
                },
                {
                    "type": "block_definition",
                    "target": "SecondBlock",
                    "line_number": 10,
                    "context": '{{- define "SecondBlock" -}}',
                },
                {
                    "type": "block_definition",
                    "target": "ThirdBlock",
                    "line_number": 20,
                    "context": '{{- define "ThirdBlock" -}}',
                },
            ],
        )

        parsed_templates = {str(template.file_path): template}
        block_lookup = _build_block_lookup(parsed_templates)

        # All blocks should map to the same template
        assert len(block_lookup) == 3
        assert block_lookup["FirstBlock"] == template
        assert block_lookup["SecondBlock"] == template
        assert block_lookup["ThirdBlock"] == template

    def test_build_block_lookup_no_dependencies(self) -> None:
        """Test template with no dependencies."""
        template = HugoTemplate(
            file_path=Path("/layouts/empty.html"),
            template_type=TemplateType.SINGLE,
            dependencies=None,
        )

        parsed_templates = {str(template.file_path): template}
        block_lookup = _build_block_lookup(parsed_templates)

        assert len(block_lookup) == 0

    def test_build_block_lookup_mixed_dependency_types(self) -> None:
        """Test template with mixed dependency types including block definitions."""
        template = HugoTemplate(
            file_path=Path("/layouts/complex.html"),
            template_type=TemplateType.SINGLE,
            dependencies=[
                {
                    "type": "partial",
                    "target": "header.html",
                    "line_number": 1,
                    "context": '{{ partial "header.html" . }}',
                },
                {
                    "type": "block_definition",
                    "target": "ContentBlock",
                    "line_number": 5,
                    "context": '{{- define "ContentBlock" -}}',
                },
                {
                    "type": "template",
                    "target": "footer.html",
                    "line_number": 15,
                    "context": '{{ template "footer.html" . }}',
                },
                {
                    "type": "block_definition",
                    "target": "SidebarBlock",
                    "line_number": 20,
                    "context": '{{- define "SidebarBlock" -}}',
                },
            ],
        )

        parsed_templates = {str(template.file_path): template}
        block_lookup = _build_block_lookup(parsed_templates)

        # Only block definitions should be in lookup
        assert len(block_lookup) == 2
        assert "ContentBlock" in block_lookup
        assert "SidebarBlock" in block_lookup
        assert "header.html" not in block_lookup
        assert "footer.html" not in block_lookup

        # Both blocks should map to the same template
        assert block_lookup["ContentBlock"] == template
        assert block_lookup["SidebarBlock"] == template
