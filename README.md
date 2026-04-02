# Aperant (Russian Fork)

> **Fork of [AndyMik90/Aperant](https://github.com/AndyMik90/Aperant)** — rolled back to stable **v2.7.6** with Russian localization, MCP server, and agent optimizations.

**Autonomous multi-agent coding framework that plans, builds, and validates software for you.**

![Auto Claude Kanban Board](.github/assets/Auto-Claude-Kanban.png)

## What's different in this fork

Based on **v2.7.6 stable** → version **2.7.8-fork.2**

### External MCP Server (30 tools)
Control Aperant from Claude Code in another terminal. One server manages multiple projects.
- **Full lifecycle:** create task (17 params, Literal enums) → build → QA → approve/reject → merge → PR
- **GitHub integration:** import issues as tasks, list PRs
- **Strategic tools:** roadmap (view/generate/accept features), ideation (generate/accept/dismiss ideas)
- **Builds via Electron API:** `start_task` delegates to UI via local HTTP (OAuth handled by Electron, zero tokens in MCP)
- **Auto-refresh:** UI picks up MCP/CLI changes every 10s
- Setup: add to `~/.claude/settings.json`, see [MCP_GUIDE.md](MCP_GUIDE.md)

### Project Map
Auto-generated `.auto-claude/project_map.md` — AST-parsed project structure injected into agent prompts.
- Python AST: classes, functions, imports per module
- TypeScript regex: exported functions and classes
- Database: ORM tables with columns
- Updated automatically after every merge, created on first access
- Agents receive full project map in system prompt — zero exploration overhead

### Agent Performance (61% waste → ~15%)
- **4 MCP tools** — `complete_subtask`, `get_next_subtask`, `run_verification`, `append_progress`
- **coder.md** slimmed 33KB → 20KB — removed ritual overhead
- **Per-subtask model selection** — haiku/sonnet/opus assigned by complexity
- **Model auto-escalation** — haiku fails → sonnet → opus
- **Prompt injection** — spec.md, progress, project map injected (0 startup reads)

### Localization
- **Russian UI** — 11 locale files (3500+ lines), CLDR pluralization
- **Dynamic agent language** — agents respond in UI-selected language

### Merge Auto-Resolve
- Auto-commit dirty files before merge → auto-resolve .gitignore, .lock, JSON conflicts → finalize (status done + delete worktree + branch)
- Direct merge first, smart merge fallback — handles diverged branches with uncommitted changes

### Stability
- **Electron 41.1.1** (Chromium 146) — fixes GPU crash on Linux ([#1906](https://github.com/AndyMik90/Aperant/issues/1906))
- **Stuck detection 15s** (was 60s) — 4x faster recovery
- **Startup recovery** — resets stuck subtasks on app launch
- **Crash logging** — child/render process crashes logged with details

### UI
- QA progress bar with phase counter (3/9) instead of bouncing animation
- Color-coded timestamps in logs (green = fresh, red = old)
- Last AI activity time on kanban cards
- Usage recovery % in badge and popup
- Metadata badges with type labels (Priority/Effort/Impact)
- Task detail: Context Files + Agent Config sections
- Model badge per subtask (haiku/sonnet/opus)
- Dev server on port 5199 (avoids Vite conflicts)

### Docs
- [MCP_GUIDE.md](MCP_GUIDE.md) — MCP server setup and workflows
- [CHANGELOG.md](CHANGELOG.md) — full list of changes
- [TODO.md](TODO.md) — prioritized roadmap

### Why v2.7.6?
Upstream v2.8.0-beta rewrote the entire Python backend to TypeScript in a single commit, breaking agent execution. The project has 255 unreviewed PRs and the sole maintainer hasn't merged anything since Feb 14. This fork stays on the last stable release that actually works.

---

[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](./agpl-3.0.txt)
[![Upstream](https://img.shields.io/badge/upstream-AndyMik90%2FAperant-blue?style=flat-square)](https://github.com/AndyMik90/Aperant)

---

## Download

### Stable Release

<!-- STABLE_VERSION_BADGE -->
[![Stable](https://img.shields.io/badge/stable-2.7.6-blue?style=flat-square)](https://github.com/AndyMik90/Auto-Claude/releases/tag/v2.7.6)
<!-- STABLE_VERSION_BADGE_END -->

<!-- STABLE_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [Auto-Claude-2.7.6-win32-x64.exe](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-win32-x64.exe) |
| **macOS (Apple Silicon)** | [Auto-Claude-2.7.6-darwin-arm64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-darwin-arm64.dmg) |
| **macOS (Intel)** | [Auto-Claude-2.7.6-darwin-x64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-darwin-x64.dmg) |
| **Linux** | [Auto-Claude-2.7.6-linux-x86_64.AppImage](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-linux-x86_64.AppImage) |
| **Linux (Debian)** | [Auto-Claude-2.7.6-linux-amd64.deb](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-linux-amd64.deb) |
| **Linux (Flatpak)** | [Auto-Claude-2.7.6-linux-x86_64.flatpak](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6/Auto-Claude-2.7.6-linux-x86_64.flatpak) |
<!-- STABLE_DOWNLOADS_END -->

### Beta Release

> ⚠️ Beta releases may contain bugs and breaking changes. [View all releases](https://github.com/AndyMik90/Auto-Claude/releases)

<!-- BETA_VERSION_BADGE -->
[![Beta](https://img.shields.io/badge/beta-2.7.6--beta.6-orange?style=flat-square)](https://github.com/AndyMik90/Auto-Claude/releases/tag/v2.7.6-beta.6)
<!-- BETA_VERSION_BADGE_END -->

<!-- BETA_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [Auto-Claude-2.7.6-beta.6-win32-x64.exe](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-win32-x64.exe) |
| **macOS (Apple Silicon)** | [Auto-Claude-2.7.6-beta.6-darwin-arm64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-darwin-arm64.dmg) |
| **macOS (Intel)** | [Auto-Claude-2.7.6-beta.6-darwin-x64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-darwin-x64.dmg) |
| **Linux** | [Auto-Claude-2.7.6-beta.6-linux-x86_64.AppImage](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-linux-x86_64.AppImage) |
| **Linux (Debian)** | [Auto-Claude-2.7.6-beta.6-linux-amd64.deb](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-linux-amd64.deb) |
| **Linux (Flatpak)** | [Auto-Claude-2.7.6-beta.6-linux-x86_64.flatpak](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.6/Auto-Claude-2.7.6-beta.6-linux-x86_64.flatpak) |
<!-- BETA_DOWNLOADS_END -->

> All releases include SHA256 checksums and VirusTotal scan results for security verification.

---

## Requirements

- **Claude Pro/Max subscription** - [Get one here](https://claude.ai/upgrade)
- **Claude Code CLI** - `npm install -g @anthropic-ai/claude-code`
- **Git repository** - Your project must be initialized as a git repo

---

## Quick Start

1. **Download and install** the app for your platform
2. **Open your project** - Select a git repository folder
3. **Connect Claude** - The app will guide you through OAuth setup
4. **Create a task** - Describe what you want to build
5. **Watch it work** - Agents plan, code, and validate autonomously

---

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Tasks** | Describe your goal; agents handle planning, implementation, and validation |
| **Parallel Execution** | Run multiple builds simultaneously with up to 12 agent terminals |
| **Isolated Workspaces** | All changes happen in git worktrees - your main branch stays safe |
| **Self-Validating QA** | Built-in quality assurance loop catches issues before you review |
| **AI-Powered Merge** | Automatic conflict resolution when integrating back to main |
| **Memory Layer** | Agents retain insights across sessions for smarter builds |
| **GitHub/GitLab Integration** | Import issues, investigate with AI, create merge requests |
| **Linear Integration** | Sync tasks with Linear for team progress tracking |
| **Cross-Platform** | Native desktop apps for Windows, macOS, and Linux |
| **Auto-Updates** | App updates automatically when new versions are released |

---

## Interface

### Kanban Board
Visual task management from planning through completion. Create tasks and monitor agent progress in real-time.

### Agent Terminals
AI-powered terminals with one-click task context injection. Spawn multiple agents for parallel work.

![Agent Terminals](.github/assets/Auto-Claude-Agents-terminals.png)

### Roadmap
AI-assisted feature planning with competitor analysis and audience targeting.

![Roadmap](.github/assets/Auto-Claude-roadmap.png)

### Additional Features
- **Insights** - Chat interface for exploring your codebase
- **Ideation** - Discover improvements, performance issues, and vulnerabilities
- **Changelog** - Generate release notes from completed tasks

---

## Project Structure

```
Auto-Claude/
├── apps/
│   ├── backend/     # Python agents, specs, QA pipeline
│   └── frontend/    # Electron desktop application
├── guides/          # Additional documentation
├── tests/           # Test suite
└── scripts/         # Build utilities
```

---

## CLI Usage

For headless operation, CI/CD integration, or terminal-only workflows:

```bash
cd apps/backend

# Create a spec interactively
python spec_runner.py --interactive

# Run autonomous build
python run.py --spec 001

# Review and merge
python run.py --spec 001 --review
python run.py --spec 001 --merge
```

See [guides/CLI-USAGE.md](guides/CLI-USAGE.md) for complete CLI documentation.

---

## Development

Want to build from source or contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for complete development setup instructions.

For Linux-specific builds (Flatpak, AppImage), see [guides/linux.md](guides/linux.md).

---

## Security

Auto Claude uses a three-layer security model:

1. **OS Sandbox** - Bash commands run in isolation
2. **Filesystem Restrictions** - Operations limited to project directory
3. **Dynamic Command Allowlist** - Only approved commands based on detected project stack

All releases are:
- Scanned with VirusTotal before publishing
- Include SHA256 checksums for verification
- Code-signed where applicable (macOS)

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run install:all` | Install backend and frontend dependencies |
| `npm start` | Build and run the desktop app |
| `npm run dev` | Run in development mode with hot reload |
| `npm run package` | Package for current platform |
| `npm run package:mac` | Package for macOS |
| `npm run package:win` | Package for Windows |
| `npm run package:linux` | Package for Linux |
| `npm run package:flatpak` | Package as Flatpak (see [guides/linux.md](guides/linux.md)) |
| `npm run lint` | Run linter |
| `npm test` | Run frontend tests |
| `npm run test:backend` | Run backend tests |

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

---

## Community

- **Discord** - [Join our community](https://discord.gg/KCXaPBr4Dj)
- **Issues** - [Report bugs or request features](https://github.com/AndyMik90/Auto-Claude/issues)
- **Discussions** - [Ask questions](https://github.com/AndyMik90/Auto-Claude/discussions)

---

## License

**AGPL-3.0** - GNU Affero General Public License v3.0

Auto Claude is free to use. If you modify and distribute it, or run it as a service, your code must also be open source under AGPL-3.0.

Commercial licensing available for closed-source use cases.

---

## Star History

[![GitHub Repo stars](https://img.shields.io/github/stars/AndyMik90/Auto-Claude?style=social)](https://github.com/AndyMik90/Auto-Claude/stargazers)

[![Star History Chart](https://api.star-history.com/svg?repos=AndyMik90/Auto-Claude&type=Date)](https://star-history.com/#AndyMik90/Auto-Claude&Date)
