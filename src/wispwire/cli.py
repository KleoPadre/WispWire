from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from wispwire.capture import CaptureError, CaptureSession
from wispwire.diagnostics import collect_doctor_report, list_interfaces
from wispwire.file_source import FilePacketSource
from wispwire.live_controller import LiveCaptureController
from wispwire.live_source import LivePacketSource
from wispwire.live_tui import LiveCaptureApp, LiveCaptureRuntime
from wispwire.packets import PacketDetails, PacketSummary
from wispwire.sessions import SessionStorage
from wispwire.tshark import (
    TsharkReadError,
    read_display_filter_fields,
    read_packet_details,
)
from wispwire.tui import WispWireApp
from wispwire.wireshark import inspect_tool

app = typer.Typer(
    help="WispWire is a terminal utility for network-analysis diagnostics."
)
console = Console()


@app.callback()
def main() -> None:
    """Run WispWire."""


@app.command()
def doctor() -> None:
    """Check tools and live-capture availability."""
    report = collect_doctor_report()
    console.print("[bold]WispWire Diagnostics[/bold]")
    console.print(f"Python: {report.python_version}")
    console.print(f"WispWire version: {report.wispwire_version}")
    sqlite_status = "OK" if report.sqlite_fts5.available else "ERROR"
    console.print(f"SQLite FTS5 trigram: {sqlite_status}")

    tools_table = Table(title="Tools")
    tools_table.add_column("Tool")
    tools_table.add_column("Path")
    tools_table.add_column("Version")
    tools_table.add_column("Status")
    for tool in report.tools:
        status = "OK" if tool.error is None else "ERROR"
        tools_table.add_row(
            tool.name,
            str(tool.path) if tool.path is not None else "—",
            tool.version or "—",
            status,
        )
    console.print(tools_table)

    _print_interfaces(report.interfaces)
    if not report.sqlite_fts5.available:
        console.print(f"[yellow]Warning: {report.sqlite_fts5.error}[/yellow]")
    if report.capture_warning is not None:
        console.print(f"[yellow]Warning: {report.capture_warning}[/yellow]")


@app.command()
def interfaces() -> None:
    """Show available interfaces for live capture."""
    available_interfaces = list_interfaces()
    if not available_interfaces:
        console.print("No interfaces found. Check dumpcap and capture permissions.")
        return

    _print_interfaces(available_interfaces)


@app.command()
def capture(
    interface: str = typer.Option(..., "--iface", help="Interface for live capture."),
) -> None:
    """Start live capture in the live-TUI."""
    dumpcap = inspect_tool("dumpcap")
    if dumpcap.path is None or dumpcap.error is not None:
        console.print(
            "dumpcap is unavailable. Run `wispwire doctor` to check the environment."
        )
        raise typer.Exit(code=1)

    mergecap = inspect_tool("mergecap")
    if mergecap.path is None or mergecap.error is not None:
        console.print(
            "mergecap is unavailable. Run `wispwire doctor` to check the environment."
        )
        raise typer.Exit(code=1)

    if interface not in list_interfaces():
        console.print(f"Interface {interface} is unavailable.")
        raise typer.Exit(code=2)

    tshark = inspect_tool("tshark")
    if tshark.path is None or tshark.error is not None:
        console.print(
            "TShark is unavailable. Run `wispwire doctor` to check the environment."
        )
        raise typer.Exit(code=1)
    dumpcap_path = dumpcap.path
    mergecap_path = mergecap.path
    tshark_path = tshark.path

    try:

        def create_runtime(selected_interface: str) -> LiveCaptureRuntime:
            session = CaptureSession(
                dumpcap_path,
                mergecap_path,
                selected_interface,
                storage=SessionStorage(),
            )
            source = LivePacketSource(tshark_path)
            controller = LiveCaptureController(
                session,
                source,
                destination_factory=_capture_destination,
            )
            return LiveCaptureRuntime(controller, source.query, source.read_details)

        runtime = create_runtime(interface)
        display_filter_fields = read_display_filter_fields(tshark_path)
        saved_path = LiveCaptureApp(
            interface,
            runtime.controller,
            runtime.query_packets,
            runtime.read_details,
            display_filter_fields=display_filter_fields,
            available_interfaces=list_interfaces(),
            runtime_factory=create_runtime,
        ).run(mouse=False)
        if saved_path is not None:
            _open_capture_in_tui(saved_path)
    except CaptureError as error:
        console.print(f"Live-capture error: {error}")
        raise typer.Exit(code=1) from None


@app.command()
def open(
    capture_path: Path,
    limit: int = typer.Option(1000, min=1, help="Maximum number of packets to show."),
    display_filter: str = typer.Option("", "--filter", help="Display filter TShark."),
) -> None:
    """Open an existing capture in the TUI."""
    _open_capture_in_tui(capture_path, limit=limit, display_filter=display_filter)


def _open_capture_in_tui(
    capture_path: Path,
    *,
    limit: int = 1000,
    display_filter: str = "",
) -> None:
    """Open an existing capture file in the shared file TUI."""
    if not capture_path.exists():
        console.print("Capture file not found.")
        raise typer.Exit(code=2)
    if not capture_path.is_file():
        console.print("Expected a capture file.")
        raise typer.Exit(code=2)

    status = inspect_tool("tshark")
    if status.path is None:
        console.print(
            "TShark is unavailable. Run `wispwire doctor` to check the environment."
        )
        raise typer.Exit(code=1)
    tshark_path = status.path

    source: FilePacketSource | None = None
    try:
        source = FilePacketSource(capture_path, tshark_path)
        packets = source.load(limit)
        if not packets:
            console.print("No packets found.")
            return

        def read_details(packet: PacketSummary) -> PacketDetails:
            return read_packet_details(capture_path, tshark_path, packet.number)

        WispWireApp(
            packets,
            capture_path.name,
            read_details,
            query_packets=source.query,
            initial_filter=display_filter,
        ).run(mouse=False)
    except TsharkReadError as error:
        console.print(f"Could not read capture: {error}")
        raise typer.Exit(code=1) from None
    finally:
        if source is not None:
            source.close()


def _capture_destination() -> Path:
    """Return a new persistent live-capture path without creating the file."""
    catalog = Path.home() / "WispWire" / "Captures"
    catalog.mkdir(parents=True, exist_ok=True)
    stem = f"capture_{datetime.now().astimezone():%Y-%m-%d_%H-%M-%S}"
    destination = catalog / f"{stem}.pcapng"
    suffix = 2
    while destination.exists():
        destination = catalog / f"{stem}-{suffix}.pcapng"
        suffix += 1
    return destination


def _print_interfaces(interfaces: tuple[str, ...]) -> None:
    """Print a numbered list of network interfaces."""
    if not interfaces:
        console.print("No interfaces found.")
        return

    console.print("[bold]Interfaces[/bold]")
    for number, interface in enumerate(interfaces, start=1):
        console.print(f"{number}. {interface}")


if __name__ == "__main__":
    app()
