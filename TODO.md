# TODO

## Приоритет 1 — высокая отдача

- [x] **Shared project context** — ✅ СДЕЛАНО. `.auto-claude/project_index.json` shared. Planner проверяет shared → пропускает exploration. Post-merge update в workspace.py. prompt_generator fallback shared → per-spec.

## Приоритет 2 — средняя сложность

- [x] **Внешний MCP-сервер для управления Aperant** — ✅ СДЕЛАНО. `apps/backend/mcp_server.py` на FastMCP, 29 инструментов. Задачи, билды, QA, merge, PR, roadmap, ideation, GitHub issues. Гайд: `MCP_GUIDE.md`.
- [x] **Project Map (вариант D)** — ✅ СДЕЛАНО. `core/project_map.py` AST-парсит Python, regex для TS, DB tables. Post-merge + auto-gen при первом запуске. Инжектится в промпт автоматически. Кодер не трогает.
- [x] **RDR система** — ✅ СДЕЛАНО. `services/recovery.py` (retry/rollback/skip/escalate) + rate-limit-detector (auto-swap профилей) + stuck detection 15 сек + startup recovery scan (reset stuck subtasks при запуске app, `runStartupRecoveryScan` в agent-manager.ts, вызов через setTimeout 5s в index.ts).
- [x] **Skill-файлы для Claude Code** — ✅ ЗАМЕНЕНО MCP-сервером. 29 тулзов в `mcp_server.py` + `MCP_GUIDE.md`. MCP даёт типизированные тулзы с валидацией — skills избыточны.

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

## Сделано (2 апреля)

- [x] **Electron 40 → 41.1.1** — фикс краша GPU/Chromium 144 при смене статуса задачи на Linux
- [x] **MCP-сервер** — 29 инструментов (tasks, QA, merge, PR, roadmap, ideation, GitHub issues)
- [x] **QA progress на канбане** — заполняющаяся полоска по фазам (3/9), не бегающая
- [x] **Stuck detection 60s → 15s** — в 4 раза быстрее обнаружение зависших агентов
- [x] **AI Review анимация** — карточка пульсирует, полоска показывает фазу QA
- [x] **Timestamps в логах** — время на каждом tool entry, цветовой градиент свежести (зелёный→красный)
- [x] **Last activity на карточке** — показывает время с последнего AI действия для running задач
- [x] **Dev порт 5199** — не конфликтует с другими Vite проектами
- [x] **Crash logging** — child-process-gone и render-process-gone в логи

## UI баги

- [ ] **Кнопка "Слить с AI" disable при uncommitted changes** — UI показывает warning но кнопка активна.

## Другие идеи

- [ ] Kanban reconciliation fix из Sallvainian/BMAD-Studio — auto-heal stuck задач
- [ ] Third-party auth паттерн из tytsxai/Auto-Claude-Chinese — reuse Claude CLI токена
