"""Workspace 명령어 테스트."""

from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands.workspace import (
    WorkspaceGraphCommand,
    WorkspaceInitCommand,
    WorkspaceValidateCommand,
    graph_cmd,
    init_cmd,
    validate_cmd,
)


class TestWorkspaceValidateCommand:
    """WorkspaceValidateCommand 테스트."""

    def test_valid_workspace(self, tmp_path: Path) -> None:
        """유효한 workspace.yaml 검증 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        workspace_config = {
            "version": "1.0",
            "metadata": {"name": "test-workspace"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sources.yaml",
                    "app_groups": ["a000_network"],
                }
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))
        workspace = cmd.execute()

        assert workspace.version == "1.0"
        assert workspace.metadata.name == "test-workspace"
        assert len(workspace.phases) == 1

    def test_missing_workspace_file(self, tmp_path: Path) -> None:
        """workspace.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_invalid_workspace_structure(self, tmp_path: Path) -> None:
        """잘못된 workspace.yaml 구조 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        # 잘못된 버전 형식
        invalid_config = {
            "version": "1",  # 잘못된 형식 (1.0이어야 함)
            "metadata": {"name": "test"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                }
            },
        }
        workspace_file.write_text(yaml.dump(invalid_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_circular_dependency(self, tmp_path: Path) -> None:
        """순환 의존성 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        circular_config = {
            "version": "1.0",
            "metadata": {"name": "circular-test"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sources.yaml",
                    "app_groups": ["app2"],
                    "depends_on": ["p1"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(circular_config))

        cmd = WorkspaceValidateCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceGraphCommand:
    """WorkspaceGraphCommand 테스트."""

    def test_dependency_graph(self, tmp_path: Path) -> None:
        """의존성 그래프 출력 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        workspace_config = {
            "version": "1.0",
            "metadata": {"name": "graph-test"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sources.yaml",
                    "app_groups": ["a000_network"],
                },
                "p2-data": {
                    "description": "Data layer",
                    "source": "p2-kube/sources.yaml",
                    "app_groups": ["a100_postgres"],
                    "depends_on": ["p1-infra"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))

        cmd = WorkspaceGraphCommand(str(workspace_file))
        # 그래프 출력은 에러 없이 완료되어야 함
        cmd.execute()

    def test_graph_missing_file(self, tmp_path: Path) -> None:
        """workspace.yaml 파일 없음 테스트."""
        workspace_file = tmp_path / "nonexistent.yaml"

        cmd = WorkspaceGraphCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()

    def test_graph_circular_dependency(self, tmp_path: Path) -> None:
        """순환 의존성 그래프 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        circular_config = {
            "version": "1.0",
            "metadata": {"name": "circular-graph"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sources.yaml",
                    "app_groups": ["app2"],
                    "depends_on": ["p1"],
                },
            },
        }
        workspace_file.write_text(yaml.dump(circular_config))

        cmd = WorkspaceGraphCommand(str(workspace_file))

        with pytest.raises(click.Abort):
            cmd.execute()


class TestWorkspaceCLI:
    """Workspace CLI 명령어 테스트."""

    def test_validate_cli_success(self, tmp_path: Path) -> None:
        """workspace validate CLI 성공 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        workspace_config = {
            "version": "1.0",
            "metadata": {"name": "cli-test"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                }
            },
        }
        workspace_file.write_text(yaml.dump(workspace_config))

        runner = CliRunner()
        result = runner.invoke(validate_cmd, [str(workspace_file)])

        assert result.exit_code == 0
        assert "Workspace 검증 완료" in result.output

    def test_validate_cli_failure(self, tmp_path: Path) -> None:
        """workspace validate CLI 실패 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        # 잘못된 구조
        invalid_config = {"version": "1.0", "metadata": {"name": "test"}, "phases": {}}
        workspace_file.write_text(yaml.dump(invalid_config))

        runner = CliRunner()
        result = runner.invoke(validate_cmd, [str(workspace_file)])

        assert result.exit_code != 0

    def test_graph_cli_success(self, tmp_path: Path) -> None:
        """workspace graph CLI 성공 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        workspace_config = {
            "version": "1.0",
            "metadata": {"name": "graph-cli-test"},
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure",
                    "source": "p1-kube/sources.yaml",
                    "app_groups": ["a000_network"],
                },
                "p2-data": {
                    "description": "Data",
                    "source": "p2-kube/sources.yaml",
                    "app_groups": ["a100_postgres"],
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
        """workspace graph CLI 순환 의존성 테스트."""
        workspace_file = tmp_path / "workspace.yaml"
        circular_config = {
            "version": "1.0",
            "metadata": {"name": "circular-cli"},
            "phases": {
                "p1": {
                    "description": "Phase 1",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                    "depends_on": ["p2"],
                },
                "p2": {
                    "description": "Phase 2",
                    "source": "sources.yaml",
                    "app_groups": ["app2"],
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
        output_file = tmp_path / "workspace.yaml"

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

        assert workspace["version"] == "1.0"
        assert workspace["metadata"]["name"] == "my-workspace"
        assert len(workspace["phases"]) == 3
        assert "p1-infra" in workspace["phases"]
        assert "p2-data" in workspace["phases"]
        assert "p3-app" in workspace["phases"]

    def test_file_already_exists_no_overwrite(self, tmp_path: Path) -> None:
        """파일 존재 시 덮어쓰기 거부 테스트."""
        output_file = tmp_path / "workspace.yaml"
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
        output_file = tmp_path / "workspace.yaml"
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
        assert workspace["version"] == "1.0"

    def test_init_cli_non_interactive(self, tmp_path: Path) -> None:
        """workspace init CLI 비대화형 모드 테스트."""
        output_file = tmp_path / "workspace.yaml"

        runner = CliRunner()
        result = runner.invoke(init_cmd, [str(output_file), "--non-interactive"])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Workspace 파일 생성 완료" in result.output

    def test_init_cli_with_existing_file(self, tmp_path: Path) -> None:
        """workspace init CLI 기존 파일 존재 시 테스트."""
        output_file = tmp_path / "workspace.yaml"
        output_file.write_text("existing")

        runner = CliRunner()
        # 'n' 입력으로 덮어쓰기 거부
        result = runner.invoke(
            init_cmd, [str(output_file), "--non-interactive"], input="n\n"
        )

        # Abort되므로 exit_code != 0
        assert result.exit_code != 0
