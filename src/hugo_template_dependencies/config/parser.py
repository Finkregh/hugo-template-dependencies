"""Hugo configuration parser for module integration.

This module provides functionality to parse Hugo configuration files
and extract module import information for dependency analysis.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

import toml

logger = logging.getLogger(__name__)


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
                ["hugo", "config"],  # noqa: S607
                cwd=project_path,
                check=True,
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

    def extract_module_replacements(self, config: dict[str, Any]) -> dict[str, str]:
        """Extract module replacements from Hugo configuration.

        Replacements map remote module paths to local/alternative paths.
        Format: 'github.com/user/module -> ../../..'

        Args:
            config: Parsed Hugo configuration dictionary

        Returns:
            Dictionary mapping original paths to replacement paths

        """
        replacements = {}

        if "module" in config and "replacements" in config["module"]:
            replacement_list = config["module"]["replacements"]

            # Can be a single string or list of strings
            if isinstance(replacement_list, str):
                replacement_list = [replacement_list]

            for replacement in replacement_list:
                if not isinstance(replacement, str):
                    continue

                # Parse format: "original -> replacement"
                if "->" in replacement:
                    parts = replacement.split("->", 1)
                    if len(parts) == 2:  # noqa: PLR2004
                        original = parts[0].strip()
                        replaced = parts[1].strip()
                        replacements[original] = replaced
                        logger.debug(f"Found replacement: {original} -> {replaced}")

        return replacements

    def get_cachedir(self, config: dict[str, Any]) -> Path:
        """Extract cachedir from Hugo configuration.

        Args:
            config: Parsed Hugo configuration dictionary

        Returns:
            Cache directory path

        Raises:
            ValueError: If cache directory cannot be determined

        """
        # Check for explicit cacheDir in config
        if "cachedir" in config:
            cachedir_path = config["cachedir"]
            cache_path = Path(cachedir_path).expanduser()
            logger.debug(f"Using explicit cachedir from config: {cache_path}")
            return cache_path

        if "cacheDir" in config:
            cachedir_path = config["cacheDir"]
            cache_path = Path(cachedir_path).expanduser()
            logger.debug(f"Using explicit cacheDir from config: {cache_path}")
            return cache_path

        # Check nested caches config
        if "caches" in config:
            caches_config = config["caches"]
            if "cachedir" in caches_config:
                cachedir_path = caches_config["cachedir"]
                cache_path = Path(cachedir_path).expanduser()
                logger.debug(f"Using cachedir from caches config: {cache_path}")
                return cache_path

        # Default Hugo cache location
        default_cache = Path.home() / "Library" / "Caches" / "hugo_cache"
        logger.debug(f"Using default Hugo cache location: {default_cache}")
        return default_cache

    def resolve_module_path(  # noqa: PLR0912, PLR0915, PLR0911
        self,
        module_import: dict[str, Any],
        project_path: Path,
        cachedir: Path | None = None,
        replacements: dict[str, str] | None = None,
    ) -> Path | None:
        """Resolve module import path to actual file system location.

        Resolution logic:
        1. Check if module has a replacement mapping
        2. If replacement exists:
           - Try as relative path from project (without version)
           - If not found, try cachedir with @version suffix
        3. If no replacement:
           - If version specified: use exact version in cachedir
           - If no version: use latest version from cachedir (semver)

        Args:
            module_import: Module import dictionary with 'path' and optional 'version'
            project_path: Hugo project path
            cachedir: Optional Hugo cache directory
            replacements: Optional module replacement mappings

        Returns:
            Resolved path to module, or None if not found

        """
        module_path_str = module_import.get("path")
        if not module_path_str:
            logger.debug("No 'path' in module import")
            return None

        version = module_import.get("version")
        replacements = replacements or {}

        logger.debug(
            f"Resolving module: {module_path_str} (version: {version or 'none'})",
        )

        # Check if this module has a replacement
        replacement_path = replacements.get(module_path_str)

        if replacement_path:
            logger.debug(
                f"  Found replacement: {module_path_str} -> {replacement_path}",
            )

            # Extract module basename from original path
            # e.g., github.com/finkregh/hugo-theme-component-ical -> hugo-theme-component-ical
            module_basename = (
                module_path_str.split("/")[-1]
                if "/" in module_path_str
                else module_path_str
            )

            # Hugo's replacement format: append module basename to replacement path
            # e.g., ../../.. + hugo-theme-component-ical = ../../../hugo-theme-component-ical
            full_replacement_path = f"{replacement_path}/{module_basename}"
            logger.debug(
                f"  Full replacement path (with basename): {full_replacement_path}",
            )

            # Try as relative path (without version)
            relative_path = Path(full_replacement_path)
            if not relative_path.is_absolute():
                resolved_path = (project_path / relative_path).resolve()
                logger.debug(f"  Trying replacement as relative path: {resolved_path}")

                if resolved_path.exists():
                    logger.debug(
                        f"  ✓ Resolved via replacement (relative): {resolved_path}",
                    )
                    return resolved_path
                logger.debug(
                    f"  ✗ Replacement relative path does not exist: {resolved_path}",
                )

                # Also try without the basename appended (some configs might use full path in replacement)
                fallback_resolved = (project_path / replacement_path).resolve()
                logger.debug(
                    f"  Trying fallback without basename: {fallback_resolved}",
                )
                if fallback_resolved.exists():
                    logger.debug(
                        f"  ✓ Resolved via replacement fallback: {fallback_resolved}",
                    )
                    return fallback_resolved

            # Replacement path doesn't exist locally, try cachedir with version
            if cachedir and version:
                cache_path = self._resolve_from_cache(
                    module_path=module_path_str,
                    version=version,
                    cachedir=cachedir,
                )
                if cache_path:
                    logger.debug(f"  ✓ Resolved replacement from cache: {cache_path}")
                    return cache_path
                logger.debug("  ✗ Replacement not found in cache")

            # Replacement failed - fall through to regular module resolution
            logger.debug(
                f"Replacement not resolved locally or in cache: {module_path_str} -> {replacement_path}. Attempting regular resolution.",
            )

        # No replacement - handle as regular module
        # Check if it's a local relative path
        module_path = Path(module_path_str)
        if not module_path.is_absolute() and not self._is_remote_module(
            module_path_str,
        ):
            # Local relative module - check for reverse replacement lookup
            # If module_path_str appears as a VALUE in replacements, append basename from KEY
            reverse_replacement_basename = None
            for original_path, replacement_value in replacements.items():
                if replacement_value == module_path_str:
                    # Found reverse match: extract basename from original_path
                    reverse_replacement_basename = (
                        original_path.split("/")[-1]
                        if "/" in original_path
                        else original_path
                    )
                    logger.debug(
                        f"  Found reverse replacement: {module_path_str} <- {original_path} (basename: {reverse_replacement_basename})",
                    )
                    break

            if reverse_replacement_basename:
                # Append basename to local path
                full_local_path = f"{module_path_str}/{reverse_replacement_basename}"
                logger.debug(f"  Trying local path with basename: {full_local_path}")
                resolved_with_basename = (project_path / full_local_path).resolve()

                if resolved_with_basename.exists():
                    logger.debug(
                        f"  ✓ Resolved local with basename: {resolved_with_basename}",
                    )
                    return resolved_with_basename
                logger.debug(
                    f"  ✗ Local path with basename does not exist: {resolved_with_basename}",
                )

            # Try original path without basename
            resolved_path = (project_path / module_path).resolve()
            logger.debug(f"  Trying as local relative path: {resolved_path}")

            if resolved_path.exists():
                logger.debug(f"  ✓ Resolved as local module: {resolved_path}")
                return resolved_path
            logger.debug(f"  ✗ Local path does not exist: {resolved_path}")
            return None

        # Remote module - must use cachedir
        if not cachedir:
            logger.warning(
                f"Cannot resolve remote module {module_path_str} without cachedir",
            )
            return None

        # If version specified, use exact version
        if version:
            cache_path = self._resolve_from_cache(module_path_str, version, cachedir)
            if cache_path:
                logger.debug(f"  ✓ Resolved from cache (exact version): {cache_path}")
                return cache_path
            logger.warning(
                f"  ✗ Module not found in cache: {module_path_str}@{version}",
            )
            return None

        # No version specified - find latest
        cache_path = self._find_latest_in_cache(module_path_str, cachedir)
        if cache_path:
            logger.debug(f"  ✓ Resolved from cache (latest): {cache_path}")
            return cache_path
        logger.warning(f"  ✗ Module not found in cache: {module_path_str}")
        return None

    def _is_remote_module(self, module_path: str) -> bool:
        """Check if module path looks like a remote module.

        Remote modules typically start with a domain: github.com, gitlab.com, golang.org, etc.
        Local paths start with . or / or don't contain domains.

        Args:
            module_path: Module path string

        Returns:
            True if module appears to be remote

        """
        # Local paths
        if module_path.startswith((".", "/", "~")):
            return False

        # Remote modules contain domain-like structure
        # Must have "/" AND first part must look like domain (contains ".")
        if "/" in module_path:
            first_part = module_path.split("/", maxsplit=1)[0]
            return "." in first_part

        return False

    def _resolve_from_cache(
        self,
        module_path: str,
        version: str,
        cachedir: Path,
    ) -> Path | None:
        """Resolve module from cache with specific version.

        Tries multiple cache formats:
        1. Flat: cache_base/full/module/path@version
        2. Hierarchical: cache_base/domain/rest/of/path@version
        3. Version suffix stripping: Try removing +vendor, +incompatible, etc.

        Args:
            module_path: Module path
            version: Specific version to find
            cachedir: Hugo cache directory or cache base (ends with .../pkg/mod)

        Returns:
            Path to module in cache, or None if not found

        """
        # Check if cachedir is already the full cache base path
        if cachedir.name == "mod" and cachedir.parent.name == "pkg":
            cache_base = cachedir
        else:
            # Add the standard Hugo cache subdirectory structure
            cache_base = cachedir / "modules" / "filecache" / "modules" / "pkg" / "mod"

        if not cache_base.exists():
            logger.debug(f"  Cache base does not exist: {cache_base}")
            return None

        # Try exact version match in flat format
        flat_path = cache_base / f"{module_path}@{version}"
        if flat_path.exists():
            logger.debug(f"  ✓ Found (flat format): {flat_path}")
            return flat_path

        # Try without version suffix (e.g., v1.0.0+vendor -> v1.0.0)
        base_version = version.split("+", maxsplit=1)[0]
        if base_version != version:
            flat_base_path = cache_base / f"{module_path}@{base_version}"
            if flat_base_path.exists():
                logger.debug(f"  ✓ Found (flat format, base version): {flat_base_path}")
                return flat_base_path

        # Try hierarchical format (domain/module@version)
        if "/" in module_path:
            parts = module_path.split("/", 1)  # Split only on first /
            domain = parts[0]
            module_name = parts[1] if len(parts) > 1 else ""

            if module_name:
                hierarchical_path = cache_base / domain / f"{module_name}@{version}"
                if hierarchical_path.exists():
                    logger.debug(
                        f"  ✓ Found (hierarchical format): {hierarchical_path}",
                    )
                    return hierarchical_path

                # Try base version in hierarchical format
                if base_version != version:
                    hierarchical_base = (
                        cache_base / domain / f"{module_name}@{base_version}"
                    )
                    if hierarchical_base.exists():
                        logger.debug(
                            f"  ✓ Found (hierarchical, base version): {hierarchical_base}",
                        )
                        return hierarchical_base

        logger.debug("  ✗ Not found in any cache format")
        return None

    def _find_latest_in_cache(self, module_path: str, cachedir: Path) -> Path | None:
        """Find latest version of module in cache.

        Uses simple lexicographic sorting (reverse) to find "latest".
        For proper semver, would need external library.

        Args:
            module_path: Module path
            cachedir: Hugo cache directory or cache base (ends with .../pkg/mod)

        Returns:
            Path to latest module version, or None if not found

        """
        # Check if cachedir is already the full cache base path
        if cachedir.name == "mod" and cachedir.parent.name == "pkg":
            cache_base = cachedir
        else:
            # Add the standard Hugo cache subdirectory structure
            cache_base = cachedir / "modules" / "filecache" / "modules" / "pkg" / "mod"

        if not cache_base.exists():
            logger.debug(f"  Cache base does not exist: {cache_base}")
            return None

        return self._scan_cache_for_module(
            cache_base,
            module_path,
            preferred_version=None,
        )

    def _scan_cache_for_module(  # noqa: PLR0912, PLR0915
        self,
        cache_base: Path,
        module_path_str: str,
        preferred_version: str | None = None,
    ) -> Path | None:
        """Scan cache directory recursively to find matching module.

        Hugo's cache structure can be hierarchical or flat:
        - Hierarchical: domain.com/ → module/path@version/
        - Flat: domain.com/module/path@version/

        Args:
            cache_base: Base cache directory to scan
            module_path_str: Full module path to match (e.g., 'golang.foundata.com/hugo-theme-dev')
            preferred_version: Preferred version if specified, or None for latest

        Returns:
            Path to matching module directory with version, or None if not found

        """
        logger.debug(
            f"Scanning cache for module: {module_path_str} (version: {preferred_version or 'any'})",
        )
        logger.debug(f"Cache base directory: {cache_base}")

        matching_dirs = []

        # Strategy 1: Flat directory format (module/path@version)
        # Strategy 1: Flat directory format (module/path@version)
        try:
            all_entries = list(cache_base.iterdir())
            logger.debug(
                f"Scanning {len(all_entries)} cache entries for module: {module_path_str}",
            )

            for entry in all_entries:
                if not entry.is_dir():
                    continue

                # Check flat format: full/path@version
                if entry.name.startswith(f"{module_path_str}@"):
                    logger.debug(f"  ✓ Found flat format match: {entry.name}")
                    matching_dirs.append(entry)
                    continue

                # Strategy 2: Hierarchical format - check if entry is a domain directory
                if "/" in module_path_str:
                    parts = module_path_str.split("/", 1)
                    domain = parts[0]
                    module_name = parts[1] if len(parts) > 1 else ""

                    # If this entry is the domain directory
                    if entry.name == domain and module_name:
                        logger.debug(f"  ✓ Found domain directory: {entry.name}")
                        # Recursively search for module@version directories
                        # Hugo cache can be deeply nested: github.com/org/subdir/module@version
                        try:
                            domain_matches = []
                            # Get the module basename (last component before @version)
                            module_basename = module_name.split("/")[-1]

                            # Use rglob to recursively find directories matching pattern
                            for match in entry.rglob(f"{module_basename}@*"):
                                if match.is_dir():
                                    logger.debug(
                                        f"    ✓ Found hierarchical match: {match.relative_to(cache_base)}",
                                    )
                                    matching_dirs.append(match)
                                    domain_matches.append(
                                        str(match.relative_to(cache_base)),
                                    )

                            if not domain_matches:
                                logger.debug(
                                    f"    ✗ No matches in domain {domain} for module {module_name}",
                                )
                        except Exception as e:
                            logger.debug(
                                f"    Error scanning domain directory {domain}: {e}",
                            )
        except Exception as e:
            logger.warning(f"Error iterating cache directory: {e}")
            return None

        if not matching_dirs:
            logger.debug(f"No matching directories found for {module_path_str}")
            return None

        logger.debug(
            f"Found {len(matching_dirs)} matching directories: {[d.name for d in matching_dirs]}",
        )

        # If preferred version specified, try to find exact match
        if preferred_version:
            # Try both formats: with and without full module path
            possible_names = [
                f"{module_path_str}@{preferred_version}",  # Flat format
            ]
            if "/" in module_path_str:
                parts = module_path_str.split("/", 1)
                module_name = parts[1] if len(parts) > 1 else ""
                if module_name:
                    possible_names.append(
                        f"{module_name}@{preferred_version}",
                    )  # Hierarchical format

            for dir_path in matching_dirs:
                if dir_path.name in possible_names:
                    logger.debug(f"Found exact version match: {dir_path}")
                    return dir_path
            logger.debug(
                f"No exact match for version {preferred_version}, using latest",
            )

        # No preferred version or no exact match - select latest version
        # Sort by version string (lexicographic for simplicity, reverse for latest first)
        def extract_version(path: Path) -> str:
            """Extract version from directory name."""
            name = path.name
            if "@" in name:
                return name.split("@")[-1]
            return "0.0.0"  # Fallback

        # Sort in reverse lexicographic order to get latest version first
        try:
            sorted_dirs = sorted(matching_dirs, key=extract_version, reverse=True)
            selected = sorted_dirs[0] if sorted_dirs else None
            if selected:
                logger.debug(f"Selected module directory: {selected}")
            return selected
        except Exception as e:
            logger.warning(f"Error sorting module versions: {e}")
            # Fallback to first available if sorting fails
            fallback = matching_dirs[0] if matching_dirs else None
            if fallback:
                logger.debug(f"Using fallback (first available): {fallback}")
            return fallback

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
