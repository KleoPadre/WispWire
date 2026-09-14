# WispWire

WispWire is a terminal utility for network-analysis diagnostics.

## Installation

### Homebrew

The primary user installation path is Homebrew:

```bash
brew install kleopadre/tap/wispwire
wispwire doctor
```

This installs WispWire, its Python runtime dependencies, and the Wireshark CLI tools (`tshark`, `dumpcap`, and `mergecap`). After installation, run WispWire directly from the terminal:

```bash
wispwire capture --iface en0
wispwire open ~/Downloads/capture.pcapng
```

WispWire does not install or run a background service. `brew services` is not used; every command is started explicitly from the terminal.

On macOS, the interface list can be empty when the system lacks permission to access BPF devices. This is not a WispWire Python dependency issue; it is an operating-system packet-capture permission. `wispwire doctor` reports this condition and shows the Homebrew command for fixing it:

```bash
brew install --cask wireshark-chmodbpf
```

### Development From Source

Create a virtual environment and install the package with development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

If the environment already exists, use its interpreter:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

## Checks

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
```

Check the shipped command with:

```bash
wispwire --help
wispwire doctor
wispwire interfaces
```

## Environment Diagnostics

Check for `tshark`, `dumpcap`, `mergecap`, live-capture availability, and SQLite FTS5 trigram support, which is required for the packet index and `Info` search:

```bash
.venv/bin/wispwire doctor
```

List the interfaces visible to `dumpcap`:

```bash
.venv/bin/wispwire interfaces
```

These commands only read environment information and do not require `sudo`. Elevated permissions may be needed later when starting live capture.

If `doctor` reports an SQLite FTS5 trigram error, existing capture files can still be opened, but the packet index and `Info` search will not be created.

## Opening Existing Captures

Open an existing capture in the read-only TUI:

```bash
.venv/bin/wispwire open ~/Downloads/capture.pcapng
.venv/bin/wispwire open ~/Downloads/capture.pcap --limit 500
.venv/bin/wispwire open ~/Downloads/capture.pcapng --filter "udp"
```

The TUI does not modify the source file. `tshark` reads packet summaries and, for the selected frame, shows the protocol tree and Hex/ASCII dump. Display filters are passed to TShark with `-Y` without rewriting the expression.

Use `Up` and `Down` to select a packet, `F` to focus the display-filter field, `Esc` to clear the active field, `Tab` to move focus, and `Q` to quit. WispWire is not a full Wireshark replacement.

## Live Capture

Start segmented live capture on a known `dumpcap` interface:

```bash
.venv/bin/wispwire capture --iface en0
```

Before starting, the command checks `dumpcap`, `mergecap`, and the selected interface. It creates a temporary session only after those checks and opens the live TUI. The packet table receives packets only from confirmed closed segments.

Live-TUI shortcuts:

- `S` stops capture, saves the result, and opens it in the file TUI.
- `Q` stops capture and quits without opening the file TUI.
- `C` continues a stopped capture.
- `R` restarts capture.
- `W` saves a snapshot without stopping capture.
- `F` focuses the display-filter field.
- `Esc` clears the active filter field.
- `Tab` moves focus.

`S` and `W` save results in `~/WispWire/Captures/` with names such as `capture_YYYY-MM-DD_HH-MM-SS.pcapng`. If a name already exists, WispWire appends `-2`, `-3`, and so on without overwriting existing files.

Live capture requires manual verification on a real accessible interface. Automated tests do not prove that `dumpcap` works with local permissions or that real packets appear. Acceptance should verify new packets, filtering, `W`, the `S` transition into the file TUI, and the separate `Q` exit path.

## Release

Public releases are created only from a clean `main`. Local agent directories, IDE settings, working packet captures, and other service files must not enter `main`. Before tagging, inspect the tracked file set:

```bash
git status --short --branch
git ls-files | rg '(^|/)(\.claude|\.codex|\.cursor|\.gemini|\.vscode|\.codegraph|\.mcp\.json|GEMINI\.md|.*\.pcap|.*\.pcapng)'
```

If `rg` finds no matches and exits with code 1, that is the expected clean result.

Release checklist:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/wispwire doctor
.venv/bin/python -m hatchling build -t sdist -t wheel
shasum -a 256 dist/wispwire-0.1.3.tar.gz dist/wispwire-0.1.3-py3-none-any.whl
git tag v0.1.3
git push origin main v0.1.3
```

After the GitHub Release is available, compare the SHA-256 of `wispwire-0.1.3.tar.gz` with `SHA256SUMS.txt` and use that SHA in the Homebrew formula. The formula must install Wireshark and Python dependencies automatically. `wireshark-chmodbpf` remains a separate macOS cask for capture permissions; a Homebrew formula cannot correctly declare a cask as a dependency.
