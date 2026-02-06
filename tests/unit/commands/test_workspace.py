"""Workspace 명령어 테스트.

Note: These tests use the unified sbkube.yaml format (v0.10.0+).
The legacy sbkube.yaml format is no longer supported.
"""

from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands.workspace import (
    WorkspaceDeployCommand,
    WorkspaceGraphCommand,
    WorkspaceInitCommand,
    WorkspaceStatusCommand,
    WorkspaceValidateCommand,
    deploy_cmd,
    graph_cmd,
    init_cmd,
    status_cmd,
    validate_cmd,
)


def create_unified_workspace_config(
    name: str = "test-workspace",
    phases: dict | None = None,
) -> dict:
    """Create a valid unified workspace config (sbkube.yaml format).

    Args:
        name: Workspace name
        phases: Phase definitions

    Returns:
        dict: Valid sbkube.yaml config

    """
    if phases is None:
        phases = {
            "p1-infra": {
                "description": "Infrastructure",
                "source": "p1-kube/sbkube.yaml",
            }
        }

    return {
        "apiVersion": "sbkube/v1",
        "metadata": {"name": name},
        "settings": {
            "namespace": "default",
        },
        "phases": phases,
    }


class TestWorkspaceValidateCommand:
    """WorkspaceValidateCommand 테스트."""

    def test_valid_workspace(self, tmp_path: Path) -> None:
        """유효한 sbkube.yaml 검증 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = create_unified_workspace_config(
            name="test-workspace",
            phases={
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                }
            },
        )
        workspace_file.write_text(yaml.dump(workspace_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))
        workspace = cmd.execute()

        assert workspace.apiVersion == "sbkube/v1"
        assert workspace.metadata.get("name") == "test-workspace"
        assert len(workspace.phases) == 1

    def test_missing_workspace_file(self, tmp_path: Path) -> None:
        """sbkube.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_invalid_workspace_structure(self, tmp_path: Path) -> None:
        """잘못된 sbkube.yaml 구조 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        # 잘못된 apiVersion 형식
        invalid_config = {
            "apiVersion": "invalid",  # 잘못된 형식 (sbkube/v1이어야 함)
            "metadata": {"name": "test"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                }
            },
        }
        workspace_file.write_text(yaml.dump(invalid_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_circular_dependency(self, tmp_path: Path) -> None:
        """순환 의존성 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        circular_config = create_unified_workspace_config(
            name="circular-test",
            phases={
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sbkube.yaml",
                    "depends_on": ["p1"],
                },
            },
        )
        workspace_file.write_text(yaml.dump(circular_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceGraphCommand:
    """WorkspaceGraphCommand 테스트."""

    def test_dependency_graph(self, tmp_path: Path) -> None:
        """의존성 그래프 출력 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = create_unified_workspace_config(
            name="graph-test",
            phases={
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                },
                "p2-data": {
                    "description": "Data layer",
                    "source": "p2-kube/sbkube.yaml",
                    "depends_on": ["p1-infra"],
                },
            },
        )
        workspace_file.write_text(yaml.dump(workspace_config))

        cmd = WorkspaceGraphCommand(str(workspace_file))
        # 그래프 출력은 에러 없이 완료되어야 함
        cmd.execute()

    def test_graph_missing_file(self, tmp_path: Path) -> None:
        """sbkube.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceGraphCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_graph_circular_dependency(self, tmp_path: Path) -> None:
        """순환 의존성 그래프 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        circular_config = create_unified_workspace_config(
            name="circular-graph",
            phases={
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sbkube.yaml",
                    "depends_on": ["p1"],
                },
            },
        )
        workspace_file.write_text(yaml.dump(circular_config))

        cmd = WorkspaceGraphCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceCLI:
    """Workspace CLI 명령어 테스트."""

    def test_validate_cli_success(self, tmp_path: Path) -> None:
        """Workspace validate CLI 성공 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "cli-test"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                }
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))

        runner = CliRunner()
        result = runner.invoke(validate_cmd, ["-v", str(workspace_file)])

        assert result.exit_code == 0
        assert "Workspace 검증 완료" in result.output

    def test_validate_cli_failure(self, tmp_path: Path) -> None:
        """Workspace validate CLI 실패 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        # 잘못된 apiVersion 형식 (sbkube/v1 이어야 함)
        invalid_config = {"apiVersion": "invalid", "metadata": {"name": "test"}, "phases": {}}
        workspace_file.write_text(yaml.dump(invalid_config))

        runner = CliRunner()
        result = runner.invoke(validate_cmd, [str(workspace_file)])

        assert result.exit_code != 0

    def test_graph_cli_success(self, tmp_path: Path) -> None:
        """Workspace graph CLI 성공 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "graph-cli-test"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                },
                "p2-data": {
                    "description": "Data",
                    "source": "p2-kube/sbkube.yaml",
                    "depends_on": ["p1-infra"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))

        runner = CliRunner()
        result = runner.invoke(graph_cmd, [str(workspace_file)])

        assert result.exit_code == 0
        assert "Phase Dependency Graph" in result.output
        assert "p1-infra" in result.output
        assert "p2-data" in result.output

    def test_graph_cli_circular_dependency(self, tmp_path: Path) -> None:
        """Workspace graph CLI 순환 의존성 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        circular_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "circular-cli"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sbkube.yaml",
                    "depends_on": ["p1"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(circular_config))

        runner = CliRunner()
        result = runner.invoke(graph_cmd, [str(workspace_file)])

        assert result.exit_code != 0


class TestWorkspaceInitCommand:
    """WorkspaceInitCommand 테스트."""

    def test_default_template(self, tmp_path: Path) -> None:
        """기본 템플릿 생성 테스트."""
        output_file = tmp_path / "sbkube.yaml"

        cmd = WorkspaceInitCommand(
            output_file=str(output_file),
            interactive=False,
        )
        cmd.execute()

        # 파일 생성 확인
        assert output_file.exists()

        # 내용 검증
        with open(output_file, encoding="utf-8") as f:
            workspace = yaml.safe_load(f)

        assert workspace["apiVersion"] == "sbkube/v1"
        assert workspace["metadata"]["name"] == "my-workspace"
        assert len(workspace["phases"]) == 3
        assert "p1-infra" in workspace["phases"]
        assert "p2-data" in workspace["phases"]
        assert "p3-app" in workspace["phases"]

    def test_file_already_exists_no_overwrite(self, tmp_path: Path) -> None:
        """파일 존재 시 덮어쓰기 거부 테스트."""
        output_file = tmp_path / "sbkube.yaml"
        output_file.write_text("existing content")

        cmd = WorkspaceInitCommand(
            output_file=str(output_file),
            interactive=False,
        )

        # click.confirm이 False를 반환하도록 mock
        with patch("click.confirm", return_value=False):
            with pytest.raises(click.Abort):
                cmd.execute()

    def test_file_already_exists_overwrite(self, tmp_path: Path) -> None:
        """파일 존재 시 덮어쓰기 허용 테스트."""
        output_file = tmp_path / "sbkube.yaml"
        output_file.write_text("existing content")

        cmd = WorkspaceInitCommand(
            output_file=str(output_file),
            interactive=False,
        )

        # click.confirm이 True를 반환하도록 mock
        with patch("click.confirm", return_value=True):
            cmd.execute()

        # 새 내용으로 덮어쓰기 확인
        with open(output_file, encoding="utf-8") as f:
            workspace = yaml.safe_load(f)
        assert workspace["apiVersion"] == "sbkube/v1"

    def test_init_cli_non_interactive(self, tmp_path: Path) -> None:
        """Workspace init CLI 비대화형 모드 테스트."""
        output_file = tmp_path / "sbkube.yaml"

        runner = CliRunner()
        result = runner.invoke(init_cmd, ["-v", str(output_file), "--non-interactive"])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Workspace 파일 생성 완료" in result.output

    def test_init_cli_with_existing_file(self, tmp_path: Path) -> None:
        """Workspace init CLI 기존 파일 존재 시 테스트."""
        output_file = tmp_path / "sbkube.yaml"
        output_file.write_text("existing")

        runner = CliRunner()
        # 'n' 입력으로 덮어쓰기 거부
        result = runner.invoke(
            init_cmd, [str(output_file), "--non-interactive"], input="n\n"
        )

        # Abort되므로 exit_code != 0
        assert result.exit_code != 0


class TestWorkspaceDeployCommand:
    """WorkspaceDeployCommand 테스트."""

    def _create_workspace_file(
        self, tmp_path: Path, phases: dict | None = None
    ) -> Path:
        """Helper to create sbkube.yaml for tests."""
        workspace_file = tmp_path / "sbkube.yaml"
        default_phases = {
            "p1-infra": {
                "description": "Infrastructure",
                "source": "p1-kube/sbkube.yaml",
            },
            "p2-data": {
                "description": "Data layer",
                "source": "p2-kube/sbkube.yaml",
                "depends_on": ["p1-infra"],
            },
        }
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "test-workspace", "environment": "test"},
            "phases": phases or default_phases,
        }
        workspace_file.write_text(yaml.dump(workspace_config))
        return workspace_file

    def test_dry_run_mode(self, tmp_path: Path) -> None:
        """DRY-RUN 모드 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
        )
        result = cmd.execute()

        # Dry-run should succeed without actual deployment
        assert result is True

    def test_deploy_single_phase(self, tmp_path: Path) -> None:
        """단일 Phase 배포 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            phase="p1-infra",
            dry_run=True,
            skip_validation=True,
        )
        result = cmd.execute()

        assert result is True
        # Only p1-infra should be in results
        assert "p1-infra" in cmd.phase_results

    def test_deploy_missing_workspace_file(self, tmp_path: Path) -> None:
        """sbkube.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
        )

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_deploy_invalid_phase_name(self, tmp_path: Path) -> None:
        """존재하지 않는 Phase 지정 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            phase="nonexistent-phase",
            dry_run=True,
        )

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_deploy_phase_order(self, tmp_path: Path) -> None:
        """Phase 실행 순서 테스트."""
        phases = {
            "p1": {
                "description": "First",
                "source": "p1/sbkube.yaml",
            },
            "p2": {
                "description": "Second",
                "source": "p2/sbkube.yaml",
                "depends_on": ["p1"],
            },
            "p3": {
                "description": "Third",
                "source": "p3/sbkube.yaml",
                "depends_on": ["p2"],
            },
        }
        workspace_file = self._create_workspace_file(tmp_path, phases)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
        )
        # Execute in dry-run mode, then check results
        cmd.execute()

        # Check phase order from results - all phases should be in results
        executed_phases = list(cmd.phase_results.keys())
        # p1 must come before p2, p2 must come before p3
        assert executed_phases.index("p1") < executed_phases.index("p2")
        assert executed_phases.index("p2") < executed_phases.index("p3")

    def test_deploy_circular_dependency(self, tmp_path: Path) -> None:
        """순환 의존성 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        circular_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "circular-deploy"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sbkube.yaml",
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sbkube.yaml",
                    "depends_on": ["p1"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(circular_config))

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
        )

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceStatusCommand:
    """WorkspaceStatusCommand 테스트."""

    def _create_workspace_file(self, tmp_path: Path) -> Path:
        """Helper to create sbkube.yaml for tests."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {
                "name": "status-test",
                "description": "Test workspace",
                "environment": "test",
            },
            "settings": {
                "kubeconfig": "~/.kube/config",
                "kubeconfig_context": "test-context",
                "timeout": 300,
            },
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                },
                "p2-data": {
                    "description": "Data layer",
                    "source": "p2-kube/sbkube.yaml",
                    "depends_on": ["p1-infra"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))
        return workspace_file

    def test_status_success(self, tmp_path: Path) -> None:
        """Status 명령어 성공 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        cmd = WorkspaceStatusCommand(str(workspace_file))
        # Should not raise
        cmd.execute()

    def test_status_missing_file(self, tmp_path: Path) -> None:
        """sbkube.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceStatusCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_status_invalid_workspace(self, tmp_path: Path) -> None:
        """잘못된 sbkube.yaml 테스트."""
        workspace_file = tmp_path / "sbkube.yaml"
        invalid_config = {
            "apiVersion": "invalid",  # Invalid apiVersion format
            "metadata": {"name": "invalid"},
            "phases": {},
        }
        workspace_file.write_text(yaml.dump(invalid_config))

        cmd = WorkspaceStatusCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceDeployCLI:
    """Workspace deploy CLI 테스트."""

    def _create_workspace_file(self, tmp_path: Path) -> Path:
        """Helper to create sbkube.yaml for tests."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "deploy-cli-test"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                }
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))
        return workspace_file

    def test_deploy_cli_dry_run(self, tmp_path: Path) -> None:
        """Workspace deploy --dry-run CLI 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            deploy_cmd,
            [str(workspace_file), "--dry-run", "--skip-validation"],
        )

        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    def test_deploy_cli_missing_file(self, tmp_path: Path) -> None:
        """Workspace deploy 파일 없음 CLI 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        runner = CliRunner()
        result = runner.invoke(deploy_cmd, [str(workspace_file)])

        assert result.exit_code != 0
        # Click's built-in file validation returns "does not exist"
        assert (
            "not found" in result.output.lower()
            or "찾을 수 없습니다" in result.output
            or "does not exist" in result.output.lower()
        )

    def test_deploy_cli_single_phase(self, tmp_path: Path) -> None:
        """Workspace deploy --phase CLI 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            deploy_cmd,
            [str(workspace_file), "--phase", "p1-infra", "--dry-run", "--skip-validation"],
        )

        assert result.exit_code == 0


class TestWorkspaceStatusCLI:
    """Workspace status CLI 테스트."""

    def _create_workspace_file(self, tmp_path: Path) -> Path:
        """Helper to create sbkube.yaml for tests."""
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "status-cli-test", "environment": "test"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sbkube.yaml",
                }
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))
        return workspace_file

    def test_status_cli_success(self, tmp_path: Path) -> None:
        """Workspace status CLI 성공 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        runner = CliRunner()
        result = runner.invoke(status_cmd, [str(workspace_file)])

        assert result.exit_code == 0
        assert "Workspace Status" in result.output

    def test_status_cli_missing_file(self, tmp_path: Path) -> None:
        """Workspace status 파일 없음 CLI 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        runner = CliRunner()
        result = runner.invoke(status_cmd, [str(workspace_file)])

        assert result.exit_code != 0


class TestWorkspaceParallelExecution:
    """Workspace 병렬 실행 테스트."""

    def _create_workspace_file(
        self, tmp_path: Path, phases: dict | None = None
    ) -> Path:
        """Helper to create sbkube.yaml for tests."""
        workspace_file = tmp_path / "sbkube.yaml"
        default_phases = {
            "p1-infra": {
                "description": "Infrastructure",
                "source": "p1-kube/sbkube.yaml",
            },
            "p2-data": {
                "description": "Data layer",
                "source": "p2-kube/sbkube.yaml",
                "depends_on": ["p1-infra"],
            },
            "p3-cache": {
                "description": "Cache layer",
                "source": "p3-kube/sbkube.yaml",
                "depends_on": ["p1-infra"],
            },
        }
        workspace_config = {
            "apiVersion": "sbkube/v1",
            "metadata": {"name": "parallel-test", "environment": "test"},
            "phases": phases or default_phases,
        }
        workspace_file.write_text(yaml.dump(workspace_config))
        return workspace_file

    def test_parallel_dry_run_mode(self, tmp_path: Path) -> None:
        """병렬 실행 DRY-RUN 모드 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
            parallel=True,
            max_workers=4,
        )
        result = cmd.execute()

        # Dry-run should succeed without actual deployment
        assert result is True
        # All phases should be in results
        assert len(cmd.phase_results) == 3

    def test_parallel_level_calculation(self, tmp_path: Path) -> None:
        """병렬 레벨 계산 테스트."""
        # p1 -> p2, p3 (p2 and p3 can run in parallel)
        phases = {
            "p1": {
                "description": "First",
                "source": "p1/sbkube.yaml",
            },
            "p2": {
                "description": "Second",
                "source": "p2/sbkube.yaml",
                "depends_on": ["p1"],
            },
            "p3": {
                "description": "Third",
                "source": "p3/sbkube.yaml",
                "depends_on": ["p1"],
            },
        }
        workspace_file = self._create_workspace_file(tmp_path, phases)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
            parallel=True,
        )

        # Load workspace
        workspace = cmd._load_and_validate_workspace()
        phase_order = workspace.get_phase_order()

        # Calculate levels
        levels = cmd._calculate_parallel_levels(workspace, phase_order)

        # Level 0: p1 (no dependencies)
        # Level 1: p2, p3 (both depend only on p1)
        assert len(levels) == 2
        assert levels[0] == ["p1"]
        assert set(levels[1]) == {"p2", "p3"}

    def test_parallel_cli_options(self, tmp_path: Path) -> None:
        """Workspace deploy --parallel CLI 옵션 테스트."""
        workspace_file = self._create_workspace_file(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            deploy_cmd,
            [
                str(workspace_file),
                "--dry-run",
                "--skip-validation",
                "--parallel",
                "--max-workers",
                "2",
                "-v",
            ],
        )

        assert result.exit_code == 0
        assert "PARALLEL MODE" in result.output

    def test_complex_dependency_levels(self, tmp_path: Path) -> None:
        """복잡한 의존성 레벨 계산 테스트."""
        # Diamond dependency pattern:
        # p1 -> p2, p3
        # p2, p3 -> p4
        phases = {
            "p1": {
                "description": "Root",
                "source": "p1/sbkube.yaml",
            },
            "p2": {
                "description": "Left branch",
                "source": "p2/sbkube.yaml",
                "depends_on": ["p1"],
            },
            "p3": {
                "description": "Right branch",
                "source": "p3/sbkube.yaml",
                "depends_on": ["p1"],
            },
            "p4": {
                "description": "Merge",
                "source": "p4/sbkube.yaml",
                "depends_on": ["p2", "p3"],
            },
        }
        workspace_file = self._create_workspace_file(tmp_path, phases)

        cmd = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
            parallel=True,
        )

        workspace = cmd._load_and_validate_workspace()
        phase_order = workspace.get_phase_order()
        levels = cmd._calculate_parallel_levels(workspace, phase_order)

        # Level 0: p1
        # Level 1: p2, p3 (can run in parallel)
        # Level 2: p4 (depends on both p2 and p3)
        assert len(levels) == 3
        assert levels[0] == ["p1"]
        assert set(levels[1]) == {"p2", "p3"}
        assert levels[2] == ["p4"]

    def test_sequential_vs_parallel_results_consistency(self, tmp_path: Path) -> None:
        """순차 vs 병렬 결과 일관성 테스트."""
        phases = {
            "p1": {
                "description": "First",
                "source": "p1/sbkube.yaml",
            },
            "p2": {
                "description": "Second",
                "source": "p2/sbkube.yaml",
                "depends_on": ["p1"],
            },
        }
        workspace_file = self._create_workspace_file(tmp_path, phases)

        # Sequential execution
        cmd_seq = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
            parallel=False,
        )
        result_seq = cmd_seq.execute()

        # Parallel execution
        cmd_par = WorkspaceDeployCommand(
            workspace_file=str(workspace_file),
            dry_run=True,
            skip_validation=True,
            parallel=True,
        )
        result_par = cmd_par.execute()

        # Both should succeed
        assert result_seq is True
        assert result_par is True

        # Both should have same phases in results
        assert set(cmd_seq.phase_results.keys()) == set(cmd_par.phase_results.keys())
