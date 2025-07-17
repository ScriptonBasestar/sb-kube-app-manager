---
phase: 3
order: 14
source_plan: /tasks/plan/phase3-intelligent-features.md
priority: medium
tags: [interactive-assistant, troubleshooting, user-support]
estimated_days: 2
depends_on: [013-custom-workflow-engine]
---

# 📌 작업: 대화형 사용자 지원 시스템 구현

## 🎯 목표
사용자 문제를 대화형으로 진단하고 해결하는 인터랙티브 지원 시스템을 구현합니다. 단계적 문제 해결과 컨텍스트 인식 제안을 제공합니다.

## 📋 작업 내용

### 1. 대화형 지원 시스템 기본 구조
```python
# sbkube/utils/interactive_assistant.py
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import re
from abc import ABC, abstractmethod

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from sbkube.utils.logger import logger

class QuestionType(Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    YES_NO = "yes_no"
    NUMERIC = "numeric"

@dataclass
class DialogChoice:
    """대화 선택지"""
    key: str
    text: str
    description: str = ""
    action: Optional[Callable] = None
    next_question: Optional[str] = None

@dataclass
class DialogQuestion:
    """대화 질문"""
    id: str
    text: str
    type: QuestionType
    choices: List[DialogChoice] = field(default_factory=list)
    default_answer: Any = None
    validation: Optional[Callable] = None
    context_filter: Optional[Callable] = None  # 컨텍스트 기반 필터링
    
    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """컨텍스트에 적용 가능한지 확인"""
        if self.context_filter:
            return self.context_filter(context)
        return True

class InteractiveSession:
    """대화형 세션"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.questions: Dict[str, DialogQuestion] = {}
        self.current_question_id: Optional[str] = None
        
        # 기본 질문들 등록
        self._register_default_questions()
    
    def start_session(self, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """대화형 세션 시작"""
        self.context.update(initial_context or {})
        
        self.console.print("🤖 SBKube 지원 시스템에 오신 것을 환영합니다!")
        self.console.print("문제를 해결할 수 있도록 몇 가지 질문을 드리겠습니다.\n")
        
        # 초기 질문 결정
        self.current_question_id = self._determine_initial_question()
        
        # 대화 진행
        while self.current_question_id:
            next_question = self._ask_question(self.current_question_id)
            self.current_question_id = next_question
        
        return self._generate_solution()
    
    def add_question(self, question: DialogQuestion):
        """질문 추가"""
        self.questions[question.id] = question
    
    def _ask_question(self, question_id: str) -> Optional[str]:
        """질문하기"""
        question = self.questions.get(question_id)
        if not question:
            return None
        
        # 컨텍스트 적용성 확인
        if not question.is_applicable(self.context):
            return None
        
        self.console.print(f"\n❓ {question.text}")
        
        # 질문 타입별 처리
        if question.type == QuestionType.SINGLE_CHOICE:
            answer = self._handle_single_choice(question)
        elif question.type == QuestionType.MULTIPLE_CHOICE:
            answer = self._handle_multiple_choice(question)
        elif question.type == QuestionType.YES_NO:
            answer = self._handle_yes_no(question)
        elif question.type == QuestionType.TEXT_INPUT:
            answer = self._handle_text_input(question)
        elif question.type == QuestionType.NUMERIC:
            answer = self._handle_numeric_input(question)
        else:
            return None
        
        # 답변 기록
        self.history.append({
            'question_id': question_id,
            'question': question.text,
            'answer': answer,
            'timestamp': self._get_timestamp()
        })
        
        # 답변 기반 컨텍스트 업데이트
        self._update_context(question_id, answer)
        
        # 다음 질문 결정
        return self._determine_next_question(question, answer)
    
    def _handle_single_choice(self, question: DialogQuestion) -> Optional[DialogChoice]:
        """단일 선택 처리"""
        if not question.choices:
            return None
        
        # 선택지 표시
        for i, choice in enumerate(question.choices, 1):
            description = f" - {choice.description}" if choice.description else ""
            self.console.print(f"  {i}. {choice.text}{description}")
        
        # 사용자 입력
        while True:
            try:
                choice_num = IntPrompt.ask(
                    "선택하세요",
                    default=1,
                    show_default=True
                )
                
                if 1 <= choice_num <= len(question.choices):
                    selected_choice = question.choices[choice_num - 1]
                    
                    # 액션 실행
                    if selected_choice.action:
                        selected_choice.action(self.context)
                    
                    return selected_choice
                else:
                    self.console.print("❌ 올바른 번호를 선택해주세요.")
                    
            except (ValueError, KeyboardInterrupt):
                self.console.print("❌ 올바른 번호를 입력해주세요.")
    
    def _handle_yes_no(self, question: DialogQuestion) -> bool:
        """예/아니오 처리"""
        return Confirm.ask(question.text, default=question.default_answer)
    
    def _handle_text_input(self, question: DialogQuestion) -> str:
        """텍스트 입력 처리"""
        while True:
            answer = Prompt.ask("답변", default=question.default_answer)
            
            if question.validation:
                if question.validation(answer):
                    return answer
                else:
                    self.console.print("❌ 올바른 형식으로 입력해주세요.")
            else:
                return answer
    
    def _handle_numeric_input(self, question: DialogQuestion) -> int:
        """숫자 입력 처리"""
        return IntPrompt.ask("숫자를 입력하세요", default=question.default_answer)
    
    def _determine_initial_question(self) -> str:
        """초기 질문 결정"""
        # 컨텍스트에 따른 초기 질문 선택
        if self.context.get('error_type'):
            return 'specific_error_diagnosis'
        elif self.context.get('command_failed'):
            return 'command_failure_analysis'
        else:
            return 'general_problem_category'
    
    def _determine_next_question(self, question: DialogQuestion, answer: Any) -> Optional[str]:
        """다음 질문 결정"""
        if isinstance(answer, DialogChoice) and answer.next_question:
            return answer.next_question
        
        # 컨텍스트 기반 다음 질문 결정
        return self._smart_next_question_selection()
    
    def _smart_next_question_selection(self) -> Optional[str]:
        """지능적 다음 질문 선택"""
        problem_category = self.context.get('problem_category')
        
        if problem_category == 'network':
            if 'network_details' not in self.context:
                return 'network_details'
        elif problem_category == 'configuration':
            if 'config_details' not in self.context:
                return 'config_details'
        elif problem_category == 'permissions':
            if 'permission_details' not in self.context:
                return 'permission_details'
        
        return None  # 질문 종료
    
    def _update_context(self, question_id: str, answer: Any):
        """컨텍스트 업데이트"""
        if question_id == 'general_problem_category' and isinstance(answer, DialogChoice):
            self.context['problem_category'] = answer.key
        elif question_id == 'network_details':
            self.context['network_details'] = answer
        elif question_id == 'config_details':
            self.context['config_details'] = answer
        # 추가 컨텍스트 업데이트 로직
    
    def _generate_solution(self) -> Dict[str, Any]:
        """해결책 생성"""
        solution = {
            'recommendations': [],
            'commands': [],
            'next_steps': [],
            'context': self.context.copy(),
            'session_id': self._generate_session_id()
        }
        
        problem_category = self.context.get('problem_category')
        
        if problem_category == 'network':
            solution.update(self._generate_network_solution())
        elif problem_category == 'configuration':
            solution.update(self._generate_config_solution())
        elif problem_category == 'permissions':
            solution.update(self._generate_permission_solution())
        elif problem_category == 'unknown':
            solution.update(self._generate_diagnostic_solution())
        
        self._display_solution(solution)
        return solution
    
    def _generate_network_solution(self) -> Dict[str, Any]:
        """네트워크 문제 해결책"""
        return {
            'recommendations': [
                "네트워크 연결 상태를 확인하세요",
                "프록시 설정을 점검하세요",
                "방화벽 규칙을 확인하세요"
            ],
            'commands': [
                "ping google.com",
                "kubectl cluster-info",
                "curl -I https://charts.bitnami.com"
            ],
            'next_steps': [
                "네트워크 관리자에게 문의",
                "VPN 연결 확인",
                "DNS 설정 점검"
            ]
        }
    
    def _generate_config_solution(self) -> Dict[str, Any]:
        """설정 문제 해결책"""
        return {
            'recommendations': [
                "설정 파일 문법을 확인하세요",
                "필수 필드가 누락되지 않았는지 점검하세요",
                "값의 타입이 올바른지 확인하세요"
            ],
            'commands': [
                "sbkube doctor",
                "sbkube validate",
                "sbkube fix --dry-run"
            ],
            'next_steps': [
                "설정 파일 백업 후 수정",
                "예제 설정 파일 참조",
                "문서 재검토"
            ]
        }
    
    def _generate_permission_solution(self) -> Dict[str, Any]:
        """권한 문제 해결책"""
        return {
            'recommendations': [
                "Kubernetes 클러스터 권한을 확인하세요",
                "서비스 계정 설정을 점검하세요",
                "RBAC 규칙을 검토하세요"
            ],
            'commands': [
                "kubectl auth can-i '*' '*'",
                "kubectl get serviceaccounts",
                "kubectl describe clusterrolebinding"
            ],
            'next_steps': [
                "클러스터 관리자에게 권한 요청",
                "서비스 계정 재설정",
                "kubeconfig 파일 확인"
            ]
        }
    
    def _generate_diagnostic_solution(self) -> Dict[str, Any]:
        """진단 기반 해결책"""
        return {
            'recommendations': [
                "종합 진단을 실행하세요",
                "로그 파일을 확인하세요",
                "최근 변경사항을 검토하세요"
            ],
            'commands': [
                "sbkube doctor --detailed",
                "sbkube history --failures",
                "kubectl get events --sort-by='.lastTimestamp'"
            ],
            'next_steps': [
                "문제 재현해보기",
                "커뮤니티 포럼 검색",
                "GitHub 이슈 확인"
            ]
        }
    
    def _display_solution(self, solution: Dict[str, Any]):
        """해결책 표시"""
        self.console.print("\n🎯 추천 해결책")
        self.console.print("=" * 50)
        
        if solution['recommendations']:
            self.console.print("\n💡 권장사항:")
            for rec in solution['recommendations']:
                self.console.print(f"  • {rec}")
        
        if solution['commands']:
            self.console.print("\n🔧 실행할 명령어:")
            for cmd in solution['commands']:
                self.console.print(f"  $ {cmd}")
        
        if solution['next_steps']:
            self.console.print("\n📋 다음 단계:")
            for step in solution['next_steps']:
                self.console.print(f"  • {step}")
        
        session_id = solution.get('session_id', 'unknown')
        self.console.print(f"\n📋 세션 ID: {session_id}")
        self.console.print("이 ID로 나중에 이 세션을 참조할 수 있습니다.")
    
    def _register_default_questions(self):
        """기본 질문들 등록"""
        # 일반적인 문제 분류
        self.add_question(DialogQuestion(
            id='general_problem_category',
            text='어떤 종류의 문제가 발생했나요?',
            type=QuestionType.SINGLE_CHOICE,
            choices=[
                DialogChoice('network', '네트워크 연결 문제', 
                           '인터넷 연결, DNS, 방화벽 관련', next_question='network_details'),
                DialogChoice('configuration', '설정 파일 오류',
                           'config.yaml, values 파일 문제', next_question='config_details'),
                DialogChoice('permissions', '권한 관련 문제',
                           'Kubernetes 권한, 인증 문제', next_question='permission_details'),
                DialogChoice('unknown', '잘 모르겠음 (자동 진단)',
                           '문제를 정확히 파악하기 어려움', next_question='auto_diagnosis')
            ]
        ))
        
        # 네트워크 상세 문제
        self.add_question(DialogQuestion(
            id='network_details',
            text='네트워크 문제의 구체적인 증상은 무엇인가요?',
            type=QuestionType.TEXT_INPUT,
            default_answer='연결 시간 초과 오류'
        ))
        
        # 설정 상세 문제
        self.add_question(DialogQuestion(
            id='config_details',
            text='어떤 설정 파일에서 문제가 발생했나요?',
            type=QuestionType.SINGLE_CHOICE,
            choices=[
                DialogChoice('config_yaml', 'config.yaml'),
                DialogChoice('values_files', 'values 파일들'),
                DialogChoice('sources_yaml', 'sources.yaml'),
                DialogChoice('unknown_config', '정확히 모르겠음')
            ]
        ))
        
        # 권한 상세 문제
        self.add_question(DialogQuestion(
            id='permission_details',
            text='어떤 작업에서 권한 오류가 발생했나요?',
            type=QuestionType.TEXT_INPUT,
            default_answer='kubectl 명령어 실행 시'
        ))
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        import uuid
        return str(uuid.uuid4())[:8]
```

### 2. 컨텍스트 인식 제안 시스템
```python
# sbkube/utils/context_aware_suggestions.py
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

class ContextAwareSuggestions:
    """컨텍스트 인식 제안 시스템"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.suggestion_rules = self._load_suggestion_rules()
    
    def get_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """컨텍스트 기반 제안 생성"""
        suggestions = []
        
        # 오류 메시지 기반 제안
        if context.get('error_message'):
            suggestions.extend(self._suggest_from_error(context['error_message']))
        
        # 실행 히스토리 기반 제안
        if context.get('recent_failures'):
            suggestions.extend(self._suggest_from_history(context['recent_failures']))
        
        # 프로젝트 상태 기반 제안
        if context.get('project_status'):
            suggestions.extend(self._suggest_from_project_status(context['project_status']))
        
        # 환경 기반 제안
        suggestions.extend(self._suggest_from_environment())
        
        return self._rank_suggestions(suggestions)
    
    def _suggest_from_error(self, error_message: str) -> List[Dict[str, Any]]:
        """오류 메시지 기반 제안"""
        suggestions = []
        
        error_patterns = {
            r'connection.*refused': {
                'title': 'Kubernetes 클러스터 연결 확인',
                'description': '클러스터가 실행 중인지 확인하고 kubeconfig를 점검하세요',
                'commands': ['kubectl cluster-info', 'kubectl config current-context'],
                'priority': 'high'
            },
            r'namespace.*not found': {
                'title': '네임스페이스 생성',
                'description': '필요한 네임스페이스를 생성하세요',
                'commands': ['kubectl create namespace <namespace-name>'],
                'priority': 'medium'
            },
            r'helm.*not found': {
                'title': 'Helm 설치',
                'description': 'Helm이 설치되지 않았습니다',
                'commands': ['curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash'],
                'priority': 'high'
            },
            r'permission denied': {
                'title': '권한 확인',
                'description': 'Kubernetes 클러스터에 대한 권한을 확인하세요',
                'commands': ['kubectl auth can-i "*" "*"'],
                'priority': 'high'
            }
        }
        
        for pattern, suggestion in error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_from_history(self, recent_failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """실행 히스토리 기반 제안"""
        suggestions = []
        
        # 반복되는 실패 패턴 분석
        failure_patterns = {}
        for failure in recent_failures:
            step = failure.get('step', 'unknown')
            failure_patterns[step] = failure_patterns.get(step, 0) + 1
        
        # 가장 자주 실패하는 단계에 대한 제안
        if failure_patterns:
            most_failed_step = max(failure_patterns, key=failure_patterns.get)
            failure_count = failure_patterns[most_failed_step]
            
            if failure_count >= 3:
                suggestions.append({
                    'title': f'{most_failed_step} 단계 반복 실패 해결',
                    'description': f'{most_failed_step} 단계에서 {failure_count}번 실패했습니다. 설정을 점검해보세요.',
                    'commands': [f'sbkube doctor --check {most_failed_step}'],
                    'priority': 'high'
                })
        
        return suggestions
    
    def _suggest_from_project_status(self, project_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """프로젝트 상태 기반 제안"""
        suggestions = []
        
        # 설정 파일 검사
        if not (self.base_dir / "config" / "config.yaml").exists():
            suggestions.append({
                'title': '프로젝트 초기화',
                'description': '설정 파일이 없습니다. 프로젝트를 초기화하세요.',
                'commands': ['sbkube init'],
                'priority': 'high'
            })
        
        # 환경별 설정 확인
        config_files = list((self.base_dir / "config").glob("config-*.yaml"))
        if not config_files:
            suggestions.append({
                'title': '환경별 설정 추가',
                'description': '환경별 배포를 위한 프로파일 설정을 추가하세요.',
                'commands': ['cp config/config.yaml config/config-production.yaml'],
                'priority': 'medium'
            })
        
        return suggestions
    
    def _suggest_from_environment(self) -> List[Dict[str, Any]]:
        """환경 기반 제안"""
        suggestions = []
        
        # Docker 확인
        import subprocess
        try:
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, timeout=5)
            if result.returncode != 0:
                suggestions.append({
                    'title': 'Docker 설치 또는 시작',
                    'description': 'Docker가 설치되지 않았거나 실행되지 않고 있습니다.',
                    'commands': ['docker version'],
                    'priority': 'medium'
                })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            suggestions.append({
                'title': 'Docker 설치',
                'description': 'Docker가 설치되지 않았습니다.',
                'commands': ['# Docker 설치 가이드를 참조하세요'],
                'priority': 'low'
            })
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """제안 우선순위 정렬"""
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        
        return sorted(suggestions, 
                     key=lambda x: priority_order.get(x.get('priority', 'low'), 1), 
                     reverse=True)
    
    def _load_suggestion_rules(self) -> Dict[str, Any]:
        """제안 규칙 로드"""
        # 추후 외부 파일에서 로드 가능
        return {}
```

### 3. Assistant 명령어 구현
```python
# sbkube/commands/assistant.py
import click
import sys
from rich.console import Console

from sbkube.utils.interactive_assistant import InteractiveSession
from sbkube.utils.context_aware_suggestions import ContextAwareSuggestions
from sbkube.utils.logger import logger

console = Console()

@click.command(name="assistant")
@click.option("--context", help="문제 컨텍스트 (예: 'network', 'config', 'permissions')")
@click.option("--error", help="발생한 오류 메시지")
@click.option("--quick", is_flag=True, help="빠른 제안만 표시 (대화형 없음)")
def cmd(context, error, quick):
    """대화형 문제 해결 도우미
    
    SBKube 사용 중 발생한 문제를 대화형으로 진단하고 해결 방안을 제시합니다.
    
    \\b
    사용 예시:
        sbkube assistant                           # 대화형 문제 해결
        sbkube assistant --context network         # 네트워크 문제로 시작
        sbkube assistant --error "connection refused"  # 특정 오류 분석
        sbkube assistant --quick                   # 빠른 제안만 표시
    """
    
    try:
        # 초기 컨텍스트 구성
        initial_context = {}
        
        if context:
            initial_context['problem_category'] = context
        
        if error:
            initial_context['error_message'] = error
        
        # 빠른 제안 모드
        if quick:
            _show_quick_suggestions(initial_context)
            return
        
        # 대화형 세션 시작
        session = InteractiveSession(console)
        solution = session.start_session(initial_context)
        
        # 세션 결과 저장 (선택적)
        _save_session_result(solution)
        
    except KeyboardInterrupt:
        console.print("\n\n👋 언제든 다시 도움이 필요하면 sbkube assistant를 실행하세요!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 지원 시스템 오류: {e}")
        sys.exit(1)

def _show_quick_suggestions(context: Dict[str, Any]):
    """빠른 제안 표시"""
    suggestions_system = ContextAwareSuggestions()
    suggestions = suggestions_system.get_suggestions(context)
    
    if not suggestions:
        console.print("💡 현재 컨텍스트에 대한 특별한 제안이 없습니다.")
        console.print("더 구체적인 도움을 받으려면 대화형 모드를 사용하세요: sbkube assistant")
        return
    
    console.print("💡 빠른 제안:")
    console.print("=" * 40)
    
    for i, suggestion in enumerate(suggestions[:5], 1):  # 상위 5개만 표시
        priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(
            suggestion.get('priority', 'low'), '🔵'
        )
        
        console.print(f"\n{priority_icon} {i}. {suggestion['title']}")
        console.print(f"   {suggestion['description']}")
        
        if suggestion.get('commands'):
            console.print("   권장 명령어:")
            for cmd in suggestion['commands']:
                console.print(f"     $ {cmd}")

def _save_session_result(solution: Dict[str, Any]):
    """세션 결과 저장"""
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # 세션 히스토리 디렉토리
        history_dir = Path(".sbkube") / "assistant_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 세션 파일 저장
        session_id = solution.get('session_id', 'unknown')
        session_file = history_dir / f"session_{session_id}.json"
        
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'solution': solution
        }
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # 최근 세션 링크 업데이트
        latest_file = history_dir / "latest_session.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        # 저장 실패는 치명적이지 않음
        logger.warning(f"세션 결과 저장 실패: {e}")

@click.command(name="assistant-history")
@click.option("--limit", default=10, help="표시할 세션 수")
def history_cmd(limit):
    """지원 세션 히스토리 조회"""
    try:
        from pathlib import Path
        import json
        
        history_dir = Path(".sbkube") / "assistant_history"
        
        if not history_dir.exists():
            console.print("📋 저장된 지원 세션이 없습니다.")
            return
        
        # 세션 파일들 로드
        session_files = sorted(
            history_dir.glob("session_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        if not session_files:
            console.print("📋 저장된 지원 세션이 없습니다.")
            return
        
        console.print(f"📋 최근 {len(session_files)}개 지원 세션:")
        console.print("=" * 50)
        
        for session_file in session_files:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            session_id = session_data.get('session_id', 'unknown')
            timestamp = session_data.get('timestamp', 'unknown')
            solution = session_data.get('solution', {})
            
            console.print(f"\n🔍 세션 {session_id} ({timestamp[:19]})")
            
            if solution.get('recommendations'):
                console.print(f"   권장사항: {len(solution['recommendations'])}개")
            if solution.get('commands'):
                console.print(f"   명령어: {len(solution['commands'])}개")
                
    except Exception as e:
        logger.error(f"❌ 히스토리 조회 실패: {e}")
        sys.exit(1)
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_interactive_assistant.py
import pytest
from unittest.mock import patch, MagicMock

from sbkube.utils.interactive_assistant import InteractiveSession, DialogQuestion, DialogChoice, QuestionType
from sbkube.utils.context_aware_suggestions import ContextAwareSuggestions

class TestInteractiveAssistant:
    def test_dialog_question_creation(self):
        """대화 질문 생성 테스트"""
        choice = DialogChoice("test_key", "테스트 선택", "설명")
        question = DialogQuestion(
            id="test_question",
            text="테스트 질문입니다",
            type=QuestionType.SINGLE_CHOICE,
            choices=[choice]
        )
        
        assert question.id == "test_question"
        assert len(question.choices) == 1
        assert question.choices[0].key == "test_key"
    
    def test_context_aware_suggestions(self):
        """컨텍스트 인식 제안 테스트"""
        suggestions_system = ContextAwareSuggestions()
        
        # 네트워크 오류 컨텍스트
        context = {
            'error_message': 'connection refused when connecting to kubernetes'
        }
        
        suggestions = suggestions_system.get_suggestions(context)
        
        # 네트워크 관련 제안이 포함되어야 함
        assert len(suggestions) > 0
        network_suggestions = [s for s in suggestions if 'cluster' in s['title'].lower()]
        assert len(network_suggestions) > 0
    
    @patch('rich.prompt.IntPrompt.ask')
    @patch('rich.console.Console.print')
    def test_interactive_session_single_choice(self, mock_print, mock_ask):
        """대화형 세션 단일 선택 테스트"""
        mock_ask.return_value = 1  # 첫 번째 선택
        
        session = InteractiveSession()
        
        # 테스트 질문 추가
        test_question = DialogQuestion(
            id="test_single_choice",
            text="테스트 선택 질문",
            type=QuestionType.SINGLE_CHOICE,
            choices=[
                DialogChoice("option1", "옵션 1"),
                DialogChoice("option2", "옵션 2")
            ]
        )
        
        session.add_question(test_question)
        
        # 질문 실행
        result = session._ask_question("test_single_choice")
        
        # 첫 번째 선택지가 선택되었는지 확인
        assert session.history[-1]['answer'].key == "option1"
    
    def test_suggestion_ranking(self):
        """제안 우선순위 테스트"""
        suggestions_system = ContextAwareSuggestions()
        
        test_suggestions = [
            {'title': 'Low Priority', 'priority': 'low'},
            {'title': 'High Priority', 'priority': 'high'},
            {'title': 'Medium Priority', 'priority': 'medium'}
        ]
        
        ranked = suggestions_system._rank_suggestions(test_suggestions)
        
        # 높은 우선순위가 먼저 와야 함
        assert ranked[0]['priority'] == 'high'
        assert ranked[1]['priority'] == 'medium'
        assert ranked[2]['priority'] == 'low'
```

## ✅ 완료 기준

- [ ] InteractiveSession 및 대화형 질문 시스템 구현
- [ ] 컨텍스트 인식 제안 시스템 구현
- [ ] 다양한 질문 타입 지원 (선택, 입력, 예/아니오)
- [ ] 오류 메시지 기반 자동 제안
- [ ] sbkube assistant 명령어 구현
- [ ] 세션 히스토리 관리
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 대화형 문제 해결
sbkube assistant

# 특정 컨텍스트로 시작
sbkube assistant --context network

# 오류 메시지 분석
sbkube assistant --error "connection refused"

# 빠른 제안만 표시
sbkube assistant --quick

# 지원 세션 히스토리
sbkube assistant-history

# 테스트 실행
pytest tests/unit/utils/test_interactive_assistant.py -v
```

## 📝 예상 결과

```
🤖 SBKube 지원 시스템에 오신 것을 환영합니다!
문제를 해결할 수 있도록 몇 가지 질문을 드리겠습니다.

❓ 어떤 종류의 문제가 발생했나요?
  1. 네트워크 연결 문제 - 인터넷 연결, DNS, 방화벽 관련
  2. 설정 파일 오류 - config.yaml, values 파일 문제
  3. 권한 관련 문제 - Kubernetes 권한, 인증 문제
  4. 잘 모르겠음 (자동 진단) - 문제를 정확히 파악하기 어려움

선택하세요 [1]: 1

❓ 네트워크 문제의 구체적인 증상은 무엇인가요?
답변 [연결 시간 초과 오류]: kubectl 명령어 실행 시 connection refused

🎯 추천 해결책
==================================================

💡 권장사항:
  • 네트워크 연결 상태를 확인하세요
  • 프록시 설정을 점검하세요
  • 방화벽 규칙을 확인하세요

🔧 실행할 명령어:
  $ ping google.com
  $ kubectl cluster-info
  $ curl -I https://charts.bitnami.com

📋 다음 단계:
  • 네트워크 관리자에게 문의
  • VPN 연결 확인
  • DNS 설정 점검

📋 세션 ID: a1b2c3d4
이 ID로 나중에 이 세션을 참조할 수 있습니다.
```

## 🔄 다음 단계

이 작업 완료 후 Phase 3가 완료됩니다. 전체 ToDo 변환 작업을 마무리하고 정리하겠습니다.