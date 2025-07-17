"""
기본 검증기 모듈

ValidationEngine의 기본 동작을 테스트하기 위한 예시 검증기들입니다.
"""

from pathlib import Path
import yaml
from typing import List

from sbkube.utils.validation_system import ValidationCheck, ValidationContext, ValidationResult, ValidationSeverity
from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.logger import logger


class FileExistenceValidator(ValidationCheck):
    """파일 존재성 검증기"""
    
    def __init__(self):
        super().__init__(
            name="file_existence",
            description="필수 설정 파일 존재성 확인",
            category="configuration"
        )
    
    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """필수 파일들의 존재성을 확인합니다"""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir
        
        required_files = [
            config_path / "config.yaml",
            config_path / "sources.yaml"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path.relative_to(base_path)))
        
        if missing_files:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"필수 설정 파일이 누락되었습니다: {', '.join(missing_files)}",
                details="SBKube 실행에 필요한 설정 파일들이 없습니다.",
                recommendation="sbkube init 명령어를 실행하여 기본 설정 파일을 생성하세요.",
                fix_command="sbkube init",
                fix_description="기본 설정 파일 생성",
                risk_level="high",
                affected_components=missing_files
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 필수 설정 파일이 존재합니다",
                details=f"확인된 파일: {', '.join([str(f.relative_to(base_path)) for f in required_files])}",
                risk_level="low"
            )


class ConfigSyntaxValidator(ValidationCheck):
    """설정 파일 문법 검증기"""
    
    def __init__(self):
        super().__init__(
            name="config_syntax",
            description="설정 파일 YAML 문법 확인",
            category="configuration"
        )
    
    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """설정 파일들의 YAML 문법을 확인합니다"""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir
        
        config_files = [
            config_path / "config.yaml",
            config_path / "sources.yaml"
        ]
        
        syntax_errors = []
        valid_files = []
        
        for file_path in config_files:
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                valid_files.append(str(file_path.relative_to(base_path)))
            except yaml.YAMLError as e:
                error_msg = f"{file_path.relative_to(base_path)}: {str(e)}"
                syntax_errors.append(error_msg)
            except Exception as e:
                error_msg = f"{file_path.relative_to(base_path)}: 파일 읽기 오류 - {str(e)}"
                syntax_errors.append(error_msg)
        
        if syntax_errors:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"YAML 문법 오류가 발견되었습니다",
                details="다음 파일들에서 문법 오류가 발견되었습니다:\n" + "\n".join(syntax_errors),
                recommendation="YAML 문법을 확인하고 수정하세요. YAML 문법 검사 도구를 사용하는 것을 권장합니다.",
                risk_level="high",
                affected_components=[error.split(':')[0] for error in syntax_errors]
            )
        elif valid_files:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 설정 파일의 YAML 문법이 정상입니다",
                details=f"검증된 파일: {', '.join(valid_files)}",
                risk_level="low"
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="검증할 설정 파일이 없습니다",
                details="config.yaml 또는 sources.yaml 파일이 존재하지 않습니다.",
                recommendation="필요한 설정 파일을 생성하세요.",
                risk_level="medium"
            )


class BasicSystemValidator(ValidationCheck):
    """기본 시스템 검증기"""
    
    def __init__(self):
        super().__init__(
            name="basic_system",
            description="기본 시스템 요구사항 확인",
            category="environment"
        )
    
    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """기본 시스템 요구사항을 확인합니다"""
        issues = []
        
        # Python 버전 확인 (기본적으로 실행 중이므로 문제없음)
        # 여기서는 간단한 체크만 수행
        
        # 작업 디렉토리 쓰기 권한 확인
        base_path = Path(context.base_dir)
        try:
            test_file = base_path / ".sbkube_test_write"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            issues.append(f"작업 디렉토리 쓰기 권한 없음: {e}")
        
        # .sbkube 디렉토리 생성 가능 확인
        sbkube_dir = base_path / ".sbkube"
        try:
            sbkube_dir.mkdir(exist_ok=True)
        except Exception as e:
            issues.append(f".sbkube 디렉토리 생성 불가: {e}")
        
        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message="기본 시스템 요구사항을 충족하지 않습니다",
                details="다음 문제들이 발견되었습니다:\n" + "\n".join(issues),
                recommendation="파일 시스템 권한을 확인하고 필요한 권한을 부여하세요.",
                risk_level="high",
                affected_components=["file_system", "permissions"]
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="기본 시스템 요구사항을 충족합니다",
                details="파일 시스템 권한 및 기본 요구사항이 정상입니다.",
                risk_level="low"
            )