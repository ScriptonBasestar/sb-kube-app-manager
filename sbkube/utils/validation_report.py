"""
검증 보고서 생성 및 출력 시스템

검증 결과를 다양한 형식(Console, JSON, HTML)으로 생성하고 출력하는 시스템입니다.
검증 히스토리 관리 및 트렌드 분석 기능을 포함합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import asdict
import uuid

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.align import Align

from sbkube.utils.validation_system import ValidationReport, ValidationResult, ValidationMode, ValidationSeverity
from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.logger import logger


class ValidationReportManager:
    """검증 보고서 관리자"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.sbkube_dir = self.base_dir / ".sbkube"
        self.history_file = self.sbkube_dir / "validation_history.json"
        self.console = Console()
        
        # .sbkube 디렉토리 생성
        self.sbkube_dir.mkdir(exist_ok=True)
    
    def generate_report(self, report: ValidationReport, output_format: str = "console", 
                       output_file: Optional[str] = None, show_details: bool = True) -> Optional[str]:
        """검증 보고서 생성"""
        try:
            if output_format.lower() == "console":
                generator = ConsoleReportGenerator(self.console)
                generator.generate_report(report, show_details)
                return None
            elif output_format.lower() == "json":
                generator = JSONReportGenerator()
                content = generator.generate_report(report)
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return output_file
                return content
            elif output_format.lower() == "html":
                generator = HTMLReportGenerator()
                content = generator.generate_report(report)
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return output_file
                return content
            else:
                raise ValueError(f"지원하지 않는 출력 형식: {output_format}")
        
        except Exception as e:
            logger.error(f"보고서 생성 실패: {e}")
            raise
    
    def save_to_history(self, report: ValidationReport) -> str:
        """검증 히스토리에 저장"""
        try:
            # 히스토리 로드
            history = self._load_history()
            
            # 새 검증 기록 추가
            report_id = str(uuid.uuid4())
            history_entry = {
                'id': report_id,
                'timestamp': report.start_time.isoformat() if report.start_time else datetime.now().isoformat(),
                'validation_mode': report.validation_mode.value,
                'context': {
                    'config_dir': report.context.config_dir,
                    'base_dir': report.context.base_dir,
                    'target_app': report.context.target_app,
                    'environment': report.context.environment,
                    'profile': report.context.profile
                },
                'summary': report.get_summary(),
                'results_count': len(report.results),
                'deployment_ready': report.is_deployment_ready()
            }
            
            history['validations'].append(history_entry)
            
            # 오래된 기록 정리 (100개 초과시 오래된 것 삭제)
            if len(history['validations']) > 100:
                history['validations'] = history['validations'][-100:]
            
            # 히스토리 저장
            self._save_history(history)
            
            return report_id
        
        except Exception as e:
            logger.error(f"히스토리 저장 실패: {e}")
            return ""
    
    def get_validation_trends(self, days: int = 30) -> Dict[str, Any]:
        """검증 트렌드 분석"""
        try:
            history = self._load_history()
            validations = history.get('validations', [])
            
            # 최근 N일 데이터 필터링
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_validations = [
                v for v in validations
                if datetime.fromisoformat(v['timestamp']) > cutoff_date
            ]
            
            if not recent_validations:
                return {
                    'total_validations': 0,
                    'success_rate': 0,
                    'common_issues': [],
                    'trend_analysis': "데이터 부족"
                }
            
            # 통계 계산
            total_validations = len(recent_validations)
            successful_validations = sum(1 for v in recent_validations if v.get('deployment_ready', False))
            success_rate = (successful_validations / total_validations) * 100
            
            # 모드별 통계
            mode_stats = {}
            for validation in recent_validations:
                mode = validation.get('validation_mode', 'unknown')
                if mode not in mode_stats:
                    mode_stats[mode] = {'count': 0, 'success': 0}
                mode_stats[mode]['count'] += 1
                if validation.get('deployment_ready', False):
                    mode_stats[mode]['success'] += 1
            
            # 일반적인 문제 패턴 분석
            common_issues = self._analyze_common_issues(recent_validations)
            
            return {
                'period_days': days,
                'total_validations': total_validations,
                'success_rate': round(success_rate, 1),
                'mode_statistics': mode_stats,
                'common_issues': common_issues,
                'trend_analysis': self._generate_trend_analysis(recent_validations)
            }
        
        except Exception as e:
            logger.error(f"트렌드 분석 실패: {e}")
            return {
                'total_validations': 0,
                'success_rate': 0,
                'common_issues': [],
                'trend_analysis': "분석 실패"
            }
    
    def _load_history(self) -> Dict[str, Any]:
        """히스토리 파일 로드"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"히스토리 파일 로드 실패: {e}")
        
        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'validations': []
        }
    
    def _save_history(self, history: Dict[str, Any]):
        """히스토리 파일 저장"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"히스토리 파일 저장 실패: {e}")
            raise
    
    def _analyze_common_issues(self, validations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """일반적인 문제 패턴 분석"""
        issue_patterns = {}
        
        for validation in validations:
            summary = validation.get('summary', {})
            
            # 오류/경고가 있는 검증들에서 패턴 추출
            if summary.get('by_level', {}).get('error', 0) > 0:
                # 여기서는 간단한 분석만 수행 (실제로는 more detailed analysis needed)
                mode = validation.get('validation_mode', 'unknown')
                pattern_key = f"{mode}_errors"
                
                if pattern_key not in issue_patterns:
                    issue_patterns[pattern_key] = 0
                issue_patterns[pattern_key] += 1
        
        # 빈도순 정렬
        sorted_issues = sorted(issue_patterns.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                'pattern': pattern,
                'frequency': count,
                'description': self._get_issue_description(pattern)
            }
            for pattern, count in sorted_issues[:10]
        ]
    
    def _get_issue_description(self, pattern: str) -> str:
        """문제 패턴 설명 생성"""
        descriptions = {
            'configuration_errors': '설정 파일 오류',
            'environment_errors': 'Kubernetes 환경 문제',
            'dependencies_errors': '의존성 해결 문제',
            'pre-deployment_errors': '배포 전 검증 실패'
        }
        return descriptions.get(pattern, pattern)
    
    def _generate_trend_analysis(self, validations: List[Dict[str, Any]]) -> str:
        """트렌드 분석 텍스트 생성"""
        if len(validations) < 5:
            return "데이터가 부족하여 트렌드 분석이 어렵습니다."
        
        # 시간순 정렬
        sorted_validations = sorted(validations, key=lambda x: x['timestamp'])
        
        # 최근 성공률 계산
        recent_half = sorted_validations[-len(sorted_validations)//2:]
        earlier_half = sorted_validations[:len(sorted_validations)//2]
        
        recent_success_rate = sum(1 for v in recent_half if v.get('deployment_ready', False)) / len(recent_half)
        earlier_success_rate = sum(1 for v in earlier_half if v.get('deployment_ready', False)) / len(earlier_half)
        
        if recent_success_rate > earlier_success_rate + 0.1:
            return "검증 성공률이 향상되고 있습니다."
        elif recent_success_rate < earlier_success_rate - 0.1:
            return "검증 성공률이 하락하고 있습니다. 설정 검토가 필요합니다."
        else:
            return "검증 성공률이 안정적으로 유지되고 있습니다."


class ConsoleReportGenerator:
    """콘솔 보고서 생성기"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def generate_report(self, report: ValidationReport, show_details: bool = True):
        """콘솔 보고서 생성"""
        summary = report.get_summary()
        
        # 헤더
        self._display_header(summary)
        
        # 요약 통계
        self._display_summary_stats(summary)
        
        # 검증 결과 상세
        if show_details:
            self._display_detailed_results(report)
        
        # 배포 준비 상태
        self._display_deployment_readiness(summary, report)
        
        # 권장사항
        self._display_recommendations(report)
    
    def _display_header(self, summary: Dict[str, Any]):
        """헤더 표시"""
        mode_descriptions = {
            'basic': '기본 검증',
            'comprehensive': '종합 검증',
            'pre-deploy': '배포 전 검증',
            'environment': '환경 검증',
            'dependencies': '의존성 검증'
        }
        
        mode = summary.get('validation_mode', 'basic')
        title = f"🔍 SBKube {mode_descriptions.get(mode, '검증')} 결과"
        
        self.console.print()
        self.console.print(Panel(
            Align.center(Text(title, style="bold blue")),
            border_style="blue"
        ))
        
        if summary.get('duration_seconds', 0) > 0:
            self.console.print(f"검증 시간: {summary['duration_seconds']:.2f}초")
        self.console.print()
    
    def _display_summary_stats(self, summary: Dict[str, Any]):
        """요약 통계 표시"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("상태", style="bold")
        table.add_column("개수", justify="right")
        table.add_column("비율", justify="right")
        
        total = summary.get('total_checks', 0)
        
        by_level = summary.get('by_level', {})
        if by_level.get('success', 0) > 0:
            success_count = by_level['success']
            success_rate = (success_count / total * 100) if total > 0 else 0
            table.add_row("🟢 성공", str(success_count), f"{success_rate:.1f}%")
        
        if by_level.get('warning', 0) > 0:
            warning_count = by_level['warning']
            warning_rate = (warning_count / total * 100) if total > 0 else 0
            table.add_row("🟡 경고", str(warning_count), f"{warning_rate:.1f}%")
        
        if by_level.get('error', 0) > 0:
            error_count = by_level['error']
            error_rate = (error_count / total * 100) if total > 0 else 0
            table.add_row("🔴 오류", str(error_count), f"{error_rate:.1f}%")
        
        if by_level.get('info', 0) > 0:
            info_count = by_level['info']
            info_rate = (info_count / total * 100) if total > 0 else 0
            table.add_row("🔵 정보", str(info_count), f"{info_rate:.1f}%")
        
        self.console.print(table)
        self.console.print()
    
    def _display_detailed_results(self, report: ValidationReport):
        """상세 검증 결과 표시"""
        categories = set(r.category for r in report.results)
        
        for category in sorted(categories):
            category_results = report.get_results_by_category(category)
            
            # 오류와 경고만 표시
            important_results = [
                r for r in category_results 
                if r.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]
            ]
            
            if not important_results:
                continue
            
            category_names = {
                'configuration': '📁 설정 파일',
                'environment': '🏗️ Kubernetes 환경',
                'dependencies': '📦 의존성',
                'pre-deployment': '🚀 배포 전 검증'
            }
            
            category_title = category_names.get(category, f"📋 {category}")
            self.console.print(f"\n{category_title}")
            self.console.print("─" * len(category_title))
            
            for result in important_results:
                icon = "🔴" if result.level == DiagnosticLevel.ERROR else "🟡"
                self.console.print(f"{icon} {result.message}")
                
                if result.details:
                    self.console.print(f"   {result.details}")
                
                if result.recommendation:
                    self.console.print(f"   💡 {result.recommendation}")
                
                if result.fix_command:
                    self.console.print(f"   🔧 {result.fix_description}: [code]{result.fix_command}[/code]")
                
                self.console.print()
    
    def _display_deployment_readiness(self, summary: Dict[str, Any], report: ValidationReport):
        """배포 준비 상태 표시"""
        is_ready = summary.get('deployment_ready', False)
        
        if is_ready:
            self.console.print(Panel(
                Align.center("✅ 배포 준비 완료\n모든 검증을 통과했습니다."),
                border_style="green",
                title="배포 상태"
            ))
        else:
            critical_count = summary.get('critical_issues', 0)
            self.console.print(Panel(
                Align.center(f"❌ 배포 준비 미완료\n{critical_count}개의 중요 문제를 해결해야 합니다."),
                border_style="red",
                title="배포 상태"
            ))
    
    def _display_recommendations(self, report: ValidationReport):
        """권장사항 표시"""
        fixable_results = report.get_fixable_results()
        
        if fixable_results:
            self.console.print("\n🔧 자동 수정 가능한 문제:")
            for i, result in enumerate(fixable_results[:5], 1):  # 최대 5개만 표시
                self.console.print(f"  {i}. {result.message}")
                if result.fix_description:
                    self.console.print(f"     → {result.fix_description}")
            
            self.console.print(f"\n💡 [bold]sbkube fix[/bold] 명령어로 자동 수정을 실행할 수 있습니다.")


class JSONReportGenerator:
    """JSON 보고서 생성기"""
    
    def generate_report(self, report: ValidationReport) -> str:
        """JSON 보고서 생성"""
        try:
            report_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'generator': 'SBKube Validation System',
                    'version': '1.0'
                },
                'validation': report.to_dict()
            }
            
            return json.dumps(report_data, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"JSON 보고서 생성 실패: {e}")
            raise


class HTMLReportGenerator:
    """HTML 보고서 생성기"""
    
    def generate_report(self, report: ValidationReport) -> str:
        """HTML 보고서 생성"""
        try:
            summary = report.get_summary()
            
            html_content = self._generate_html_template(report, summary)
            return html_content
        
        except Exception as e:
            logger.error(f"HTML 보고서 생성 실패: {e}")
            raise
    
    def _generate_html_template(self, report: ValidationReport, summary: Dict[str, Any]) -> str:
        """HTML 템플릿 생성"""
        mode_descriptions = {
            'basic': '기본 검증',
            'comprehensive': '종합 검증', 
            'pre-deploy': '배포 전 검증',
            'environment': '환경 검증',
            'dependencies': '의존성 검증'
        }
        
        mode = summary.get('validation_mode', 'basic')
        title = f"SBKube {mode_descriptions.get(mode, '검증')} 보고서"
        
        # 카테고리별 결과 정리
        categories = {}
        for result in report.results:
            category = result.category
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        # HTML 생성
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {title}</h1>
            <div class="meta">
                생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                {f' | 검증 시간: {summary.get("duration_seconds", 0):.2f}초' if summary.get('duration_seconds') else ''}
            </div>
        </header>
        
        <section class="summary">
            <h2>검증 요약</h2>
            <div class="stats-grid">
                <div class="stat-card success">
                    <div class="stat-number">{summary.get('by_level', {}).get('success', 0)}</div>
                    <div class="stat-label">성공</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-number">{summary.get('by_level', {}).get('warning', 0)}</div>
                    <div class="stat-label">경고</div>
                </div>
                <div class="stat-card error">
                    <div class="stat-number">{summary.get('by_level', {}).get('error', 0)}</div>
                    <div class="stat-label">오류</div>
                </div>
                <div class="stat-card info">
                    <div class="stat-number">{summary.get('by_level', {}).get('info', 0)}</div>
                    <div class="stat-label">정보</div>
                </div>
            </div>
            
            <div class="deployment-status {'ready' if summary.get('deployment_ready') else 'not-ready'}">
                {'✅ 배포 준비 완료' if summary.get('deployment_ready') else '❌ 배포 준비 미완료'}
            </div>
        </section>
        
        <section class="details">
            <h2>상세 결과</h2>
            {self._generate_category_sections(categories)}
        </section>
        
        <section class="recommendations">
            <h2>권장사항</h2>
            {self._generate_recommendations_section(report)}
        </section>
    </div>
    
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>
"""
        return html
    
    def _generate_category_sections(self, categories: Dict[str, List[ValidationResult]]) -> str:
        """카테고리별 섹션 생성"""
        category_names = {
            'configuration': '📁 설정 파일',
            'environment': '🏗️ Kubernetes 환경', 
            'dependencies': '📦 의존성',
            'pre-deployment': '🚀 배포 전 검증'
        }
        
        sections = []
        for category, results in categories.items():
            category_title = category_names.get(category, f"📋 {category}")
            
            important_results = [
                r for r in results 
                if r.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]
            ]
            
            if not important_results:
                continue
            
            section = f"""
            <div class="category-section">
                <h3>{category_title}</h3>
                <div class="results">
            """
            
            for result in important_results:
                icon = "🔴" if result.level == DiagnosticLevel.ERROR else "🟡"
                status_class = "error" if result.level == DiagnosticLevel.ERROR else "warning"
                
                section += f"""
                <div class="result-item {status_class}">
                    <div class="result-header">
                        <span class="result-icon">{icon}</span>
                        <span class="result-message">{result.message}</span>
                        <span class="result-severity">{result.severity.value}</span>
                    </div>
                """
                
                if result.details:
                    section += f'<div class="result-details">{result.details}</div>'
                
                if result.recommendation:
                    section += f'<div class="result-recommendation">💡 {result.recommendation}</div>'
                
                if result.fix_command:
                    section += f'<div class="result-fix">🔧 {result.fix_description}: <code>{result.fix_command}</code></div>'
                
                section += "</div>"
            
            section += "</div></div>"
            sections.append(section)
        
        return "".join(sections)
    
    def _generate_recommendations_section(self, report: ValidationReport) -> str:
        """권장사항 섹션 생성"""
        fixable_results = report.get_fixable_results()
        
        if not fixable_results:
            return "<p>자동 수정 가능한 문제가 없습니다.</p>"
        
        section = "<div class='recommendations-list'>"
        section += "<h4>🔧 자동 수정 가능한 문제:</h4>"
        section += "<ul>"
        
        for result in fixable_results[:10]:  # 최대 10개
            section += f"<li>{result.message}"
            if result.fix_description:
                section += f" → {result.fix_description}"
            section += "</li>"
        
        section += "</ul>"
        section += "<p><strong>sbkube fix</strong> 명령어로 자동 수정을 실행할 수 있습니다.</p>"
        section += "</div>"
        
        return section
    
    def _get_css_styles(self) -> str:
        """CSS 스타일 반환"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        header h1 {
            color: #2563eb;
            margin-bottom: 10px;
        }
        
        .meta {
            color: #666;
            font-size: 14px;
        }
        
        section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        h2 {
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            text-align: center;
            padding: 20px;
            border-radius: 8px;
            color: white;
        }
        
        .stat-card.success { background: #10b981; }
        .stat-card.warning { background: #f59e0b; }
        .stat-card.error { background: #ef4444; }
        .stat-card.info { background: #3b82f6; }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .deployment-status {
            text-align: center;
            padding: 20px;
            border-radius: 8px;
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .deployment-status.ready {
            background: #dcfce7;
            color: #166534;
        }
        
        .deployment-status.not-ready {
            background: #fef2f2;
            color: #dc2626;
        }
        
        .category-section {
            margin-bottom: 30px;
        }
        
        .category-section h3 {
            color: #374151;
            margin-bottom: 15px;
        }
        
        .result-item {
            border-left: 4px solid #e5e7eb;
            margin-bottom: 15px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 0 5px 5px 0;
        }
        
        .result-item.error {
            border-left-color: #ef4444;
            background: #fef2f2;
        }
        
        .result-item.warning {
            border-left-color: #f59e0b;
            background: #fffbeb;
        }
        
        .result-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .result-message {
            flex: 1;
            font-weight: 500;
        }
        
        .result-severity {
            background: #6b7280;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .result-details,
        .result-recommendation,
        .result-fix {
            margin-top: 8px;
            padding-left: 20px;
            font-size: 14px;
        }
        
        .result-recommendation {
            color: #059669;
        }
        
        .result-fix {
            color: #7c3aed;
        }
        
        code {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        
        .recommendations-list ul {
            margin-left: 20px;
        }
        
        .recommendations-list li {
            margin-bottom: 8px;
        }
        """
    
    def _get_javascript(self) -> str:
        """JavaScript 코드 반환"""
        return """
        // 페이지 로드 시 애니메이션
        document.addEventListener('DOMContentLoaded', function() {
            const sections = document.querySelectorAll('section');
            sections.forEach((section, index) => {
                section.style.opacity = '0';
                section.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    section.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    section.style.opacity = '1';
                    section.style.transform = 'translateY(0)';
                }, index * 100);
            });
        });
        
        // 결과 아이템 클릭으로 세부사항 토글
        document.querySelectorAll('.result-item').forEach(item => {
            item.addEventListener('click', function() {
                const details = this.querySelector('.result-details');
                if (details) {
                    details.style.display = details.style.display === 'none' ? 'block' : 'none';
                }
            });
        });
        """