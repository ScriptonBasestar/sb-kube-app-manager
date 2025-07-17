import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from sbkube.utils.execution_tracker import ExecutionTracker
from sbkube.utils.pattern_analyzer import ExecutionPatternAnalyzer


class TestHistoryManagement:
    def test_history_loading(self):
        """히스토리 로딩 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)

            # 테스트 히스토리 생성
            self._create_test_history(tmpdir)

            history = tracker.load_execution_history(10)
            assert len(history) > 0
            assert "run_id" in history[0]
            assert "status" in history[0]

    def test_pattern_analysis(self):
        """패턴 분석 테스트"""
        # 테스트 히스토리 데이터
        history = [
            {
                "status": "failed",
                "started_at": "2024-01-01T10:00:00",
                "file": "test1.json",
            },
            {
                "status": "completed",
                "started_at": "2024-01-01T11:00:00",
                "completed_at": "2024-01-01T11:05:00",
            },
            {
                "status": "failed",
                "started_at": "2024-01-01T12:00:00",
                "file": "test2.json",
            },
        ]

        analyzer = ExecutionPatternAnalyzer(history)
        failure_analysis = analyzer.analyze_failure_patterns()

        assert failure_analysis["total_failures"] == 2
        assert failure_analysis["failure_rate"] > 0

    def test_performance_trend_analysis(self):
        """성능 트렌드 분석 테스트"""
        # 완료된 실행 히스토리 데이터
        history = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        # 시간이 점점 길어지는 패턴 생성
        for i in range(10):
            start_time = base_time + timedelta(hours=i)
            duration = 300 + i * 60  # 5분에서 시작해서 1분씩 증가
            end_time = start_time + timedelta(seconds=duration)

            history.append(
                {
                    "status": "completed",
                    "started_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat(),
                    "profile": "test",
                }
            )

        analyzer = ExecutionPatternAnalyzer(history)
        performance_analysis = analyzer.analyze_performance_trends()

        assert performance_analysis["total_completed"] == 10
        assert "trend" in performance_analysis

    def test_recommendations_generation(self):
        """권장사항 생성 테스트"""
        # 높은 실패율을 가진 히스토리
        history = []
        for i in range(10):
            status = "failed" if i < 7 else "completed"  # 70% 실패율
            history.append(
                {
                    "status": status,
                    "started_at": f"2024-01-01T1{i:01d}:00:00",
                    "file": f"test{i}.json",
                }
            )

        analyzer = ExecutionPatternAnalyzer(history)
        recommendations = analyzer.generate_recommendations()

        # 높은 실패율로 인한 권장사항이 생성되어야 함
        assert any(rec["category"] == "reliability" for rec in recommendations)

    def test_failure_pattern_detection(self):
        """실패 패턴 감지 테스트"""
        # 특정 단계에서 자주 실패하는 패턴
        with tempfile.TemporaryDirectory() as tmpdir:
            # 실패 상세 정보가 포함된 파일 생성
            runs_dir = Path(tmpdir) / ".sbkube" / "runs"
            runs_dir.mkdir(parents=True, exist_ok=True)

            for i in range(3):
                failure_data = {
                    "run_id": f"test-failure-{i}",
                    "status": "failed",
                    "started_at": f"2024-01-01T1{i:01d}:00:00",
                    "steps": {
                        "prepare": {"status": "completed"},
                        "build": {"status": "failed", "error": "Build failed"},
                        "template": {"status": "pending"},
                        "deploy": {"status": "pending"},
                    },
                }

                file_path = runs_dir / f"test-failure-{i}.json"
                with open(file_path, "w") as f:
                    json.dump(failure_data, f)

            # 히스토리 데이터에 파일 경로 포함
            history = [
                {
                    "status": "failed",
                    "started_at": f"2024-01-01T1{i:01d}:00:00",
                    "file": str(runs_dir / f"test-failure-{i}.json"),
                }
                for i in range(3)
            ]

            analyzer = ExecutionPatternAnalyzer(history)
            failure_analysis = analyzer.analyze_failure_patterns()

            assert failure_analysis["failure_steps"]["build"] == 3
            assert any(
                pattern["type"] == "frequent_failure_step"
                for pattern in failure_analysis["patterns"]
            )

    def test_time_pattern_analysis(self):
        """시간대별 실패 패턴 분석 테스트"""
        # 특정 시간대에 집중된 실패 패턴
        history = []
        for i in range(5):
            # 모두 14시에 실패
            history.append(
                {
                    "status": "failed",
                    "started_at": f"2024-01-0{i + 1}T14:00:00",
                    "file": "dummy.json",
                }
            )

        analyzer = ExecutionPatternAnalyzer(history)
        failure_analysis = analyzer.analyze_failure_patterns()

        # 시간대별 패턴이 감지되어야 함
        time_patterns = [
            p for p in failure_analysis["patterns"] if p["type"] == "time_pattern"
        ]
        assert len(time_patterns) > 0
        assert "14시경" in time_patterns[0]["description"]

    def test_profile_performance_analysis(self):
        """프로파일별 성능 분석 테스트"""
        history = []

        # development 프로파일 - 빠른 실행
        for i in range(3):
            start = datetime(2024, 1, 1, 10, i, 0)
            end = start + timedelta(minutes=2)  # 2분
            history.append(
                {
                    "status": "completed",
                    "started_at": start.isoformat(),
                    "completed_at": end.isoformat(),
                    "profile": "development",
                }
            )

        # production 프로파일 - 느린 실행
        for i in range(3):
            start = datetime(2024, 1, 1, 11, i, 0)
            end = start + timedelta(minutes=5)  # 5분
            history.append(
                {
                    "status": "completed",
                    "started_at": start.isoformat(),
                    "completed_at": end.isoformat(),
                    "profile": "production",
                }
            )

        analyzer = ExecutionPatternAnalyzer(history)
        performance_analysis = analyzer.analyze_performance_trends()

        profile_perf = performance_analysis["profile_performance"]
        assert "development" in profile_perf
        assert "production" in profile_perf
        assert (
            profile_perf["development"]["avg_duration"]
            < profile_perf["production"]["avg_duration"]
        )

    def test_empty_history_handling(self):
        """빈 히스토리 처리 테스트"""
        analyzer = ExecutionPatternAnalyzer([])

        failure_analysis = analyzer.analyze_failure_patterns()
        assert failure_analysis["failures"] == 0
        assert failure_analysis["patterns"] == []

        performance_analysis = analyzer.analyze_performance_trends()
        assert performance_analysis["trend"] == "insufficient_data"

        recommendations = analyzer.generate_recommendations()
        assert len(recommendations) == 0

    def test_insufficient_data_handling(self):
        """데이터 부족 상황 처리 테스트"""
        # 완료된 실행이 1개만 있는 경우
        history = [
            {
                "status": "completed",
                "started_at": "2024-01-01T10:00:00",
                "completed_at": "2024-01-01T10:05:00",
            }
        ]

        analyzer = ExecutionPatternAnalyzer(history)
        performance_analysis = analyzer.analyze_performance_trends()

        assert performance_analysis["trend"] == "insufficient_data"

    def _create_test_history(self, tmpdir):
        """테스트용 히스토리 생성"""
        runs_dir = Path(tmpdir) / ".sbkube" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        # 성공 실행
        success_data = {
            "run_id": "test-success-1",
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "steps": {
                "prepare": {"status": "completed"},
                "build": {"status": "completed"},
                "template": {"status": "completed"},
                "deploy": {"status": "completed"},
            },
        }

        with open(runs_dir / "test-success-1.json", "w") as f:
            json.dump(success_data, f)

        # 실패 실행
        failure_data = {
            "run_id": "test-failure-1",
            "status": "failed",
            "started_at": datetime.now().isoformat(),
            "steps": {
                "prepare": {"status": "completed"},
                "build": {"status": "failed", "error": "Build failed"},
            },
        }

        with open(runs_dir / "test-failure-1.json", "w") as f:
            json.dump(failure_data, f)


class TestHistoryCommands:
    """히스토리 명령어 테스트"""

    def test_format_duration(self):
        """시간 포맷팅 테스트"""
        from sbkube.commands.history import _format_duration

        assert _format_duration(30.5) == "30.5초"
        assert _format_duration(120) == "2.0분"
        assert _format_duration(3661) == "1.0시간"

    def test_format_datetime(self):
        """날짜 포맷팅 테스트"""
        from sbkube.commands.history import _format_datetime

        iso_string = "2024-01-01T10:30:45"
        result = _format_datetime(iso_string)
        assert result == "2024-01-01 10:30:45"

    def test_analyze_execution_times(self):
        """실행 시간 분석 테스트"""
        from sbkube.commands.history import _analyze_execution_times

        history = [
            {
                "status": "completed",
                "started_at": "2024-01-01T10:00:00",
                "completed_at": "2024-01-01T10:05:00",
            },
            {
                "status": "completed",
                "started_at": "2024-01-01T11:00:00",
                "completed_at": "2024-01-01T11:03:00",
            },
        ]

        result = _analyze_execution_times(history)
        assert "avg_duration" in result
        assert "min_duration" in result
        assert "max_duration" in result
