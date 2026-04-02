# Aperant MCP Server — Guide for AI Assistants

## What is this

Aperant MCP Server lets you (Claude Code) control Aperant — an autonomous multi-agent coding framework. You can create tasks, run builds, check status, merge results, and create PRs across multiple projects.

## How MCP works

- **MCP (Model Context Protocol)** — a protocol for AI assistants to call external tools
- **This server runs locally** as a subprocess of Claude Code (stdio transport)
- **Claude Code is the host** — it starts the server process and talks to it via stdin/stdout
- **No network, no auth** — everything runs on your machine, same permissions as the user
- **One server, many projects** — every tool accepts `project_dir` parameter. No need for separate servers per project

## Setup

### Option 1: Global (all projects)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "aperant": {
      "command": "/path/to/Aperant/apps/backend/.venv/bin/python",
      "args": ["/path/to/Aperant/apps/backend/mcp_server.py"]
    }
  }
}
```

Then in any project, call tools with explicit `project_dir`:
```
mcp__aperant__list_tasks(project_dir="/path/to/my-project")
```

### Option 2: Per-project (auto-detects project)

Add `.mcp.json` to your project root:

```json
{
  "mcpServers": {
    "aperant": {
      "command": "/path/to/Aperant/apps/backend/.venv/bin/python",
      "args": ["/path/to/Aperant/apps/backend/mcp_server.py"],
      "env": {
        "APERANT_PROJECT": "/path/to/this/project"
      }
    }
  }
}
```

Then `project_dir` defaults to `APERANT_PROJECT` — no need to pass it every time:
```
mcp__aperant__list_tasks()
```

### Option 3: Multi-project orchestrator

For managing 4+ projects from one place, use global setup (Option 1) and always pass `project_dir`. Example workflow:

```
# Check all projects
mcp__aperant__list_tasks(project_dir="/projects/api-service")
mcp__aperant__list_tasks(project_dir="/projects/web-frontend")
mcp__aperant__list_tasks(project_dir="/projects/mobile-app")
mcp__aperant__list_tasks(project_dir="/projects/shared-lib")

# Start builds across projects
mcp__aperant__start_task(spec="001", project_dir="/projects/api-service")
mcp__aperant__start_task(spec="003", project_dir="/projects/web-frontend")

# Monitor progress
mcp__aperant__get_task_status(spec="001", project_dir="/projects/api-service")
```

## Available Tools (22)

### Task Management

| Tool | Description |
|------|-------------|
| `list_tasks` | List all tasks with status, subtask progress, QA state |
| `get_task_details` | Full spec, subtask breakdown, QA report for a task |
| `get_task_status` | Current status, progress, whether process is running |
| `create_task` | Create a new task from title + description |

### Execution

| Tool | Description |
|------|-------------|
| `start_task` | Start build (non-blocking, runs in background) |
| `stop_task` | Stop a running build |
| `recover_task` | Restart a stuck task from last checkpoint |

### Review

| Tool | Description |
|------|-------------|
| `approve_task` | Approve a completed task (mark done, ready to merge) |
| `reject_task` | Reject with feedback → QA_FIX_REQUEST.md → re-run |

### GitHub

| Tool | Description |
|------|-------------|
| `list_issues` | List GitHub issues (filter by state, labels) |
| `get_issue` | Get full issue details |
| `import_issue` | Import GitHub issue as Aperant task |
| `list_prs` | List pull requests with review status |

### QA

| Tool | Description |
|------|-------------|
| `run_qa` | Run QA validation (blocking, waits for result) |
| `qa_status` | Check QA validation state |

### Workspace & Merge

| Tool | Description |
|------|-------------|
| `list_worktrees` | List all build worktrees |
| `review_build` | Show diff of what was built |
| `merge_preview` | Preview merge conflicts |
| `merge_build` | Merge build into main project |
| `discard_build` | Delete a build (irreversible) |

### PR & Logs

| Tool | Description |
|------|-------------|
| `create_pr` | Create GitHub pull request |
| `get_build_logs` | Get recent build log output |

### Roadmap

| Tool | Description |
|------|-------------|
| `get_roadmap` | View roadmap with features, milestones, and status per phase |
| `generate_roadmap` | Generate strategic roadmap (long-running, optional competitor analysis) |
| `accept_roadmap_feature` | Accept a feature → creates Aperant task from it |

### Ideation

| Tool | Description |
|------|-------------|
| `get_ideas` | List generated ideas (filter by type) |
| `generate_ideas` | Generate improvement ideas (code, UX, security, perf, docs, quality) |
| `accept_idea` | Accept idea → creates Aperant task from it |
| `dismiss_idea` | Archive/dismiss an idea |

## Common Parameters

- `project_dir` (string, optional) — project path. Falls back to `APERANT_PROJECT` env, then `cwd`
- `spec` (string) — spec identifier. Can be short (`001`) or full (`001-feature-name`)
- `model` (string, optional) — Claude model override (e.g., `claude-sonnet-4-20250514`)

## Typical Workflows

### Create and build a feature

```
1. create_task(title="Add user auth", description="Implement JWT-based authentication...")
2. start_task(spec="014")          # non-blocking, runs in background
3. get_task_status(spec="014")     # poll until complete
4. get_task_details(spec="014")    # review what was built
5. merge_build(spec="014")         # merge into project
```

### Monitor and manage multiple projects

```
1. list_tasks(project_dir="/proj/A")    # see all tasks
2. list_tasks(project_dir="/proj/B")
3. start_task(spec="002", project_dir="/proj/A")
4. start_task(spec="001", project_dir="/proj/B")
5. get_task_status(spec="002", project_dir="/proj/A")  # check progress
6. get_build_logs(spec="002", project_dir="/proj/A")   # see what's happening
```

### Review and merge a completed build

```
1. review_build(spec="005")        # see the diff
2. merge_preview(spec="005")       # check for conflicts
3. merge_build(spec="005")         # merge it
4. create_pr(spec="005", target_branch="main", draft=true)
```

### Discover and implement improvements

```
1. generate_ideas(types="security_hardening,performance_optimizations")
2. get_ideas()                     # review all ideas
3. accept_idea("sh-002")           # creates task from idea
4. start_task(spec="015")          # build it
```

### Strategic planning

```
1. generate_roadmap(competitor_analysis=true)   # one-time generation
2. get_roadmap()                               # view phases and milestones
3. get_ideas(idea_type="code_improvements")    # tactical improvements
```

### GitHub issue → task → PR pipeline

```
1. list_issues()                   # see open issues
2. import_issue(42)                # creates Aperant task from issue #42
3. start_task(spec="016")          # build it
4. approve_task(spec="016")        # approve
5. merge_build(spec="016")         # merge
6. create_pr(spec="016")           # PR back to GitHub
```

## Important Notes

- `start_task` is **non-blocking** — it starts a background process and returns immediately. Use `get_task_status` to poll progress
- `run_qa` is **blocking** — it waits for QA to complete (up to 10 minutes)
- `discard_build` is **irreversible** — it deletes the worktree and branch
- Builds run in **isolated git worktrees** by default (safe, won't affect main branch)
- The server uses Aperant's own Python venv — no additional setup needed
- All task data lives in `{project}/.auto-claude/specs/` (gitignored)
