---
phase: 2
order: 9
source_plan: /tasks/plan/phase2-advanced-features.md
priority: medium
tags: [smart-restart, history-management, statistics]
estimated_days: 2
depends_on: [008-smart-restart-execution-tracker]
---

# 📌 작업: 스마트 재시작 히스토리 관리 시스템

## 🎯 목표
실행 히스토리를 체계적으로 관리하고, 성공/실패 통계를 제공하며, 패턴 분석을 통한 인사이트를 제공합니다.

## 📋 작업 내용

### 1. 히스토리 명령어 구현
```python
# sbkube/commands/history.py
import click
import sys
from typing import List, Dict, Any
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

from sbkube.utils.execution_tracker import ExecutionTracker
from sbkube.utils.logger import logger
from sbkube.models.execution_state import StepStatus

console = Console()

@click.command(name="history")
@click.option("--limit", default=10, help="표시할 히스토리 개수 (기본값: 10)")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
@click.option("--failures", is_flag=True, help="실패한 실행만 표시")
@click.option("--profile", help="특정 프로파일의 히스토리만 표시")
@click.option("--clean", is_flag=True, help="오래된 히스토리 정리")
@click.option("--stats", is_flag=True, help="통계 정보 표시")
@click.pass_context
def cmd(ctx, limit, detailed, failures, profile, clean, stats):
    """실행 히스토리 조회 및 관리
    
    최근 실행 기록을 조회하고 성공/실패 통계를 확인할 수 있습니다.
    
    \\b
    사용 예시:
        sbkube history                    # 최근 10개 실행 기록
        sbkube history --detailed         # 상세 정보 포함
        sbkube history --failures         # 실패한 실행만 표시
        sbkube history --stats            # 통계 정보 표시
        sbkube history --clean            # 오래된 기록 정리
    """
    
    try:
        tracker = ExecutionTracker(".", profile)
        
        if clean:
            _clean_old_history(tracker)
            return
        
        if stats:
            _show_statistics(tracker)
            return
        
        history = tracker.load_execution_history(limit)
        
        if failures:
            history = [h for h in history if h['status'] == 'failed']
        
        if profile:
            history = [h for h in history if h.get('profile') == profile]
        
        if not history:
            console.print("📋 히스토리가 없습니다.")
            return
        
        if detailed:
            _show_detailed_history(history)
        else:
            _show_simple_history(history)
            
    except Exception as e:
        logger.error(f"❌ 히스토리 조회 실패: {e}")
        sys.exit(1)

def _show_simple_history(history: List[Dict[str, Any]]):
    """간단한 히스토리 표시"""
    table = Table(title="📋 최근 실행 히스토리")
    table.add_column("Run ID", style="cyan", width=10)
    table.add_column("프로파일", style="blue")
    table.add_column("상태", justify="center")
    table.add_column("시작 시간", style="dim")
    table.add_column("소요 시간", justify="right")
    
    for record in history:
        # 상태 아이콘
        status_icon = {
            'completed': '✅',
            'failed': '❌',
            'in_progress': '🔄'
        }.get(record['status'], '❓')
        
        # 소요 시간 계산
        duration = ""
        if record.get('completed_at'):
            start = datetime.fromisoformat(record['started_at'])
            end = datetime.fromisoformat(record['completed_at'])
            duration = _format_duration((end - start).total_seconds())
        elif record['status'] == 'in_progress':
            start = datetime.fromisoformat(record['started_at'])
            duration = _format_duration((datetime.now() - start).total_seconds()) + " (진행중)"
        
        # 시작 시간 포맷
        start_time = datetime.fromisoformat(record['started_at'])
        formatted_time = start_time.strftime("%m/%d %H:%M")
        
        table.add_row(
            record['run_id'][:8],
            record.get('profile', 'default'),
            f"{status_icon} {record['status']}",
            formatted_time,
            duration
        )
    
    console.print(table)

def _show_detailed_history(history: List[Dict[str, Any]]):
    """상세한 히스토리 표시"""
    for i, record in enumerate(history):
        if i > 0:
            console.print()
        
        # 상태별 색상
        status_color = {
            'completed': 'green',
            'failed': 'red',
            'in_progress': 'yellow'
        }.get(record['status'], 'white')
        
        # 기본 정보
        panel_content = f"[bold]Run ID:[/bold] {record['run_id']}\n"
        panel_content += f"[bold]프로파일:[/bold] {record.get('profile', 'default')}\n"
        panel_content += f"[bold]상태:[/bold] [{status_color}]{record['status']}[/{status_color}]\n"
        panel_content += f"[bold]시작 시간:[/bold] {_format_datetime(record['started_at'])}\n"
        
        if record.get('completed_at'):
            panel_content += f"[bold]완료 시간:[/bold] {_format_datetime(record['completed_at'])}\n"
            start = datetime.fromisoformat(record['started_at'])
            end = datetime.fromisoformat(record['completed_at'])
            duration = _format_duration((end - start).total_seconds())
            panel_content += f"[bold]소요 시간:[/bold] {duration}\n"
        
        # 단계별 정보 로드
        step_info = _load_step_details(record['file'])
        if step_info:
            panel_content += "\n[bold]단계별 상태:[/bold]\n"
            for step_name, step_data in step_info.items():
                step_status = step_data.get('status', 'pending')
                step_icon = {
                    'completed': '✅',
                    'failed': '❌',
                    'in_progress': '🔄',
                    'pending': '⏳',
                    'skipped': '⏭️'
                }.get(step_status, '❓')
                
                panel_content += f"  {step_icon} {step_name}"
                
                if step_data.get('duration'):
                    duration = _format_duration(step_data['duration'])
                    panel_content += f" ({duration})"
                
                if step_data.get('error'):
                    panel_content += f"\n    [red]오류: {step_data['error']}[/red]"
                
                panel_content += "\n"
        
        console.print(Panel(
            panel_content.rstrip(),
            title=f"🔍 실행 기록 #{i+1}",
            expand=False
        ))

def _show_statistics(tracker: ExecutionTracker):
    """통계 정보 표시"""
    history = tracker.load_execution_history(100)  # 최근 100개 기록
    
    if not history:
        console.print("📊 통계를 계산할 히스토리가 없습니다.")
        return
    
    # 기본 통계
    total_runs = len(history)
    successful_runs = len([h for h in history if h['status'] == 'completed'])
    failed_runs = len([h for h in history if h['status'] == 'failed'])
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
    
    # 프로파일별 통계
    profile_stats = {}
    for record in history:
        profile = record.get('profile', 'default')
        if profile not in profile_stats:
            profile_stats[profile] = {'total': 0, 'success': 0, 'failed': 0}
        
        profile_stats[profile]['total'] += 1
        if record['status'] == 'completed':
            profile_stats[profile]['success'] += 1
        elif record['status'] == 'failed':
            profile_stats[profile]['failed'] += 1
    
    # 시간대별 분석
    time_analysis = _analyze_execution_times(history)
    
    # 통계 표시
    console.print("📊 실행 통계 (최근 100회)")
    console.print()
    
    # 전체 통계
    stats_table = Table(title="전체 실행 통계")
    stats_table.add_column("항목", style="bold")
    stats_table.add_column("값", justify="right")
    
    stats_table.add_row("총 실행 횟수", str(total_runs))
    stats_table.add_row("성공", f"[green]{successful_runs}[/green]")
    stats_table.add_row("실패", f"[red]{failed_runs}[/red]")
    stats_table.add_row("성공률", f"[bold]{success_rate:.1f}%[/bold]")
    
    console.print(stats_table)
    console.print()
    
    # 프로파일별 통계
    if len(profile_stats) > 1:
        profile_table = Table(title="프로파일별 통계")
        profile_table.add_column("프로파일", style="cyan")
        profile_table.add_column("총 실행", justify="center")
        profile_table.add_column("성공", justify="center")
        profile_table.add_column("실패", justify="center")
        profile_table.add_column("성공률", justify="right")
        
        for profile, stats in profile_stats.items():
            rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            profile_table.add_row(
                profile,
                str(stats['total']),
                f"[green]{stats['success']}[/green]",
                f"[red]{stats['failed']}[/red]",
                f"{rate:.1f}%"
            )
        
        console.print(profile_table)
        console.print()
    
    # 시간 분석
    if time_analysis:
        console.print("⏱️  실행 시간 분석")
        console.print(f"평균 실행 시간: {time_analysis['avg_duration']}")
        console.print(f"최단 실행 시간: {time_analysis['min_duration']}")
        console.print(f"최장 실행 시간: {time_analysis['max_duration']}")

def _analyze_execution_times(history: List[Dict[str, Any]]) -> Dict[str, str]:
    """실행 시간 분석"""
    durations = []
    
    for record in history:
        if record.get('completed_at') and record['status'] == 'completed':
            start = datetime.fromisoformat(record['started_at'])
            end = datetime.fromisoformat(record['completed_at'])
            duration = (end - start).total_seconds()
            durations.append(duration)
    
    if not durations:
        return {}
    
    return {
        'avg_duration': _format_duration(sum(durations) / len(durations)),
        'min_duration': _format_duration(min(durations)),
        'max_duration': _format_duration(max(durations))
    }

def _clean_old_history(tracker: ExecutionTracker):
    """오래된 히스토리 정리"""
    console.print("🧹 오래된 히스토리를 정리하고 있습니다...")
    
    # 30일 이상 된 기록 정리
    tracker.cleanup_old_states(keep_days=30)
    
    console.print("✅ 히스토리 정리가 완료되었습니다.")

def _load_step_details(file_path: str) -> Dict[str, Any]:
    """상태 파일에서 단계별 상세 정보 로드"""
    try:
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('steps', {})
    except Exception:
        return {}

def _format_datetime(iso_string: str) -> str:
    """날짜시간 포맷팅"""
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _format_duration(seconds: float) -> str:
    """소요 시간 포맷팅"""
    if seconds < 60:
        return f"{seconds:.1f}초"
    elif seconds < 3600:
        return f"{seconds/60:.1f}분"
    else:
        return f"{seconds/3600:.1f}시간"
```

### 2. 실행 패턴 분석기 구현
```python
# sbkube/utils/pattern_analyzer.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

class ExecutionPatternAnalyzer:
    """실행 패턴 분석기"""
    
    def __init__(self, history: List[Dict[str, Any]]):
        self.history = history
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """실패 패턴 분석"""
        failed_executions = [h for h in self.history if h['status'] == 'failed']
        
        if not failed_executions:
            return {'failures': 0, 'patterns': []}
        
        # 실패 단계 분석
        failure_steps = defaultdict(int)
        failure_errors = defaultdict(int)
        
        for execution in failed_executions:
            step_details = self._load_execution_details(execution)
            for step_name, step_data in step_details.get('steps', {}).items():
                if step_data.get('status') == 'failed':
                    failure_steps[step_name] += 1
                    if step_data.get('error'):
                        failure_errors[step_data['error']] += 1
        
        # 시간대별 실패 분석
        failure_times = []
        for execution in failed_executions:
            dt = datetime.fromisoformat(execution['started_at'])
            failure_times.append(dt.hour)
        
        patterns = []
        
        # 가장 자주 실패하는 단계
        if failure_steps:
            most_failed_step = max(failure_steps.items(), key=lambda x: x[1])
            patterns.append({
                'type': 'frequent_failure_step',
                'description': f"'{most_failed_step[0]}' 단계에서 가장 자주 실패 ({most_failed_step[1]}회)",
                'recommendation': f"{most_failed_step[0]} 단계의 설정을 점검해보세요"
            })
        
        # 가장 흔한 오류
        if failure_errors:
            most_common_error = max(failure_errors.items(), key=lambda x: x[1])
            patterns.append({
                'type': 'common_error',
                'description': f"가장 흔한 오류: {most_common_error[0]} ({most_common_error[1]}회)",
                'recommendation': "이 오류에 대한 해결 방법을 확인해보세요"
            })
        
        # 시간대별 실패 패턴
        if failure_times:
            failure_hour_counts = Counter(failure_times)
            if len(failure_hour_counts) > 1:
                peak_hour = max(failure_hour_counts.items(), key=lambda x: x[1])
                patterns.append({
                    'type': 'time_pattern',
                    'description': f"{peak_hour[0]}시경에 실패가 자주 발생 ({peak_hour[1]}회)",
                    'recommendation': "해당 시간대의 시스템 부하나 네트워크 상황을 확인해보세요"
                })
        
        return {
            'total_failures': len(failed_executions),
            'failure_rate': len(failed_executions) / len(self.history) * 100,
            'patterns': patterns,
            'failure_steps': dict(failure_steps),
            'failure_errors': dict(failure_errors)
        }
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """성능 트렌드 분석"""
        completed_executions = []
        
        for execution in self.history:
            if execution['status'] == 'completed' and execution.get('completed_at'):
                start = datetime.fromisoformat(execution['started_at'])
                end = datetime.fromisoformat(execution['completed_at'])
                duration = (end - start).total_seconds()
                
                completed_executions.append({
                    'duration': duration,
                    'date': start.date(),
                    'profile': execution.get('profile', 'default')
                })
        
        if len(completed_executions) < 2:
            return {'trend': 'insufficient_data'}
        
        # 시간별 트렌드
        durations = [e['duration'] for e in completed_executions]
        recent_durations = durations[-5:]  # 최근 5회
        earlier_durations = durations[:-5] if len(durations) > 5 else durations
        
        trend_analysis = {}
        
        if len(recent_durations) >= 2 and len(earlier_durations) >= 2:
            recent_avg = statistics.mean(recent_durations)
            earlier_avg = statistics.mean(earlier_durations)
            
            if recent_avg > earlier_avg * 1.2:
                trend_analysis['performance'] = 'degrading'
                trend_analysis['change'] = f"{((recent_avg - earlier_avg) / earlier_avg * 100):.1f}% 느려짐"
            elif recent_avg < earlier_avg * 0.8:
                trend_analysis['performance'] = 'improving'
                trend_analysis['change'] = f"{((earlier_avg - recent_avg) / earlier_avg * 100):.1f}% 빨라짐"
            else:
                trend_analysis['performance'] = 'stable'
                trend_analysis['change'] = "안정적"
        
        # 프로파일별 성능
        profile_performance = defaultdict(list)
        for execution in completed_executions:
            profile_performance[execution['profile']].append(execution['duration'])
        
        profile_stats = {}
        for profile, durations in profile_performance.items():
            if len(durations) >= 2:
                profile_stats[profile] = {
                    'avg_duration': statistics.mean(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
                }
        
        return {
            'trend': trend_analysis,
            'profile_performance': profile_stats,
            'total_completed': len(completed_executions)
        }
    
    def generate_recommendations(self) -> List[Dict[str, str]]:
        """개선 권장사항 생성"""
        recommendations = []
        
        failure_analysis = self.analyze_failure_patterns()
        performance_analysis = self.analyze_performance_trends()
        
        # 실패율 기반 권장사항
        if failure_analysis['failure_rate'] > 20:
            recommendations.append({
                'priority': 'high',
                'category': 'reliability',
                'title': '높은 실패율 개선',
                'description': f"실패율이 {failure_analysis['failure_rate']:.1f}%로 높습니다. 설정과 환경을 점검해보세요.",
                'action': "sbkube validate로 설정을 검증하고, 로그를 확인해보세요."
            })
        
        # 성능 기반 권장사항
        perf_trend = performance_analysis.get('trend', {})
        if perf_trend.get('performance') == 'degrading':
            recommendations.append({
                'priority': 'medium',
                'category': 'performance',
                'title': '성능 저하 감지',
                'description': f"최근 실행 시간이 {perf_trend['change']} 증가했습니다.",
                'action': "시스템 리소스와 네트워크 상태를 확인해보세요."
            })
        
        # 패턴 기반 권장사항
        for pattern in failure_analysis.get('patterns', []):
            if pattern['type'] == 'frequent_failure_step':
                recommendations.append({
                    'priority': 'high',
                    'category': 'configuration',
                    'title': f"반복적인 {pattern['description'].split("'")[1]} 단계 실패",
                    'description': pattern['description'],
                    'action': pattern['recommendation']
                })
        
        return recommendations
    
    def _load_execution_details(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """실행 상세 정보 로드"""
        try:
            import json
            with open(execution['file'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
```

### 3. 진단 명령어 추가
```python
# sbkube/commands/history.py에 추가
@click.command(name="diagnose")
@click.option("--recommendations", is_flag=True, help="개선 권장사항 표시")
@click.pass_context
def diagnose_cmd(ctx, recommendations):
    """실행 패턴 분석 및 진단
    
    최근 실행 기록을 분석하여 문제 패턴을 찾고 개선 방안을 제시합니다.
    """
    try:
        tracker = ExecutionTracker(".")
        history = tracker.load_execution_history(50)
        
        if not history:
            console.print("📋 분석할 히스토리가 없습니다.")
            return
        
        from sbkube.utils.pattern_analyzer import ExecutionPatternAnalyzer
        analyzer = ExecutionPatternAnalyzer(history)
        
        # 실패 패턴 분석
        failure_analysis = analyzer.analyze_failure_patterns()
        console.print("🔍 실패 패턴 분석")
        console.print(f"총 실패 횟수: {failure_analysis['total_failures']}")
        console.print(f"실패율: {failure_analysis['failure_rate']:.1f}%")
        
        if failure_analysis['patterns']:
            console.print("\n발견된 패턴:")
            for pattern in failure_analysis['patterns']:
                console.print(f"  • {pattern['description']}")
        
        # 성능 트렌드 분석
        performance_analysis = analyzer.analyze_performance_trends()
        perf_trend = performance_analysis.get('trend', {})
        
        if perf_trend:
            console.print(f"\n⚡ 성능 트렌드")
            console.print(f"상태: {perf_trend.get('performance', 'unknown')}")
            if 'change' in perf_trend:
                console.print(f"변화: {perf_trend['change']}")
        
        # 권장사항
        if recommendations:
            recs = analyzer.generate_recommendations()
            if recs:
                console.print("\n💡 개선 권장사항")
                for rec in recs:
                    priority_color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(rec['priority'], 'white')
                    console.print(f"[{priority_color}]• {rec['title']}[/{priority_color}]")
                    console.print(f"  {rec['description']}")
                    console.print(f"  권장 조치: {rec['action']}")
                    console.print()
        
    except Exception as e:
        logger.error(f"❌ 진단 실패: {e}")
        sys.exit(1)
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/commands/test_history.py
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
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
            assert 'run_id' in history[0]
            assert 'status' in history[0]
    
    def test_pattern_analysis(self):
        """패턴 분석 테스트"""
        # 테스트 히스토리 데이터
        history = [
            {'status': 'failed', 'started_at': '2024-01-01T10:00:00', 'file': 'test1.json'},
            {'status': 'completed', 'started_at': '2024-01-01T11:00:00', 'completed_at': '2024-01-01T11:05:00'},
            {'status': 'failed', 'started_at': '2024-01-01T12:00:00', 'file': 'test2.json'},
        ]
        
        analyzer = ExecutionPatternAnalyzer(history)
        failure_analysis = analyzer.analyze_failure_patterns()
        
        assert failure_analysis['total_failures'] == 2
        assert failure_analysis['failure_rate'] > 0
    
    def _create_test_history(self, tmpdir):
        """테스트용 히스토리 생성"""
        runs_dir = Path(tmpdir) / ".sbkube" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        
        # 성공 실행
        success_data = {
            'run_id': 'test-success-1',
            'status': 'completed',
            'started_at': datetime.now().isoformat(),
            'completed_at': (datetime.now() + timedelta(minutes=5)).isoformat(),
            'steps': {
                'prepare': {'status': 'completed'},
                'build': {'status': 'completed'},
                'template': {'status': 'completed'},
                'deploy': {'status': 'completed'}
            }
        }
        
        with open(runs_dir / "test-success-1.json", 'w') as f:
            json.dump(success_data, f)
        
        # 실패 실행
        failure_data = {
            'run_id': 'test-failure-1',
            'status': 'failed',
            'started_at': datetime.now().isoformat(),
            'steps': {
                'prepare': {'status': 'completed'},
                'build': {'status': 'failed', 'error': 'Build failed'}
            }
        }
        
        with open(runs_dir / "test-failure-1.json", 'w') as f:
            json.dump(failure_data, f)
```

## ✅ 완료 기준

- [ ] history 명령어 구현 (list, detailed, failures, stats)
- [ ] 실행 패턴 분석기 구현
- [ ] 통계 정보 표시 기능
- [ ] 진단 명령어 구현
- [ ] 오래된 히스토리 정리 기능
- [ ] 권장사항 생성 시스템
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 히스토리 조회
sbkube history
sbkube history --detailed
sbkube history --failures
sbkube history --stats

# 패턴 분석
sbkube diagnose
sbkube diagnose --recommendations

# 히스토리 정리
sbkube history --clean

# 테스트 실행
pytest tests/unit/commands/test_history.py -v
```

## 📝 예상 결과

```bash
$ sbkube history --stats
📊 실행 통계 (최근 100회)

전체 실행 통계
┌──────────┬─────┐
│ 항목     │  값 │
├──────────┼─────┤
│ 총 실행 횟수 │  25 │
│ 성공     │  20 │
│ 실패     │   5 │
│ 성공률   │80.0%│
└──────────┴─────┘

⏱️  실행 시간 분석
평균 실행 시간: 3.2분
최단 실행 시간: 1.8분
최장 실행 시간: 7.5분

$ sbkube diagnose --recommendations
🔍 실패 패턴 분석
총 실패 횟수: 5
실패율: 20.0%

발견된 패턴:
  • 'build' 단계에서 가장 자주 실패 (3회)
  • 가장 흔한 오류: Helm chart not found (2회)

⚡ 성능 트렌드
상태: stable
변화: 안정적

💡 개선 권장사항
• 반복적인 build 단계 실패
  build 단계에서 가장 자주 실패 (3회)
  권장 조치: build 단계의 설정을 점검해보세요
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `010-progress-manager-implementation.md` - 실시간 진행률 표시 시스템 구현