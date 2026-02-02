"""Hugo configuration parser for module integration.

This module provides functionality to parse Hugo configuration files
and extract module import information for dependency analysis.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import toml


class HugoConfigParser:
    """Parser for Hugo configuration files.

    This class parses Hugo configuration files and extracts module import
    information for dependency analysis.
    """

    def __init__(self) -> None:
        """Initialize Hugo configuration parser."""
        self.config_files = ["hugo.toml", "config.toml", "config.yaml", "config.yml"]

    def parse_hugo_config(self, project_path: Path) -> dict[str, Any]:
        """Parse Hugo configuration by executing hugo config command.

        Args:
            project_path: Path to Hugo project

        Returns:
            Parsed configuration dictionary

        Raises:
            ValueError: If Hugo command fails or config is invalid

        """
        try:
            # Execute hugo config command in project directory
            result = subprocess.run(
                ["hugo", "config"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = f"Failed to execute 'hugo config': {result.stderr}"
                raise ValueError(error_msg)

            # Parse TOML output
            return toml.loads(result.stdout)

        except subprocess.TimeoutExpired:
            error_msg = "hugo config command timed out after 30 seconds"
            raise ValueError(error_msg)
        except FileNotFoundError:
            error_msg = "hugo command not found. Please ensure Hugo is installed."
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error parsing Hugo config: {e}"
            raise ValueError(error_msg) from e

    def extract_module_imports(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract module imports from Hugo configuration.

        Args:
            config: Parsed Hugo configuration dictionary

        Returns:
            List of module import dictionaries

        """
        imports = []

        # Extract module imports from different possible locations
        if "module" in config:
            module_config = config["module"]

            # Handle imports list
            if "imports" in module_config:
                for import_item in module_config["imports"]:
                    if isinstance(import_item, dict):
                        imports.append(import_item)
                    elif isinstance(import_item, list):
                        imports.extend(import_item)

        return imports

    def get_cachedir(self, config: dict[str, Any]) -> Path | None:
        """Extract cachedir from Hugo configuration.

        Args:
            config: Parsed Hugo configuration dictionary

        Returns:
            Cache directory path if specified, None otherwise

        """
        # Check for cachedir in different possible locations
        if "caches" in config:
            caches_config = config["caches"]
            if "cachedir" in caches_config:
                cachedir_path = caches_config["cachedir"]
                return Path(cachedir_path).expanduser()

        # Default Hugo cache location
        return (
            Path.home()
            / ".hugo"
            / "cache"
            / "modules"
            / "filecache"
            / "modules"
            / "pkg"
            / "mod"
            / "cache"
            / "download"
        )

    def resolve_module_path(
        self,
        module_import: dict[str, Any],
        project_path: Path,
        cachedir: Path | None = None,
    ) -> Path | None:
        """Resolve module import path to actual file system location.

        Args:
            module_import: Module import dictionary
            project_path: Hugo project path
            cachedir: Optional Hugo cache directory

        Returns:
            Resolved path to module, or None if not found

        """
        module_path = module_import.get("path")
        if not module_path:
            return None

        module_path = Path(module_path)

        # Check if path is relative
        if not module_path.is_absolute():
            # Resolve relative to project directory
            resolved_path = project_path / module_path
            if resolved_path.exists():
                return resolved_path
        # Handle remote/module paths using cache
        elif cachedir:
            cache_path = cachedir / module_path
            if cache_path.exists():
                return cache_path

        return None

    def validate_module_imports(self, imports: list[dict[str, Any]]) -> list[str]:
        """Validate module imports and return warnings for issues.

        Args:
            imports: List of module import dictionaries

        Returns:
            List of warning messages

        """
        warnings = []
        seen_paths = set()

        for i, import_item in enumerate(imports):
            path = import_item.get("path")
            if not path:
                warnings.append(f"Import {i}: missing path")
                continue

            # Check for duplicate paths
            if path in seen_paths:
                warnings.append(f"Import {i}: duplicate path '{path}'")
            seen_paths.add(path)

            # Check for version conflicts
            version = import_item.get("version")
            if not version:
                warnings.append(f"Import {i}: missing version for '{path}'")

        return warnings
