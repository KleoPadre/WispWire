"""Shared helpers for rendering packets in the TUI."""

from rich.text import Text
from textual.widgets import DataTable

from wispwire.packets import PacketDetails, PacketSummary

_WIDE_COLUMN_WIDTHS = {
    "No.": 6,
    "Time": 12,
    "Source": 18,
    "Destination": 18,
    "URL": 28,
    "Protocol": 10,
    "Length": 8,
    "Info": 54,
}
_NARROW_COLUMN_WIDTHS = {
    "No.": 6,
    "Source": 18,
    "Protocol": 10,
    "Info": 52,
}
_DEFAULT_PROTOCOL_STYLE = "bold white on #303030"
_PROTOCOL_STYLES = {
    "ARP": "bold white on #3a3325",
    "DNS": "bold cyan on #123047",
    "MDNS": "bold white on #303030",
    "NBSS": "bold magenta on #33213f",
    "SMB": "bold magenta on #33213f",
    "SMB2": "bold magenta on #33213f",
    "TCP": "bold #c8b6ff on #2d1f55",
    "TLS": "bold green on #12382d",
    "TLSV1.2": "bold green on #12382d",
    "TLSV1.3": "bold green on #12382d",
    "UDP": "bold #ffd166 on #403518",
    "HTTP": "bold blue on #142d4f",
    "HTTP2": "bold blue on #142d4f",
    "ICMP": "bold red on #421f24",
    "ICMPV6": "bold red on #421f24",
}


def packet_row_values(packet: PacketSummary, wide: bool) -> tuple[Text, ...]:
    """Return literal Rich values for a table row."""

    values = (
        Text(str(packet.number)),
        Text(packet.relative_time),
        Text(packet.source),
        Text(packet.destination),
        Text(packet.url),
        protocol_badge(packet.protocol),
        Text(str(packet.length)),
        Text(packet.info),
    )
    if wide:
        return values
    return values[0], values[2], values[5], values[7]


def protocol_badge(protocol: str) -> Text:
    """Return a colored literal Rich protocol badge."""

    style = _PROTOCOL_STYLES.get(protocol.upper(), _DEFAULT_PROTOCOL_STYLE)
    return Text(protocol, style=style)


def rebuild_packet_table(
    table: DataTable, packets: tuple[PacketSummary, ...], wide: bool
) -> None:
    """Rebuild the table while keeping the selected row within the result set."""

    selected_row = table.cursor_row
    table.clear(columns=True)
    column_widths = _WIDE_COLUMN_WIDTHS if wide else _NARROW_COLUMN_WIDTHS
    for label, width in column_widths.items():
        table.add_column(label, width=width)
    for packet in packets:
        table.add_row(*packet_row_values(packet, wide))
    if packets:
        table.move_cursor(row=min(selected_row, len(packets) - 1), column=0)


def render_packet_details(packet: PacketSummary, details: PacketDetails) -> Text:
    """Build literal Rich text for packet details."""

    return Text(
        "\n".join(
            (
                f"No.: {packet.number}",
                f"Time: {packet.relative_time}",
                f"Source: {packet.source}",
                f"Destination: {packet.destination}",
                f"Protocol: {packet.protocol}",
                f"Length: {packet.length}",
                f"Info: {packet.info}",
                "",
                "Protocol tree:",
                details.protocol_tree,
                "",
                "Hex/ASCII:",
                details.hex_ascii,
            )
        )
    )
