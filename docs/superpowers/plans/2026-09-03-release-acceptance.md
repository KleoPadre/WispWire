# Поставка и приёмка WispWire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** подготовить WispWire к первой публичной поставке: стабильный GitHub Release, Homebrew tap/formula/cask, CI, локальная установка через Homebrew, проверка установленной команды и ручная приёмка live-захвата.

**Architecture:** WispWire остаётся CLI/TUI-приложением без фонового daemon и без `brew services`. Основной репозиторий `KleoPadre/WispWire` производит версионированный release-артефакт и проектные проверки; отдельный tap `KleoPadre/homebrew-tap` содержит formula `wispwire` и macOS umbrella-cask `wispwire`, который подтягивает установку CLI и ChmodBPF. Публикация разрешена только после проверки установленной Homebrew-версии, а не только editable-установки из `.venv`.

**Tech Stack:** Python 3.11+, Typer, Rich, Textual, TShark/dumpcap/mergecap из Wireshark CLI, SQLite FTS5 trigram, GitHub Actions, GitHub Releases, Homebrew formula/cask.

**Spec:** `docs/superpowers/specs/2026-08-28-wispwire-tui-design.md`

## Global Constraints

- Единственное название приложения, Python-пакета, CLI и Homebrew-токена — **WispWire** / `wispwire`.
- WispWire не заменяет Wireshark; он использует `tshark`, `dumpcap` и `mergecap`.
- Реальные PCAP/PCAPNG, пользовательские IP-адреса, токены и рабочие дампы не попадают в Git.
- Unit-тесты подменяют `dumpcap`, `mergecap` и TShark; автоматические тесты не заменяют ручную проверку live-захвата.
- Live-TUI никогда не запускается от root; права `dumpcap` проверяются через `doctor`.
- macOS-поставка использует Homebrew cask `wispwire`, который устанавливает WispWire и `wireshark-chmodbpf`.
- Linux-поставка использует Homebrew formula `wispwire`; права `dumpcap` проверяются отдельно.
- Formula и cask используют только стабильные GitHub Releases с фиксированными SHA-256.
- Homebrew-проверки включают `brew audit`, `brew style`, установку в чистом окружении и `brew test`.
- Перед публикацией обязательна проверка установленной команды `wispwire` из Homebrew, а не только `.venv/bin/wispwire`.
- `brew services` не используется: WispWire не daemon/service.
- Коммиты пишутся на русском языке.

---

## File Structure

- Modify: `pyproject.toml` — версия релиза и metadata, если Homebrew/PyPI build потребует недостающие поля.
- Create: `CHANGELOG.md` — история релизов и ручные acceptance notes.
- Modify: `README.md` — инструкции установки через Homebrew, smoke-проверки и предупреждение про ручную live-приёмку.
- Modify: `docs/superpowers/plans/2026-08-28-wispwire-tui.md` — отметить этап 8 только после фактической поставки и проверок.
- Create: `.github/workflows/ci.yml` — проверки основного репозитория на macOS и Linux.
- Create: `.github/workflows/release.yml` — сборка release-артефакта и публикация GitHub Release после tag push.
- External repo: `../homebrew-tap/Formula/wispwire.rb` — Homebrew formula для CLI/TUI.
- External repo: `../homebrew-tap/Casks/wispwire.rb` — macOS cask, который ставит formula и `wireshark-chmodbpf`.
- External repo: `../homebrew-tap/.github/workflows/tests.yml` — проверки tap: audit/style/test/install.
- External repo: `../homebrew-tap/README.md` — пользовательские команды установки.
- Optional local helper: `scripts/smoke_homebrew_install.sh` — повторяемая локальная проверка установленной Homebrew-версии.

---

### Task 1: Release metadata, changelog and source build

**Files:**
- Modify: `pyproject.toml`
- Create: `CHANGELOG.md`
- Modify: `README.md`
- Test: build and metadata commands from this task

**Interfaces:**
- Consumes: current package entry point `wispwire = "wispwire.cli:app"`.
- Produces: versioned source distribution `dist/wispwire-<version>.tar.gz`, wheel `dist/wispwire-<version>-py3-none-any.whl`, release notes text in `CHANGELOG.md`.

- [ ] **Step 1: Inspect current package metadata**

Run:

```bash
python3 - <<'PY'
import pathlib
import tomllib

data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
project = data["project"]
print("name=", project["name"])
print("version=", project["version"])
print("requires-python=", project["requires-python"])
print("dependencies=", ", ".join(project["dependencies"]))
print("scripts=", project["scripts"])
PY
```

Expected: `name=wispwire`, `requires-python=>=3.11`, script `wispwire`.

- [ ] **Step 2: Write changelog for the first packaged release**

Create `CHANGELOG.md`:

```markdown
# Changelog

## 0.1.0 — 2026-09-03

- Добавлена команда `wispwire doctor` для проверки Wireshark CLI, прав live-захвата и SQLite FTS5 trigram.
- Добавлена команда `wispwire interfaces` для безопасного чтения интерфейсов `dumpcap`.
- Добавлена команда `wispwire open PATH` для read-only просмотра PCAP/PCAPNG в TUI.
- Добавлены дерево протоколов и hex/ASCII-детали выбранного кадра через TShark.
- Добавлены временные сессии WispWire с manifest, безопасной очисткой и защитой от небезопасных путей.
- Добавлен сегментированный live-захват через `dumpcap` и сохранение snapshot через `mergecap`.
- Добавлен live-TUI с `S`, `Q`, `C`, `R`, `W`, display filter и поиском по `Info`.

### Проверки релиза

- Автоматические проверки выполняются в CI на macOS и Linux.
- Homebrew-поставка проверяется через установку установленной команды `wispwire`, `brew test`, `brew audit` и `brew style`.
- Ручная приёмка live-захвата на реальном интерфейсе обязательна перед публичной публикацией Homebrew tap.
```

- [ ] **Step 3: Add release installation preview to README**

Modify `README.md` installation section to show both development and packaged installation paths:

```markdown
## Установка через Homebrew

macOS Apple Silicon:

```bash
brew install --cask kleopadre/tap/wispwire
wispwire doctor
```

Linux:

```bash
brew install kleopadre/tap/wispwire
wispwire doctor
```

WispWire не устанавливает и не запускает фоновый сервис. `brew services` для него не используется: все команды выполняются явно из терминала.
```

- [ ] **Step 4: Install build tooling in the existing venv**

Run:

```bash
.venv/bin/python -m pip install build
```

Expected: exit code 0.

- [ ] **Step 5: Build source distribution and wheel**

Run:

```bash
rm -rf dist
.venv/bin/python -m build
ls -1 dist
```

Expected files:

```text
wispwire-0.1.0-py3-none-any.whl
wispwire-0.1.0.tar.gz
```

- [ ] **Step 6: Verify package contents do not include local captures or agent state**

Run:

```bash
tar -tzf dist/wispwire-0.1.0.tar.gz | rg '(^|/)(\\.venv|\\.git|\\.codegraph|\\.codex|Captures|\\.pcap|\\.pcapng|\\.env)'
```

Expected: command exits with no matches. If `rg` returns exit code 1 because there are no matches, that is the expected safe result.

- [ ] **Step 7: Verify installed wheel in a temporary environment**

Run:

```bash
TMP_ENV=$(mktemp -d)
python3 -m venv "$TMP_ENV/venv"
"$TMP_ENV/venv/bin/python" -m pip install dist/wispwire-0.1.0-py3-none-any.whl
"$TMP_ENV/venv/bin/wispwire" --help
"$TMP_ENV/venv/bin/wispwire" doctor
rm -rf "$TMP_ENV"
```

Expected: `wispwire --help` exits 0; `doctor` exits 0 and reports actual local dependency statuses without crashing.

- [ ] **Step 8: Run full project checks before release commit**

Run:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/wispwire open --help
.venv/bin/wispwire capture --help
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 9: Commit release metadata**

Run:

```bash
git add pyproject.toml README.md CHANGELOG.md
git commit -m "Подготовить метаданные релиза WispWire"
```

Expected: one commit containing only release metadata and docs.

---

### Task 2: Main repository CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: GitHub Actions workflow syntax and local command parity

**Interfaces:**
- Consumes: project checks from Task 1.
- Produces: CI gate for pull requests and pushes to `dev`/`main`.

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - dev
      - main

jobs:
  test:
    name: ${{ matrix.os }} / Python ${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os:
          - macos-14
          - ubuntu-24.04
        python-version:
          - "3.11"
          - "3.14"

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Wireshark CLI on macOS
        if: runner.os == 'macOS'
        run: |
          brew update
          brew install wireshark

      - name: Install Wireshark CLI on Linux
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y tshark wireshark-common

      - name: Install project
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e '.[dev]'

      - name: Test
        run: python -m pytest

      - name: Ruff
        run: |
          ruff check src tests
          ruff format --check src tests

      - name: mypy
        run: mypy src

      - name: CLI smoke
        run: |
          wispwire --help
          wispwire doctor
          wispwire interfaces || true
          wispwire open --help
          wispwire capture --help
```

- [ ] **Step 2: Validate local command parity**

Run locally:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/wispwire --help
.venv/bin/wispwire doctor
.venv/bin/wispwire interfaces || true
.venv/bin/wispwire open --help
.venv/bin/wispwire capture --help
```

Expected: all commands except `interfaces` must exit 0. `interfaces` may exit non-zero only if local `dumpcap` is missing or not usable; record the exact output in the task report.

- [ ] **Step 3: Commit CI**

Run:

```bash
git add .github/workflows/ci.yml
git commit -m "Добавить CI WispWire"
```

Expected: one commit containing only the CI workflow.

---

### Task 3: Release workflow and immutable GitHub Release

**Files:**
- Create: `.github/workflows/release.yml`
- Modify: `README.md`
- Test: dry-run build commands and tag discipline

**Interfaces:**
- Consumes: `CHANGELOG.md`, `pyproject.toml` version.
- Produces: immutable GitHub Release source archive and wheel; Homebrew formula consumes the release source URL and SHA-256.

- [ ] **Step 1: Create release workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.14"

      - name: Install build backend
        run: python -m pip install --upgrade pip build

      - name: Build distributions
        run: python -m build

      - name: Compute checksums
        run: |
          sha256sum dist/* > dist/SHA256SUMS.txt
          cat dist/SHA256SUMS.txt

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/*.tar.gz
            dist/*.whl
            dist/SHA256SUMS.txt
          generate_release_notes: true
```

- [ ] **Step 2: Add release creation instructions to README**

Append to `README.md` maintainers section:

```markdown
## Релиз

Релиз создаётся только из проверенного `dev`, слитого в release-ветку или `main`.
Порядок:

```bash
git status --short --branch
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/wispwire doctor
git tag v0.1.0
git push origin v0.1.0
```

После появления GitHub Release нужно скачать `wispwire-0.1.0.tar.gz`,
вычислить SHA-256 и использовать его в Homebrew formula.
```

- [ ] **Step 3: Dry-run release build locally**

Run:

```bash
rm -rf dist
.venv/bin/python -m build
shasum -a 256 dist/wispwire-0.1.0.tar.gz dist/wispwire-0.1.0-py3-none-any.whl
```

Expected: both files exist and have SHA-256 values.

- [ ] **Step 4: Commit release workflow**

Run:

```bash
git add .github/workflows/release.yml README.md
git commit -m "Добавить workflow релиза WispWire"
```

Expected: one commit containing release workflow and maintainer docs.

---

### Task 4: Homebrew tap formula and macOS cask

**Files:**
- External repo create/modify: `../homebrew-tap/Formula/wispwire.rb`
- External repo create/modify: `../homebrew-tap/Casks/wispwire.rb`
- External repo modify: `../homebrew-tap/README.md`
- Test: Homebrew local install, audit, style and test commands

**Interfaces:**
- Consumes: GitHub Release `v0.1.0` from `KleoPadre/WispWire`.
- Produces: Homebrew formula token `wispwire` and cask token `wispwire`.

- [ ] **Step 1: Prepare or clone the tap repository**

Run from `/Users/levon.osipov/Projects/WispWire`:

```bash
cd /Users/levon.osipov/Projects
if [ -d homebrew-tap/.git ]; then
  git -C homebrew-tap fetch origin
  git -C homebrew-tap status --short --branch
else
  git clone git@github.com:KleoPadre/homebrew-tap.git homebrew-tap
fi
```

Expected: local tap repo exists at `/Users/levon.osipov/Projects/homebrew-tap`.

- [ ] **Step 2: Create formula with computed release checksum**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
mkdir -p Formula
curl -L -o /tmp/wispwire-0.1.0.tar.gz https://github.com/KleoPadre/WispWire/archive/refs/tags/v0.1.0.tar.gz
WISPWIRE_RELEASE_SHA=$(shasum -a 256 /tmp/wispwire-0.1.0.tar.gz | awk '{print $1}')
python3 - "$WISPWIRE_RELEASE_SHA" <<'PY'
from pathlib import Path
import sys

release_sha = sys.argv[1]
Path("Formula/wispwire.rb").write_text(
    f'''class Wispwire < Formula
  include Language::Python::Virtualenv

  desc "Терминальная утилита для диагностики сетевого анализа"
  homepage "https://github.com/KleoPadre/WispWire"
  url "https://github.com/KleoPadre/WispWire/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "{release_sha}"
  license "MIT"

  depends_on "python@3.14"
  depends_on "wireshark"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Usage:", shell_output("#{{bin}}/wispwire --help")
    assert_match "Usage:", shell_output("#{{bin}}/wispwire open --help")
    assert_match "Usage:", shell_output("#{{bin}}/wispwire capture --help")
    system bin/"wispwire", "doctor"
  end
end
''',
)
PY
```

Expected: formula contains a concrete SHA-256 for `v0.1.0.tar.gz`.

- [ ] **Step 3: Generate Python resource blocks**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
brew update-python-resources Formula/wispwire.rb
brew audit --strict --new --online Formula/wispwire.rb
```

Expected: `brew update-python-resources` writes concrete `resource` blocks for Typer, Rich, Textual and transitive Python dependencies; audit sees no missing Python resources.

- [ ] **Step 4: Create macOS umbrella cask**

Create `/Users/levon.osipov/Projects/homebrew-tap/Casks/wispwire.rb`:

```ruby
cask "wispwire" do
  version "0.1.0"

  name "WispWire"
  desc "Терминальная утилита для диагностики сетевого анализа"
  homepage "https://github.com/KleoPadre/WispWire"

  depends_on formula: "kleopadre/tap/wispwire"
  depends_on cask: "wireshark-chmodbpf"

  caveats <<~EOS
    WispWire не устанавливает фоновый сервис и не использует brew services.

    После установки проверьте окружение:
      wispwire doctor

    Если ChmodBPF запросил пароль, может потребоваться повторный вход
    в систему или перезагрузка, чтобы права dumpcap применились.
  EOS
end
```

- [ ] **Step 5: Add tap README**

Create or update `/Users/levon.osipov/Projects/homebrew-tap/README.md`:

```markdown
# KleoPadre Homebrew Tap

## WispWire

macOS Apple Silicon:

```bash
brew install --cask kleopadre/tap/wispwire
wispwire doctor
```

Linux:

```bash
brew install kleopadre/tap/wispwire
wispwire doctor
```

WispWire — CLI/TUI-приложение. Оно не устанавливает daemon и не использует
`brew services`.
```

- [ ] **Step 6: Validate formula and cask style before install**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
brew style --formula Formula/wispwire.rb
brew audit --strict --new --online Formula/wispwire.rb
brew style --cask Casks/wispwire.rb
brew audit --new --cask Casks/wispwire.rb
```

Expected: every command exits 0.

- [ ] **Step 7: Commit tap package definitions**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
git add Formula/wispwire.rb Casks/wispwire.rb README.md
git commit -m "Добавить поставку WispWire"
```

Expected: one tap commit. Do not push until Tasks 5 and 6 are green.

---

### Task 5: Local Homebrew install smoke on macOS

**Files:**
- Optional create: `scripts/smoke_homebrew_install.sh`
- Modify: `README.md`
- Test: installed `wispwire` command from Homebrew prefix

**Interfaces:**
- Consumes: tap formula/cask from Task 4.
- Produces: evidence that the installed Homebrew command works outside `.venv`.

- [ ] **Step 1: Create repeatable smoke script**

Create `scripts/smoke_homebrew_install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

if [ "$(command -v wispwire)" = "" ]; then
  echo "wispwire не найден в PATH" >&2
  exit 1
fi

echo "Проверяю установленную команду: $(command -v wispwire)"
wispwire --help >/tmp/wispwire-help.txt
wispwire doctor
wispwire interfaces || true
wispwire open --help >/tmp/wispwire-open-help.txt
wispwire capture --help >/tmp/wispwire-capture-help.txt

rg 'Usage:' /tmp/wispwire-help.txt
rg 'Usage:' /tmp/wispwire-open-help.txt
rg 'Usage:' /tmp/wispwire-capture-help.txt
```

Make it executable:

```bash
chmod +x scripts/smoke_homebrew_install.sh
```

- [ ] **Step 2: Install formula from local tap without API shortcut**

Run:

```bash
brew uninstall --ignore-dependencies wispwire || true
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source /Users/levon.osipov/Projects/homebrew-tap/Formula/wispwire.rb
which wispwire
wispwire --help
wispwire doctor
```

Expected: `which wispwire` points to Homebrew prefix, not `.venv`; help and doctor exit 0.

- [ ] **Step 3: Run brew test**

Run:

```bash
HOMEBREW_NO_INSTALL_FROM_API=1 brew test /Users/levon.osipov/Projects/homebrew-tap/Formula/wispwire.rb
```

Expected: exit code 0.

- [ ] **Step 4: Run installed-command smoke script**

Run from WispWire repo:

```bash
scripts/smoke_homebrew_install.sh
```

Expected: exit code 0; `doctor` reports real local dependency status.

- [ ] **Step 5: Install macOS cask path**

Run on macOS:

```bash
brew uninstall --cask wispwire || true
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --cask /Users/levon.osipov/Projects/homebrew-tap/Casks/wispwire.rb
wispwire doctor
brew uninstall --cask wispwire
```

Expected: cask installation succeeds; `wispwire doctor` exits 0; uninstall succeeds. If `wireshark-chmodbpf` asks for credentials or reboot/login, record the exact message and rerun `wispwire doctor` after the OS-level change.

- [ ] **Step 6: Verify no accidental service registration**

Run:

```bash
brew services list | rg -i 'wispwire'
```

Expected: no matches. If `rg` exits 1 because no match exists, that is the expected result.

- [ ] **Step 7: Commit smoke script and README update**

Run:

```bash
git add scripts/smoke_homebrew_install.sh README.md
git commit -m "Добавить smoke-проверку Homebrew-установки"
```

Expected: one WispWire repo commit.

---

### Task 6: Manual live acceptance on real interface

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Optional create: `docs/acceptance/2026-09-03-release-0.1.0.md`
- Test: manual commands on installed Homebrew version

**Interfaces:**
- Consumes: installed Homebrew command from Task 5.
- Produces: written manual acceptance evidence for release `0.1.0`.

- [ ] **Step 1: Record installed binary and environment**

Run:

```bash
which wispwire
wispwire --help
wispwire doctor
wispwire interfaces
```

Expected: `which wispwire` points to Homebrew; `doctor` shows `tshark`, `dumpcap`, `mergecap`, SQLite FTS5 trigram and capture permission statuses.

- [ ] **Step 2: Run live-TUI on a real interface**

Run:

```bash
wispwire capture --iface en0
```

Expected: Textual live-TUI opens; packets appear after closed capture segments. If the active interface is not `en0`, choose an interface listed by `wispwire interfaces` and record the exact interface name.

- [ ] **Step 3: Verify live-TUI actions**

In the live-TUI:

```text
1. Дождаться появления новых пакетов.
2. Нажать F, ввести udp, убедиться, что таблица фильтруется.
3. Нажать /, ввести часть значения Info, убедиться, что поиск применяется вместе с display filter.
4. Нажать Esc, убедиться, что активное поле очищается.
5. Нажать W, убедиться, что snapshot сохранён в ~/WispWire/Captures/.
6. Нажать R, убедиться, что счётчик пакетов начинается заново и старые события не смешиваются с новыми.
7. Нажать S, убедиться, что захват остановлен, файл сохранён и открыт файловый TUI.
8. В файловом TUI выбрать пакет и проверить дерево протоколов и Hex/ASCII.
9. Выйти через Q.
```

Expected: each action behaves exactly as described; no traceback in terminal.

- [ ] **Step 4: Verify Q path separately**

Run:

```bash
wispwire capture --iface en0
```

In the live-TUI press `Q`.

Expected: capture stops, application exits without opening file TUI, no traceback.

- [ ] **Step 5: Verify temporary sessions cleanup**

Run:

```bash
SESSION_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/wispwire/sessions"
find "$SESSION_ROOT" -maxdepth 1 -type d -print 2>/dev/null
wispwire doctor
```

Expected: no active stale WispWire session remains from the accepted run. If a session remains, inspect only its manifest and filenames; do not delete with a broad command.

- [ ] **Step 6: Record manual acceptance evidence**

Run:

```bash
mkdir -p docs/acceptance
WISPWIRE_BIN=$(command -v wispwire)
WISPWIRE_IFACE=en0
python3 - "$WISPWIRE_BIN" "$WISPWIRE_IFACE" <<'PY'
from pathlib import Path
import sys

wispwire_bin = sys.argv[1]
wispwire_iface = sys.argv[2]
Path("docs/acceptance/2026-09-03-release-0.1.0.md").write_text(
    f"""# WispWire 0.1.0 manual acceptance

Дата: 2026-09-03
Установленная команда: {wispwire_bin}
Интерфейс live-захвата: {wispwire_iface}

## Проверено

- `wispwire doctor`
- `wispwire interfaces`
- live-TUI показывает новые пакеты
- display filter `udp`
- поиск по `Info`
- `Esc`
- `W`
- `R`
- `S` с переходом в файловый TUI
- `Q` без открытия файлового TUI
- очистка временных сессий

## Результат

Приёмка пройдена. Traceback и остаточные временные сессии не обнаружены.
"""
)
PY
```

Expected: acceptance file contains the actual installed `wispwire` path.

- [ ] **Step 7: Commit manual acceptance record**

Run:

```bash
git add docs/acceptance/2026-09-03-release-0.1.0.md CHANGELOG.md README.md
git commit -m "Зафиксировать ручную приёмку WispWire"
```

Expected: one docs commit with acceptance evidence.

---

### Task 7: Tap CI and Linux smoke

**Files:**
- External repo create: `../homebrew-tap/.github/workflows/tests.yml`
- External repo modify: `../homebrew-tap/README.md`
- Test: GitHub Actions workflow and local brew validation

**Interfaces:**
- Consumes: tap formula/cask from Task 4.
- Produces: tap-level CI for macOS and Linux.

- [ ] **Step 1: Create tap CI workflow**

Create `/Users/levon.osipov/Projects/homebrew-tap/.github/workflows/tests.yml`:

```yaml
name: Homebrew Tap

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  formula:
    strategy:
      fail-fast: false
      matrix:
        os:
          - macos-14
          - ubuntu-24.04
    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout tap
        uses: actions/checkout@v4

      - name: Update Homebrew
        run: brew update

      - name: Style formula
        run: brew style --formula Formula/wispwire.rb

      - name: Audit formula
        run: brew audit --strict --new --online Formula/wispwire.rb

      - name: Install formula
        run: HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source Formula/wispwire.rb

      - name: Test formula
        run: HOMEBREW_NO_INSTALL_FROM_API=1 brew test Formula/wispwire.rb

      - name: Installed CLI smoke
        run: |
          wispwire --help
          wispwire doctor
          wispwire open --help
          wispwire capture --help

  cask:
    runs-on: macos-14

    steps:
      - name: Checkout tap
        uses: actions/checkout@v4

      - name: Update Homebrew
        run: brew update

      - name: Style cask
        run: brew style --cask Casks/wispwire.rb

      - name: Audit cask
        run: brew audit --new --cask Casks/wispwire.rb

      - name: Install cask
        run: HOMEBREW_NO_INSTALL_FROM_API=1 brew install --cask Casks/wispwire.rb

      - name: Installed CLI smoke
        run: |
          wispwire --help
          wispwire doctor

      - name: Uninstall cask
        run: brew uninstall --cask wispwire
```

- [ ] **Step 2: Run tap validation locally**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
brew style --formula Formula/wispwire.rb
brew audit --strict --new --online Formula/wispwire.rb
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source Formula/wispwire.rb
HOMEBREW_NO_INSTALL_FROM_API=1 brew test Formula/wispwire.rb
brew style --cask Casks/wispwire.rb
brew audit --new --cask Casks/wispwire.rb
```

Expected: every command exits 0.

- [ ] **Step 3: Commit tap CI**

Run:

```bash
cd /Users/levon.osipov/Projects/homebrew-tap
git add .github/workflows/tests.yml README.md
git commit -m "Добавить проверки tap WispWire"
```

Expected: one tap commit.

---

### Task 8: Publication gate, push and final roadmap update

**Files:**
- Modify: `docs/superpowers/plans/2026-08-28-wispwire-tui.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- External repo: push `../homebrew-tap`
- Test: final installed-command and remote verification

**Interfaces:**
- Consumes: green Tasks 1–7 and manual acceptance evidence.
- Produces: public `origin/dev`, GitHub Release, pushed Homebrew tap, completed stage 8 status.

- [ ] **Step 1: Verify WispWire repo before publication**

Run in `/Users/levon.osipov/Projects/WispWire`:

```bash
git status --short --branch
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/wispwire doctor
.venv/bin/wispwire open --help
.venv/bin/wispwire capture --help
git diff --check
```

Expected: every command exits 0 except environment-specific `doctor` warnings, which must be explicit dependency/capability statuses and not tracebacks.

- [ ] **Step 2: Verify tap repo before publication**

Run in `/Users/levon.osipov/Projects/homebrew-tap`:

```bash
git status --short --branch
brew style --formula Formula/wispwire.rb
brew audit --strict --new --online Formula/wispwire.rb
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source Formula/wispwire.rb
HOMEBREW_NO_INSTALL_FROM_API=1 brew test Formula/wispwire.rb
brew style --cask Casks/wispwire.rb
brew audit --new --cask Casks/wispwire.rb
```

Expected: every command exits 0.

- [ ] **Step 3: Verify installed Homebrew command one final time**

Run:

```bash
which wispwire
wispwire --help
wispwire doctor
wispwire open --help
wispwire capture --help
brew services list | rg -i 'wispwire'
```

Expected: `which wispwire` points to Homebrew; command smoke passes; `brew services` has no WispWire entry.

- [ ] **Step 4: Update roadmap after all gates pass**

Modify `docs/superpowers/plans/2026-08-28-wispwire-tui.md` using generated commit lists:

```bash
WISPWIRE_STAGE8_COMMITS=$(git log --oneline --reverse origin/dev..HEAD | awk '{print $1}' | paste -sd ', ' -)
TAP_STAGE8_COMMITS=$(git -C /Users/levon.osipov/Projects/homebrew-tap log --oneline --reverse origin/main..HEAD | awk '{print $1}' | paste -sd ', ' -)
python3 - "$WISPWIRE_STAGE8_COMMITS" "$TAP_STAGE8_COMMITS" <<'PY'
from pathlib import Path
import sys

wispwire_commits = sys.argv[1]
tap_commits = sys.argv[2]
path = Path("docs/superpowers/plans/2026-08-28-wispwire-tui.md")
text = path.read_text()
old = """### Этап 8: поставка и приёмка

- [ ] Подготовить Homebrew formula/cask, CI, документацию и проверяемые
  smoke-тесты macOS Apple Silicon и Linux ARM64/x86_64.
- [ ] Провести ручную проверку UI и live-захвата: автоматические тесты не
  заменяют реальный захват пакетов.

## Ближайшая исполнимая задача

Следующим реализуется **этап 8 — поставка и приёмка**. Для него нужен отдельный
детальный план поставки, CI и платформенных smoke-тестов; ручная приёмка
live-захвата остаётся самостоятельной проверкой на реальном интерфейсе.
"""
new = f"""### Этап 8: поставка и приёмка

- [x] Подготовить Homebrew formula/cask, CI, документацию и проверяемые
  smoke-тесты macOS Apple Silicon и Linux ARM64/x86_64 — коммиты {wispwire_commits}; tap-коммиты {tap_commits}.
- [x] Провести ручную проверку UI и live-захвата: автоматические тесты не
  заменяют реальный захват пакетов — acceptance record `docs/acceptance/2026-09-03-release-0.1.0.md`.

## Ближайшая исполнимая задача

Публичная поставка WispWire 0.1.0 завершена. Следующие задачи открываются отдельными спецификациями после фактической обратной связи по установке и live-захвату.
"""
if old not in text:
    raise SystemExit("expected stage 8 block not found")
path.write_text(text.replace(old, new))
PY
```

Expected: stage 8 checkboxes are marked `[x]` only after all gates pass, with concrete WispWire and tap commit hashes.

- [ ] **Step 5: Commit final roadmap update**

Run:

```bash
git add docs/superpowers/plans/2026-08-28-wispwire-tui.md README.md CHANGELOG.md
git commit -m "Завершить план поставки WispWire"
```

Expected: one WispWire repo commit.

- [ ] **Step 6: Push WispWire dev**

Run:

```bash
git fetch origin
git log --left-right --graph --oneline dev...origin/dev
git push origin dev
git ls-remote --heads origin dev
```

Expected: `origin/dev` points to the local `dev` tip. If remote moved, stop and inspect `dev...origin/dev`; do not force-push.

- [ ] **Step 7: Create and push release tag**

Run only after `dev` is pushed and CI is green:

```bash
git tag -a v0.1.0 -m "WispWire 0.1.0"
git push origin v0.1.0
```

Expected: GitHub Release workflow creates release assets and checksums.

- [ ] **Step 8: Push Homebrew tap**

Run in `/Users/levon.osipov/Projects/homebrew-tap` only after release assets exist and formula SHA matches them:

```bash
git fetch origin
git log --left-right --graph --oneline main...origin/main
git push origin main
git ls-remote --heads origin main
```

Expected: `origin/main` in tap points to the local tap commit. If remote moved, stop and inspect; do not force-push.

- [ ] **Step 9: Verify public installation path**

Run from a clean shell:

```bash
brew untap kleopadre/tap || true
brew tap kleopadre/tap
brew uninstall --cask wispwire || true
brew uninstall wispwire || true
brew install --cask kleopadre/tap/wispwire
which wispwire
wispwire doctor
wispwire open --help
wispwire capture --help
```

Expected: public install succeeds and command smoke passes from Homebrew installation.

---

## Final Verification Matrix

Before marking stage 8 complete, all rows must be green or explicitly recorded with a non-blocking environment reason:

| Area | Command or action | Required result |
|---|---|---|
| Unit/integration | `.venv/bin/python -m pytest` | exit 0 |
| Lint | `.venv/bin/ruff check src tests` | exit 0 |
| Format | `.venv/bin/ruff format --check src tests` | exit 0 |
| Types | `.venv/bin/mypy src` | exit 0 |
| CLI editable | `.venv/bin/wispwire doctor` | no traceback |
| CLI installed | `wispwire doctor` | Homebrew command, no traceback |
| File TUI smoke | `wispwire open --help` | exit 0 |
| Live TUI smoke | `wispwire capture --help` | exit 0 |
| Homebrew formula style | `brew style --formula Formula/wispwire.rb` | exit 0 |
| Homebrew formula audit | `brew audit --strict --new --online Formula/wispwire.rb` | exit 0 |
| Homebrew formula install | `HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source Formula/wispwire.rb` | exit 0 |
| Homebrew formula test | `HOMEBREW_NO_INSTALL_FROM_API=1 brew test Formula/wispwire.rb` | exit 0 |
| Homebrew cask style | `brew style --cask Casks/wispwire.rb` | exit 0 |
| Homebrew cask audit | `brew audit --new --cask Casks/wispwire.rb` | exit 0 |
| Homebrew cask install | `HOMEBREW_NO_INSTALL_FROM_API=1 brew install --cask Casks/wispwire.rb` | exit 0 |
| No service | `brew services list | rg -i 'wispwire'` | no matches |
| Manual live acceptance | `wispwire capture --iface <real-interface>` | packets, filters, save, restart and cleanup verified |
| Release assets | GitHub Release `v0.1.0` | `.tar.gz`, `.whl`, `SHA256SUMS.txt` |
| Public install | `brew install --cask kleopadre/tap/wispwire` | installed command works |

---

## Self-Review

- Spec coverage: Homebrew macOS cask, Linux formula, Wireshark CLI dependencies, ChmodBPF, immutable release SHA-256, CI, brew audit/style/test, installed-command smoke and manual live acceptance are covered.
- Scope boundary: no `brew services`, daemon, background agent, telemetry, analytics, export or Wireshark replacement was added to the plan.
- Test design: every task has an executable verification gate; Homebrew checks use installed command paths and not only `.venv`.
- Publication safety: tap push happens only after release assets exist, SHA matches, formula/cask checks pass, installed-command smoke passes and manual live acceptance is recorded.
