# TODO

## Приоритет 1 — высокая отдача

- [x] **Shared project context** — ✅ СДЕЛАНО. `.auto-claude/project_index.json` shared. Planner проверяет shared → пропускает exploration. Post-merge update в workspace.py. prompt_generator fallback shared → per-spec.

## Приоритет 2 — средняя сложность

- [ ] **Внешний MCP-сервер для управления Aperant** — Claude Code из другого сеанса создаёт задачи, запускает билды, проверяет статус. Референс: Aperant-MCP (15 инструментов). Портировать на Python (FastMCP). Ключ к full automation.
- [ ] **RDR система (упрощённая)** — автовосстановление застрявших задач. 2-3 уровня эскалации: auto-continue → auto-recover → request changes. У нас есть `services/recovery.py` но без эскалации.
- [ ] **Skill-файлы для Claude Code** — `.claude/skills/` с инструкциями как управлять задачами через MCP. Просто markdown.

## Приоритет 3 — на потом

- [ ] **Per-task provider selection** — каждая задача юзает свой API профиль. Актуально при 2+ аккаунтах или API credits. Референс: Aperant-MCP коммит `c776af7`.
- [ ] **Auto-Shutdown** — мониторит задачи, шатдаунит систему когда всё done. Адаптировать под Linux.
- [ ] **Watchdog** — внешний процесс-надзиратель. Проще через systemd unit.

## Промпт оптимизация

- [x] **qa_reviewer.md** — ✅ СДЕЛАНО. Phase 0 на тулзах, spec.md injected, port check
- [x] **planner.md** — ✅ СДЕЛАНО. Efficiency rules, no pwd/ls, use get_session_context
- [x] **Bash tool_input в QA логах** — ✅ СДЕЛАНО. reviewer.py теперь показывает command
- [x] **Auto-resolve JSON/plaintext merge conflicts** — ✅ СДЕЛАНО. workspace.py: JSON deep-merge + plaintext line-merge. Без AI.
- [x] **UsageMonitor 429 backoff** — ✅ СДЕЛАНО. 5 мин пауза после rate limit вместо спама каждые 30 сек.

## UI баги

- [ ] **Кнопка "Слить с AI" disable при uncommitted changes** — UI показывает warning но кнопка активна.

## Другие идеи

- [ ] Kanban reconciliation fix из Sallvainian/BMAD-Studio — auto-heal stuck задач
- [ ] Third-party auth паттерн из tytsxai/Auto-Claude-Chinese — reuse Claude CLI токена
