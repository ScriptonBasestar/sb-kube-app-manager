import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from sbkube.utils.auto_fix_system import AutoFix
from sbkube.utils.diagnostic_system import DiagnosticResult
from sbkube.utils.logger import logger


class MissingNamespaceFix(AutoFix):
    """누락된 네임스페이스 생성"""

    def __init__(self):
        super().__init__(
            fix_id="create_missing_namespace",
            description="누락된 네임스페이스 생성",
            risk_level="low",
        )

    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return "네임스페이스" in diagnostic_result.message and (
            "존재하지 않음" in diagnostic_result.message
            or "존재하지 않습니다" in diagnostic_result.message
        )

    def create_backup(self) -> str | None:
        """백업 생성 (네임스페이스는 백업 불필요)"""
        return None

    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """네임스페이스 생성"""
        try:
            # 네임스페이스 이름 추출
            namespace = self._extract_namespace_name(diagnostic_result.message)
            if not namespace:
                return False

            # 네임스페이스 생성
            result = subprocess.run(
                ["kubectl", "create", "namespace", namespace],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info(f"네임스페이스 '{namespace}' 생성 완료")
                return True
            else:
                logger.error(f"네임스페이스 생성 실패: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("네임스페이스 생성 시간 초과")
            return False
        except Exception as e:
            logger.error(f"네임스페이스 생성 중 오류: {e}")
            return False

    def rollback(self, backup_path: str) -> bool:
        """롤백 (네임스페이스 삭제)"""
        # 네임스페이스 삭제는 위험하므로 기본적으로 수행하지 않음
        # 실제 환경에서는 신중하게 처리해야 함
        logger.info("네임스페이스 삭제는 안전상 자동으로 수행하지 않습니다")
        return True

    def validate_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 후 검증"""
        try:
            namespace = self._extract_namespace_name(diagnostic_result.message)
            if not namespace:
                return False

            # 네임스페이스 존재 확인
            result = subprocess.run(
                ["kubectl", "get", "namespace", namespace],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0

        except Exception:
            return False

    def _extract_namespace_name(self, message: str) -> str | None:
        """오류 메시지에서 네임스페이스 이름 추출"""
        # 따옴표 안의 텍스트 추출
        quote_match = re.search(r"'([^']+)'", message)
        if quote_match:
            return quote_match.group(1)

        # 쌍따옴표 안의 텍스트 추출
        double_quote_match = re.search(r'"([^"]+)"', message)
        if double_quote_match:
            return double_quote_match.group(1)

        # 네임스페이스 뒤의 단어 추출
        namespace_match = re.search(r"네임스페이스\s+([^\s]+)", message)
        if namespace_match:
            return namespace_match.group(1)

        return None


class ConfigFileFix(AutoFix):
    """설정 파일 수정"""

    def __init__(self):
        super().__init__(
            fix_id="fix_config_file",
            description="설정 파일 오류 수정",
            risk_level="medium",
        )

    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return (
            "설정 파일" in diagnostic_result.message
            or "config.yaml" in diagnostic_result.message
            or "필수 설정이 누락" in diagnostic_result.message
            or "YAML 문법 오류" in diagnostic_result.message
        )

    def create_backup(self) -> str | None:
        """설정 파일 백업"""
        try:
            config_file = Path("config/config.yaml")
            if not config_file.exists():
                return None

            backup_dir = Path(".sbkube/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config_backup_{timestamp}.yaml"

            shutil.copy2(config_file, backup_path)
            logger.info(f"설정 파일 백업 생성: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"설정 파일 백업 실패: {e}")
            return None

    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """설정 파일 수정"""
        try:
            if "필수 설정이 누락" in diagnostic_result.message:
                return self._add_missing_fields(diagnostic_result)
            elif "YAML 문법 오류" in diagnostic_result.message:
                return self._fix_yaml_syntax(diagnostic_result)
            elif "설정 파일이 없습니다" in diagnostic_result.message:
                return self._create_default_config()

            return False

        except Exception as e:
            logger.error(f"설정 파일 수정 중 오류: {e}")
            return False

    def rollback(self, backup_path: str) -> bool:
        """설정 파일 롤백"""
        try:
            config_file = Path("config/config.yaml")
            shutil.copy2(backup_path, config_file)
            logger.info(f"설정 파일 롤백 완료: {backup_path} -> {config_file}")
            return True
        except Exception as e:
            logger.error(f"설정 파일 롤백 실패: {e}")
            return False

    def validate_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 후 검증"""
        try:
            import yaml

            config_file = Path("config/config.yaml")
            if not config_file.exists():
                return False

            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 기본 검증
            if not config:
                return False

            # 필수 필드 확인
            required_fields = ["namespace", "apps"]
            for field in required_fields:
                if field not in config:
                    return False

            return True

        except Exception:
            return False

    def _add_missing_fields(self, diagnostic_result: DiagnosticResult) -> bool:
        """누락된 필드 추가"""
        import yaml

        try:
            config_file = Path("config/config.yaml")
            config_file.parent.mkdir(parents=True, exist_ok=True)

            config: dict[str, Any] = {}
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

            # 기본 필드 추가
            if "namespace" not in config:
                config["namespace"] = "default"

            if "apps" not in config:
                config["apps"] = []

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            logger.info("누락된 설정 필드 추가 완료")
            return True

        except Exception as e:
            logger.error(f"설정 필드 추가 실패: {e}")
            return False

    def _fix_yaml_syntax(self, diagnostic_result: DiagnosticResult) -> bool:
        """YAML 문법 오류 수정 (기본적인 것만)"""
        try:
            config_file = Path("config/config.yaml")

            if not config_file.exists():
                return self._create_default_config()

            with open(config_file, encoding="utf-8") as f:
                content = f.read()

            # 기본적인 YAML 수정
            # 탭을 스페이스로 변경
            content = content.replace("\t", "  ")

            # 기본 구조가 없으면 추가
            if not content.strip():
                content = "namespace: default\napps: []\n"

            with open(config_file, "w", encoding="utf-8") as f:
                f.write(content)

            # YAML 파싱 테스트
            import yaml

            yaml.safe_load(content)

            logger.info("YAML 문법 오류 수정 완료")
            return True

        except Exception as e:
            logger.error(f"YAML 문법 수정 실패: {e}")
            return False

    def _create_default_config(self) -> bool:
        """기본 설정 파일 생성"""
        try:
            config_file = Path("config/config.yaml")
            config_file.parent.mkdir(parents=True, exist_ok=True)

            default_config = {"namespace": "default", "apps": []}

            import yaml

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    default_config, f, default_flow_style=False, allow_unicode=True
                )

            logger.info("기본 설정 파일 생성 완료")
            return True

        except Exception as e:
            logger.error(f"기본 설정 파일 생성 실패: {e}")
            return False


class HelmRepositoryFix(AutoFix):
    """Helm 리포지토리 추가"""

    def __init__(self):
        super().__init__(
            fix_id="add_helm_repository",
            description="필요한 Helm 리포지토리 추가",
            risk_level="low",
        )

    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return "helm" in diagnostic_result.message.lower() and (
            "리포지토리" in diagnostic_result.message
            or "repository" in diagnostic_result.message.lower()
        )

    def create_backup(self) -> str | None:
        """백업 생성 (리포지토리 목록 백업)"""
        try:
            result = subprocess.run(
                ["helm", "repo", "list", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                backup_dir = Path(".sbkube/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"helm_repos_backup_{timestamp}.json"

                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                logger.info(f"Helm 리포지토리 백업 생성: {backup_path}")
                return str(backup_path)

            return None

        except Exception as e:
            logger.error(f"Helm 리포지토리 백업 실패: {e}")
            return None

    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """Helm 리포지토리 추가"""
        try:
            # 기본 리포지토리들 추가
            repositories = [
                ("bitnami", "https://charts.bitnami.com/bitnami"),
                ("stable", "https://charts.helm.sh/stable"),
            ]

            success_count = 0
            for name, url in repositories:
                try:
                    result = subprocess.run(
                        ["helm", "repo", "add", name, url],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        success_count += 1
                        logger.info(f"Helm 리포지토리 추가 성공: {name}")
                    else:
                        logger.warning(
                            f"Helm 리포지토리 추가 실패: {name} - {result.stderr}"
                        )

                except subprocess.TimeoutExpired:
                    logger.error(f"Helm 리포지토리 추가 시간 초과: {name}")

            if success_count > 0:
                # 리포지토리 업데이트
                try:
                    subprocess.run(
                        ["helm", "repo", "update"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    logger.info("Helm 리포지토리 업데이트 완료")
                except Exception as e:
                    logger.warning(f"Helm 리포지토리 업데이트 실패: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Helm 리포지토리 추가 중 오류: {e}")
            return False

    def rollback(self, backup_path: str) -> bool:
        """Helm 리포지토리 롤백"""
        try:
            # 현재 리포지토리 제거
            result = subprocess.run(
                ["helm", "repo", "list", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                current_repos = json.loads(result.stdout)

                for repo in current_repos:
                    subprocess.run(
                        ["helm", "repo", "remove", repo["name"]],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

            # 백업된 리포지토리 복원
            with open(backup_path, encoding="utf-8") as f:
                backup_repos = json.load(f)

            for repo in backup_repos:
                subprocess.run(
                    ["helm", "repo", "add", repo["name"], repo["url"]],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            logger.info("Helm 리포지토리 롤백 완료")
            return True

        except Exception as e:
            logger.error(f"Helm 리포지토리 롤백 실패: {e}")
            return False

    def validate_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 후 검증"""
        try:
            result = subprocess.run(
                ["helm", "repo", "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                # bitnami 또는 stable 리포지토리가 있는지 확인
                output = result.stdout.lower()
                return "bitnami" in output or "stable" in output

            return False

        except Exception:
            return False
