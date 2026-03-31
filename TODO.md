# TODO

## Портировать из Aperant-MCP (topemalheiro/Aperant-MCP)

Референс: https://github.com/topemalheiro/Aperant-MCP (v2.7.6-beta.5, совместим с нашей базой)

### Приоритет 1 — быстро, большая отдача

- [ ] **exitReason tracking** — `_save_exit_reason()` в `coder.py` и `planner.py` (~80 строк). Пишет причину падения в `implementation_plan.json`. У нас есть `stuck_subtasks` recovery в `prompts_pkg/prompts.py` но нет structured exit reason. Это дополняет.

- [ ] **Per-task provider selection** — каждая задача может юзать свой API профиль. У нас уже есть `providerId` в `integrations/types.ts` но не используется для выбора провайдера при старте агента. У них полная цепочка: metadata → env override → agent.

### Уже есть у нас

- [x] **Project Index Cache** — `core/client.py`, `_get_cached_project_data()` с TTL 5 мин + threading.Lock
- [x] **Stuck subtask recovery** — `prompts_pkg/prompts.py:306` — recovery context для stuck subtasks с attempt count
- [x] **File watcher** — `file-watcher.ts` + chokidar уже подключён (11 файлов юзают), мониторит plan-файлы
- [x] **MCP базовый** — `auto_claude_tools.py` + `create_auto_claude_mcp_server()` — уже есть MCP-сервер для тулзов агентов
- [x] **Overnight token refresh** — `token-refresh.ts` + `usage-monitor.ts` — автообновление токенов для ночных билдов
- [x] **Queue routing** — `queue-routing-handlers.ts` — profile-aware task distribution

### Приоритет 2 — средняя сложность

- [ ] **RDR система (упрощённая)** — 6-уровневая автоэскалация при падении задач. У нас есть recovery (`services/recovery.py`) но без эскалации. RDR добавляет: auto-continue → auto-recover → request changes → fix JSON → debug → recreate.

- [ ] **Skill-файлы для Claude Code** — `.claude/skills/` с инструкциями как управлять задачами. Просто markdown, адаптировать под наш workflow.

### Приоритет 3 — на потом

- [ ] **Расширенный MCP-сервер** — у них 15 инструментов (create_task, start_batch, wait_for_review, recover_stuck). У нас базовый MCP есть, но нет batch-операций и recovery через MCP.

- [ ] **Auto-Shutdown** — мониторит задачи, шатдаунит систему когда всё done. Полезно для overnight runs. Адаптировать под Linux.

- [ ] **Watchdog** — внешний процесс-надзиратель. У нас проще через systemd unit.

### Не портировать

- **Window Manager** — Windows-only, PowerShell, слепой paste через Ctrl+V
- **Output Monitor** — читает JSONL internals Claude Code через regex, хрупко
- **MiniMax preset** — специфичный провайдер
- **HuggingFace OAuth** — не нужен

## Разница версий: наш v2.7.6 vs Aperant-MCP v2.7.6-beta.5

Оба на одной базе (v2.7.6), разница минимальная:
- beta.5 = develop на момент 13 февраля (несколько фиксов до финального release)
- v2.7.6 stable = develop на 20 февраля (включает все beta-фиксы + merge cleanup)
- Наш форк = v2.7.6 stable + русификация + UI фиксы
- Их форк = v2.7.6-beta.5 + MCP/RDR/Watchdog/Per-task provider (444 коммита)
- Код совместим: те же пути, тот же Python backend, тот же Electron frontend

## UI улучшения

- [ ] **Группировка логов по subtask'ам** — сейчас 900+ записей в Coding фазе идут плоской лентой. Backend уже пишет `subtask_id` в каждую лог-запись (`TaskLogEntry.subtask_id`), но UI (`TaskLogs.tsx`) это поле игнорирует. Нужно: сгруппировать entries по subtask_id через `useMemo`, добавить collapsible `SubtaskLogGroup` между phase и entries, подтянуть название из `task.subtasks`. Только фронтенд, backend не трогать.

## Другие идеи

- [ ] Посмотреть kanban reconciliation fix из **Sallvainian/BMAD-Studio** — auto-heal stuck задач
- [ ] Посмотреть third-party auth паттерн из **tytsxai/Auto-Claude-Chinese** — reuse Claude CLI токена
