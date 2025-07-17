import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


class ExecutionPatternAnalyzer:
    """실행 패턴 분석기"""

    def __init__(self, history: list[dict[str, Any]]):
        self.history = history

    def analyze_failure_patterns(self) -> dict[str, Any]:
        """실패 패턴 분석"""
        failed_executions = [h for h in self.history if h["status"] == "failed"]

        if not failed_executions:
            return {"failures": 0, "patterns": []}

        # 실패 단계 분석
        failure_steps = defaultdict(int)
        failure_errors = defaultdict(int)

        for execution in failed_executions:
            step_details = self._load_execution_details(execution)
            for step_name, step_data in step_details.get("steps", {}).items():
                if step_data.get("status") == "failed":
                    failure_steps[step_name] += 1
                    if step_data.get("error"):
                        failure_errors[step_data["error"]] += 1

        # 시간대별 실패 분석
        failure_times = []
        for execution in failed_executions:
            dt = datetime.fromisoformat(execution["started_at"])
            failure_times.append(dt.hour)

        patterns = []

        # 가장 자주 실패하는 단계
        if failure_steps:
            most_failed_step = max(failure_steps.items(), key=lambda x: x[1])
            patterns.append(
                {
                    "type": "frequent_failure_step",
                    "description": f"'{most_failed_step[0]}' 단계에서 가장 자주 실패 ({most_failed_step[1]}회)",
                    "recommendation": f"{most_failed_step[0]} 단계의 설정을 점검해보세요",
                }
            )

        # 가장 흔한 오류
        if failure_errors:
            most_common_error = max(failure_errors.items(), key=lambda x: x[1])
            patterns.append(
                {
                    "type": "common_error",
                    "description": f"가장 흔한 오류: {most_common_error[0]} ({most_common_error[1]}회)",
                    "recommendation": "이 오류에 대한 해결 방법을 확인해보세요",
                }
            )

        # 시간대별 실패 패턴
        if failure_times:
            failure_hour_counts = Counter(failure_times)
            if len(failure_hour_counts) > 1:
                peak_hour = max(failure_hour_counts.items(), key=lambda x: x[1])
                patterns.append(
                    {
                        "type": "time_pattern",
                        "description": f"{peak_hour[0]}시경에 실패가 자주 발생 ({peak_hour[1]}회)",
                        "recommendation": "해당 시간대의 시스템 부하나 네트워크 상황을 확인해보세요",
                    }
                )

        return {
            "total_failures": len(failed_executions),
            "failure_rate": len(failed_executions) / len(self.history) * 100
            if self.history
            else 0,
            "patterns": patterns,
            "failure_steps": dict(failure_steps),
            "failure_errors": dict(failure_errors),
        }

    def analyze_performance_trends(self) -> dict[str, Any]:
        """성능 트렌드 분석"""
        completed_executions = []

        for execution in self.history:
            if execution["status"] == "completed" and execution.get("completed_at"):
                start = datetime.fromisoformat(execution["started_at"])
                end = datetime.fromisoformat(execution["completed_at"])
                duration = (end - start).total_seconds()

                completed_executions.append(
                    {
                        "duration": duration,
                        "date": start.date(),
                        "profile": execution.get("profile", "default"),
                    }
                )

        if len(completed_executions) < 2:
            return {"trend": "insufficient_data"}

        # 시간별 트렌드
        durations = [e["duration"] for e in completed_executions]
        recent_durations = durations[-5:]  # 최근 5회
        earlier_durations = durations[:-5] if len(durations) > 5 else durations

        trend_analysis = {}

        if len(recent_durations) >= 2 and len(earlier_durations) >= 2:
            recent_avg = statistics.mean(recent_durations)
            earlier_avg = statistics.mean(earlier_durations)

            if recent_avg > earlier_avg * 1.2:
                trend_analysis["performance"] = "degrading"
                trend_analysis["change"] = (
                    f"{((recent_avg - earlier_avg) / earlier_avg * 100):.1f}% 느려짐"
                )
            elif recent_avg < earlier_avg * 0.8:
                trend_analysis["performance"] = "improving"
                trend_analysis["change"] = (
                    f"{((earlier_avg - recent_avg) / earlier_avg * 100):.1f}% 빨라짐"
                )
            else:
                trend_analysis["performance"] = "stable"
                trend_analysis["change"] = "안정적"

        # 프로파일별 성능
        profile_performance = defaultdict(list)
        for execution in completed_executions:
            profile_performance[execution["profile"]].append(execution["duration"])

        profile_stats = {}
        for profile, durations in profile_performance.items():
            if len(durations) >= 2:
                profile_stats[profile] = {
                    "avg_duration": statistics.mean(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
                }

        return {
            "trend": trend_analysis,
            "profile_performance": profile_stats,
            "total_completed": len(completed_executions),
        }

    def generate_recommendations(self) -> list[dict[str, str]]:
        """개선 권장사항 생성"""
        recommendations = []

        failure_analysis = self.analyze_failure_patterns()
        performance_analysis = self.analyze_performance_trends()

        # 실패율 기반 권장사항
        if failure_analysis["failure_rate"] > 20:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "reliability",
                    "title": "높은 실패율 개선",
                    "description": f"실패율이 {failure_analysis['failure_rate']:.1f}%로 높습니다. 설정과 환경을 점검해보세요.",
                    "action": "sbkube validate로 설정을 검증하고, 로그를 확인해보세요.",
                }
            )

        # 성능 기반 권장사항
        perf_trend = performance_analysis.get("trend", {})
        if perf_trend.get("performance") == "degrading":
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "performance",
                    "title": "성능 저하 감지",
                    "description": f"최근 실행 시간이 {perf_trend['change']} 증가했습니다.",
                    "action": "시스템 리소스와 네트워크 상태를 확인해보세요.",
                }
            )

        # 패턴 기반 권장사항
        for pattern in failure_analysis.get("patterns", []):
            if pattern["type"] == "frequent_failure_step":
                step_name = pattern["description"].split("'")[1]
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "configuration",
                        "title": f"반복적인 {step_name} 단계 실패",
                        "description": pattern["description"],
                        "action": pattern["recommendation"],
                    }
                )

        return recommendations

    def _load_execution_details(self, execution: dict[str, Any]) -> dict[str, Any]:
        """실행 상세 정보 로드"""
        try:
            import json

            with open(execution["file"], encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
