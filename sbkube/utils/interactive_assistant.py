from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt


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
    action: Callable | None = None
    next_question: str | None = None


@dataclass
class DialogQuestion:
    """대화 질문"""

    id: str
    text: str
    type: QuestionType
    choices: list[DialogChoice] = field(default_factory=list)
    default_answer: Any = None
    validation: Callable | None = None
    context_filter: Callable | None = None  # 컨텍스트 기반 필터링

    def is_applicable(self, context: dict[str, Any]) -> bool:
        """컨텍스트에 적용 가능한지 확인"""
        if self.context_filter:
            return self.context_filter(context)
        return True


class InteractiveSession:
    """대화형 세션"""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.context: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self.questions: dict[str, DialogQuestion] = {}
        self.current_question_id: str | None = None

        # 기본 질문들 등록
        self._register_default_questions()

    def start_session(self, initial_context: dict[str, Any] = None) -> dict[str, Any]:
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

    def _ask_question(self, question_id: str) -> str | None:
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
        self.history.append(
            {
                "question_id": question_id,
                "question": question.text,
                "answer": answer,
                "timestamp": self._get_timestamp(),
            }
        )

        # 답변 기반 컨텍스트 업데이트
        self._update_context(question_id, answer)

        # 다음 질문 결정
        return self._determine_next_question(question, answer)

    def _handle_single_choice(self, question: DialogQuestion) -> DialogChoice | None:
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
                choice_num = IntPrompt.ask("선택하세요", default=1, show_default=True)

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

    def _handle_multiple_choice(self, question: DialogQuestion) -> list[DialogChoice]:
        """다중 선택 처리"""
        if not question.choices:
            return []

        # 선택지 표시
        for i, choice in enumerate(question.choices, 1):
            description = f" - {choice.description}" if choice.description else ""
            self.console.print(f"  {i}. {choice.text}{description}")

        self.console.print(
            "\n여러 항목을 선택하려면 번호를 쉼표로 구분하여 입력하세요 (예: 1,3,5)"
        )

        while True:
            try:
                user_input = Prompt.ask("선택하세요", default="1")
                choice_nums = [int(x.strip()) for x in user_input.split(",")]

                selected_choices = []
                for num in choice_nums:
                    if 1 <= num <= len(question.choices):
                        selected_choices.append(question.choices[num - 1])
                    else:
                        self.console.print(f"❌ 올바르지 않은 번호: {num}")
                        break
                else:
                    return selected_choices

            except (ValueError, KeyboardInterrupt):
                self.console.print("❌ 올바른 형식으로 입력해주세요.")

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
        if self.context.get("error_type"):
            return "specific_error_diagnosis"
        elif self.context.get("command_failed"):
            return "command_failure_analysis"
        else:
            return "general_problem_category"

    def _determine_next_question(
        self, question: DialogQuestion, answer: Any
    ) -> str | None:
        """다음 질문 결정"""
        if isinstance(answer, DialogChoice) and answer.next_question:
            return answer.next_question

        # 컨텍스트 기반 다음 질문 결정
        return self._smart_next_question_selection()

    def _smart_next_question_selection(self) -> str | None:
        """지능적 다음 질문 선택"""
        problem_category = self.context.get("problem_category")

        if problem_category == "network":
            if "network_details" not in self.context:
                return "network_details"
        elif problem_category == "configuration":
            if "config_details" not in self.context:
                return "config_details"
        elif problem_category == "permissions":
            if "permission_details" not in self.context:
                return "permission_details"

        return None  # 질문 종료

    def _update_context(self, question_id: str, answer: Any):
        """컨텍스트 업데이트"""
        if question_id == "general_problem_category" and isinstance(
            answer, DialogChoice
        ):
            self.context["problem_category"] = answer.key
        elif question_id == "network_details":
            self.context["network_details"] = answer
        elif question_id == "config_details":
            self.context["config_details"] = answer
        # 추가 컨텍스트 업데이트 로직

    def _generate_solution(self) -> dict[str, Any]:
        """해결책 생성"""
        solution = {
            "recommendations": [],
            "commands": [],
            "next_steps": [],
            "context": self.context.copy(),
            "session_id": self._generate_session_id(),
        }

        problem_category = self.context.get("problem_category")

        if problem_category == "network":
            solution.update(self._generate_network_solution())
        elif problem_category == "configuration":
            solution.update(self._generate_config_solution())
        elif problem_category == "permissions":
            solution.update(self._generate_permission_solution())
        elif problem_category == "unknown":
            solution.update(self._generate_diagnostic_solution())

        self._display_solution(solution)
        return solution

    def _generate_network_solution(self) -> dict[str, Any]:
        """네트워크 문제 해결책"""
        return {
            "recommendations": [
                "네트워크 연결 상태를 확인하세요",
                "프록시 설정을 점검하세요",
                "방화벽 규칙을 확인하세요",
            ],
            "commands": [
                "ping google.com",
                "kubectl cluster-info",
                "curl -I https://charts.bitnami.com",
            ],
            "next_steps": [
                "네트워크 관리자에게 문의",
                "VPN 연결 확인",
                "DNS 설정 점검",
            ],
        }

    def _generate_config_solution(self) -> dict[str, Any]:
        """설정 문제 해결책"""
        return {
            "recommendations": [
                "설정 파일 문법을 확인하세요",
                "필수 필드가 누락되지 않았는지 점검하세요",
                "값의 타입이 올바른지 확인하세요",
            ],
            "commands": ["sbkube doctor", "sbkube validate", "sbkube fix --dry-run"],
            "next_steps": [
                "설정 파일 백업 후 수정",
                "예제 설정 파일 참조",
                "문서 재검토",
            ],
        }

    def _generate_permission_solution(self) -> dict[str, Any]:
        """권한 문제 해결책"""
        return {
            "recommendations": [
                "Kubernetes 클러스터 권한을 확인하세요",
                "서비스 계정 설정을 점검하세요",
                "RBAC 규칙을 검토하세요",
            ],
            "commands": [
                "kubectl auth can-i '*' '*'",
                "kubectl get serviceaccounts",
                "kubectl describe clusterrolebinding",
            ],
            "next_steps": [
                "클러스터 관리자에게 권한 요청",
                "서비스 계정 재설정",
                "kubeconfig 파일 확인",
            ],
        }

    def _generate_diagnostic_solution(self) -> dict[str, Any]:
        """진단 기반 해결책"""
        return {
            "recommendations": [
                "종합 진단을 실행하세요",
                "로그 파일을 확인하세요",
                "최근 변경사항을 검토하세요",
            ],
            "commands": [
                "sbkube doctor --detailed",
                "sbkube history --failures",
                "kubectl get events --sort-by='.lastTimestamp'",
            ],
            "next_steps": ["문제 재현해보기", "커뮤니티 포럼 검색", "GitHub 이슈 확인"],
        }

    def _display_solution(self, solution: dict[str, Any]):
        """해결책 표시"""
        self.console.print("\n🎯 추천 해결책")
        self.console.print("=" * 50)

        if solution["recommendations"]:
            self.console.print("\n💡 권장사항:")
            for rec in solution["recommendations"]:
                self.console.print(f"  • {rec}")

        if solution["commands"]:
            self.console.print("\n🔧 실행할 명령어:")
            for cmd in solution["commands"]:
                self.console.print(f"  $ {cmd}")

        if solution["next_steps"]:
            self.console.print("\n📋 다음 단계:")
            for step in solution["next_steps"]:
                self.console.print(f"  • {step}")

        session_id = solution.get("session_id", "unknown")
        self.console.print(f"\n📋 세션 ID: {session_id}")
        self.console.print("이 ID로 나중에 이 세션을 참조할 수 있습니다.")

    def _register_default_questions(self):
        """기본 질문들 등록"""
        # 일반적인 문제 분류
        self.add_question(
            DialogQuestion(
                id="general_problem_category",
                text="어떤 종류의 문제가 발생했나요?",
                type=QuestionType.SINGLE_CHOICE,
                choices=[
                    DialogChoice(
                        "network",
                        "네트워크 연결 문제",
                        "인터넷 연결, DNS, 방화벽 관련",
                        next_question="network_details",
                    ),
                    DialogChoice(
                        "configuration",
                        "설정 파일 오류",
                        "config.yaml, values 파일 문제",
                        next_question="config_details",
                    ),
                    DialogChoice(
                        "permissions",
                        "권한 관련 문제",
                        "Kubernetes 권한, 인증 문제",
                        next_question="permission_details",
                    ),
                    DialogChoice(
                        "unknown",
                        "잘 모르겠음 (자동 진단)",
                        "문제를 정확히 파악하기 어려움",
                        next_question="auto_diagnosis",
                    ),
                ],
            )
        )

        # 네트워크 상세 문제
        self.add_question(
            DialogQuestion(
                id="network_details",
                text="네트워크 문제의 구체적인 증상은 무엇인가요?",
                type=QuestionType.TEXT_INPUT,
                default_answer="연결 시간 초과 오류",
            )
        )

        # 설정 상세 문제
        self.add_question(
            DialogQuestion(
                id="config_details",
                text="어떤 설정 파일에서 문제가 발생했나요?",
                type=QuestionType.SINGLE_CHOICE,
                choices=[
                    DialogChoice("config_yaml", "config.yaml"),
                    DialogChoice("values_files", "values 파일들"),
                    DialogChoice("sources_yaml", "sources.yaml"),
                    DialogChoice("unknown_config", "정확히 모르겠음"),
                ],
            )
        )

        # 권한 상세 문제
        self.add_question(
            DialogQuestion(
                id="permission_details",
                text="어떤 작업에서 권한 오류가 발생했나요?",
                type=QuestionType.TEXT_INPUT,
                default_answer="kubectl 명령어 실행 시",
            )
        )

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        import uuid

        return str(uuid.uuid4())[:8]
