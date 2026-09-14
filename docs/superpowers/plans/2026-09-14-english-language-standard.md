# Plan: English Language Standard

> **For agentic workers:** use Superpowers execution discipline for this plan. Keep the change narrow, test-visible, and verify before reporting completion.

## Task 1: Runtime Text

- [x] Translate CLI help, runtime errors, diagnostics, TUI labels, status messages, docstrings, and inline comments to English.
- [x] Update tests that assert runtime text.
- [x] Run targeted tests for CLI, diagnostics, TShark parsing, file TUI, live TUI, live source, live controller, index, SQLite support, sessions, and Wireshark discovery.

## Task 2: Project Documentation

- [x] Translate README, changelog, package metadata, Homebrew formula caveats/tests, and repository guidance to English.
- [x] Replace legacy Russian Superpowers plan/spec prose with English summaries that preserve each file's purpose and completion status.
- [x] Translate the original product brief in `plan.md`.

## Task 3: Verification

- [x] Confirm no Cyrillic text remains in tracked project files.
- [x] Run the full automated verification set.
- [x] Inspect the final diff for unintended behavior changes.
