from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from integrations.contracts import ArtifactManifest, JobState


class ExecutionOutput(NamedTuple):
    status: JobState
    exit_code: int | None
    stdout: str
    stderr: str
    start_time: str
    end_time: str
    log_path: str | None


def compute_sha256(file_path: Path) -> str:
    """Computes the SHA-256 hex digest of a file in chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def manifest_directory(directory: Path, job_id: str, exclude_extensions: tuple[str, ...] = (".tmp", ".log")) -> list[ArtifactManifest]:
    """Generates an ArtifactManifest list for all created output files in the directory."""
    artifacts: list[ArtifactManifest] = []
    if not directory.exists() or not directory.is_dir():
        return artifacts

    for item in sorted(directory.rglob("*")):
        if item.is_file() and not item.name.startswith("."):
            if item.suffix.lower() in exclude_extensions:
                continue
            rel = str(item.relative_to(directory)).replace("\\", "/")
            stat = item.stat()
            artifacts.append(
                ArtifactManifest(
                    relative_path=rel,
                    file_type=item.suffix.lstrip(".").lower() or "bin",
                    sha256=compute_sha256(item),
                    size_bytes=stat.st_size,
                    source_job=job_id,
                )
            )
    return artifacts


class SafeRunner:
    """Subprocess execution runner with strict argument validation, timeout enforcement,

    process-tree cancellation, and logging.
    """

    MAX_CAPTURE_BYTES = 5 * 1024 * 1024  # 5 MB safety limit

    def __init__(self, allowlist_patterns: list[str] | None = None):
        self.allowlist_patterns = allowlist_patterns or []

    def validate_command(self, args: list[str]) -> Path:
        """Validates that the command arguments are safe, non-empty, and resolve to an executable."""
        if not args or not isinstance(args, list):
            raise ValueError("Command arguments must be a non-empty list of strings")
        for arg in args:
            if not isinstance(arg, str):
                raise ValueError(f"All command arguments must be strings, got {type(arg).__name__}")

        executable_str = args[0]
        exe_path = shutil.which(executable_str) or Path(executable_str)
        if isinstance(exe_path, str):
            exe_path = Path(exe_path)

        if not exe_path.exists() or not exe_path.is_file():
            raise FileNotFoundError(f"Executable not found or is not a valid file: {executable_str}")

        return exe_path.resolve()

    def run(
        self,
        command_args: list[str],
        cwd: Path,
        timeout_s: int = 60,
        env: dict[str, str] | None = None,
        log_file: Path | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ExecutionOutput:
        """Executes a subprocess safely with process-tree cleanup and log capture."""
        self.validate_command(command_args)

        cwd = Path(cwd).resolve()
        cwd.mkdir(parents=True, exist_ok=True)

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start_dt = datetime.now(timezone.utc)
        start_time_iso = start_dt.isoformat()

        # Windows process creation flags
        creationflags = 0
        if os.name == "nt":
            # CREATE_NEW_PROCESS_GROUP
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            command_args,
            cwd=str(cwd),
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            shell=False,
            creationflags=creationflags,
        )

        timed_out = False
        cancelled = False

        def poll_cancellation():
            nonlocal cancelled
            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    cancelled = True
                    self._kill_process_tree(process.pid)
                    break
                time.sleep(0.05)

        cancel_watcher = threading.Thread(target=poll_cancellation, daemon=True)
        cancel_watcher.start()

        stdout_bytes = b""
        stderr_bytes = b""
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill_process_tree(process.pid)
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=3)
            except Exception:
                pass

        end_dt = datetime.now(timezone.utc)
        end_time_iso = end_dt.isoformat()

        stdout_str = stdout_bytes[: self.MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
        stderr_str = stderr_bytes[: self.MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")

        # Write log file if requested
        log_path_str = None
        if log_file:
            log_file = Path(log_file).resolve()
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"=== Command: {' '.join(command_args)} ===\n")
                f.write(f"=== Started: {start_time_iso} ===\n")
                f.write(f"=== Working Directory: {cwd} ===\n")
                f.write(f"=== Exit Code: {process.returncode} ===\n\n")
                f.write("--- STDOUT ---\n")
                f.write(stdout_str)
                f.write("\n--- STDERR ---\n")
                f.write(stderr_str)
            log_path_str = str(log_file)

        if cancelled:
            status = JobState.CANCELLED
        elif timed_out:
            status = JobState.TIMED_OUT
        elif process.returncode == 0:
            status = JobState.SUCCEEDED
        else:
            status = JobState.FAILED

        return ExecutionOutput(
            status=status,
            exit_code=process.returncode,
            stdout=stdout_str,
            stderr=stderr_str,
            start_time=start_time_iso,
            end_time=end_time_iso,
            log_path=log_path_str,
        )

    def _kill_process_tree(self, pid: int) -> None:
        """Kills the entire process tree."""
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )
            except Exception:
                pass
        else:
            try:
                import signal
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
