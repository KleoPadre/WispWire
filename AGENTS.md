# Repository Guidelines

## Current State And Structure

WispWire is a Python terminal utility for reading PCAP/PCAPNG files and running live capture through `tshark`/`dumpcap`. Keep the scope focused: WispWire is not intended to replace all of Wireshark.

Use this structure:

```text
src/wispwire/     # CLI, TUI, models, and tshark/dumpcap integration
tests/            # tests mirroring src/
docs/             # user and technical documentation
```

Do not commit working captures, dumps, or other large/generated packet files. Use a temporary directory or an explicitly requested `--out` path for local captures.

## Required Superpowers Process

All changes use applicable Superpowers skills. New features and architectural decisions start with `superpowers:brainstorming`: inspect the context, agree on the design, and save the approved specification under `docs/superpowers/specs/`. Then use `superpowers:writing-plans` and create a step-by-step plan under `docs/superpowers/plans/`.

Implement from the plan with `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Features and fixes require `superpowers:test-driven-development`; before reporting completion, use `superpowers:verification-before-completion`. Do not implement before the design and plan have explicit approval.

## Development, Run, And Checks

Use the commands documented in `pyproject.toml`. The minimum expected loop is:

```bash
python -m pytest
ruff check src tests
ruff format --check src tests
wispwire doctor
```

Do not require `sudo` to read an existing capture file. Elevated permissions may be required only for live capture. Tests must replace external process calls and must not run real capture.

## Code Style And Naming

Target Python 3.11+. Use four spaces, type annotations for public functions, and `snake_case` for modules, functions, and variables. Name classes and Pydantic models with `PascalCase`; constants use `UPPER_SNAKE_CASE`. Documentation, code comments, CLI help, TUI text, and other user-facing prose must be in English. Prefer small modules with explicit boundaries, such as `capture.py`, `tshark.py`, and `views/packets.py`.

## Tests

Add a test for each new behavior branch: TShark parsing, filter construction, missing-tool errors, and CLI commands. Test names should describe the result, for example `test_doctor_reports_missing_tshark`. Keep PCAP fixtures minimal and anonymized.

## Commits And Pull Requests

Commit messages must be short Russian imperative phrases, unless another project rule explicitly changes this. One commit should represent one logical task. Pull requests should state the goal, key changes, verification method, and related tasks; include a TUI screenshot for TUI changes. Do not include real user captures, IP addresses, tokens, or other sensitive data.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it before grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call: relevant symbols' verbatim source plus call paths between them, including dynamic-dispatch hops grep cannot follow. Name a file or symbol in the query to read its current line-numbered source. If it is listed but deferred, load it by name through tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely; indexing is the user's decision.
<!-- CODEGRAPH_END -->

## Branches And Homebrew Publication

- Development happens on `dev`.
- LLM/agent instructions and artifacts, including `AGENTS.md`, Superpowers materials, and service agent settings, may be committed and pushed to `dev`.
- Before publication, send only clean product code, tests, packaging, and necessary user/technical documentation to `main`; do not carry LLM/agent service materials into `main`.
- Verified `dev` changes must be merged into `main` before Homebrew publication.
- GitHub Releases, tags, and Homebrew formula updates are created only from a commit on `main`; do not publish Homebrew from `dev`.
