"""Lightweight performance profiling utilities for SBKube.

Enabled via environment variable SBKUBE_PERF=1.
Records durations for subprocess calls and explicit timers,
and writes JSONL events under tmp/perf/.
"""

from __future__ import annotations

import atexit
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


_TRUTHY = {"1", "true", "yes", "on"}


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in _TRUTHY


def _cmd_to_display(cmd: Any, max_len: int = 300) -> str:
    try:
        if isinstance(cmd, (list, tuple)):
            rendered = " ".join(str(part) for part in cmd)
        else:
            rendered = str(cmd)
    except Exception:
        rendered = "<unprintable>"

    if len(rendered) > max_len:
        return f"{rendered[:max_len]}..."
    return rendered


def _cmd_to_tool(cmd: Any) -> str:
    if isinstance(cmd, (list, tuple)) and cmd:
        return str(cmd[0])
    try:
        text = str(cmd).strip()
    except Exception:
        return "unknown"
    if not text:
        return "unknown"
    return text.split()[0]


@dataclass
class PerfEvent:
    """Single performance event."""

    name: str
    duration_seconds: float
    timestamp: float
    tags: dict[str, Any] = field(default_factory=dict)


class PerfRecorder:
    """Collects and summarizes performance events."""

    def __init__(self) -> None:
        self.enabled = False
        self.events: list[PerfEvent] = []
        self.output_format: str = "human"
        self.log_path: Path | None = None
        self._process_start: float | None = None
        self._subprocess_patched = False
        self._atexit_registered = False

    def enable(self, output_format: str | None = None, log_dir: Path | None = None) -> None:
        """Enable perf recording and register subprocess wrapper."""
        if self.enabled:
            return
        self.enabled = True
        if output_format:
            self.output_format = output_format
        self._process_start = time.perf_counter()

        log_dir = log_dir or Path("tmp") / "perf"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we cannot create the directory, just disable file output
            log_dir = None
        if log_dir:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.log_path = log_dir / f"perf-{timestamp}.jsonl"

        self._patch_subprocess_run()
        if not self._atexit_registered:
            atexit.register(self.flush)
            self._atexit_registered = True

    def record(self, name: str, duration_seconds: float, **tags: Any) -> None:
        """Record a performance event."""
        if not self.enabled:
            return
        event = PerfEvent(
            name=name,
            duration_seconds=duration_seconds,
            timestamp=time.time(),
            tags=tags,
        )
        self.events.append(event)

    def _patch_subprocess_run(self) -> None:
        if self._subprocess_patched:
            return
        import subprocess  # local import to avoid side effects

        if getattr(subprocess.run, "_sbkube_perf_wrapped", False):
            self._subprocess_patched = True
            return

        original_run = subprocess.run

        def wrapped_run(*args, **kwargs):
            if not self.enabled:
                return original_run(*args, **kwargs)

            cmd = args[0] if args else kwargs.get("args")
            tool = _cmd_to_tool(cmd)
            cmd_display = _cmd_to_display(cmd)
            start = time.perf_counter()
            try:
                result = original_run(*args, **kwargs)
                duration = time.perf_counter() - start
                self.record(
                    name="subprocess",
                    duration_seconds=duration,
                    tool=tool,
                    cmd=cmd_display,
                    returncode=getattr(result, "returncode", None),
                )
                return result
            except Exception as exc:  # noqa: BLE001 - pass through
                duration = time.perf_counter() - start
                tags = {
                    "tool": tool,
                    "cmd": cmd_display,
                    "error": type(exc).__name__,
                }
                if hasattr(exc, "returncode"):
                    tags["returncode"] = getattr(exc, "returncode")
                self.record(
                    name="subprocess",
                    duration_seconds=duration,
                    **tags,
                )
                raise

        wrapped_run._sbkube_perf_wrapped = True  # type: ignore[attr-defined]
        subprocess.run = wrapped_run
        self._subprocess_patched = True

    def summary(self) -> dict[str, Any]:
        """Build a summary report of recorded events."""
        totals_by_name: dict[str, float] = {}
        counts_by_name: dict[str, int] = {}
        totals_by_tool: dict[str, float] = {}
        counts_by_tool: dict[str, int] = {}

        for event in self.events:
            totals_by_name[event.name] = totals_by_name.get(event.name, 0.0) + event.duration_seconds
            counts_by_name[event.name] = counts_by_name.get(event.name, 0) + 1

            tool = event.tags.get("tool")
            if tool:
                totals_by_tool[tool] = totals_by_tool.get(tool, 0.0) + event.duration_seconds
                counts_by_tool[tool] = counts_by_tool.get(tool, 0) + 1

        slowest = sorted(self.events, key=lambda e: e.duration_seconds, reverse=True)[:10]

        process_duration = None
        if self._process_start is not None:
            process_duration = time.perf_counter() - self._process_start

        return {
            "process_duration_seconds": process_duration,
            "totals_by_name": totals_by_name,
            "counts_by_name": counts_by_name,
            "totals_by_tool": totals_by_tool,
            "counts_by_tool": counts_by_tool,
            "slowest_events": slowest,
        }

    def _format_duration(self, seconds: float | None) -> str:
        if seconds is None:
            return "-"
        return f"{seconds:.2f}s"

    def flush(self) -> None:
        """Write events to disk and print a summary (if safe)."""
        if not self.enabled:
            return

        if self.log_path:
            try:
                with self.log_path.open("w", encoding="utf-8") as fp:
                    for event in self.events:
                        payload = {
                            "name": event.name,
                            "duration_seconds": event.duration_seconds,
                            "timestamp": event.timestamp,
                            "tags": event.tags,
                        }
                        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                # Ignore file write errors
                pass

        # Avoid polluting structured outputs
        if self.output_format in {"json", "yaml"}:
            return

        if not self.events:
            return

        from sbkube.utils.logger import logger

        summary = self.summary()
        total_time = summary.get("process_duration_seconds")
        logger.heading("Perf Summary")
        logger.info(f"Total process time: {self._format_duration(total_time)}")

        totals_by_name = summary.get("totals_by_name", {})
        if totals_by_name:
            top_by_name = sorted(totals_by_name.items(), key=lambda x: x[1], reverse=True)[:6]
            logger.info("Top stages (by total time):")
            for name, duration in top_by_name:
                logger.info(f"- {name}: {self._format_duration(duration)}")

        totals_by_tool = summary.get("totals_by_tool", {})
        counts_by_tool = summary.get("counts_by_tool", {})
        if totals_by_tool:
            logger.info("Subprocess by tool:")
            for tool, duration in sorted(totals_by_tool.items(), key=lambda x: x[1], reverse=True):
                count = counts_by_tool.get(tool, 0)
                avg = duration / count if count else 0
                logger.info(f"- {tool}: {self._format_duration(duration)} (calls: {count}, avg: {avg:.2f}s)")

        slowest = summary.get("slowest_events", [])
        if slowest:
            logger.info("Slowest commands:")
            for event in slowest:
                cmd = event.tags.get("cmd", "")
                tool = event.tags.get("tool", "")
                label = f"{tool} {cmd}".strip() if cmd else tool
                logger.info(f"- {label}: {self._format_duration(event.duration_seconds)}")

        if self.log_path:
            logger.info(f"Raw perf log: {self.log_path}")


_perf_recorder = PerfRecorder()


def enable_from_env(output_format: str | None = None) -> None:
    """Enable perf recording if SBKUBE_PERF is set."""
    if _env_truthy("SBKUBE_PERF"):
        _perf_recorder.enable(output_format=output_format)


@contextmanager
def perf_timer(name: str, **tags: Any) -> Iterable[None]:
    """Context manager for timing code blocks."""
    if not _perf_recorder.enabled:
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        _perf_recorder.record(name, duration, **tags)
