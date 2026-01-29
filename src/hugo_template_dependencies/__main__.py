"""Main entry point for hugo_template_dependencies package.

This module allows the package to be executed with `python -m hugo_template_dependencies`.
"""

from __future__ import annotations

from .cli import app

if __name__ == "__main__":
    app()
