"""
Cluster configuration resolver.

Resolves cluster configuration with explicit priorities:
1. CLI options (--kubeconfig, --context) - Override
2. sources.yaml (kubeconfig, kubeconfig_context) - Required
3. ❌ KUBECONFIG environment variable - NOT USED
4. ❌ ~/.kube/config default - NOT USED
"""

from pathlib import Path

from rich.console import Console

from sbkube.models.sources_model import SourceScheme

console = Console()


class ClusterConfigError(Exception):
    """클러스터 설정 오류."""


def apply_cluster_config_to_command(
    cmd: list[str],
    kubeconfig: str | None,
    context: str | None,
) -> list[str]:
    """
    명령어에 kubeconfig와 context 옵션을 추가합니다.

    Args:
        cmd: 기본 명령어 리스트 (예: ["helm", "upgrade", ...])
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름

    Returns:
        kubeconfig/context가 추가된 명령어 리스트
    """
    if not kubeconfig or not context:
        return cmd

    # helm 명령어
    if cmd[0] == "helm":
        if kubeconfig:
            cmd.extend(["--kubeconfig", kubeconfig])
        if context:
            cmd.extend(["--kube-context", context])

    # kubectl 명령어
    elif cmd[0] == "kubectl":
        if kubeconfig:
            cmd.extend(["--kubeconfig", kubeconfig])
        if context:
            cmd.extend(["--context", context])

    return cmd


def resolve_cluster_config(
    cli_kubeconfig: str | None,
    cli_context: str | None,
    sources: SourceScheme | None,
) -> tuple[str, str]:
    """
    클러스터 설정 해석 및 검증.

    우선순위:
    1. CLI 옵션 (--kubeconfig, --context) - 오버라이드
    2. sources.yaml (kubeconfig, kubeconfig_context) - 필수

    ❌ KUBECONFIG 환경변수 사용 안 함
    ❌ ~/.kube/config 기본값 사용 안 함

    Args:
        cli_kubeconfig: CLI --kubeconfig 옵션
        cli_context: CLI --context 옵션
        sources: sources.yaml 로드된 객체

    Returns:
        (kubeconfig_path, context_name)

    Raises:
        ClusterConfigError: 클러스터 설정이 없거나 유효하지 않은 경우
    """
    # CLI 옵션 최우선 (오버라이드)
    if cli_kubeconfig and cli_context:
        kubeconfig = str(Path(cli_kubeconfig).expanduser())
        context = cli_context

        console.print("[yellow]⚠️  Using CLI override for cluster configuration[/yellow]")
        console.print(f"  Kubeconfig: {kubeconfig}")
        console.print(f"  Context: {context}")

        # kubeconfig 파일 존재 확인
        if not Path(kubeconfig).exists():
            raise ClusterConfigError(
                f"Kubeconfig file not found: {kubeconfig}\n"
                "Please check the --kubeconfig option.",
            )

        return kubeconfig, context

    # CLI 부분 지정 에러
    if cli_kubeconfig or cli_context:
        raise ClusterConfigError(
            "Both --kubeconfig and --context must be specified together.\n"
            f"Given: --kubeconfig={cli_kubeconfig}, --context={cli_context}",
        )

    # sources.yaml 필수 검증
    if not sources:
        raise ClusterConfigError(
            "❌ sources.yaml file is required but not found.\n\n"
            "SBKube requires explicit cluster configuration to prevent accidental deployments.\n\n"
            "📝 Please create sources.yaml with cluster settings:\n"
            "  cluster: my-cluster\n"
            "  kubeconfig: ~/.kube/config\n"
            "  kubeconfig_context: my-context\n\n"
            "💡 Or use CLI options:\n"
            "  sbkube deploy --kubeconfig <path> --context <name>",
        )

    # sources.yaml에서 kubeconfig/context 필수 확인
    if not sources.kubeconfig or not sources.kubeconfig_context:
        missing_fields = []
        if not sources.kubeconfig:
            missing_fields.append("kubeconfig")
        if not sources.kubeconfig_context:
            missing_fields.append("kubeconfig_context")

        raise ClusterConfigError(
            f"❌ Cluster configuration is incomplete in sources.yaml.\n\n"
            f"Missing required fields: {', '.join(missing_fields)}\n\n"
            f"Current values:\n"
            f"  kubeconfig: {sources.kubeconfig or '(missing)'}\n"
            f"  kubeconfig_context: {sources.kubeconfig_context or '(missing)'}\n\n"
            f"📝 Please update sources.yaml:\n"
            f"  cluster: production\n"
            f"  kubeconfig: ~/.kube/prod-config\n"
            f"  kubeconfig_context: prod-cluster",
        )

    # kubeconfig 경로 확장
    kubeconfig = str(Path(sources.kubeconfig).expanduser())
    context = sources.kubeconfig_context

    # kubeconfig 파일 존재 확인
    if not Path(kubeconfig).exists():
        raise ClusterConfigError(
            f"❌ Kubeconfig file not found: {kubeconfig}\n"
            f"   (from sources.yaml: {sources.kubeconfig})\n\n"
            "Please check:\n"
            "  1. File path is correct in sources.yaml\n"
            "  2. File exists and is accessible\n"
            f"  3. Run: ls -la {kubeconfig}",
        )

    # 성공 - 설정 정보 표시
    console.print("[cyan]🔍 Cluster Configuration (from sources.yaml):[/cyan]")
    if sources.cluster:
        console.print(f"  Target Cluster: {sources.cluster}")
    console.print(f"  Kubeconfig: {kubeconfig}")
    console.print(f"  Context: {context}")

    return kubeconfig, context
