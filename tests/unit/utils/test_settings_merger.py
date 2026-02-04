"""Tests for settings merger utility."""

import pytest

from sbkube.models.unified_config_model import UnifiedSettings
from sbkube.utils.settings_merger import (
    _merge_lists,
    apply_settings_to_dict,
    extract_settings_subset,
    merge_settings,
    merge_settings_chain,
)


class TestMergeLists:
    """리스트 병합 테스트."""

    def test_simple_merge(self) -> None:
        """기본 병합 테스트."""
        result = _merge_lists(["a", "b"], ["c", "d"])
        assert result == ["a", "b", "c", "d"]

    def test_deduplication(self) -> None:
        """중복 제거 테스트."""
        result = _merge_lists(["a", "b"], ["b", "c"])
        assert result == ["a", "b", "c"]

    def test_preserve_order(self) -> None:
        """순서 보존 테스트."""
        result = _merge_lists(["a", "b", "c"], ["d", "a", "e"])
        assert result == ["a", "b", "c", "d", "e"]

    def test_empty_parent(self) -> None:
        """빈 부모 리스트 테스트."""
        result = _merge_lists([], ["a", "b"])
        assert result == ["a", "b"]

    def test_empty_child(self) -> None:
        """빈 자식 리스트 테스트."""
        result = _merge_lists(["a", "b"], [])
        assert result == ["a", "b"]

    def test_dict_items(self) -> None:
        """딕셔너리 아이템 병합 테스트."""
        result = _merge_lists(
            [{"key": "a"}],
            [{"key": "b"}, {"key": "a"}],
        )
        # Dict items should be deduplicated by content
        assert len(result) == 2
        assert {"key": "a"} in result
        assert {"key": "b"} in result


class TestMergeSettings:
    """설정 병합 테스트."""

    def test_scalar_override(self) -> None:
        """스칼라 값 오버라이드 테스트."""
        parent = UnifiedSettings(timeout=600, namespace="default")
        child = UnifiedSettings(timeout=300)

        merged = merge_settings(parent, child)

        assert merged.timeout == 300
        assert merged.namespace == "default"  # Not overridden

    def test_none_child(self) -> None:
        """None 자식 테스트."""
        parent = UnifiedSettings(kubeconfig="/path/to/config")

        merged = merge_settings(parent, None)

        assert merged.kubeconfig == "/path/to/config"

    def test_none_values_not_override(self) -> None:
        """None 값이 기존 값을 덮어쓰지 않음 테스트."""
        parent = UnifiedSettings(kubeconfig="/existing/path")
        child = UnifiedSettings()  # kubeconfig is None by default

        merged = merge_settings(parent, child)

        # None should not override existing value
        assert merged.kubeconfig == "/existing/path"

    def test_list_merge(self) -> None:
        """리스트 병합 테스트."""
        parent = UnifiedSettings(incompatible_charts=["chart1", "chart2"])
        child = UnifiedSettings(incompatible_charts=["chart2", "chart3"])

        merged = merge_settings(parent, child)

        assert "chart1" in merged.incompatible_charts
        assert "chart2" in merged.incompatible_charts
        assert "chart3" in merged.incompatible_charts

    def test_dict_merge(self) -> None:
        """딕셔너리 병합 테스트."""
        parent = UnifiedSettings(
            helm_repos={"grafana": {"url": "https://grafana.github.io/helm-charts"}}
        )
        child = UnifiedSettings(
            helm_repos={"bitnami": {"url": "https://charts.bitnami.com/bitnami"}}
        )

        merged = merge_settings(parent, child)

        assert "grafana" in merged.helm_repos
        assert "bitnami" in merged.helm_repos

    def test_full_override(self) -> None:
        """전체 설정 오버라이드 테스트."""
        parent = UnifiedSettings(
            kubeconfig="/parent/config",
            timeout=600,
            parallel=False,
            max_workers=4,
        )
        child = UnifiedSettings(
            kubeconfig="/child/config",
            timeout=300,
            parallel=True,
            max_workers=8,
        )

        merged = merge_settings(parent, child)

        assert merged.kubeconfig == "/child/config"
        assert merged.timeout == 300
        assert merged.parallel is True
        assert merged.max_workers == 8


class TestMergeSettingsChain:
    """설정 체인 병합 테스트."""

    def test_three_level_chain(self) -> None:
        """3단계 체인 테스트."""
        global_settings = UnifiedSettings(
            kubeconfig="/global",
            timeout=600,
            namespace="global-ns",
        )
        phase_settings = UnifiedSettings(
            timeout=300,
            namespace="phase-ns",
        )
        app_settings = UnifiedSettings(
            namespace="app-ns",
        )

        merged = merge_settings_chain(global_settings, phase_settings, app_settings)

        assert merged.kubeconfig == "/global"  # From global
        assert merged.timeout == 300  # From phase
        assert merged.namespace == "app-ns"  # From app

    def test_skip_none_in_chain(self) -> None:
        """체인에서 None 건너뛰기 테스트."""
        s1 = UnifiedSettings(timeout=100)
        s2 = None
        s3 = UnifiedSettings(timeout=200)

        merged = merge_settings_chain(s1, s2, s3)

        assert merged.timeout == 200

    def test_single_settings(self) -> None:
        """단일 설정 테스트."""
        settings = UnifiedSettings(timeout=100)

        merged = merge_settings_chain(settings)

        assert merged.timeout == 100

    def test_all_none_raises_error(self) -> None:
        """모두 None인 경우 오류 테스트."""
        with pytest.raises(ValueError):
            merge_settings_chain(None, None, None)


class TestApplySettingsToDict:
    """설정 적용 테스트."""

    def test_basic_apply(self) -> None:
        """기본 적용 테스트."""
        settings = UnifiedSettings(
            kubeconfig="/path/to/config",
            timeout=300,
        )
        target = {"other_key": "value"}

        result = apply_settings_to_dict(settings, target)

        assert result["kubeconfig"] == "/path/to/config"
        assert result["timeout"] == 300
        assert result["other_key"] == "value"

    def test_key_mapping(self) -> None:
        """키 매핑 테스트."""
        settings = UnifiedSettings(kubeconfig="/path/to/config")
        target = {}

        result = apply_settings_to_dict(
            settings,
            target,
            key_mapping={"kubeconfig": "kubeconfig_path"},
        )

        assert "kubeconfig_path" in result
        assert result["kubeconfig_path"] == "/path/to/config"

    def test_no_override_existing(self) -> None:
        """기존 값 덮어쓰지 않음 테스트."""
        settings = UnifiedSettings(timeout=300)
        target = {"timeout": 600}  # Already set

        result = apply_settings_to_dict(settings, target)

        assert result["timeout"] == 600  # Original value preserved


class TestExtractSettingsSubset:
    """설정 서브셋 추출 테스트."""

    def test_extract_subset(self) -> None:
        """서브셋 추출 테스트."""
        settings = UnifiedSettings(
            kubeconfig="/path",
            timeout=300,
            parallel=True,
        )

        result = extract_settings_subset(settings, ["kubeconfig", "parallel"])

        assert "kubeconfig" in result
        assert "parallel" in result
        assert "timeout" not in result

    def test_missing_keys(self) -> None:
        """없는 키 무시 테스트."""
        settings = UnifiedSettings(timeout=300)

        result = extract_settings_subset(settings, ["timeout", "nonexistent"])

        assert "timeout" in result
        assert "nonexistent" not in result
