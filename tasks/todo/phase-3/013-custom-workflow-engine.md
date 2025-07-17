---
phase: 3
order: 13
source_plan: /tasks/plan/phase3-intelligent-features.md
priority: medium
tags: [workflow-engine, yaml-parser, parallel-execution]
estimated_days: 3
depends_on: [012-auto-fix-system]
---

# 📌 작업: 커스텀 워크플로우 엔진 구현

## 🎯 목표
YAML 기반으로 사용자 정의 워크플로우를 정의하고 실행할 수 있는 엔진을 구현합니다. 조건부 실행, 병렬 처리, 스크립트 실행을 지원합니다.

## 📋 작업 내용

### 1. 워크플로우 모델 정의
```python
# sbkube/models/workflow_model.py
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import yaml

class StepType(Enum):
    BUILTIN = "builtin"        # sbkube 내장 명령어
    SCRIPT = "script"          # 사용자 스크립트
    PARALLEL = "parallel"      # 병렬 실행 그룹

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowStep:
    """워크플로우 단계"""
    name: str
    type: StepType = StepType.BUILTIN
    command: Optional[str] = None
    script: Optional[str] = None
    condition: Optional[str] = None
    parallel: bool = False
    apps: Optional[List[str]] = None
    timeout: int = 300  # 5분 기본 타임아웃
    retry_count: int = 0
    on_failure: Optional[str] = None  # continue, stop, retry
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 실행 상태
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'type': self.type.value,
            'command': self.command,
            'script': self.script,
            'condition': self.condition,
            'parallel': self.parallel,
            'apps': self.apps,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'on_failure': self.on_failure,
            'metadata': self.metadata,
            'status': self.status.value,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'output': self.output,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """딕셔너리에서 생성"""
        step = cls(
            name=data['name'],
            type=StepType(data.get('type', 'builtin')),
            command=data.get('command'),
            script=data.get('script'),
            condition=data.get('condition'),
            parallel=data.get('parallel', False),
            apps=data.get('apps'),
            timeout=data.get('timeout', 300),
            retry_count=data.get('retry_count', 0),
            on_failure=data.get('on_failure'),
            metadata=data.get('metadata', {})
        )
        
        # 실행 상태 복원
        if 'status' in data:
            step.status = StepStatus(data['status'])
        step.started_at = data.get('started_at')
        step.completed_at = data.get('completed_at')
        step.output = data.get('output')
        step.error = data.get('error')
        
        return step

@dataclass
class Workflow:
    """워크플로우 정의"""
    name: str
    description: str = ""
    version: str = "1.0"
    variables: Dict[str, Any] = field(default_factory=dict)
    steps: List[WorkflowStep] = field(default_factory=list)
    
    # 실행 상태
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'variables': self.variables,
            'steps': [step.to_dict() for step in self.steps],
            'status': self.status.value,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """딕셔너리에서 생성"""
        workflow = cls(
            name=data['name'],
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            variables=data.get('variables', {}),
            steps=[WorkflowStep.from_dict(step_data) for step_data in data.get('steps', [])]
        )
        
        # 실행 상태 복원
        if 'status' in data:
            workflow.status = StepStatus(data['status'])
        workflow.started_at = data.get('started_at')
        workflow.completed_at = data.get('completed_at')
        
        return workflow
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'Workflow':
        """YAML 파일에서 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    def save_to_yaml(self, file_path: str):
        """YAML 파일로 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)
    
    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """단계 이름으로 조회"""
        return next((step for step in self.steps if step.name == name), None)
    
    def get_pending_steps(self) -> List[WorkflowStep]:
        """대기 중인 단계들"""
        return [step for step in self.steps if step.status == StepStatus.PENDING]
    
    def get_failed_steps(self) -> List[WorkflowStep]:
        """실패한 단계들"""
        return [step for step in self.steps if step.status == StepStatus.FAILED]
```

### 2. 조건 평가 시스템 구현
```python
# sbkube/utils/condition_evaluator.py
import re
import os
from typing import Dict, Any, Union

class ConditionEvaluator:
    """조건 평가기"""
    
    def __init__(self, context: Dict[str, Any] = None):
        self.context = context or {}
        self.context.update({
            'env': dict(os.environ),
            'true': True,
            'false': False,
            'null': None
        })
    
    def evaluate(self, condition: str) -> bool:
        """조건 평가"""
        if not condition or condition.strip() == "":
            return True
        
        try:
            # 안전한 평가를 위한 전처리
            safe_condition = self._preprocess_condition(condition)
            
            # 제한된 네임스페이스에서 평가
            allowed_names = {
                '__builtins__': {},
                **self.context
            }
            
            result = eval(safe_condition, allowed_names)
            return bool(result)
            
        except Exception as e:
            # 조건 평가 실패 시 False 반환
            print(f"조건 평가 실패 '{condition}': {e}")
            return False
    
    def _preprocess_condition(self, condition: str) -> str:
        """조건 전처리"""
        # 변수 참조 처리 (${var} -> context['var'])
        condition = re.sub(
            r'\$\{([^}]+)\}',
            lambda m: f"context.get('{m.group(1)}', None)",
            condition
        )
        
        # 환경변수 참조 처리 ($VAR -> env.get('VAR'))
        condition = re.sub(
            r'\$([A-Z_][A-Z0-9_]*)',
            lambda m: f"env.get('{m.group(1)}', '')",
            condition
        )
        
        # 파일 존재 확인 함수
        condition = re.sub(
            r'file\.exists\([\'"]([^\'"]+)[\'"]\)',
            lambda m: f"__import__('pathlib').Path('{m.group(1)}').exists()",
            condition
        )
        
        # 캐시 존재 확인 함수
        condition = re.sub(
            r'cache\.exists\([\'"]([^\'"]+)[\'"]\)',
            lambda m: f"context.get('cache', {{}}).get('{m.group(1)}', False)",
            condition
        )
        
        return condition
    
    def update_context(self, updates: Dict[str, Any]):
        """컨텍스트 업데이트"""
        self.context.update(updates)

# 조건 평가 헬퍼 함수들
def check_environment(env_name: str) -> bool:
    """환경 확인"""
    return os.environ.get('ENVIRONMENT') == env_name

def check_profile(profile_name: str, context: Dict[str, Any]) -> bool:
    """프로파일 확인"""
    return context.get('profile') == profile_name

def check_app_exists(app_name: str, context: Dict[str, Any]) -> bool:
    """앱 존재 확인"""
    apps = context.get('config', {}).get('apps', [])
    return any(app.get('name') == app_name for app in apps)
```

### 3. 워크플로우 실행 엔진 구현
```python
# sbkube/utils/workflow_engine.py
import asyncio
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import concurrent.futures

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.panel import Panel

from sbkube.models.workflow_model import Workflow, WorkflowStep, StepType, StepStatus
from sbkube.utils.condition_evaluator import ConditionEvaluator
from sbkube.utils.logger import logger

class WorkflowEngine:
    """워크플로우 실행 엔진"""
    
    def __init__(self, console: Console = None, max_parallel: int = 4):
        self.console = console or Console()
        self.max_parallel = max_parallel
        self.evaluator = ConditionEvaluator()
        self.builtin_commands = {
            'prepare': self._execute_prepare,
            'build': self._execute_build,
            'template': self._execute_template,
            'deploy': self._execute_deploy,
            'validate': self._execute_validate
        }
        
        # 실행 상태
        self.current_workflow: Optional[Workflow] = None
        self.step_progress: Dict[str, Any] = {}
        
    async def execute_workflow(self, workflow: Workflow, context: Dict[str, Any] = None) -> bool:
        """워크플로우 실행"""
        self.current_workflow = workflow
        self.evaluator.update_context(context or {})
        
        logger.info(f"🚀 워크플로우 '{workflow.name}' 실행 시작")
        
        workflow.status = StepStatus.RUNNING
        workflow.started_at = datetime.now().isoformat()
        
        try:
            success = await self._execute_steps(workflow.steps)
            
            if success:
                workflow.status = StepStatus.COMPLETED
                logger.success("✅ 워크플로우 실행 완료")
            else:
                workflow.status = StepStatus.FAILED
                logger.error("❌ 워크플로우 실행 실패")
            
            return success
            
        except Exception as e:
            workflow.status = StepStatus.FAILED
            logger.error(f"❌ 워크플로우 실행 중 오류: {e}")
            return False
        
        finally:
            workflow.completed_at = datetime.now().isoformat()
    
    async def _execute_steps(self, steps: List[WorkflowStep]) -> bool:
        """단계들 실행"""
        for step in steps:
            # 조건 확인
            if step.condition and not self.evaluator.evaluate(step.condition):
                step.status = StepStatus.SKIPPED
                logger.info(f"⏭️  단계 건너뛰기: {step.name} (조건 불만족)")
                continue
            
            # 단계 실행
            if step.parallel and step.apps:
                success = await self._execute_parallel_step(step)
            else:
                success = await self._execute_single_step(step)
            
            if not success:
                # 실패 처리
                if step.on_failure == "continue":
                    logger.warning(f"⚠️  단계 실패했지만 계속 진행: {step.name}")
                    continue
                elif step.on_failure == "retry" and step.retry_count > 0:
                    logger.info(f"🔄 단계 재시도: {step.name}")
                    step.retry_count -= 1
                    success = await self._execute_single_step(step)
                    if not success:
                        return False
                else:
                    logger.error(f"❌ 단계 실패로 중단: {step.name}")
                    return False
        
        return True
    
    async def _execute_single_step(self, step: WorkflowStep) -> bool:
        """단일 단계 실행"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        logger.info(f"🔄 실행 중: {step.name}")
        
        try:
            if step.type == StepType.BUILTIN:
                success = await self._execute_builtin_step(step)
            elif step.type == StepType.SCRIPT:
                success = await self._execute_script_step(step)
            else:
                logger.error(f"알 수 없는 단계 타입: {step.type}")
                success = False
            
            if success:
                step.status = StepStatus.COMPLETED
                logger.success(f"✅ 완료: {step.name}")
            else:
                step.status = StepStatus.FAILED
                logger.error(f"❌ 실패: {step.name}")
            
            return success
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            logger.error(f"❌ 단계 실행 오류 ({step.name}): {e}")
            return False
        
        finally:
            step.completed_at = datetime.now().isoformat()
    
    async def _execute_parallel_step(self, step: WorkflowStep) -> bool:
        """병렬 단계 실행"""
        if not step.apps:
            return await self._execute_single_step(step)
        
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        logger.info(f"🔄 병렬 실행: {step.name} ({len(step.apps)}개 앱)")
        
        # 앱별로 개별 단계 생성
        parallel_steps = []
        for app in step.apps:
            app_step = WorkflowStep(
                name=f"{step.name}-{app}",
                type=step.type,
                command=step.command,
                script=step.script,
                timeout=step.timeout
            )
            # 앱 컨텍스트 설정
            app_step.metadata = {'target_app': app}
            parallel_steps.append(app_step)
        
        # 병렬 실행
        tasks = []
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def execute_with_semaphore(app_step):
            async with semaphore:
                return await self._execute_single_step(app_step)
        
        for app_step in parallel_steps:
            task = asyncio.create_task(execute_with_semaphore(app_step))
            tasks.append(task)
        
        # 모든 태스크 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        success_count = sum(1 for result in results if result is True)
        total_count = len(results)
        
        if success_count == total_count:
            step.status = StepStatus.COMPLETED
            logger.success(f"✅ 병렬 실행 완료: {step.name} ({success_count}/{total_count})")
            return True
        else:
            step.status = StepStatus.FAILED
            step.error = f"병렬 실행 일부 실패: {success_count}/{total_count}"
            logger.error(f"❌ 병렬 실행 실패: {step.name} ({success_count}/{total_count})")
            return False
    
    async def _execute_builtin_step(self, step: WorkflowStep) -> bool:
        """내장 명령어 실행"""
        command = step.command or step.name
        
        if command in self.builtin_commands:
            return await self.builtin_commands[command](step)
        else:
            logger.error(f"알 수 없는 내장 명령어: {command}")
            return False
    
    async def _execute_script_step(self, step: WorkflowStep) -> bool:
        """스크립트 실행"""
        if not step.script:
            logger.error("스크립트가 정의되지 않았습니다")
            return False
        
        try:
            # 비동기 프로세스 실행
            process = await asyncio.create_subprocess_shell(
                step.script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 타임아웃과 함께 실행
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=step.timeout
            )
            
            # 결과 저장
            step.output = stdout.decode('utf-8') if stdout else ""
            if stderr:
                step.error = stderr.decode('utf-8')
            
            return process.returncode == 0
            
        except asyncio.TimeoutError:
            step.error = f"스크립트 실행 시간 초과 ({step.timeout}초)"
            return False
        except Exception as e:
            step.error = str(e)
            return False
    
    # 내장 명령어 구현들
    async def _execute_prepare(self, step: WorkflowStep) -> bool:
        """준비 단계 실행"""
        # 실제 준비 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True
    
    async def _execute_build(self, step: WorkflowStep) -> bool:
        """빌드 단계 실행"""
        # 실제 빌드 로직 구현
        target_app = step.metadata.get('target_app')
        if target_app:
            logger.info(f"  📦 빌드 중: {target_app}")
        
        await asyncio.sleep(2)  # 시뮬레이션
        return True
    
    async def _execute_template(self, step: WorkflowStep) -> bool:
        """템플릿 단계 실행"""
        # 실제 템플릿 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True
    
    async def _execute_deploy(self, step: WorkflowStep) -> bool:
        """배포 단계 실행"""
        # 실제 배포 로직 구현
        target_app = step.metadata.get('target_app')
        if target_app:
            logger.info(f"  🚀 배포 중: {target_app}")
        
        await asyncio.sleep(3)  # 시뮬레이션
        return True
    
    async def _execute_validate(self, step: WorkflowStep) -> bool:
        """검증 단계 실행"""
        # 실제 검증 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True
```

### 4. 워크플로우 관리자 구현
```python
# sbkube/utils/workflow_manager.py
from typing import Dict, Any, List, Optional
from pathlib import Path
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
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """사용 가능한 워크플로우 목록"""
        workflows = []
        
        for workflow_file in self.workflows_dir.glob("*.yaml"):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                workflows.append({
                    'name': data.get('name', workflow_file.stem),
                    'description': data.get('description', ''),
                    'version': data.get('version', '1.0'),
                    'steps_count': len(data.get('steps', [])),
                    'file': str(workflow_file)
                })
                
            except Exception as e:
                logger.warning(f"워크플로우 파일 로드 실패 ({workflow_file}): {e}")
        
        return workflows
    
    def load_workflow(self, name: str) -> Optional[Workflow]:
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
            'quick-deploy': {
                'name': 'quick-deploy',
                'description': '빠른 배포 (캐시 활용)',
                'version': '1.0',
                'variables': {
                    'use_cache': True
                },
                'steps': [
                    {
                        'name': 'prepare',
                        'type': 'builtin',
                        'condition': '!cache.exists("charts")'
                    },
                    {
                        'name': 'deploy',
                        'type': 'builtin',
                        'parallel': True,
                        'apps': ['frontend', 'backend']
                    }
                ]
            },
            'full-ci-cd': {
                'name': 'full-ci-cd',
                'description': '전체 CI/CD 파이프라인',
                'version': '1.0',
                'steps': [
                    {
                        'name': 'validate',
                        'type': 'builtin'
                    },
                    {
                        'name': 'test',
                        'type': 'script',
                        'script': 'pytest tests/',
                        'on_failure': 'stop'
                    },
                    {
                        'name': 'build',
                        'type': 'builtin'
                    },
                    {
                        'name': 'security-scan',
                        'type': 'script',
                        'script': 'bandit -r sbkube/',
                        'on_failure': 'continue'
                    },
                    {
                        'name': 'deploy',
                        'type': 'builtin',
                        'condition': 'env.get("ENVIRONMENT") == "production"'
                    },
                    {
                        'name': 'smoke-test',
                        'type': 'script',
                        'script': 'curl -f http://app.example.com/health',
                        'timeout': 60
                    }
                ]
            }
        }
        
        for workflow_name, workflow_data in default_workflows.items():
            workflow_file = self.workflows_dir / f"{workflow_name}.yaml"
            
            if not workflow_file.exists():
                try:
                    with open(workflow_file, 'w', encoding='utf-8') as f:
                        yaml.dump(workflow_data, f, default_flow_style=False, allow_unicode=True)
                except Exception as e:
                    logger.warning(f"기본 워크플로우 생성 실패 ({workflow_name}): {e}")
    
    def _get_builtin_workflow_path(self, name: str) -> Optional[Path]:
        """내장 워크플로우 경로 반환"""
        # 패키지 내 워크플로우 디렉토리
        import sbkube
        package_dir = Path(sbkube.__file__).parent
        builtin_path = package_dir / "workflows" / f"{name}.yaml"
        
        return builtin_path if builtin_path.exists() else None
```

### 5. 워크플로우 명령어 구현
```python
# sbkube/commands/workflow.py
import click
import sys
import asyncio
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sbkube.utils.workflow_manager import WorkflowManager
from sbkube.utils.workflow_engine import WorkflowEngine
from sbkube.utils.logger import logger

console = Console()

@click.group(name="workflow")
def workflow_group():
    """커스텀 워크플로우 관리"""
    pass

@workflow_group.command("list")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
def list_workflows(detailed):
    """사용 가능한 워크플로우 목록"""
    try:
        manager = WorkflowManager()
        workflows = manager.list_workflows()
        
        if not workflows:
            console.print("📋 사용 가능한 워크플로우가 없습니다.")
            return
        
        if detailed:
            _show_detailed_workflows(workflows)
        else:
            _show_simple_workflows(workflows)
            
    except Exception as e:
        logger.error(f"❌ 워크플로우 목록 조회 실패: {e}")
        sys.exit(1)

@workflow_group.command("run")
@click.argument("workflow_name")
@click.option("--var", multiple=True, help="변수 설정 (key=value)")
@click.option("--profile", help="사용할 프로파일")
@click.option("--dry-run", is_flag=True, help="실제 실행하지 않고 계획만 표시")
def run_workflow(workflow_name, var, profile, dry_run):
    """워크플로우 실행"""
    try:
        manager = WorkflowManager()
        workflow = manager.load_workflow(workflow_name)
        
        if not workflow:
            console.print(f"❌ 워크플로우를 찾을 수 없습니다: {workflow_name}")
            sys.exit(1)
        
        # 변수 파싱
        variables = {}
        for v in var:
            if '=' in v:
                key, value = v.split('=', 1)
                variables[key] = value
        
        # 실행 컨텍스트 구성
        context = {
            'profile': profile,
            'variables': variables,
            'workflow_name': workflow_name
        }
        
        if dry_run:
            _show_workflow_plan(workflow, context)
            return
        
        # 워크플로우 실행
        engine = WorkflowEngine(console)
        success = asyncio.run(engine.execute_workflow(workflow, context))
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ 워크플로우 실행 실패: {e}")
        sys.exit(1)

@workflow_group.command("show")
@click.argument("workflow_name")
def show_workflow(workflow_name):
    """워크플로우 상세 정보 표시"""
    try:
        manager = WorkflowManager()
        workflow = manager.load_workflow(workflow_name)
        
        if not workflow:
            console.print(f"❌ 워크플로우를 찾을 수 없습니다: {workflow_name}")
            sys.exit(1)
        
        _show_workflow_details(workflow)
        
    except Exception as e:
        logger.error(f"❌ 워크플로우 조회 실패: {e}")
        sys.exit(1)

def _show_simple_workflows(workflows: List[Dict[str, Any]]):
    """간단한 워크플로우 목록"""
    table = Table(title="🔄 사용 가능한 워크플로우")
    table.add_column("이름", style="cyan")
    table.add_column("설명", style="green")
    table.add_column("단계 수", justify="center")
    table.add_column("버전", justify="center")
    
    for workflow in workflows:
        table.add_row(
            workflow["name"],
            workflow["description"],
            str(workflow["steps_count"]),
            workflow["version"]
        )
    
    console.print(table)

def _show_detailed_workflows(workflows: List[Dict[str, Any]]):
    """상세한 워크플로우 목록"""
    for workflow in workflows:
        panel_content = f"""[bold]설명:[/bold] {workflow['description']}
[bold]버전:[/bold] {workflow['version']}
[bold]단계 수:[/bold] {workflow['steps_count']}
[bold]파일:[/bold] {workflow['file']}"""
        
        console.print(Panel(
            panel_content,
            title=f"🔄 {workflow['name']}",
            expand=False
        ))

def _show_workflow_plan(workflow, context: Dict[str, Any]):
    """워크플로우 실행 계획 표시"""
    console.print(f"🔍 워크플로우 '{workflow.name}' 실행 계획:")
    console.print("━" * 50)
    
    for i, step in enumerate(workflow.steps, 1):
        step_info = f"{i}. {step.name}"
        
        if step.type.value != "builtin":
            step_info += f" ({step.type.value})"
        
        if step.condition:
            step_info += f" [조건: {step.condition}]"
        
        if step.parallel and step.apps:
            step_info += f" [병렬: {', '.join(step.apps)}]"
        
        console.print(step_info)
        
        if step.script:
            console.print(f"   스크립트: {step.script}")
        elif step.command:
            console.print(f"   명령어: {step.command}")
    
    console.print(f"\n💡 실제 실행하려면 --dry-run 옵션을 제거하세요.")

def _show_workflow_details(workflow):
    """워크플로우 상세 정보"""
    console.print(f"🔄 워크플로우: {workflow.name}")
    console.print(f"📝 설명: {workflow.description}")
    console.print(f"🏷️  버전: {workflow.version}")
    
    if workflow.variables:
        console.print("\n📊 변수:")
        for key, value in workflow.variables.items():
            console.print(f"  {key}: {value}")
    
    console.print("\n📋 단계:")
    for i, step in enumerate(workflow.steps, 1):
        console.print(f"  {i}. {step.name}")
        if step.condition:
            console.print(f"     조건: {step.condition}")
        if step.parallel and step.apps:
            console.print(f"     병렬 실행: {', '.join(step.apps)}")
        if step.script:
            console.print(f"     스크립트: {step.script}")
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_workflow_engine.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from sbkube.models.workflow_model import Workflow, WorkflowStep, StepType, StepStatus
from sbkube.utils.workflow_engine import WorkflowEngine
from sbkube.utils.condition_evaluator import ConditionEvaluator

class TestWorkflowEngine:
    def test_workflow_model_creation(self):
        """워크플로우 모델 생성 테스트"""
        step = WorkflowStep(
            name="test-step",
            type=StepType.BUILTIN,
            command="prepare"
        )
        
        workflow = Workflow(
            name="test-workflow",
            description="테스트 워크플로우",
            steps=[step]
        )
        
        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].name == "test-step"
    
    def test_condition_evaluator(self):
        """조건 평가기 테스트"""
        evaluator = ConditionEvaluator({
            'env': 'production',
            'cache': {'charts': True}
        })
        
        # 기본 조건
        assert evaluator.evaluate("true") == True
        assert evaluator.evaluate("false") == False
        
        # 변수 참조
        assert evaluator.evaluate("context.get('env') == 'production'") == True
        
        # 캐시 확인
        assert evaluator.evaluate("cache.exists('charts')") == True
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """워크플로우 실행 테스트"""
        step1 = WorkflowStep(name="step1", type=StepType.BUILTIN, command="prepare")
        step2 = WorkflowStep(name="step2", type=StepType.BUILTIN, command="build")
        
        workflow = Workflow(
            name="test-workflow",
            steps=[step1, step2]
        )
        
        engine = WorkflowEngine()
        
        # Mock 내장 명령어
        with patch.object(engine, '_execute_prepare', return_value=True), \
             patch.object(engine, '_execute_build', return_value=True):
            
            success = await engine.execute_workflow(workflow)
            
            assert success == True
            assert workflow.status == StepStatus.COMPLETED
            assert step1.status == StepStatus.COMPLETED
            assert step2.status == StepStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """병렬 실행 테스트"""
        step = WorkflowStep(
            name="parallel-build",
            type=StepType.BUILTIN,
            command="build",
            parallel=True,
            apps=["app1", "app2", "app3"]
        )
        
        workflow = Workflow(name="test", steps=[step])
        engine = WorkflowEngine()
        
        with patch.object(engine, '_execute_build', return_value=True):
            success = await engine.execute_workflow(workflow)
            
            assert success == True
            assert step.status == StepStatus.COMPLETED
```

## ✅ 완료 기준

- [ ] 워크플로우 모델 정의 (Workflow, WorkflowStep)
- [ ] 조건 평가 시스템 구현
- [ ] 워크플로우 실행 엔진 구현
- [ ] 병렬 실행 및 타임아웃 지원
- [ ] 워크플로우 관리자 구현
- [ ] 기본 워크플로우 템플릿 제공
- [ ] 워크플로우 명령어 구현
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 워크플로우 목록 조회
sbkube workflow list
sbkube workflow list --detailed

# 워크플로우 실행
sbkube workflow run quick-deploy
sbkube workflow run full-ci-cd --profile production

# 실행 계획 확인
sbkube workflow run quick-deploy --dry-run

# 워크플로우 상세 정보
sbkube workflow show full-ci-cd

# 변수와 함께 실행
sbkube workflow run quick-deploy --var env=staging --var debug=true

# 테스트 실행
pytest tests/unit/utils/test_workflow_engine.py -v
```

## 📝 예상 결과

```bash
$ sbkube workflow run quick-deploy
🚀 워크플로우 'quick-deploy' 실행 시작
⏭️  단계 건너뛰기: prepare (조건 불만족)
🔄 병렬 실행: deploy (2개 앱)
  📦 배포 중: frontend
  📦 배포 중: backend
✅ 병렬 실행 완료: deploy (2/2)
✅ 워크플로우 실행 완료

$ sbkube workflow list
🔄 사용 가능한 워크플로우
┌──────────────┬─────────────────────────┬────────┬────────┐
│ 이름         │ 설명                    │ 단계 수│ 버전   │
├──────────────┼─────────────────────────┼────────┼────────┤
│ quick-deploy │ 빠른 배포 (캐시 활용)   │    2   │  1.0   │
│ full-ci-cd   │ 전체 CI/CD 파이프라인   │    6   │  1.0   │
└──────────────┴─────────────────────────┴────────┴────────┘
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `014-interactive-assistant-system.md` - 대화형 사용자 지원 시스템 구현