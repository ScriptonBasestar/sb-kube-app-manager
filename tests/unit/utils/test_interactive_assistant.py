from unittest.mock import patch

from sbkube.utils.context_aware_suggestions import ContextAwareSuggestions
from sbkube.utils.interactive_assistant import (
    DialogChoice,
    DialogQuestion,
    InteractiveSession,
    QuestionType,
)


class TestInteractiveAssistant:
    def test_dialog_question_creation(self):
        """대화 질문 생성 테스트"""
        choice = DialogChoice("test_key", "테스트 선택", "설명")
        question = DialogQuestion(
            id="test_question",
            text="테스트 질문입니다",
            type=QuestionType.SINGLE_CHOICE,
            choices=[choice],
        )

        assert question.id == "test_question"
        assert len(question.choices) == 1
        assert question.choices[0].key == "test_key"

    def test_context_aware_suggestions(self):
        """컨텍스트 인식 제안 테스트"""
        suggestions_system = ContextAwareSuggestions()

        # 네트워크 오류 컨텍스트
        context = {"error_message": "connection refused when connecting to kubernetes"}

        suggestions = suggestions_system.get_suggestions(context)

        # 네트워크 관련 제안이 포함되어야 함
        assert len(suggestions) > 0
        network_suggestions = [
            s for s in suggestions if "kubernetes" in s["title"].lower()
        ]
        assert len(network_suggestions) > 0

    def test_error_pattern_matching(self):
        """오류 패턴 매칭 테스트"""
        suggestions_system = ContextAwareSuggestions()

        # 권한 오류
        context = {"error_message": "permission denied"}
        suggestions = suggestions_system.get_suggestions(context)

        permission_suggestions = [s for s in suggestions if "권한" in s["title"]]
        assert len(permission_suggestions) > 0

        # 타임아웃 오류
        context = {"error_message": "operation timed out"}
        suggestions = suggestions_system.get_suggestions(context)

        timeout_suggestions = [s for s in suggestions if "타임아웃" in s["title"]]
        assert len(timeout_suggestions) > 0

    @patch("rich.prompt.IntPrompt.ask")
    @patch("rich.console.Console.print")
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
                DialogChoice("option2", "옵션 2"),
            ],
        )

        session.add_question(test_question)

        # 질문 실행
        session._ask_question("test_single_choice")

        # 첫 번째 선택지가 선택되었는지 확인
        assert len(session.history) > 0
        assert session.history[-1]["answer"].key == "option1"

    @patch("rich.prompt.Confirm.ask")
    def test_yes_no_question(self, mock_confirm):
        """예/아니오 질문 테스트"""
        mock_confirm.return_value = True

        session = InteractiveSession()

        yes_no_question = DialogQuestion(
            id="test_yes_no",
            text="계속 진행하시겠습니까?",
            type=QuestionType.YES_NO,
            default_answer=True,
        )

        session.add_question(yes_no_question)
        session._ask_question("test_yes_no")

        assert session.history[-1]["answer"] is True

    @patch("rich.prompt.Prompt.ask")
    def test_text_input_question(self, mock_prompt):
        """텍스트 입력 질문 테스트"""
        mock_prompt.return_value = "테스트 답변"

        session = InteractiveSession()

        text_question = DialogQuestion(
            id="test_text", text="문제를 설명해주세요", type=QuestionType.TEXT_INPUT
        )

        session.add_question(text_question)
        session._ask_question("test_text")

        assert session.history[-1]["answer"] == "테스트 답변"

    def test_suggestion_ranking(self):
        """제안 우선순위 테스트"""
        suggestions_system = ContextAwareSuggestions()

        test_suggestions = [
            {"title": "Low Priority", "priority": "low"},
            {"title": "High Priority", "priority": "high"},
            {"title": "Medium Priority", "priority": "medium"},
        ]

        ranked = suggestions_system._rank_suggestions(test_suggestions)

        # 높은 우선순위가 먼저 와야 함
        assert ranked[0]["priority"] == "high"
        assert ranked[1]["priority"] == "medium"
        assert ranked[2]["priority"] == "low"

    def test_context_update(self):
        """컨텍스트 업데이트 테스트"""
        session = InteractiveSession()

        # 초기 컨텍스트 설정
        session.context = {"test_key": "test_value"}

        # 컨텍스트 업데이트
        session._update_context(
            "general_problem_category", DialogChoice("network", "Network Issue")
        )

        assert session.context["problem_category"] == "network"

    def test_solution_generation(self):
        """해결책 생성 테스트"""
        session = InteractiveSession()
        session.context = {"problem_category": "network"}

        solution = session._generate_solution()

        assert "recommendations" in solution
        assert "commands" in solution
        assert "next_steps" in solution
        assert "session_id" in solution
        assert len(solution["recommendations"]) > 0
        assert len(solution["commands"]) > 0

    def test_session_id_generation(self):
        """세션 ID 생성 테스트"""
        session = InteractiveSession()

        session_id1 = session._generate_session_id()
        session_id2 = session._generate_session_id()

        # 서로 다른 ID가 생성되어야 함
        assert session_id1 != session_id2
        assert len(session_id1) == 8  # UUID 앞 8자리
        assert len(session_id2) == 8
