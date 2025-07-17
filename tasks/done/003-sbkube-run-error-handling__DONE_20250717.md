---
phase: 1
order: 3
source_plan: /tasks/plan/phase1-basic-convenience.md
priority: medium
tags: [run-command, error-handling, user-guidance]
estimated_days: 2
depends_on: [002-sbkube-run-step-control]
status: completed
completed_date: 2025-07-17
---

# 📌 작업: sbkube run 기본 오류 처리 구현

## 🎯 목표
`sbkube run` 명령어에 각 단계별 실패 처리, 명확한 오류 메시지 표시, 다음 액션 제안 기능을 구현합니다.

## 📋 실제 구현 내용

### 1. 오류 처리 클래스 구현
```python
# sbkube/commands/run.py에 추가
from sbkube.exceptions import SbkubeError

class RunExecutionError(SbkubeError):
    """Run 명령어 실행 중 발생하는 오류"""
    def __init__(self, step: str, message: str, suggestions: List[str] = None):
        self.step = step
        self.suggestions = suggestions or []
        super().__init__(f"{step} 단계 실패: {message}")
```

### 2. 단계별 실패 처리
```python
def execute(self):
    """단계별 실행 제어를 적용한 실행 (오류 처리 포함)"""
    steps = self._determine_steps()
    
    for i, step in enumerate(steps):
        try:
            logger.info(f"🚀 {step.title()} 단계 시작... ({i+1}/{len(steps)})")
            self._execute_step(step)
            logger.success(f"✅ {step.title()} 단계 완료")
            
        except Exception as e:
            self._handle_step_failure(step, e, i+1, len(steps))
            raise RunExecutionError(step, str(e), self._get_failure_suggestions(step, e))

def _handle_step_failure(self, step: str, error: Exception, current_step: int, total_steps: int):
    """단계별 실패 처리"""
    logger.error(f"❌ {step.title()} 단계 실패 ({current_step}/{total_steps})")
    logger.error(f"오류 내용: {error}")
    
    # 진행 상황 표시
    progress = "█" * (current_step - 1) + "❌" + "░" * (total_steps - current_step)
    logger.info(f"진행 상황: {progress} {current_step-1}/{total_steps} 완료")
    
    # 실패한 단계 정보 저장
    self._save_failure_state(step, error)
```

### 3. 오류 메시지 강화
```python
def _enhance_error_message(self, step: str, error: Exception) -> str:
    """단계별 오류 메시지 강화"""
    base_message = str(error)
    
    if step == "prepare":
        return f"소스 준비 중 오류 발생: {base_message}"
    elif step == "build":
        return f"앱 빌드 중 오류 발생: {base_message}"
    elif step == "template":
        return f"템플릿 렌더링 중 오류 발생: {base_message}"
    elif step == "deploy":
        return f"배포 중 오류 발생: {base_message}"
    else:
        return base_message
```

### 4. 단계별 해결 방법 제안
```python
def _get_failure_suggestions(self, step: str, error: Exception) -> List[str]:
    """단계별 실패 시 해결 방법 제안"""
    suggestions = []
    error_msg = str(error).lower()
    
    if step == "prepare":
        suggestions.extend([
            "sources.yaml 파일에서 저장소 설정을 확인하세요",
            "네트워크 연결 상태를 확인하세요",
        ])
        if "not found" in error_msg:
            suggestions.append("저장소 URL이 올바른지 확인하세요")
        if "permission" in error_msg:
            suggestions.append("저장소 접근 권한을 확인하세요")
            
    elif step == "build":
        suggestions.extend([
            "config.yaml 파일의 앱 설정을 확인하세요",
            "필요한 소스 파일들이 존재하는지 확인하세요",
        ])
        if "file not found" in error_msg:
            suggestions.append("prepare 단계가 정상적으로 완료되었는지 확인하세요")
            
    elif step == "template":
        suggestions.extend([
            "Helm 차트 문법을 확인하세요",
            "values 파일의 형식을 확인하세요",
        ])
        if "yaml" in error_msg:
            suggestions.append("YAML 파일 문법 오류를 확인하세요")
            
    elif step == "deploy":
        suggestions.extend([
            "Kubernetes 클러스터 연결을 확인하세요",
            "네임스페이스가 존재하는지 확인하세요",
            "권한 설정을 확인하세요",
        ])
        if "namespace" in error_msg:
            suggestions.append("kubectl create namespace <namespace-name>으로 네임스페이스를 생성하세요")
        if "permission" in error_msg:
            suggestions.append("kubectl 권한 설정을 확인하세요")
    
    # 공통 제안사항
    suggestions.extend([
        f"sbkube run --from-step {step}로 해당 단계부터 재시작하세요",
        "sbkube validate로 설정 파일을 검증하세요",
        "-v 옵션으로 상세 로그를 확인하세요",
    ])
    
    return suggestions
```

### 5. 사용자 친화적 CLI 오류 출력
```python
@click.command(name="run")
# ... 기존 옵션들 ...
def cmd(ctx, app_dir, base_dir, app, config_file, from_step, to_step, only):
    """전체 워크플로우를 통합 실행합니다."""
    # ... 기존 검증 로직 ...
    
    try:
        command.execute()
        logger.success("🎉 모든 단계가 성공적으로 완료되었습니다!")
        
    except RunExecutionError as e:
        logger.error(f"\n{e}")
        
        if e.suggestions:
            logger.info("\n💡 다음 해결 방법을 시도해보세요:")
            for i, suggestion in enumerate(e.suggestions, 1):
                logger.info(f"   {i}. {suggestion}")
        
        logger.info(f"\n🔄 재시작 방법: sbkube run --from-step {e.step}")
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"❌ 옵션 오류: {e}")
        logger.info("💡 sbkube run --help로 사용법을 확인하세요")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  사용자에 의해 중단되었습니다")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        logger.info("💡 다음 방법을 시도해보세요:")
        logger.info("   1. -v 옵션으로 상세 로그를 확인하세요")
        logger.info("   2. GitHub Issues에 버그를 신고하세요")
        logger.info("   3. sbkube validate로 설정을 검증하세요")
        sys.exit(1)
```

## 🧪 구현된 테스트

### 오류 처리 단위 테스트
- `test_run_error_handling.py`: RunExecutionError 클래스 및 오류 처리 로직 테스트
- 단계별 오류 메시지 강화 테스트
- 단계별 해결 방법 제안 테스트
- 실패 상태 저장 테스트

### CLI 오류 처리 통합 테스트
- `test_run_error_handling.py`: CLI 오류 출력 형식 테스트
- 키보드 인터럽트 처리 테스트
- 예상치 못한 오류 처리 테스트
- 단계별 실패 시나리오 테스트

## ✅ 완료 기준

- [x] `RunExecutionError` 예외 클래스 구현
- [x] 단계별 실패 처리 로직 구현
- [x] 오류 메시지 강화 기능 구현
- [x] 단계별 해결 방법 제안 시스템 구현
- [x] 사용자 친화적 CLI 오류 출력 구현
- [x] 오류 처리 테스트 케이스 통과

## 🔍 검증 명령어

```bash
# 의도적 실패 테스트 (잘못된 설정으로)
sbkube run --app-dir nonexistent

# 키보드 인터럽트 테스트
sbkube run  # Ctrl+C로 중단

# 테스트 실행
pytest tests/unit/commands/test_run_error_handling.py -v
pytest tests/integration/test_run_error_handling.py -v
```

## 📝 예상 결과

```bash
$ sbkube run --app-dir nonexistent
📋 실행할 단계: prepare → build → template → deploy
🚀 Prepare 단계 시작... (1/4)
❌ Prepare 단계 실패 (1/4)
오류 내용: 설정 파일을 찾을 수 없습니다
진행 상황: ❌░░░ 0/4 완료

❌ prepare 단계 실패: 소스 준비 중 오류 발생: 설정 파일을 찾을 수 없습니다

💡 다음 해결 방법을 시도해보세요:
   1. sources.yaml 파일에서 저장소 설정을 확인하세요
   2. 네트워크 연결 상태를 확인하세요
   3. sbkube run --from-step prepare로 해당 단계부터 재시작하세요
   4. sbkube validate로 설정 파일을 검증하세요
   5. -v 옵션으로 상세 로그를 확인하세요

🔄 재시작 방법: sbkube run --from-step prepare
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `004-sbkube-run-cli-integration.md` - CLI 통합 및 최종 검증

## 🎯 실제 구현 결과

### 구현된 기능들:
1. **포괄적인 오류 처리**: 모든 단계에서 발생할 수 있는 오류를 체계적으로 처리
2. **단계별 맞춤 제안**: 각 단계의 특성에 맞는 구체적인 해결방안 제시
3. **시각적 진행 상황**: 실패 지점을 명확히 보여주는 진행 바 표시
4. **재시작 지원**: 실패한 단계부터 다시 시작할 수 있는 명령어 제공
5. **다양한 오류 시나리오**: 키보드 인터럽트, 옵션 오류, 예상치 못한 오류 등 모든 상황 처리

### 주요 개선사항:
- SbkubeError를 상속받은 전용 예외 클래스로 일관된 오류 처리
- 오류 유형별 맞춤형 제안사항으로 사용자 경험 향상
- 포괄적인 테스트 커버리지로 안정성 확보
- 미래 확장을 위한 실패 상태 저장 인터페이스 준비