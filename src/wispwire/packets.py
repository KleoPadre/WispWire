from dataclasses import dataclass


@dataclass(frozen=True)
class PacketDetails:
    """Details for rendering one packet tree and dump."""

    protocol_tree: str
    hex_ascii: str


@dataclass(frozen=True)
class PacketSummary:
    """Packet summary for table rendering."""

    number: int
    relative_time: str
    source: str
    destination: str
    protocol: str
    length: int
    info: str
    url: str = ""
