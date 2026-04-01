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

## Agent DX (Developer Experience) — 61% tool calls впустую

Реальные данные: задача 002 Game-Master, 22 subtask'а, 655 tool calls.
Полезная работа: 256 (39%). Bookkeeping/waste: 399 (61%).

### Проблема 1: Startup ритуал — 87 calls потрачено (13%)

**Что происходит:** coder.md Step 1 (строки 130-205) заставляет агента при КАЖДОЙ сессии выполнить 11 команд: pwd, ls, find plan, cat plan.json, cat spec.md, cat project_index.json, cat context.json, cat build-progress.txt, git log, grep completed/pending, cat memory/*. Это 5-15 tool calls ПЕРЕД первой строкой кода.

**Почему плохо:** spec.md никогда не меняется — зачем читать каждый раз? Plan JSON уже парсится тулзой get_build_progress. Memory файлы можно получить через get_session_context. Агент тратит 30% контекста на ориентацию.

**Как исправить:**
- [ ] **Инжектить subtask context в системный промпт** — `prompts_pkg/prompt_generator.py` уже генерирует промпт для конкретного subtask'а. Расширить: добавить поля subtask'а (id, description, files_to_modify, files_to_create, patterns_from, verification) прямо в промпт. Агент стартует уже зная что делать.
- [ ] **Убрать обязательные cat** из Step 1 — заменить на: "Если нужна дополнительная информация — используй get_build_progress и get_session_context тулзы". Файл: `prompts/coder.md` строки 130-205.
- [ ] **spec.md — один раз** — инжектить summary из spec.md в системный промпт, убрать cat spec.md из Step 1.

### Проблема 2: Дублирующиеся Read — 98 calls потрачено (15%)

**Что происходит:** Агент читает одни и те же файлы по кругу:
- implementation_plan.json: 31 Read (нужен 1-2 раза)
- spec.md: 18 Read (нужен 0 раз — контент не меняется)
- build-progress.txt: 12 Read (нужен 0 раз — только append)
- Рабочие файлы (server.py, config.py): повторные Read после того как сам только что написал

**Почему плохо:** Каждый Read = файл целиком в контекст. plan.json + spec.md = ~15KB. При 30 повторных Read = ~450KB контекста впустую.

**Как исправить:**
- [ ] **get_next_subtask() тулза** — возвращает полные данные pending subtask'а: id, description, files_to_modify, files_to_create, patterns_from, verification, phase_name. Агенту не надо Read'ить план. Файл: `tools/subtask.py`
- [ ] **get_subtask_files() тулза** — по subtask_id возвращает только files без загрузки всего JSON. Файл: `tools/subtask.py`
- [ ] **Убрать "Read plan to find next subtask" из Step 3** (строки 245-256) — заменить на вызов get_next_subtask(). Файл: `prompts/coder.md`

### Проблема 3: Git overhead — 67 calls потрачено (10%)

**Что происходит:** coder.md Step 9 (строки 753-823) требует Mandatory Path Verification перед КАЖДЫМ git add: pwd → ls → verify → git add → git commit. При 19 subtask'ах = 3.5 git операции на subtask.

Плюс Step 6 (строка 468-477) — "MANDATORY: Before implementing anything, confirm where you are: pwd" перед каждой записью.

**Как исправить:**
- [ ] **complete_subtask() тулза** — объединяет: update_status(completed) + append build-progress.txt + git add+commit + return next subtask. ОДИН вызов вместо 5. Файл: `tools/subtask.py`
- [ ] **Убрать Mandatory Pre-Command Check** (строки 111-126) — pwd перед каждым git это паранойя. Достаточно одного pwd при старте сессии. Файл: `prompts/coder.md`
- [ ] **Убрать pwd из Step 6** (строки 468-477) — агент уже знает где он после Step 1. Файл: `prompts/coder.md`

### Проблема 4: Server start loops — 49 calls потрачено (7.5%)

**Что происходит:** Step 4 (строки 262-284) требует запускать dev environment перед каждым subtask'ом. Агент пытается: uvicorn → fail → uv run → fail → timeout → fail → ищет venv по всем папкам (42 команды типа `find .venv`, `ls -la ../.venv`).

**Как исправить:**
- [ ] **Передавать venv_path и run_command в контексте** — `prompt_generator.py` уже знает project_index.json где есть dev_command и venv path. Инжектить в промпт: "Твой venv: ./.venv, запуск: uv run uvicorn ...". Файл: `prompts_pkg/prompt_generator.py`
- [ ] **Step 4 — только для первого subtask'а** — если сервер уже запущен (порт занят), не перезапускать. Добавить проверку `lsof -i:PORT` перед запуском. Файл: `prompts/coder.md` строки 262-284.

### Проблема 5: Self-Critique overhead — 15+ calls потрачено

**Что происходит:** Step 6.5 (строки 543-675) — MANDATORY Self-Critique Checklist с 25+ пунктами. Агент реально проходит каждый пункт, запускает echo-команды, перечитывает файлы для проверки. На тривиальном subtask'е (создать config.py) — это overkill.

**Как исправить:**
- [ ] **Привязать critique к сложности subtask'а** — тривиальные (1 файл, scaffold) → skip critique. Средние → краткий checklist (5 пунктов). Сложные → полный. Связать с полем `model` из Smart Model Selection. Файл: `prompts/coder.md` строки 543-675.

### Проблема 6: Planner over-splitting — 6 subtask'ов на тривиальную задачу

**Что происходит:** planner.md строка 362: "Small scope — Each subtask should take 1-3 files max". Planner послушно нарезает AdminFilter (тривиальная задача: 1 файл создать, 1 изменить) на 6 subtask'ов: создать директорию, создать класс, создать __init__, рефакторинг, тесты, запуск тестов. Claude Code сделал бы это за 30 секунд одним действием.

**Почему плохо:** 6 subtask'ов × ~30 tool calls overhead = ~180 tool calls на задачу которая стоит 5. Плюс 6 сессий = 6 startup ритуалов.

**Как исправить:**
- [ ] **Добавить правило слияния в planner.md** — "Для SIMPLE workflow: если все subtask'и в одном сервисе и ≤5 файлов суммарно → объединить в 1-2 subtask'а. Не нарезать 'создать директорию' и 'создать __init__.py' как отдельные subtask'и — это одна операция." Файл: `prompts/planner.md`, секция Subtask Guidelines (строки 359-364).
- [ ] **Complexity-aware splitting** — planner уже знает complexity assessment (trivial/low/medium/high/critical из complexity_assessor.md). Привязать гранулярность: trivial → 1-2 subtask'а max, low → 3-5, medium → 5-10, high/critical → без лимита. Файл: `prompts/planner.md`

### Проблема 7: build-progress.txt — 23 calls потрачено

**Что происходит:** Step 10 (строки 834-856) требует Read + APPEND подробного отчёта после каждого subtask'а. Формат: 10 строк с датой, service, files modified, verification result, next subtask.

**Как исправить:**
- [ ] **append_progress() тулза** — одним вызовом дописывает текст. Без Read. Файл: `tools/progress.py`
- [ ] **Или включить в complete_subtask()** — summary передаётся как параметр, тулза сама формирует и дописывает.

### Проблема 8: Verification без автоматизации — ~30 calls

**Что происходит:** Каждый subtask имеет verification (command + expected). Агент вручную: Read plan → находит verification → Bash command → сравнивает вывод глазами → пишет результат. Часто создаёт temp файлы (test_config_debug.py) → запускает → удаляет = 3-5 лишних calls.

**Как исправить:**
- [ ] **run_verification() тулза** — принимает subtask_id, читает verification из плана, выполняет command, сравнивает с expected, возвращает pass/fail с diff. Файл: `tools/subtask.py`

### Сводка: потенциальная экономия + сложность внедрения

| # | Фикс | Экономия | Сложность | Что менять | Время |
|---|------|----------|-----------|-----------|-------|
| 1 | Убрать pwd-ритуалы из промпта | ~45 calls | 🟢 Лёгкая | Удалить строки из `coder.md` | 10 мин |
| 2 | Убрать обязательные cat из Step 1 | ~40 calls | 🟢 Лёгкая | Переписать Step 1 в `coder.md` | 15 мин |
| 3 | Step 4 — проверять порт перед запуском | ~49 calls | 🟢 Лёгкая | Добавить `lsof` check в `coder.md` | 5 мин |
| 4 | Critique по сложности | ~15 calls | 🟢 Лёгкая | Условие в `coder.md` Step 6.5 | 10 мин |
| 5 | get_next_subtask() тулза | ~50 calls, ~20% ctx | 🟡 Средняя | Новая функция в `tools/subtask.py`, регистрация в `models.py` | 30 мин |
| 6 | append_progress() тулза | ~23 calls | 🟢 Лёгкая | Новая функция в `tools/progress.py` | 15 мин |
| 7 | run_verification() тулза | ~30 calls | 🟡 Средняя | Новая функция в `tools/subtask.py`, subprocess.run | 30 мин |
| 8 | complete_subtask() тулза | ~87 calls, ~15% ctx | 🟡 Средняя | Комбо: update status + progress + git + next. `tools/subtask.py` | 45 мин |
| 9 | Инжекция subtask в промпт | ~80 calls, ~30% ctx | 🟡 Средняя | `prompt_generator.py` — добавить subtask data в промпт | 30 мин |
| 10 | venv/run_command в контексте | ~42 calls | 🟡 Средняя | `prompt_generator.py` — читать project_index, инжектить пути | 20 мин |
| 11 | Planner smart splitting | ~100+ calls | 🔴 Сложная | `planner.md` — переписать Subtask Guidelines, complexity rules | 1-2 часа |

**Рекомендуемый порядок:** сначала 🟢 (40 мин, чистка промптов), потом 🟡 тулзы (2.5 часа), потом 🔴 planner (1-2 часа).

**ROI:** фиксы 1-4 (чистка промптов) = 40 мин работы → ~150 calls экономии на каждую задачу. Это самый жирный ROI.

## Smart Model Selection

- [ ] **Per-subtask model selection by Planner** — Planner (Opus, high thinking) уже видит сложность каждого subtask'а. Добавить поле `model: "haiku" | "sonnet" | "opus"` в subtask schema. Planner при планировании выбирает модель: haiku для scaffold/config, sonnet для CRUD/API, opus для архитектуры/сложной логики. Coder.py читает `subtask.model` и передаёт в `create_client()`. Три файла: `prompts/planner.md` (schema + инструкция), `agents/coder.py` (читать model), `shared/types/task.ts` (тип). Ноль доп. API calls — Planner уже запущен.

## UI улучшения

- [ ] **Группировка логов по subtask'ам** — сейчас 900+ записей в Coding фазе идут плоской лентой. Backend уже пишет `subtask_id` в каждую лог-запись (`TaskLogEntry.subtask_id`), но UI (`TaskLogs.tsx`) это поле игнорирует. Нужно: сгруппировать entries по subtask_id через `useMemo`, добавить collapsible `SubtaskLogGroup` между phase и entries, подтянуть название из `task.subtasks`. Только фронтенд, backend не трогать.

## Другие идеи

- [ ] Посмотреть kanban reconciliation fix из **Sallvainian/BMAD-Studio** — auto-heal stuck задач
- [ ] Посмотреть third-party auth паттерн из **tytsxai/Auto-Claude-Chinese** — reuse Claude CLI токена
