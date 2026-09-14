"""Streaming live-capture controller with no UI-thread blocking."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from wispwire.capture import CaptureError, CaptureSession, CaptureState
from wispwire.live_source import LivePacketSource
from wispwire.packets import PacketSummary
from wispwire.sessions import SessionSafetyError
from wispwire.tshark import TsharkReadError


@dataclass(frozen=True)
class LivePacketsAdded:
    """Packets added during one controller iteration."""

    packets: tuple[PacketSummary, ...]
    generation: int = 0


@dataclass(frozen=True)
class LiveStateChanged:
    """Current capture state and confirmed totals."""

    state: CaptureState
    packets: int
    size: int
    generation: int = 0


@dataclass(frozen=True)
class LiveSaved:
    """Capture snapshot saved to the requested file."""

    path: Path
    open_in_file_tui: bool


@dataclass(frozen=True)
class LiveFailure:
    """Capture operation ended with an expected error."""

    message: str
    generation: int = 0


LiveEvent: TypeAlias = LivePacketsAdded | LiveStateChanged | LiveSaved | LiveFailure
LiveCommand: TypeAlias = Literal["stop_and_save", "continue", "restart", "save", "quit"]


class LiveCaptureController:
    """Single owner thread for CaptureSession and LivePacketSource."""

    def __init__(
        self,
        capture: CaptureSession,
        source: LivePacketSource,
        *,
        destination_factory: Callable[[], Path] | None = None,
        poll_interval: float = 0.25,
    ) -> None:
        self._capture = capture
        self._source = source
        self._destination_factory = destination_factory or _default_destination
        self._poll_interval = poll_interval
        self._commands: queue.SimpleQueue[LiveCommand] = queue.SimpleQueue()
        self._events: queue.SimpleQueue[LiveEvent] = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._generation = 0
        self._terminal_error: BaseException | None = None

    def start(self) -> None:
        """Start the non-blocking capture-control thread."""
        if self._thread is not None:
            raise RuntimeError("live-capture controller is already running")
        self._thread = threading.Thread(target=self._run, name="wispwire-live-capture")
        self._thread.start()

    def submit(self, command: LiveCommand) -> None:
        """Put a command into the queue without waiting for the capture thread."""
        self._commands.put(command)

    def drain_events(self) -> tuple[LiveEvent, ...]:
        """Return all already published events without blocking."""
        events: list[LiveEvent] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return tuple(events)

    def join(self) -> None:
        """Wait for the controller thread to finish."""
        if self._thread is not None:
            self._thread.join()
        if self._terminal_error is not None:
            raise CaptureError(
                f"could not safely close live capture: {self._terminal_error}"
            ) from self._terminal_error

    def _run(self) -> None:
        try:
            try:
                self._capture.start()
                self._publish_state()
            except (CaptureError, OSError) as error:
                self._fail(error)

            while True:
                if self._process_commands():
                    return
                if self._capture.state in (CaptureState.RUNNING, CaptureState.STOPPED):
                    try:
                        segments = self._capture.collect_closed_segments()
                        packets = self._source.ingest(segments)
                        if packets:
                            self._events.put(
                                LivePacketsAdded(packets, self._generation)
                            )
                        self._publish_state()
                    except (CaptureError, OSError, TsharkReadError) as error:
                        self._fail(error)
                threading.Event().wait(self._poll_interval)
        finally:
            self._close_resources()

    def _process_commands(self) -> bool:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return False

            if command == "quit":
                return True
            try:
                self._process_command(command)
            except (CaptureError, OSError, SessionSafetyError) as error:
                self._fail(error)

    def _process_command(self, command: LiveCommand) -> None:
        if command == "continue":
            if self._capture.state is CaptureState.LIMIT_REACHED:
                raise CaptureError("cannot continue capture: size limit reached")
            self._capture.continue_capture()
        elif command == "restart":
            try:
                self._capture.restart()
            except (CaptureError, OSError) as error:
                self._generation += 1
                self._capture.state = CaptureState.FAILED
                self._fail(error)
                return
            try:
                self._source.reset()
            except (OSError, SessionSafetyError) as error:
                failure: CaptureError | OSError | SessionSafetyError = error
                try:
                    if self._capture.state is CaptureState.RUNNING:
                        self._capture.stop()
                except (CaptureError, OSError) as stop_error:
                    failure = CaptureError(
                        "could not reset the live-capture index; "
                        f"additionally could not stop the new capture: {stop_error}"
                    )
                self._generation += 1
                self._capture.state = CaptureState.FAILED
                self._fail(failure)
                return
            self._generation += 1
        elif command == "save":
            destination = self._destination_factory()
            self._capture.save(destination)
            self._events.put(LiveSaved(destination, False))
        elif command == "stop_and_save":
            destination = self._destination_factory()
            self._capture.stop()
            self._capture.save(destination)
            self._events.put(LiveSaved(destination, True))
        self._publish_state()

    def _publish_state(self) -> None:
        self._events.put(
            LiveStateChanged(
                self._capture.state,
                self._source.packet_count,
                self._capture.confirmed_size,
                self._generation,
            )
        )

    def _fail(
        self, error: CaptureError | OSError | SessionSafetyError | TsharkReadError
    ) -> None:
        self._events.put(LiveFailure(str(error), self._generation))
        self._publish_state()

    def _close_resources(self) -> None:
        terminal_error: BaseException | None = None
        try:
            self._source.close()
        except (CaptureError, OSError, SessionSafetyError) as error:
            terminal_error = error
        try:
            self._capture.close()
        except (CaptureError, OSError, SessionSafetyError) as error:
            if terminal_error is None:
                terminal_error = error
        self._terminal_error = terminal_error


def _default_destination() -> Path:
    """Return the path selected before command submission."""
    raise CaptureError("no path was provided for saving the live capture")
