# ARCHITECTURE.md

> Quick-reference map for AI agents. Не дублирует CLAUDE.md — дополняет его.
> CLAUDE.md = правила разработки. Этот файл = как всё устроено внутри.

---

## Что это

Aperant — форк [AndyMik90/Aperant](https://github.com/AndyMik90/Aperant) v2.7.6 stable.
Автономный мультиагентный кодинг-фреймворк: описываешь задачу → AI сам планирует, реализует и тестирует.
Monorepo: Python backend (весь AI + логика) + Electron/React frontend (desktop UI + CLI).

## Что добавлено в этом форке (vs upstream v2.7.6)

- Русская локализация — 11 locale файлов, 3500+ строк, CLDR-compliant (`_one`/`_few`/`_many`)
- Dynamic agent language — агенты отвечают на языке из UI settings (инжектится Python prompt loader)
- Cyrillic-safe JSON — `ensure_ascii=False` в spec pipeline
- Фикс: дублирование subtask title/description в task detail panel
- Фикс: PhaseProgressIndicator tooltip при отсутствии title

**НЕ портировано** из [Aperant-MCP](https://github.com/topemalheiro/Aperant-MCP): exitReason tracking, per-task provider selection, RDR escalation система. Планы в TODO.md.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12+, `claude-agent-sdk`, `uv`, pytest, Ruff |
| Frontend | Electron 39, React 19, TypeScript strict, Zustand 5, Tailwind v4, Vite 7, Vitest 4, Biome 2 |
| UI components | Radix UI, xterm.js 6 (WebGL), Framer Motion |
| IPC | Electron IPC via `window.electronAPI.*` bridge (preload) |
| Memory | Graphiti (Neo4j knowledge graph) — опционально |
| Integrations | GitHub, GitLab, Linear, Context7 MCP |

---

## Структура директорий

```
apps/
├── backend/                         # Весь AI + бизнес-логика
│   ├── run.py                       # Точка входа CLI: python run.py --spec 001
│   ├── core/
│   │   ├── client.py                # create_client() — ЕДИНСТВЕННЫЙ способ создать AI клиент
│   │   ├── simple_client.py         # create_simple_client() — для разовых calls без сессии
│   │   ├── auth.py                  # OAuth + API key management
│   │   ├── worktree.py              # Git worktree isolation
│   │   └── platform/               # isWindows(), isMacOS(), findExecutable() — КРОССПЛАТФОРМА
│   ├── agents/
│   │   ├── planner.py               # Planner agent — разбивает spec на subtasks
│   │   ├── coder.py                 # Coder agent — основной рабочий цикл реализации
│   │   ├── session.py               # Session management
│   │   ├── base.py                  # Base agent class
│   │   └── tools_pkg/
│   │       ├── models.py            # AGENT_CONFIGS — source of truth для tools/MCP per phase
│   │       └── tools/               # Custom tool implementations
│   ├── prompts/                     # System prompts агентов (.md файлы)
│   │   ├── planner.md               # Planner prompt
│   │   ├── coder.md                 # Coder prompt
│   │   ├── coder_recovery.md        # Recovery при зависшем агенте
│   │   ├── qa_reviewer.md           # QA validation
│   │   ├── qa_fixer.md              # QA issue resolution
│   │   ├── spec_gatherer.md         # Spec: сбор контекста
│   │   ├── spec_researcher.md       # Spec: research
│   │   ├── spec_writer.md           # Spec: написание
│   │   ├── spec_critic.md           # Spec: критика и улучшение
│   │   └── complexity_assessor.md   # Оценка сложности задачи
│   ├── spec/                        # Spec creation pipeline (5 фаз)
│   ├── qa/                          # QA loop: reviewer → fixer → repeat
│   ├── context/                     # Контекст для агентов (semantic search)
│   ├── merge/                       # Intent-aware semantic merge параллельных агентов
│   ├── services/
│   │   └── recovery.py              # Recovery orchestration для stuck задач
│   ├── security/                    # Command allowlisting, validators, hooks
│   ├── integrations/
│   │   ├── graphiti/                # Knowledge graph memory (Graphiti/Neo4j)
│   │   ├── github/                  # GitHub API интеграция
│   │   └── linear/                  # Linear project management
│   ├── runners/                     # Standalone runners (spec, roadmap, insights, github)
│   ├── phase_config.py              # get_phase_model(), get_phase_client_thinking_kwargs()
│   ├── phase_event.py               # ExecutionPhase events
│   ├── progress.py                  # count_subtasks(), get_next_subtask(), is_build_complete()
│   ├── prompt_generator.py          # generate_subtask_prompt(), format_context_for_prompt()
│   ├── recovery.py                  # RecoveryManager
│   ├── auto_claude_tools.py         # create_auto_claude_mcp_server() — MCP сервер для агентов
│   └── task_logger/                 # Логирование с subtask_id per entry
│
└── frontend/                        # Electron desktop UI
    └── src/
        ├── main/                    # Electron main process (Node.js)
        │   ├── index.ts             # Точка входа: BrowserWindow, env loading, Sentry
        │   ├── agent/
        │   │   ├── agent-queue.ts   # Очередь агентов, приоритеты, spec-locking
        │   │   ├── agent-process.ts # Spawn + IPC с Python subprocess
        │   │   ├── agent-state.ts   # Состояние запущенных агентов
        │   │   └── agent-events.ts  # Lifecycle events и state transitions
        │   ├── claude-profile/
        │   │   ├── credential-utils.ts   # OS keychain (Keychain/Win Cred Manager)
        │   │   ├── token-refresh.ts      # OAuth token lifecycle + auto-refresh
        │   │   ├── usage-monitor.ts      # Rate limit tracking per profile
        │   │   └── profile-scorer.ts     # Выбор профиля по доступности
        │   ├── terminal/
        │   │   ├── pty-daemon.ts         # Background PTY процесс
        │   │   ├── terminal-lifecycle.ts # Session creation/cleanup
        │   │   └── claude-integration-handler.ts  # Claude SDK в терминале
        │   ├── ipc-handlers/        # 40+ domain-специфичных IPC обработчиков
        │   ├── platform/            # isWindows(), getPathDelimiter() — кроссплатформа
        │   ├── services/            # SDK session recovery, profile service
        │   └── changelog/           # Changelog generation
        ├── preload/                 # electronAPI bridge (Main → Renderer)
        ├── renderer/                # React UI
        │   ├── App.tsx              # Root component
        │   ├── stores/              # 24+ Zustand stores
        │   │   ├── project-store.ts
        │   │   ├── task-store.ts
        │   │   ├── terminal-store.ts
        │   │   ├── settings-store.ts
        │   │   └── github/          # issues-store, pr-review-store
        │   ├── components/          # UI компоненты
        │   └── hooks/               # useIpc, useTerminal, и др.
        └── shared/
            ├── i18n/locales/
            │   ├── en/*.json        # 8 неймспейсов: common, navigation, settings, dialogs, tasks, errors, onboarding, welcome
            │   ├── fr/*.json
            │   └── ru/*.json        # ДОБАВЛЕНО в этом форке
            ├── types/               # 19+ TypeScript type files
            └── constants/themes.ts  # 7 цветовых тем (Default, Dusk, Lime, Ocean, Retro, Neo...)
```

---

## Pipeline: задача → код → merge

```
User input
    │
    ▼
[Spec Pipeline] — 5 фаз
  spec_gatherer  → читает проект, собирает контекст
  spec_researcher → Context7 MCP, docs lookup
  complexity_assessor → оценивает сложность (ai-based)
  spec_writer    → пишет spec.md + requirements.json
  spec_critic    → критикует и улучшает spec
    │
    ▼  .auto-claude/specs/XXX-name/spec.md
    │
[Planner Agent] — prompts/planner.md
  → implementation_plan.json со списком subtasks
    │
    ▼
[Coder Agent Loop] — prompts/coder.md
  Для каждого subtask:
    generate_subtask_prompt() → inject context → run agent
    → update_subtask_status (MCP tool)
    → git commit в worktree
  При зависании: RecoveryManager + coder_recovery.md
    │
    ▼
[QA Loop] — qa/
  qa_reviewer.md → проверяет, пишет qa_report.md
  Если issues → qa_fixer.md → исправляет → повтор
    │
    ▼
[Merge] — merge/
  Intent-aware semantic merge (если параллельные агенты)
    │
    ▼
User review → merge в main branch
```

---

## Ключевые файлы — быстрый доступ

| Задача | Файл |
|--------|------|
| Создать AI клиент | `apps/backend/core/client.py` → `create_client()` |
| Конфиг tools per phase | `apps/backend/agents/tools_pkg/models.py` → `AGENT_CONFIGS` |
| Изменить промпт агента | `apps/backend/prompts/*.md` |
| Добавить новый MCP tool | `models.py` + `AGENT_CONFIGS[phase]["mcp_servers"]` |
| IPC handler (новый домен) | `apps/frontend/src/main/ipc-handlers/` |
| Добавить i18n ключ | `apps/frontend/src/shared/i18n/locales/{en,fr,ru}/*.json` (ВСЕ языки!) |
| Platform detection (TS) | `apps/frontend/src/main/platform/` |
| Platform detection (Py) | `apps/backend/core/platform/` |
| Agent queue/routing | `apps/frontend/src/main/agent/agent-queue.ts` |
| Model/thinking per phase | `apps/backend/phase_config.py` |

---

## MCP-серверы

Конфиг: `AGENT_CONFIGS` в `agents/tools_pkg/models.py` — какие MCP серверы доступны в каждой фазе.

| MCP сервер | Когда доступен | Инструменты |
|------------|----------------|-------------|
| `auto-claude` | Coder, QA | `update_subtask_status`, `get_build_progress`, `record_discovery`, `record_gotcha`, `get_session_context`, `update_qa_status` |
| `context7` | spec_researcher, Coder, Planner | `resolve-library-id`, `query-docs` — документация библиотек |
| `linear-server` | Coder, QA (если LINEAR_API_KEY) | CRUD issues, projects, comments |
| `graphiti-memory` | Coder, QA (если GRAPHITI_MCP_URL) | `search_nodes`, `search_facts`, `add_episode`, `get_episodes` |
| `puppeteer` | QA only | Browser automation для web-проектов |
| `electron` | QA only (если ELECTRON_MCP_ENABLED=true) | `take_screenshot`, `send_command_to_electron`, `read_electron_logs` |

MCP сервер `auto-claude` создаётся в `apps/backend/auto_claude_tools.py` → `create_auto_claude_mcp_server()`.

---

## Данные проекта

```
.auto-claude/                    # gitignored, создаётся при первой задаче
├── specs/
│   └── 001-feature-name/
│       ├── spec.md              # Техзадание
│       ├── requirements.json    # Структурированные требования
│       ├── context.json         # Собранный контекст проекта
│       ├── implementation_plan.json  # Subtasks с статусами
│       ├── qa_report.md         # Результаты QA
│       └── QA_FIX_REQUEST.md    # Запросы на исправление QA
└── github/
    ├── pr/                      # PR review logs и результаты
    └── bot_detection_state.json # Gatekeeper для bot detector
```

---

## Запуск

```bash
# Установка
npm run install:all

# Desktop app
npm run dev          # Dev mode + HMR
npm run dev:debug    # Debug mode (verbose + Electron DevTools)
npm run dev:mcp      # Electron MCP сервер для AI отладки

# CLI только backend
cd apps/backend && python run.py --spec 001

# QA run
cd apps/backend && python run.py --spec 001 --qa

# E2E (QA агент управляет Electron)
npm run dev:debug                             # Терминал 1
ELECTRON_MCP_ENABLED=true python run.py --spec 001 --qa  # Терминал 2
```

---

## Паттерны — частые ошибки

1. **Никогда `anthropic.Anthropic()` напрямую** — только `create_client()` из `core.client`
2. **Никогда `process.platform`** — только функции из `platform/`
3. **Никогда хардкодить строки в JSX** — только `t('namespace:key')` через `react-i18next`
4. **Production debugging** — не `console.log`, только Sentry
5. **Electron paths** — проверять оба контекста: `app.isPackaged` true/false
6. **PR target** — всегда `develop`, не `main`
