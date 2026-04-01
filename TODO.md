# TODO

## Приоритет 1 — высокая отдача

- [ ] **Shared project context** — общий `.auto-claude/project_context/` для всех задач проекта (project_index.json, architecture.md, patterns.md). Planner читает при старте вместо 20 tool calls на исследование. Писать только **после мержа** (post-merge hook), не во время задачи — worktree'ы видят одну версию. Первая задача создаёт, остальные переиспользуют. Экономит 15-25 tool calls на каждый новый planner.

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

## UI баги

- [ ] **AI merge resolver для plaintext** — `apps/backend/merge/ai_resolver/` падает на `.gitignore` конфликтах. Для plaintext файлов объединять обе стороны без AI.
- [ ] **Кнопка "Слить с AI" disable при uncommitted changes** — UI показывает warning но кнопка активна.

## Другие идеи

- [ ] Kanban reconciliation fix из Sallvainian/BMAD-Studio — auto-heal stuck задач
- [ ] Third-party auth паттерн из tytsxai/Auto-Claude-Chinese — reuse Claude CLI токена
