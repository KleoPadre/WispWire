# Product Brief: Terminal PCAP/PCAPNG Viewer And Analyzer

## Project Name

The project is named WispWire. The command and Python package are both `wispwire`.

## Goal

Build a free terminal utility for macOS, Linux, and ideally Windows that can open existing `.pcap` and `.pcapng` files, run live network capture, stop capture and immediately analyze the collected file, browse packets in a terminal UI, quickly find IPs, domains, UDP/STUN/TURN traffic, Telegram-call clues, DNS, and TLS SNI, and cover lightweight analysis tasks without opening the full Wireshark GUI.

WispWire is not a full Wireshark replacement. Its job is quick viewing, filtering, and traffic inspection from the terminal.

## Core Scenarios

### Open Existing Capture

The user runs:

```bash
wispwire open capture.pcapng
```

WispWire opens a read-only TUI with a packet table, protocol badges, source and destination columns, URL/domain hints when available, an `Info` column, display-filter input, search, and selected-packet details.

### Live Capture

The user runs:

```bash
wispwire capture --iface en0
```

WispWire starts `dumpcap`, writes short PCAPNG segments, shows live packet summaries, lets the user stop, continue, restart, save a snapshot, and open the saved capture in the file TUI.

## Technical Stack

- Python 3.11+
- Typer for CLI commands
- Rich and Textual for terminal UI
- SQLite FTS5 trigram for packet indexing and `Info` search
- TShark for packet decoding and display filters
- dumpcap for live capture
- mergecap for safe snapshot/save output

WispWire must not parse PCAP files itself and must not implement its own Wireshark filter language. It shells out to external Wireshark tools with argument lists, never with `shell=True`.

## Safety Boundaries

- Existing capture files are read-only inputs and must not be changed.
- Temporary sessions are isolated under WispWire-owned cache roots.
- Cleanup only removes registered regular files from a verified session.
- Symlinks, special files, path traversal, and replaced directories are rejected.
- Tests must mock external tools and must not require real packet capture.
- Live capture permissions are an operating-system concern and may require macOS BPF configuration outside the formula.

## Current Roadmap Status

Implemented stages include foundation CLI commands, PCAP/PCAPNG opening, SQLite indexing, read-only TUI details, safe temporary sessions, segmented live capture, file-mode filters/search, live TUI controls, Homebrew packaging, and domain/URL table support.

Remaining product work should be planned narrowly from the current codebase and verified through tests plus manual live-interface acceptance when capture behavior changes.
