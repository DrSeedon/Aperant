# ARCHITECTURE.md

> Quick-reference map for AI agents. Does not duplicate CLAUDE.md — complements it.
> CLAUDE.md = development rules. This file = how everything works inside.

---

## What is this

Aperant — fork of [AndyMik90/Aperant](https://github.com/AndyMik90/Aperant) v2.7.6 stable.
Autonomous multi-agent coding framework: describe a task → AI plans, implements, and validates it.
Monorepo: Python backend (all AI + logic) + Electron/React frontend (desktop UI).

## Fork changes (vs upstream v2.7.6)

- Russian localization — 11 locale files, 3500+ lines, CLDR-compliant (`_one`/`_few`/`_many`)
- Dynamic agent language — agents respond in UI-selected language (Python prompt loader)
- Cyrillic-safe JSON — `ensure_ascii=False` in spec pipeline
- 4 new MCP tools — `complete_subtask`, `get_next_subtask`, `run_verification`, `append_progress`
- Agent DX — coder.md slimmed 33KB→20KB, self-critique scales to complexity, venv/port checks
- Planner — complexity-aware subtask splitting (trivial→1-2, not 6)
- UI — log grouping by subtask, title/description dedup, page title rebrand
- Fix: subtask title/description duplication in task detail panel
- Fix: PhaseProgressIndicator tooltip when title is missing

**Not ported** from [Aperant-MCP](https://github.com/topemalheiro/Aperant-MCP): exitReason tracking, per-task provider selection, RDR escalation. Plans in TODO.md.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12+, `claude-agent-sdk`, `uv`, pytest, Ruff |
| Frontend | Electron 39, React 19, TypeScript strict, Zustand 5, Tailwind v4, Vite 7, Vitest 4, Biome 2 |
| UI components | Radix UI, xterm.js 6 (WebGL), Framer Motion |
| IPC | Electron IPC via `window.electronAPI.*` bridge (preload) |
| Memory | Graphiti (Neo4j knowledge graph) — optional |
| Integrations | GitHub, GitLab, Linear, Context7 MCP |

---

## Directory Structure

```
apps/
├── backend/                         # All AI + business logic
│   ├── run.py                       # CLI entry point: python run.py --spec 001
│   ├── core/
│   │   ├── client.py                # create_client() — THE ONLY way to create an AI client
│   │   ├── simple_client.py         # create_simple_client() — for one-off calls without session
│   │   ├── auth.py                  # OAuth + API key management
│   │   ├── worktree.py              # Git worktree isolation
│   │   └── platform/               # isWindows(), isMacOS(), findExecutable() — CROSS-PLATFORM
│   ├── agents/
│   │   ├── planner.py               # Planner agent — breaks spec into subtasks
│   │   ├── coder.py                 # Coder agent — main implementation work loop
│   │   ├── session.py               # Session management
│   │   ├── base.py                  # Base agent class
│   │   └── tools_pkg/
│   │       ├── models.py            # AGENT_CONFIGS — source of truth for tools/MCP per phase
│   │       └── tools/               # Custom MCP tool implementations
│   │           ├── subtask.py       # update_subtask_status, get_next_subtask, run_verification, complete_subtask
│   │           ├── progress.py      # get_build_progress, append_progress
│   │           ├── memory.py        # record_discovery, record_gotcha, get_session_context
│   │           └── qa.py            # update_qa_status
│   ├── prompts/                     # Agent system prompts (.md files)
│   │   ├── planner.md               # Planner prompt (complexity-aware splitting rules)
│   │   ├── coder.md                 # Coder prompt (20KB, tool-first workflow)
│   │   ├── coder_recovery.md        # Recovery for stuck agents
│   │   ├── qa_reviewer.md           # QA validation
│   │   ├── qa_fixer.md              # QA issue resolution
│   │   ├── spec_gatherer.md         # Spec: context gathering
│   │   ├── spec_researcher.md       # Spec: research
│   │   ├── spec_writer.md           # Spec: writing
│   │   ├── spec_critic.md           # Spec: critique and improvement
│   │   └── complexity_assessor.md   # Task complexity assessment
│   ├── prompts_pkg/
│   │   ├── prompt_generator.py      # generate_subtask_prompt() — injects subtask data + venv info
│   │   └── prompts.py               # load prompts, inject language instruction
│   ├── spec/                        # Spec creation pipeline (5 phases)
│   ├── qa/                          # QA loop: reviewer → fixer → repeat
│   ├── context/                     # Agent context (semantic search)
│   ├── merge/                       # Intent-aware semantic merge for parallel agents
│   ├── services/
│   │   └── recovery.py              # Recovery orchestration for stuck tasks
│   ├── security/                    # Command allowlisting, validators, hooks
│   ├── integrations/
│   │   ├── graphiti/                # Knowledge graph memory (Graphiti/Neo4j)
│   │   ├── github/                  # GitHub API integration
│   │   └── linear/                  # Linear project management
│   ├── runners/                     # Standalone runners (spec, roadmap, insights, github)
│   └── auto_claude_tools.py         # create_auto_claude_mcp_server() — MCP server for agents
│
└── frontend/                        # Electron desktop UI
    └── src/
        ├── main/                    # Electron main process (Node.js)
        │   ├── index.ts             # Entry point: BrowserWindow, env loading, Sentry
        │   ├── agent/
        │   │   ├── agent-queue.ts   # Agent queue, priorities, spec-locking
        │   │   ├── agent-process.ts # Spawn + IPC with Python subprocess
        │   │   ├── agent-state.ts   # Running agent state
        │   │   └── agent-events.ts  # Lifecycle events and state transitions
        │   ├── claude-profile/
        │   │   ├── credential-utils.ts   # OS keychain (Keychain/Win Cred Manager)
        │   │   ├── token-refresh.ts      # OAuth token lifecycle + auto-refresh
        │   │   ├── usage-monitor.ts      # Rate limit tracking per profile
        │   │   └── profile-scorer.ts     # Profile selection by availability
        │   ├── terminal/
        │   │   ├── pty-daemon.ts         # Background PTY process
        │   │   ├── terminal-lifecycle.ts # Session creation/cleanup
        │   │   └── claude-integration-handler.ts  # Claude SDK in terminal
        │   ├── ipc-handlers/        # 40+ domain-specific IPC handlers
        │   ├── platform/            # isWindows(), getPathDelimiter() — cross-platform
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
        │   ├── components/          # UI components
        │   └── hooks/               # useIpc, useTerminal, etc.
        └── shared/
            ├── i18n/locales/
            │   ├── en/*.json        # 11 namespaces
            │   ├── fr/*.json
            │   └── ru/*.json        # Added in this fork
            ├── types/               # 19+ TypeScript type files
            └── constants/themes.ts  # 7 color themes (Default, Dusk, Lime, Ocean, Retro, Neo...)
```

---

## Pipeline: task → code → merge

```
User input
    │
    ▼
[Spec Pipeline] — 5 phases
  spec_gatherer  → reads project, collects context
  spec_researcher → Context7 MCP, docs lookup
  complexity_assessor → AI-based complexity assessment
  spec_writer    → writes spec.md + requirements.json
  spec_critic    → critiques and improves spec
    │
    ▼  .auto-claude/specs/XXX-name/spec.md
    │
[Planner Agent] — prompts/planner.md
  → implementation_plan.json with subtask list
  → complexity-aware splitting (trivial: 1-2 subtasks, complex: unlimited)
    │
    ▼
[Coder Agent Loop] — prompts/coder.md
  For each subtask:
    get_next_subtask() → implement → run_verification() → complete_subtask()
    All bookkeeping via MCP tools (no manual plan/progress/git management)
  On failure: RecoveryManager + coder_recovery.md
    │
    ▼
[QA Loop] — qa/
  qa_reviewer.md → validates, writes qa_report.md
  If issues → qa_fixer.md → fixes → repeat
    │
    ▼
[Merge] — merge/
  Intent-aware semantic merge (for parallel agents)
    │
    ▼
User review → merge into main branch
```

---

## Key Files — Quick Access

| Task | File |
|------|------|
| Create AI client | `apps/backend/core/client.py` → `create_client()` |
| Tools config per phase | `apps/backend/agents/tools_pkg/models.py` → `AGENT_CONFIGS` |
| Edit agent prompt | `apps/backend/prompts/*.md` |
| Add new MCP tool | `tools_pkg/tools/*.py` + register in `models.py` `AGENT_CONFIGS` |
| IPC handler (new domain) | `apps/frontend/src/main/ipc-handlers/` |
| Add i18n key | `apps/frontend/src/shared/i18n/locales/{en,fr,ru}/*.json` (ALL languages!) |
| Platform detection (TS) | `apps/frontend/src/main/platform/` |
| Platform detection (Py) | `apps/backend/core/platform/` |
| Agent queue/routing | `apps/frontend/src/main/agent/agent-queue.ts` |
| Model/thinking per phase | `apps/backend/phase_config.py` |

---

## MCP Servers

Config: `AGENT_CONFIGS` in `agents/tools_pkg/models.py` — which MCP servers are available per phase.

| MCP Server | When Available | Tools |
|------------|---------------|-------|
| `auto-claude` | Coder, Planner, QA | `update_subtask_status`, `get_build_progress`, `get_next_subtask`, `run_verification`, `complete_subtask`, `append_progress`, `record_discovery`, `record_gotcha`, `get_session_context`, `update_qa_status` |
| `context7` | spec_researcher, Coder, Planner | `resolve-library-id`, `query-docs` — library documentation |
| `linear-server` | Coder, QA (if LINEAR_API_KEY) | CRUD issues, projects, comments |
| `graphiti-memory` | Coder, QA (if GRAPHITI_MCP_URL) | `search_nodes`, `search_facts`, `add_episode`, `get_episodes` |
| `puppeteer` | QA only | Browser automation for web projects |
| `electron` | QA only (if ELECTRON_MCP_ENABLED=true) | `take_screenshot`, `send_command_to_electron`, `read_electron_logs` |

MCP server `auto-claude` is created in `apps/backend/auto_claude_tools.py` → `create_auto_claude_mcp_server()`.

---

## Project Data

```
.auto-claude/                    # gitignored, created on first task
├── specs/
│   └── 001-feature-name/
│       ├── spec.md              # Task specification
│       ├── requirements.json    # Structured requirements
│       ├── context.json         # Collected project context
│       ├── implementation_plan.json  # Subtasks with statuses
│       ├── qa_report.md         # QA results
│       └── QA_FIX_REQUEST.md    # QA fix requests
└── github/
    ├── pr/                      # PR review logs and results
    └── bot_detection_state.json # Gatekeeper for bot detector
```

---

## Running

```bash
# Install
npm run install:all

# Desktop app
npm run dev          # Dev mode + HMR
npm run dev:debug    # Debug mode (verbose + Electron DevTools)

# CLI only (backend)
cd apps/backend && python run.py --spec 001

# QA run
cd apps/backend && python run.py --spec 001 --qa
```

---

## Common Mistakes

1. **Never `anthropic.Anthropic()` directly** — only `create_client()` from `core.client`
2. **Never `process.platform`** — only functions from `platform/`
3. **Never hardcode strings in JSX** — only `t('namespace:key')` via `react-i18next`
4. **Production debugging** — not `console.log`, only Sentry
5. **Electron paths** — check both contexts: `app.isPackaged` true/false
6. **PR target** — always `develop`, not `main`
