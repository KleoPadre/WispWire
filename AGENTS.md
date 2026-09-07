# Repository Guidelines

## Текущее состояние и структура

Сейчас репозиторий содержит только [ТЗ](plan.md) для WispWire TUI — терминальной утилиты на Python для просмотра PCAP/PCAPNG и live-захвата через `tshark`/`dumpcap`. Реализация, тесты и конфигурация зависимостей ещё не созданы. Перед добавлением кода сверяйте решения с ТЗ; не расширяйте заявленную цель до полной замены Wireshark.

Для реализации используйте предсказуемую структуру:

```text
src/wispwire/     # CLI, TUI, модели и интеграция с tshark/dumpcap
tests/               # тесты, повторяющие структуру src/
docs/                # пользовательская и техническая документация
```

Не помещайте рабочие захваты, дампы или другие крупные файлы в Git. Для локальных PCAP используйте временный каталог или явно заданный `--out`.

## Обязательный процесс Superpowers

Все изменения выполняйте через применимые навыки Superpowers. Новые функции и архитектурные решения начинайте с `superpowers:brainstorming`: изучите контекст, согласуйте дизайн с пользователем и сохраните утверждённую спецификацию в `docs/superpowers/specs/`. Затем примените `superpowers:writing-plans` и создайте пошаговый план в `docs/superpowers/plans/`.

Реализацию ведите по плану через `superpowers:subagent-driven-development` или `superpowers:executing-plans`. Для функций и исправлений обязателен `superpowers:test-driven-development`; перед заявлением о готовности используйте `superpowers:verification-before-completion`. Не переходите к реализации до явного утверждения дизайна и плана.

## Разработка, запуск и проверки

После появления `pyproject.toml` используйте документированные в нём команды. Ожидаемый минимальный цикл:

```bash
python -m pytest          # запускает все тесты
ruff check src tests      # проверяет стиль и типичные ошибки
ruff format --check src tests  # проверяет форматирование
wispwire doctor        # проверяет tshark, dumpcap и права на захват
```

Не требуйте `sudo` для чтения готового файла; он может понадобиться только для live-захвата. В тестах подменяйте вызовы внешних программ и не запускайте реальный захват.

## Стиль кода и именование

Цель — Python 3.11+. Используйте четыре пробела, аннотации типов для публичных функций и `snake_case` для модулей, функций и переменных. Классы и Pydantic-модели именуйте в `PascalCase`; константы — в `UPPER_SNAKE_CASE`. Комментарии, строки справки CLI, тексты TUI и документация должны быть на русском. Предпочитайте небольшие модули с явными границами: например, `capture.py`, `tshark.py`, `views/packets.py`.

## Тесты

Добавляйте тест на каждую новую ветвь поведения: разбор JSON `tshark`, построение фильтров, ошибки отсутствующих утилит и команды CLI. Имена тестов должны описывать результат: `test_doctor_reports_missing_tshark`. Фикстуры PCAP держите минимальными и обезличенными.

## Коммиты и pull request

Истории коммитов пока нет. Пишите короткие сообщения на русском в повелительном наклонении: `Добавить проверку tshark` или `Исправить фильтр UDP`. Один коммит — одна логическая задача. В PR укажите цель, ключевые изменения, способ проверки и связанные задачи; приложите скриншот для изменений TUI. Не включайте реальные пользовательские захваты, IP-адреса, токены или другие чувствительные данные.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

## Ветки и публикация Homebrew

- Разработка ведётся в ветке `dev`.
- Инструкции и артефакты для LLM/агентов, включая `AGENTS.md`, материалы Superpowers и служебные agent-настройки, можно коммитить и отправлять в `dev`.
- В `main` перед публикацией отправляйте только чистый продуктовый код, тесты, packaging и пользовательскую/техническую документацию, необходимую для релиза; LLM/agent-служебные материалы в `main` не переносите.
- Перед публикацией Homebrew проверенные изменения из `dev` необходимо влить в `main`.
- GitHub Release, тег и обновление Homebrew formula создаются только от коммита из `main`; не публикуйте Homebrew из `dev`.
