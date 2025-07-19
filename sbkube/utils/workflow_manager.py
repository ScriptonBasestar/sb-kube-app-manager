from pathlib import Path
from typing import Any

import yaml

from sbkube.models.workflow_model import Workflow
from sbkube.utils.logger import logger


class WorkflowManager:
    """워크플로우 관리자"""

    def __init__(self, workflows_dir: str = ".sbkube/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        # 기본 워크플로우 생성
        self._create_default_workflows()

    def list_workflows(self) -> list[dict[str, Any]]:
        """사용 가능한 워크플로우 목록"""
        workflows = []

        for workflow_file in self.workflows_dir.glob("*.yaml"):
            try:
                with open(workflow_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                workflows.append(
                    {
                        "name": data.get("name", workflow_file.stem),
                        "description": data.get("description", ""),
                        "version": data.get("version", "1.0"),
                        "steps_count": len(data.get("steps", [])),
                        "file": str(workflow_file),
                    }
                )

            except Exception as e:
                logger.warning(f"워크플로우 파일 로드 실패 ({workflow_file}): {e}")

        return workflows

    def load_workflow(self, name: str) -> Workflow | None:
        """워크플로우 로드"""
        workflow_file = self.workflows_dir / f"{name}.yaml"

        if not workflow_file.exists():
            # 내장 워크플로우 확인
            builtin_file = self._get_builtin_workflow_path(name)
            if builtin_file and builtin_file.exists():
                workflow_file = builtin_file
            else:
                return None

        try:
            return Workflow.from_yaml_file(str(workflow_file))
        except Exception as e:
            logger.error(f"워크플로우 로드 실패: {e}")
            return None

    def save_workflow(self, workflow: Workflow) -> bool:
        """워크플로우 저장"""
        try:
            workflow_file = self.workflows_dir / f"{workflow.name}.yaml"
            workflow.save_to_yaml(str(workflow_file))
            logger.info(f"워크플로우 저장됨: {workflow_file}")
            return True
        except Exception as e:
            logger.error(f"워크플로우 저장 실패: {e}")
            return False

    def delete_workflow(self, name: str) -> bool:
        """워크플로우 삭제"""
        workflow_file = self.workflows_dir / f"{name}.yaml"

        if workflow_file.exists():
            try:
                workflow_file.unlink()
                logger.info(f"워크플로우 삭제됨: {name}")
                return True
            except Exception as e:
                logger.error(f"워크플로우 삭제 실패: {e}")
                return False

        return False

    def _create_default_workflows(self):
        """기본 워크플로우 생성"""
        default_workflows = {
            "quick-deploy": {
                "name": "quick-deploy",
                "description": "빠른 배포 (캐시 활용)",
                "version": "1.0",
                "variables": {"use_cache": True},
                "steps": [
                    {
                        "name": "prepare",
                        "type": "builtin",
                        "condition": '!cache.exists("charts")',
                    },
                    {
                        "name": "deploy",
                        "type": "builtin",
                        "parallel": True,
                        "apps": ["frontend", "backend"],
                    },
                ],
            },
            "full-ci-cd": {
                "name": "full-ci-cd",
                "description": "전체 CI/CD 파이프라인",
                "version": "1.0",
                "steps": [
                    {"name": "validate", "type": "builtin"},
                    {
                        "name": "test",
                        "type": "script",
                        "script": "pytest tests/",
                        "on_failure": "stop",
                    },
                    {"name": "build", "type": "builtin"},
                    {
                        "name": "security-scan",
                        "type": "script",
                        "script": "bandit -r sbkube/",
                        "on_failure": "continue",
                    },
                    {
                        "name": "deploy",
                        "type": "builtin",
                        "condition": 'env.get("ENVIRONMENT") == "production"',
                    },
                    {
                        "name": "smoke-test",
                        "type": "script",
                        "script": "curl -f http://app.example.com/health",
                        "timeout": 60,
                    },
                ],
            },
        }

        for workflow_name, workflow_data in default_workflows.items():
            workflow_file = self.workflows_dir / f"{workflow_name}.yaml"

            if not workflow_file.exists():
                try:
                    with open(workflow_file, "w", encoding="utf-8") as f:
                        yaml.dump(
                            workflow_data,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                        )
                except Exception as e:
                    logger.warning(f"기본 워크플로우 생성 실패 ({workflow_name}): {e}")

    def _get_builtin_workflow_path(self, name: str) -> Path | None:
        """내장 워크플로우 경로 반환"""
        # 패키지 내 워크플로우 디렉토리
        import sbkube

        package_dir = Path(sbkube.__file__).parent
        builtin_path = package_dir / "workflows" / f"{name}.yaml"

        return builtin_path if builtin_path.exists() else None
