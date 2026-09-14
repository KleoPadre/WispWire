"""dumpcap live-capture process control."""

from __future__ import annotations

import os
import queue
import stat
import subprocess
import threading
from collections.abc import Callable, Iterable
from enum import StrEnum
from pathlib import Path

from wispwire.sessions import Session, SessionSafetyError, SessionStorage


class CaptureState(StrEnum):
    """Current live-capture state."""

    RUNNING = "running"
    STOPPED = "stopped"
    LIMIT_REACHED = "limit_reached"
    FAILED = "failed"
    CLOSED = "closed"


class CaptureError(RuntimeError):
    """Live capture cannot safely continue."""


def build_dumpcap_command(
    dumpcap_path: Path, interface: str, output_base: Path
) -> list[str]:
    """Build a dumpcap command with half-second segmentation."""
    return [
        str(dumpcap_path),
        "-i",
        interface,
        "-w",
        str(output_base),
        "-b",
        "duration:0.5",
        "-b",
        "printname:stdout",
    ]


def build_mergecap_command(
    mergecap_path: Path, output_path: Path, segments: tuple[Path, ...]
) -> list[str]:
    """Build a mergecap command for joining segments."""
    return [
        str(mergecap_path),
        "-w",
        str(output_path),
        *(str(path) for path in segments),
    ]


class CaptureSession:
    """Start and stop one dumpcap process."""

    def __init__(
        self,
        dumpcap_path: Path,
        mergecap_path: Path,
        interface: str,
        *,
        storage: SessionStorage,
        max_size: int = 1_073_741_824,
        popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.dumpcap_path = dumpcap_path
        self.mergecap_path = mergecap_path
        self.interface = interface
        self.storage = storage
        self.max_size = max_size
        self._popen = popen
        self._run = run
        self._process: subprocess.Popen[str] | None = None
        self._stdout_lines: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._stderr_lines: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._stdout_reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._stdout_source: object | None = None
        self._stderr_source: object | None = None
        self.session: Session | None = None
        self._segments: list[Path] = []
        self.state = CaptureState.STOPPED

    def start(self) -> None:
        """Create a session and start dumpcap."""
        if self.state is not CaptureState.STOPPED or self.session is not None:
            raise CaptureError("capture can only start from the initial state")

        self.session = self.storage.create_session()
        command = build_dumpcap_command(
            self.dumpcap_path, self.interface, self.session.path / "segment"
        )
        try:
            self._process = self._popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            self.state = CaptureState.FAILED
            raise CaptureError("could not start dumpcap") from error
        self._start_stream_readers()
        self.state = CaptureState.RUNNING

    @property
    def segments(self) -> tuple[Path, ...]:
        """Return confirmed closed capture segments."""
        return tuple(self._segments)

    @property
    def confirmed_size(self) -> int:
        """Return the current session size from confirmed segments."""
        return sum(segment.stat().st_size for segment in self._segments)

    def collect_closed_segments(self) -> tuple[Path, ...]:
        """Register safely finished dumpcap segments from stdout."""
        if self.state not in (CaptureState.RUNNING, CaptureState.STOPPED):
            raise CaptureError("segments can only be read from a running capture")
        if self._process is None:
            raise CaptureError("capture process is unavailable")
        if self.session is None or self._process.stdout is None:
            self.state = CaptureState.FAILED
            raise CaptureError("capture session or stdout is unavailable")

        self._ensure_stream_readers()
        try:
            limit_reached = self._register_closed_segment_lines(
                self._queued_stdout_lines()
            )
        except CaptureError:
            self._drain_after_capture_error()
            raise

        returncode = self._poll_process()
        if limit_reached and returncode is None:
            returncode = self._terminate_existing_process()
            limit_reached = (
                self._register_closed_segment_lines(self._queued_stdout_lines())
                or limit_reached
            )
        elif returncode is not None:
            self._wait_for_stream_readers()
            limit_reached = (
                self._register_closed_segment_lines(self._queued_stdout_lines())
                or limit_reached
            )

        if returncode is not None:
            if returncode != 0:
                self.state = CaptureState.FAILED
                raise CaptureError(self._dumpcap_error(returncode))
            self.state = (
                CaptureState.LIMIT_REACHED if limit_reached else CaptureState.STOPPED
            )
        return self.segments

    def continue_capture(self) -> None:
        """Continue a stopped capture in an already created session."""
        if self.state is CaptureState.LIMIT_REACHED:
            raise CaptureError("cannot continue capture: size limit reached")
        if self.state is not CaptureState.STOPPED or self.session is None:
            raise CaptureError("only a stopped capture can be continued")

        self._ensure_stream_readers()
        self._wait_for_stream_readers()
        if self._register_closed_segment_lines(self._queued_stdout_lines()):
            self.state = CaptureState.LIMIT_REACHED
            raise CaptureError("cannot continue capture: size limit reached")

        command = build_dumpcap_command(
            self.dumpcap_path, self.interface, self.session.path / "segment"
        )
        try:
            self._process = self._popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            self.state = CaptureState.FAILED
            raise CaptureError("could not start dumpcap") from error
        self._start_stream_readers()
        self.state = CaptureState.RUNNING

    def stop(self) -> None:
        """Stop dumpcap and check its exit code."""
        if self.state is not CaptureState.RUNNING or self._process is None:
            raise CaptureError("only a running capture can be stopped")

        returncode = self._terminate_existing_process()
        assert returncode is not None
        try:
            limit_reached = self._register_closed_segment_lines(
                self._queued_stdout_lines()
            )
        except CaptureError:
            self.state = CaptureState.FAILED
            raise
        if returncode != 0:
            self.state = CaptureState.FAILED
            raise CaptureError(self._dumpcap_error(returncode))
        self.state = (
            CaptureState.LIMIT_REACHED if limit_reached else CaptureState.STOPPED
        )

    def save(self, destination: Path) -> Path:
        """Save confirmed segments into a new PCAPNG file."""
        destination = Path(destination)
        if destination.exists():
            raise CaptureError("destination file already exists")

        was_running = self.state is CaptureState.RUNNING
        if was_running:
            self.stop()
        if not self._segments:
            raise CaptureError("at least one closed segment is required for saving")

        temporary = destination.with_name(f"{destination.name}.part")
        temporary_fd: int | None = None
        temporary_identity: os.stat_result | None = None
        try:
            temporary_fd = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            temporary_identity = os.fstat(temporary_fd)
            result = self._run(
                build_mergecap_command(self.mergecap_path, temporary, self.segments),
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
            if result.returncode != 0:
                error = result.stderr.strip() or (
                    f"mergecap exited with code {result.returncode}"
                )
                raise CaptureError(error)
            if not self._is_expected_temporary(temporary, temporary_identity):
                raise CaptureError("temporary .part file was unsafely replaced")
            os.link(temporary, destination, follow_symlinks=False)
        except FileExistsError as error:
            if temporary_fd is None:
                raise CaptureError(
                    "temporary .part file already exists or is unsafe"
                ) from error
            raise CaptureError("destination file already exists") from error
        except OSError as error:
            raise CaptureError("could not save capture snapshot") from error
        except CaptureError:
            raise
        finally:
            if temporary_fd is not None and temporary_identity is not None:
                self._unlink_owned_temporary(temporary, temporary_identity)
                os.close(temporary_fd)

        if was_running and self.state is CaptureState.STOPPED:
            self.continue_capture()
        return destination

    def restart(self) -> None:
        """Close the current session and start a new one."""
        if self.state not in (
            CaptureState.STOPPED,
            CaptureState.FAILED,
            CaptureState.LIMIT_REACHED,
        ):
            raise CaptureError("restart is available only for a stopped capture")
        self._drain_before_cleanup()
        if self.session is not None and not self.storage.close_session(self.session):
            raise CaptureError("could not safely close capture session")

        self._process = None
        self._stdout_reader = None
        self._stderr_reader = None
        self._stdout_source = None
        self._stderr_source = None
        self.session = None
        self._segments.clear()
        self.state = CaptureState.STOPPED
        self.start()

    def close(self) -> bool:
        """Stop capture and close only its own session."""
        if self.state is CaptureState.CLOSED:
            return True
        self._drain_before_cleanup()
        if self.session is not None and not self.storage.close_session(self.session):
            raise CaptureError("could not safely close capture session")

        self._process = None
        self._stdout_reader = None
        self._stderr_reader = None
        self._stdout_source = None
        self._stderr_source = None
        self.session = None
        self._segments.clear()
        self.state = CaptureState.CLOSED
        return True

    def _terminate_existing_process(self) -> int | None:
        """Terminate the current process regardless of capture state."""
        if self._process is None:
            return None
        self._ensure_stream_readers()
        if self._poll_process() is None:
            self._process.terminate()
        returncode = self._process.wait()
        self._wait_for_stream_readers()
        return returncode

    def _poll_process(self) -> int | None:
        """Return the exit code without waiting for the process."""
        assert self._process is not None
        return self._process.poll()

    def _drain_before_cleanup(self) -> None:
        """Drain output and register final segments before removing the session."""
        if self._process is None:
            return
        self._terminate_existing_process()
        self._register_closed_segment_lines(self._queued_stdout_lines())

    def _drain_after_capture_error(self) -> None:
        """Stop a failed process and drain its streams without blocking."""
        if self._process is None:
            return
        self._terminate_existing_process()

    def _register_closed_segment_lines(self, lines: Iterable[str]) -> bool:
        """Validate and register closed-segment lines."""
        if self.session is None:
            self.state = CaptureState.FAILED
            raise CaptureError("capture session is unavailable")

        limit_reached = False
        for line in lines:
            segment = Path(line.strip())
            if not self._is_safe_segment(segment):
                self.state = CaptureState.FAILED
                raise CaptureError("segment is outside the session or unsafe")
            if segment in self._segments:
                continue
            try:
                self.session = self.storage.register_file(self.session, segment)
                size = self.storage.session_size(self.session)
            except (OSError, SessionSafetyError) as error:
                self.state = CaptureState.FAILED
                raise CaptureError("could not safely register segment") from error
            self._segments.append(segment)
            limit_reached = limit_reached or size > self.max_size
        return limit_reached

    def _dumpcap_error(self, returncode: int) -> str:
        """Return dumpcap stderr or an exit-code message."""
        stderr = "".join(self._queued_stderr_lines()).strip()
        return stderr or f"dumpcap exited with code {returncode}"

    @staticmethod
    def _is_expected_temporary(temporary: Path, expected: os.stat_result) -> bool:
        """Verify the regular .part file created by the current save() call."""
        try:
            current = temporary.lstat()
        except OSError:
            return False
        return (
            stat.S_ISREG(current.st_mode)
            and current.st_dev == expected.st_dev
            and current.st_ino == expected.st_ino
            and current.st_nlink == 1
        )

    @classmethod
    def _unlink_owned_temporary(cls, temporary: Path, expected: os.stat_result) -> None:
        """Remove only the regular .part file still owned by this call."""
        try:
            current = temporary.lstat()
        except OSError:
            return
        if not (
            stat.S_ISREG(current.st_mode)
            and current.st_dev == expected.st_dev
            and current.st_ino == expected.st_ino
        ):
            return
        try:
            temporary.unlink()
        except OSError:
            return

    def _is_safe_segment(self, segment: Path) -> bool:
        """Verify that a segment is a regular file inside the current session."""
        assert self.session is not None
        try:
            segment.resolve().relative_to(self.session.path.resolve())
        except (OSError, ValueError):
            return False
        return (
            segment.exists()
            and not segment.is_symlink()
            and segment.is_file()
            and segment.stat().st_nlink == 1
        )

    def _start_stream_readers(self) -> None:
        """Start background readers for dumpcap stdout and stderr."""
        self._stdout_lines = queue.SimpleQueue()
        self._stderr_lines = queue.SimpleQueue()
        self._stdout_reader = None
        self._stderr_reader = None
        self._stdout_source = None
        self._stderr_source = None
        self._ensure_stream_readers()

    def _ensure_stream_readers(self) -> None:
        """Attach non-blocking readers to the current process streams."""
        assert self._process is not None
        stdout = self._process.stdout
        if stdout is not None and stdout is not self._stdout_source:
            self._stdout_source = stdout
            self._stdout_reader = self._start_stream_reader(
                stdout, self._stdout_lines, "wispwire-dumpcap-stdout"
            )
        stderr = self._process.stderr
        if stderr is not None and stderr is not self._stderr_source:
            self._stderr_source = stderr
            self._stderr_reader = self._start_stream_reader(
                stderr, self._stderr_lines, "wispwire-dumpcap-stderr"
            )

    @staticmethod
    def _start_stream_reader(
        stream: Iterable[str], lines: queue.SimpleQueue[str], name: str
    ) -> threading.Thread:
        reader = threading.Thread(
            target=CaptureSession._read_stream,
            args=(stream, lines),
            name=name,
            daemon=True,
        )
        reader.start()
        return reader

    @staticmethod
    def _read_stream(stream: Iterable[str], lines: queue.SimpleQueue[str]) -> None:
        """Move stream lines into a queue without blocking the main thread."""
        try:
            for line in stream:
                lines.put(line)
        except (OSError, ValueError):
            return

    def _wait_for_stream_readers(self) -> None:
        """Wait for EOF on both streams after dumpcap exits."""
        if self._stdout_reader is not None:
            self._stdout_reader.join()
        if self._stderr_reader is not None:
            self._stderr_reader.join()

    def _queued_stdout_lines(self) -> tuple[str, ...]:
        """Drain already received stdout lines without waiting."""
        if self._stdout_reader is not None:
            self._stdout_reader.join(timeout=0.01)
        return self._queued_lines(self._stdout_lines)

    def _queued_stderr_lines(self) -> tuple[str, ...]:
        """Drain already received stderr lines without waiting."""
        return self._queued_lines(self._stderr_lines)

    @staticmethod
    def _queued_lines(lines_queue: queue.SimpleQueue[str]) -> tuple[str, ...]:
        """Drain accumulated lines from the given queue."""
        lines: list[str] = []
        while True:
            try:
                lines.append(lines_queue.get_nowait())
            except queue.Empty:
                return tuple(lines)
