# WispWire English Language Standard

## Goal

Make English the default and only project language for product-facing text, documentation, tests, comments, and contributor guidance. Russian text may be removed rather than kept as a selectable locale.

## Scope

- Runtime CLI, TUI, diagnostic, and error messages are in English.
- README, changelog, package metadata, Homebrew caveats, and repository guidance are in English.
- Tests assert the English behavior.
- Historical Superpowers files remain present as project records, but their visible text is converted to English so the repository no longer carries Russian prose.

## Non-Goals

- No runtime localization framework is added in this step.
- No release, tag, Homebrew publication, or push is performed in this step.
- No packet-processing behavior changes are intended.

## Verification

- Search the repository for Cyrillic characters.
- Run the Python test suite.
- Run Ruff check and format check.
- Run mypy.
- Check CLI help output.
