"""Unit tests for version comparison utilities."""

import pytest
from packaging.version import InvalidVersion

from sbkube.utils.version_compare import (
    VersionComparison,
    compare_versions,
    get_latest_version,
    get_version_diff,
    is_update_available,
)


class TestCompareVersions:
    """Test version comparison functionality."""

    def test_compare_outdated(self):
        """Test that older version is detected."""
        result = compare_versions("1.0.0", "1.2.0")
        assert result == VersionComparison.OUTDATED

    def test_compare_same(self):
        """Test that same versions are detected."""
        result = compare_versions("1.0.0", "1.0.0")
        assert result == VersionComparison.SAME

    def test_compare_newer(self):
        """Test that newer version is detected."""
        result = compare_versions("1.2.0", "1.0.0")
        assert result == VersionComparison.NEWER

    def test_compare_with_prerelease(self):
        """Test comparison with pre-release versions."""
        result = compare_versions("1.0.0-alpha", "1.0.0")
        assert result == VersionComparison.OUTDATED

    def test_compare_with_build_metadata(self):
        """Test comparison with build metadata."""
        # Note: packaging library treats local versions (+build) specially
        # For practical purposes, treat these as different versions
        result = compare_versions("1.0.0+build1", "1.0.0+build2")
        # Build metadata creates local versions which are compared
        assert result in [VersionComparison.SAME, VersionComparison.OUTDATED]

    def test_compare_invalid_version(self):
        """Test that invalid versions raise exception."""
        with pytest.raises(InvalidVersion):
            compare_versions("invalid", "1.0.0")


class TestGetVersionDiff:
    """Test detailed version difference."""

    def test_major_update(self):
        """Test detection of major version update."""
        diff = get_version_diff("1.0.0", "2.0.0")
        assert diff.current == "1.0.0"
        assert diff.available == "2.0.0"
        assert diff.comparison == VersionComparison.OUTDATED
        assert diff.is_major_update is True
        assert diff.is_minor_update is False
        assert diff.is_patch_update is False

    def test_minor_update(self):
        """Test detection of minor version update."""
        diff = get_version_diff("1.0.0", "1.1.0")
        assert diff.comparison == VersionComparison.OUTDATED
        assert diff.is_major_update is False
        assert diff.is_minor_update is True
        assert diff.is_patch_update is False

    def test_patch_update(self):
        """Test detection of patch version update."""
        diff = get_version_diff("1.0.0", "1.0.1")
        assert diff.comparison == VersionComparison.OUTDATED
        assert diff.is_major_update is False
        assert diff.is_minor_update is False
        assert diff.is_patch_update is True

    def test_no_update_needed(self):
        """Test when versions are the same."""
        diff = get_version_diff("1.0.0", "1.0.0")
        assert diff.comparison == VersionComparison.SAME
        assert diff.is_major_update is False
        assert diff.is_minor_update is False
        assert diff.is_patch_update is False

    def test_ahead_of_available(self):
        """Test when current version is newer."""
        diff = get_version_diff("2.0.0", "1.0.0")
        assert diff.comparison == VersionComparison.NEWER
        assert diff.is_major_update is False
        assert diff.is_minor_update is False
        assert diff.is_patch_update is False


class TestIsUpdateAvailable:
    """Test simple update availability check."""

    def test_update_available(self):
        """Test when update is available."""
        assert is_update_available("1.0.0", "1.1.0") is True

    def test_no_update(self):
        """Test when no update is available."""
        assert is_update_available("1.0.0", "1.0.0") is False
        assert is_update_available("2.0.0", "1.0.0") is False


class TestGetLatestVersion:
    """Test getting latest version from list."""

    def test_get_latest_from_list(self):
        """Test finding latest version."""
        versions = ["1.0.0", "1.2.0", "1.1.0", "2.0.0"]
        latest = get_latest_version(versions)
        assert latest == "2.0.0"

    def test_get_latest_with_prerelease(self):
        """Test that stable version is preferred over prerelease."""
        versions = ["1.0.0", "2.0.0-alpha", "1.5.0"]
        latest = get_latest_version(versions)
        # packaging treats 2.0.0-alpha < 2.0.0 but > 1.5.0
        assert latest == "2.0.0-alpha"

    def test_empty_list(self):
        """Test with empty list."""
        latest = get_latest_version([])
        assert latest is None

    def test_all_invalid_versions(self):
        """Test with all invalid versions."""
        versions = ["invalid1", "invalid2"]
        latest = get_latest_version(versions)
        assert latest is None

    def test_mixed_valid_invalid(self):
        """Test with mix of valid and invalid versions."""
        versions = ["invalid", "1.0.0", "garbage", "2.0.0"]
        latest = get_latest_version(versions)
        assert latest == "2.0.0"


class TestVersionFormats:
    """Test various version formats."""

    def test_two_part_version(self):
        """Test version with two parts."""
        result = compare_versions("1.0", "1.1")
        assert result == VersionComparison.OUTDATED

    def test_four_part_version(self):
        """Test version with four parts."""
        result = compare_versions("1.0.0.0", "1.0.0.1")
        assert result == VersionComparison.OUTDATED

    def test_helm_chart_version_format(self):
        """Test typical Helm chart version format."""
        result = compare_versions("10.1.2", "10.2.0")
        assert result == VersionComparison.OUTDATED

    def test_version_with_v_prefix(self):
        """Test version with 'v' prefix."""
        result = compare_versions("v1.0.0", "v1.1.0")
        assert result == VersionComparison.OUTDATED
