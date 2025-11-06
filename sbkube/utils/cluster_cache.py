"""Cluster status cache manager.

This module provides functionality to cache and retrieve Kubernetes cluster status
information in YAML format with TTL (Time To Live) support.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

# Constants
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes

console = Console()


class ClusterCache:
    """Manages cluster status cache in YAML format.

    Cache files are stored in {base_dir}/.sbkube/cluster_status/ with option-based naming:
    - Standard view: {context}_{cluster}.yaml
    - By-group view: {context}_{cluster}_by-group.yaml
    - Specific group: {context}_{cluster}_group-{app_group}.yaml

    Each view type has its own cache file with TTL-based expiration.
    """

    def __init__(
        self,
        cache_dir: Path,
        context: str,
        cluster: str,
        by_group: bool = False,
        app_group: str | None = None,
    ) -> None:
        """Initialize cluster cache manager.

        Args:
            cache_dir: Directory for cache storage (.sbkube/cluster_status/)
            context: kubeconfig context name
            cluster: cluster identifier (from sources.yaml)
            by_group: Whether to group by app-group
            app_group: Specific app-group (if filtering)

        """
        self.cache_dir = Path(cache_dir)
        self.context = context
        self.cluster = cluster or "unknown"
        self.by_group = by_group
        self.app_group = app_group
        self.cache_file = self._generate_cache_filename()

    def _generate_cache_filename(self) -> Path:
        """Generate cache filename based on options.

        Returns:
            Path object for cache file

        Examples:
            Standard: {context}_{cluster}.yaml
            By-group: {context}_{cluster}_by-group.yaml
            Specific group: {context}_{cluster}_group-{app_group}.yaml

        """
        base_name = f"{self.context}_{self.cluster}"

        if self.app_group:
            # Specific app-group view
            filename = f"{base_name}_group-{self.app_group}.yaml"
        elif self.by_group:
            # All app-groups grouped view
            filename = f"{base_name}_by-group.yaml"
        else:
            # Standard flat view
            filename = f"{base_name}.yaml"

        return self.cache_dir / filename

    def save(
        self, data: dict[str, Any], ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    ) -> None:
        """Save cluster status data to cache file.

        Uses atomic write (temp file + rename) to prevent corruption.

        Args:
            data: Cluster status data to cache
            ttl_seconds: Time to live in seconds (default: 300 = 5 minutes)

        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Add metadata
        cache_data = {
            "context": self.context,
            "cluster_name": self.cluster,
            "timestamp": datetime.now(UTC).isoformat(),
            "ttl_seconds": ttl_seconds,
            **data,
        }

        # Atomic write: write to temp file, then rename
        temp_file = self.cache_file.with_suffix(".tmp")
        try:
            with temp_file.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    cache_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            temp_file.rename(self.cache_file)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save cache: {e}[/yellow]")
            if temp_file.exists():
                temp_file.unlink()

    def load(self) -> dict[str, Any] | None:
        """Load cluster status data from cache file.

        Returns:
            Cached data if valid, None if cache doesn't exist or is invalid

        """
        if not self.cache_file.exists():
            return None

        try:
            with self.cache_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load cache: {e}[/yellow]")
            return None

    def is_valid(self, ttl_seconds: int | None = None) -> bool:
        """Check if cached data is still valid based on TTL.

        Args:
            ttl_seconds: Override TTL from cache file (optional)

        Returns:
            True if cache exists and hasn't expired, False otherwise

        """
        data = self.load()
        if not data:
            return False

        try:
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return False

            cached_time = datetime.fromisoformat(timestamp_str)
            # Ensure timezone awareness for comparison
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=UTC)
            current_time = datetime.now(UTC)

            # Use provided TTL or fall back to cached TTL
            ttl = (
                ttl_seconds
                if ttl_seconds is not None
                else data.get("ttl_seconds", DEFAULT_CACHE_TTL_SECONDS)
            )

            elapsed_seconds = (current_time - cached_time).total_seconds()
            return elapsed_seconds < ttl
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to validate cache: {e}[/yellow]")
            return False

    def get_age_seconds(self) -> float | None:
        """Get cache age in seconds.

        Returns:
            Age in seconds, or None if cache doesn't exist or is invalid

        """
        data = self.load()
        if not data:
            return None

        try:
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return None

            cached_time = datetime.fromisoformat(timestamp_str)
            # Ensure timezone awareness for comparison
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=UTC)
            current_time = datetime.now(UTC)
            return (current_time - cached_time).total_seconds()
        except Exception:
            return None

    def get_remaining_ttl(self) -> float | None:
        """Get remaining TTL in seconds.

        Returns:
            Remaining seconds until expiration, or None if expired/invalid

        """
        data = self.load()
        if not data:
            return None

        age = self.get_age_seconds()
        if age is None:
            return None

        ttl = data.get("ttl_seconds", 300)
        remaining = ttl - age
        return remaining if remaining > 0 else None

    def delete(self) -> None:
        """Delete cache file."""
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to delete cache: {e}[/yellow]")

    def exists(self) -> bool:
        """Check if cache file exists.

        Returns:
            True if cache file exists, False otherwise

        """
        return self.cache_file.exists()
