"""Deployment status checker utility for validating app-group dependencies."""

from pathlib import Path

from sbkube.state.database import DeploymentDatabase, DeploymentStatus


def get_current_cluster() -> str:
    """Get current cluster from kubectl context.

    Returns:
        str: Current cluster name, or "unknown" if not available

    """
    import subprocess

    try:
        result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "unknown"


class DeploymentChecker:
    """Utility class for checking deployment status of app-groups.

    This class provides methods to validate whether app-groups are deployed
    in the cluster, which is useful for dependency validation.
    """

    def __init__(
        self,
        base_dir: Path,
        cluster: str | None = None,
        namespace: str | None = None,
    ):
        """Initialize DeploymentChecker.

        Args:
            base_dir: Base directory containing app-group directories
            cluster: Kubernetes cluster name (defaults to current context)
            namespace: Kubernetes namespace (optional, can be per-app-group)

        """
        self.base_dir = Path(base_dir)
        self.cluster = cluster or get_current_cluster()
        self.namespace = namespace
        self.db = DeploymentDatabase()

    def check_app_group_deployed(
        self, app_config_dir: str, namespace: str | None = None
    ) -> tuple[bool, str]:
        """Check if an app-group is successfully deployed.

        If namespace is not provided, automatically detects the namespace
        from deployment history. This allows dependencies to be in different
        namespaces than the current app.

        Args:
            app_config_dir: App-group directory name (e.g., "a000_infra_network")
            namespace: Kubernetes namespace (optional - if None, auto-detects from DB)

        Returns:
            tuple[bool, str]: (is_deployed, status_message)
                - is_deployed: True if successfully deployed, False otherwise
                - status_message: Human-readable status description with namespace info

        """
        # Resolve full path to app-group directory
        app_dir_path = str((self.base_dir / app_config_dir).resolve())

        # Try namespace-specific query first (if namespace provided)
        if namespace:
            try:
                latest = self.db.get_latest_deployment(
                    cluster=self.cluster,
                    namespace=namespace,
                    app_config_dir=app_dir_path,
                )
                if latest:
                    if latest.status != DeploymentStatus.SUCCESS:
                        return False, f"last status: {latest.status.value}"
                    return (
                        True,
                        f"deployed at {latest.timestamp} in namespace '{namespace}'",
                    )
            except Exception as e:
                return False, f"database error: {e}"

        # Fallback: Search across all namespaces (namespace auto-detection)
        try:
            latest = self.db.get_latest_deployment_any_namespace(
                cluster=self.cluster,
                app_config_dir=app_dir_path,
            )
        except Exception as e:
            return False, f"database error: {e}"

        # No deployment record found
        if not latest:
            return False, "never deployed"

        # Check deployment status
        if latest.status != DeploymentStatus.SUCCESS:
            return False, f"last status: {latest.status.value}"

        # Successfully deployed - include namespace in message
        deployed_ns = latest.namespace
        return True, f"deployed at {latest.timestamp} in namespace '{deployed_ns}'"

    def check_dependencies(self, deps: list[str], namespace: str | None = None) -> dict:
        """Check deployment status of multiple dependencies.

        Args:
            deps: List of app-group directory names
            namespace: Kubernetes namespace (overrides instance namespace)

        Returns:
            dict: Deployment status summary with keys:
                - "all_deployed" (bool): True if all deps are deployed
                - "missing" (list[str]): List of undeployed dep names
                - "details" (dict[str, tuple[bool, str]]): Per-dep status details

        """
        details = {}
        missing = []

        for dep in deps:
            is_deployed, msg = self.check_app_group_deployed(dep, namespace)
            details[dep] = (is_deployed, msg)
            if not is_deployed:
                missing.append(dep)

        return {
            "all_deployed": len(missing) == 0,
            "missing": missing,
            "details": details,
        }

    def get_deployment_info(
        self, app_config_dir: str, namespace: str | None = None
    ) -> dict | None:
        """Get detailed deployment information for an app-group.

        Args:
            app_config_dir: App-group directory name
            namespace: Kubernetes namespace (overrides instance namespace)

        Returns:
            Optional[dict]: Deployment details or None if not found

        """
        app_dir_path = str((self.base_dir / app_config_dir).resolve())
        ns = namespace or self.namespace or "default"

        try:
            latest = self.db.get_latest_deployment(
                cluster=self.cluster,
                namespace=ns,
                app_config_dir=app_dir_path,
            )
        except Exception:
            return None

        if not latest:
            return None

        return {
            "cluster": latest.cluster,
            "namespace": latest.namespace,
            "app_config_dir": latest.app_config_dir,
            "status": latest.status.value,
            "timestamp": str(latest.timestamp),
        }
