# Changelog

## 0.1.3 - 2026-09-07

- Moved release publication to `main`: GitHub Releases and the Homebrew formula are published only from the release branch.

## 0.1.2 - 2026-09-07

- Fixed immediate highlighting for unknown display-filter protocols: `ava` turns red before Enter or Apply is pressed.

## 0.1.1 - 2026-09-04

- Fixed handling for late packet-detail events after the live TUI closes.
- Updated Homebrew packaging so the formula installs WispWire, Python runtime dependencies, and the Wireshark CLI in one command.
- `doctor` now suggests `brew install --cask wireshark-chmodbpf` on macOS when `dumpcap` is installed but no interfaces are visible.

## 0.1.0 - 2026-09-04

- Added `wispwire doctor` for checking the Wireshark CLI, live-capture permissions, and SQLite FTS5 trigram support.
- Added `wispwire interfaces` for safely reading interfaces from `dumpcap`.
- Added `wispwire open PATH` for read-only PCAP/PCAPNG viewing in the TUI.
- Added protocol-tree and Hex/ASCII details for the selected frame through TShark.
- Added temporary WispWire sessions with manifests, safe cleanup, and unsafe-path protection.
- Added segmented live capture through `dumpcap` and snapshot saving through `mergecap`.
- Added a live TUI with Wireshark display filters, syntax suggestions, filter validity highlighting, and interface switching.

### Release Checks

- Automated checks run locally and in CI on macOS/Linux.
- Homebrew delivery is verified through installed-command checks, `brew test`, `brew audit`, and `brew style`.
- Manual live-capture acceptance on a real interface is required before public Homebrew tap publication.
