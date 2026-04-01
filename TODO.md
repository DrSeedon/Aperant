# TODO

## Приоритет 1 — высокая отдача

- [x] **exitReason tracking** — `_save_exit_reason()` в `coder.py`. Пишет причину падения в `implementation_plan.json` (complete, concurrency_limit, rate_limit, max_iterations). ✅ СДЕЛАНО
- [ ] **Per-task provider selection** — каждая задача юзает свой API профиль. `providerId` в `task_metadata.json` → env override → agent. Референс: Aperant-MCP коммит `c776af7`.
- [ ] **Per-subtask model selection by Planner** — Planner выбирает модель для каждого subtask'а: haiku для scaffold, sonnet для CRUD, opus для архитектуры. Поле `model` в subtask schema. Файлы: `planner.md`, `coder.py`, `task.ts`.

## Приоритет 2 — средняя сложность

- [ ] **Внешний MCP-сервер для управления Aperant** — Claude Code из другого сеанса создаёт задачи, запускает билды, проверяет статус. Референс: Aperant-MCP (15 инструментов). Портировать на Python (FastMCP). Ключ к full automation.
- [ ] **RDR система (упрощённая)** — автовосстановление застрявших задач. 2-3 уровня эскалации: auto-continue → auto-recover → request changes. У нас есть `services/recovery.py` но без эскалации.
- [ ] **Skill-файлы для Claude Code** — `.claude/skills/` с инструкциями как управлять задачами через MCP. Просто markdown.
- [ ] **Инжекция spec.md summary в системный промпт** — spec.md не меняется, но агент читает его каждую сессию. Инжектить summary один раз.

## Приоритет 3 — на потом

- [ ] **Auto-Shutdown** — мониторит задачи, шатдаунит систему когда всё done. Адаптировать под Linux.
- [ ] **Watchdog** — внешний процесс-надзиратель. Проще через systemd unit.

## UI

- [ ] **AI merge resolver для plaintext** — `apps/backend/merge/ai_resolver/` падает на `.gitignore` конфликтах. Для plaintext файлов объединять обе стороны без AI.
- [ ] **Кнопка "Слить с AI" disable при uncommitted changes** — UI показывает warning но кнопка активна.

## Другие идеи

- [ ] Kanban reconciliation fix из Sallvainian/BMAD-Studio — auto-heal stuck задач
- [ ] Third-party auth паттерн из tytsxai/Auto-Claude-Chinese — reuse Claude CLI токена
