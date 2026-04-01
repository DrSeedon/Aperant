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

### Приоритет 2 — средняя сложность (продолжение)

- [ ] **Внешний MCP-сервер для управления Aperant** — чтобы Claude Code из другого сеанса мог создавать задачи, запускать билды, проверять статус, управлять несколькими проектами. Референс: Aperant-MCP (15 инструментов: create_task, start_batch, get_status, wait_for_review, recover_stuck). Портировать на Python (FastMCP). Это ключ к full automation: Master LLM → Aperant MCP → агенты работают.

### Приоритет 3 — на потом

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

## Agent DX (Developer Experience)

- [ ] **complete_subtask()** — объединяет 4-5 tool calls в один: update_status(completed) + append build-progress.txt + git add+commit + return next subtask. Сейчас агент после каждого subtask'а: Read plan → update_subtask_status → Read progress → Edit progress → Bash git commit = 5 вызовов × 22 subtask'а = 110 вызовов впустую. Файл: `apps/backend/agents/tools_pkg/tools/subtask.py`

- [ ] **get_next_subtask()** — полные данные следующего pending subtask'а: id, description, files_to_modify, files_to_create, patterns_from, verification. Сейчас `get_build_progress` возвращает текстовый отчёт, после чего агент всё равно Read'ит весь plan JSON чтобы достать конкретные поля. Файл: `tools/subtask.py` или `tools/progress.py`

- [ ] **run_verification()** — принимает subtask_id, читает verification из плана, выполняет команду, сравнивает с expected, возвращает pass/fail. Агент сейчас вручную: Read plan → Bash command → сравнивает в голове → пишет результат. Файл: `tools/subtask.py`

- [ ] **append_progress()** — дописывает текст в build-progress.txt одним вызовом. Агент сейчас Read + Edit = 2 вызова каждый раз. Файл: `tools/progress.py`

- [ ] **get_subtask_files()** — по subtask_id возвращает files_to_modify, files_to_create, patterns_from без загрузки всего plan JSON в контекст агента. Файл: `tools/subtask.py`

## Smart Model Selection

- [ ] **Per-subtask model selection by Planner** — Planner (Opus, high thinking) уже видит сложность каждого subtask'а. Добавить поле `model: "haiku" | "sonnet" | "opus"` в subtask schema. Planner при планировании выбирает модель: haiku для scaffold/config, sonnet для CRUD/API, opus для архитектуры/сложной логики. Coder.py читает `subtask.model` и передаёт в `create_client()`. Три файла: `prompts/planner.md` (schema + инструкция), `agents/coder.py` (читать model), `shared/types/task.ts` (тип). Ноль доп. API calls — Planner уже запущен.

## UI улучшения

- [ ] **Группировка логов по subtask'ам** — сейчас 900+ записей в Coding фазе идут плоской лентой. Backend уже пишет `subtask_id` в каждую лог-запись (`TaskLogEntry.subtask_id`), но UI (`TaskLogs.tsx`) это поле игнорирует. Нужно: сгруппировать entries по subtask_id через `useMemo`, добавить collapsible `SubtaskLogGroup` между phase и entries, подтянуть название из `task.subtasks`. Только фронтенд, backend не трогать.

## Другие идеи

- [ ] Посмотреть kanban reconciliation fix из **Sallvainian/BMAD-Studio** — auto-heal stuck задач
- [ ] Посмотреть third-party auth паттерн из **tytsxai/Auto-Claude-Chinese** — reuse Claude CLI токена
