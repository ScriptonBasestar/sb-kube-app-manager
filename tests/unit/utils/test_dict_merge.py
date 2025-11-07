"""Unit tests for dict_merge utility functions."""

from sbkube.utils.dict_merge import deep_merge, merge_multiple


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_simple_merge(self) -> None:
        """Test simple key-value merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}
        # Ensure originals are not modified
        assert base == {"a": 1, "b": 2}
        assert override == {"b": 3, "c": 4}

    def test_nested_dict_merge(self) -> None:
        """Test nested dictionary merge."""
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"d": 4, "e": 5}, "f": 6}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": {"c": 2, "d": 4, "e": 5}, "f": 6}

    def test_deep_nested_merge(self) -> None:
        """Test deeply nested dictionary merge."""
        base = {
            "level1": {"level2": {"level3": {"key": "base_value", "other": "keep"}}}
        }
        override = {"level1": {"level2": {"level3": {"key": "override_value"}}}}
        result = deep_merge(base, override)

        assert result == {
            "level1": {"level2": {"level3": {"key": "override_value", "other": "keep"}}}
        }

    def test_list_replacement_not_merge(self) -> None:
        """Test that lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = deep_merge(base, override)

        assert result == {"items": [4, 5]}  # List replaced, not merged

    def test_empty_dicts(self) -> None:
        """Test merge with empty dictionaries."""
        assert deep_merge({}, {}) == {}
        assert deep_merge({"a": 1}, {}) == {"a": 1}
        assert deep_merge({}, {"b": 2}) == {"b": 2}

    def test_override_different_types(self) -> None:
        """Test overriding with different types."""
        base = {"key": "string"}
        override = {"key": 123}
        result = deep_merge(base, override)
        assert result == {"key": 123}

        base2 = {"key": {"nested": "dict"}}
        override2 = {"key": "string"}
        result2 = deep_merge(base2, override2)
        assert result2 == {"key": "string"}

    def test_none_values(self) -> None:
        """Test handling None values."""
        base = {"a": 1, "b": None}
        override = {"b": 2, "c": None}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 2, "c": None}


class TestMergeMultiple:
    """Tests for merge_multiple function."""

    def test_merge_two_dicts(self) -> None:
        """Test merging two dictionaries."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        result = merge_multiple(d1, d2)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_three_dicts(self) -> None:
        """Test merging three dictionaries."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        d3 = {"c": 5, "d": 6}
        result = merge_multiple(d1, d2, d3)

        assert result == {"a": 1, "b": 3, "c": 5, "d": 6}

    def test_merge_with_none(self) -> None:
        """Test merging with None values."""
        d1 = {"a": 1}
        d2 = None
        d3 = {"b": 2}
        result = merge_multiple(d1, d2, d3)

        assert result == {"a": 1, "b": 2}

    def test_merge_with_empty(self) -> None:
        """Test merging with empty dicts."""
        d1 = {"a": 1}
        d2 = {}
        d3 = {"b": 2}
        result = merge_multiple(d1, d2, d3)

        assert result == {"a": 1, "b": 2}

    def test_merge_nested_dicts(self) -> None:
        """Test merging nested dictionaries."""
        d1 = {"global": {"storageClass": "nfs", "domain": "example.com"}}
        d2 = {"global": {"environment": "production"}}
        d3 = {"global": {"storageClass": "ceph"}}  # Override
        result = merge_multiple(d1, d2, d3)

        assert result == {
            "global": {
                "storageClass": "ceph",  # d3 overrides d1
                "domain": "example.com",
                "environment": "production",
            }
        }

    def test_merge_no_args(self) -> None:
        """Test merge with no arguments."""
        result = merge_multiple()
        assert result == {}

    def test_merge_single_dict(self) -> None:
        """Test merge with single dictionary."""
        d1 = {"a": 1, "b": 2}
        result = merge_multiple(d1)
        assert result == {"a": 1, "b": 2}
        # Ensure original is not modified
        assert d1 == {"a": 1, "b": 2}


class TestClusterGlobalValuesScenario:
    """Real-world scenario tests for cluster global values."""

    def test_cluster_values_precedence(self) -> None:
        """Test cluster values file + inline values merge."""
        # cluster_values_file (lowest priority)
        cluster_file_values = {
            "global": {
                "storageClass": "nfs-client",
                "domain": "prod.example.com",
                "monitoring": {"enabled": True, "retention": "30d"},
            }
        }

        # global_values inline (higher priority)
        inline_values = {
            "global": {
                "environment": "production",
                "monitoring": {"enabled": False},  # Override
            }
        }

        result = deep_merge(cluster_file_values, inline_values)

        assert result == {
            "global": {
                "storageClass": "nfs-client",  # From file
                "domain": "prod.example.com",  # From file
                "environment": "production",  # From inline
                "monitoring": {
                    "enabled": False,  # Inline overrides file
                    "retention": "30d",  # From file
                },
            }
        }

    def test_full_helm_values_precedence(self) -> None:
        """Test full Helm values precedence chain."""
        # 1. cluster_values_file
        cluster_file = {"global": {"storageClass": "nfs", "replicas": 1}}

        # 2. global_values inline
        global_inline = {"global": {"environment": "production"}}

        # 3. app values file
        app_values = {"global": {"replicas": 3}, "service": {"type": "LoadBalancer"}}

        # 4. app set_values
        app_set = {"service": {"port": 8080}}

        # Merge in order: cluster_file -> global_inline -> app_values -> app_set
        result = merge_multiple(cluster_file, global_inline, app_values, app_set)

        assert result == {
            "global": {
                "storageClass": "nfs",  # From cluster_file
                "replicas": 3,  # From app_values (overrides cluster_file)
                "environment": "production",  # From global_inline
            },
            "service": {
                "type": "LoadBalancer",  # From app_values
                "port": 8080,  # From app_set
            },
        }
