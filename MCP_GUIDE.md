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

Then `project_dir` defaults to `APERANT_PROJECT` — no need to pass it every time.

### Option 3: Multi-project orchestrator

For managing 4+ projects from one place, use global setup (Option 1) and always pass `project_dir`.

---

## Available Tools (30)

### Task Management

**`list_tasks`** — List all tasks with status, subtask progress, QA state.
- `project_dir` (optional) — project path

**`get_task_details`** — Full spec, subtask breakdown, QA report for a task.
- `spec` (required) — spec identifier (e.g., `001` or `001-feature-name`)
- `project_dir` (optional)

**`get_task_status`** — Current status, progress, whether process is running.
- `spec` (required)
- `project_dir` (optional)

**`delete_task`** — Delete a task completely (spec + worktree). **Irreversible!**
- `spec` (required)
- `project_dir` (optional)
- Stops running process if active, deletes spec dir and worktree

**`create_task`** — Create a new task with full metadata.
- `title` (required) — short task title
- `description` (required) — detailed task description
- `project_dir` (optional)
- `category` (optional) — `feature`, `bug_fix`, `refactoring`, `documentation`, `security`, `performance`, `ui_ux`, `infrastructure`, `testing`
- `priority` (optional) — `low`, `medium`, `high`, `urgent`
- `complexity` (optional) — `trivial`, `small`, `medium`, `large`, `complex`
- `impact` (optional) — `low`, `medium`, `high`, `critical`
- `rationale` (optional) — why this task matters
- `acceptance_criteria` (optional) — comma-separated list of done criteria
- `affected_files` (optional) — comma-separated list of files to modify
- `referenced_files` (optional) — comma-separated list of context files
- `model` (optional) — `haiku`, `sonnet`, `opus`
- `thinking_level` (optional) — `low`, `medium`, `high`
- `fast_mode` (optional, default false) — faster Opus output
- `base_branch` (optional) — git branch for worktree
- `direct` (optional, default false) — build without worktree isolation

Creates:
```
.auto-claude/specs/{NNN}-{slug}/
  ├── spec.md                  # Title + description
  ├── implementation_plan.json # Status, workflow_type, phases (empty until start)
  ├── requirements.json        # Description + workflow_type
  └── task_metadata.json       # All metadata (category, priority, model, etc.)
```

### Execution

**`start_task`** — Start a task (spec creation → build → QA). Non-blocking, runs in background.
- `spec` (required)
- `project_dir` (optional)
- `model` (optional) — Claude model override
- `skip_qa` (optional, default false) — skip QA validation
- `direct` (optional, default false) — no worktree isolation
- Returns PID and log file path. Use `get_task_status` to poll.

**`stop_task`** — Stop a running task.
- `spec` (required)
- `project_dir` (optional)

**`recover_task`** — Recover a stuck task (restart from last checkpoint).
- `spec` (required)
- `project_dir` (optional)

### Review

**`approve_task`** — Approve a completed task (mark done, ready to merge).
- `spec` (required)
- `project_dir` (optional)
- Updates `implementation_plan.json` status → `done`, qa_signoff → `approved`

**`reject_task`** — Reject with feedback, send back for fixes.
- `spec` (required)
- `feedback` (required) — what needs to be fixed
- `project_dir` (optional)
- Creates `QA_FIX_REQUEST.md` in spec dir. Use `start_task` to re-run with fixes.

### QA

**`run_qa`** — Run QA validation on a completed build. **Blocking** — waits up to 10 minutes.
- `spec` (required)
- `model` (optional)
- `project_dir` (optional)

**`qa_status`** — Show QA validation status.
- `spec` (required)
- `project_dir` (optional)

### Workspace & Merge

**`list_worktrees`** — List all build worktrees and their status.
- `project_dir` (optional)

**`review_build`** — Show what a build contains (diff of changes).
- `spec` (required)
- `project_dir` (optional)

**`merge_preview`** — Preview merge conflicts without merging.
- `spec` (required)
- `project_dir` (optional)
- `base_branch` (optional)

**`merge_build`** — Merge a completed build into the main project.
- `spec` (required)
- `project_dir` (optional)
- `no_commit` (optional, default false) — stage only, don't commit
- `base_branch` (optional)

**`discard_build`** — Discard a build (delete worktree). **Irreversible!**
- `spec` (required)
- `project_dir` (optional)

### PR & Logs

**`create_pr`** — Create a GitHub pull request from a completed build.
- `spec` (required)
- `project_dir` (optional)
- `target_branch` (optional)
- `title` (optional)
- `draft` (optional, default false)

**`get_build_logs`** — Get recent build log output.
- `spec` (required)
- `lines` (optional, default 50) — number of lines
- `project_dir` (optional)

### GitHub (convenience wrappers around `gh` CLI)

**`list_issues`** — List GitHub issues. Use `gh issue list` for advanced filters.
- `project_dir` (optional)
- `state` (optional, default `open`) — `open`, `closed`, `all`
- `limit` (optional, default 20)
- `labels` (optional) — comma-separated label filter

**`get_issue`** — Get issue details. Use `gh issue view` for comments/timeline.
- `issue_number` (required)
- `project_dir` (optional)

**`import_issue`** — Import a GitHub issue as Aperant task (creates spec from issue title+body).
- `issue_number` (required)
- `project_dir` (optional)

**`list_prs`** — List pull requests. Use `gh pr list` for advanced queries.
- `project_dir` (optional)
- `state` (optional, default `open`) — `open`, `closed`, `merged`, `all`
- `limit` (optional, default 20)

### Roadmap

**`get_roadmap`** — View project roadmap with phases, features (with IDs), and milestones.
- `project_dir` (optional)
- Shows: `[feature-1] Feature Title (status)` — use feature ID in `accept_roadmap_feature`

**`generate_roadmap`** — Generate strategic roadmap. **Long-running** (up to 10 min).
- `project_dir` (optional)
- `refresh` (optional, default false) — force regeneration
- `competitor_analysis` (optional, default false) — include competitor analysis
- `model` (optional)

**`accept_roadmap_feature`** — Accept a roadmap feature → creates Aperant task with full metadata.
- `feature_id` (required) — e.g., `feature-1`
- `project_dir` (optional)
- Sets: `sourceType=roadmap`, `featureId`, `rationale`, `category=feature`

### Ideation

**`get_ideas`** — List generated ideas with status and effort.
- `project_dir` (optional)
- `idea_type` (optional) — filter: `code_improvements`, `ui_ux_improvements`, `documentation_gaps`, `security_hardening`, `performance_optimizations`, `code_quality`

**`generate_ideas`** — Generate improvement ideas. **Long-running** (up to 10 min).
- `project_dir` (optional)
- `types` (optional) — comma-separated types to generate
- `max_ideas` (optional, default 5) — ideas per type
- `refresh` (optional, default false)
- `model` (optional)

**`accept_idea`** — Accept an idea → creates Aperant task with full metadata.
- `idea_id` (required) — e.g., `ci-001`
- `project_dir` (optional)
- Sets: `sourceType=ideation`, `ideationType`, `ideaId`, `rationale`, `affectedFiles`, `category` (auto-mapped from idea type), `complexity`

**`dismiss_idea`** — Archive/dismiss an idea.
- `idea_id` (required)
- `project_dir` (optional)

---

## Data Structure

All task data lives in `{project}/.auto-claude/` (gitignored):

```
.auto-claude/
├── specs/
│   └── {NNN}-{slug}/
│       ├── spec.md                    # Task specification
│       ├── implementation_plan.json   # Phases, subtasks, status, QA signoff
│       ├── requirements.json          # Task description, workflow type
│       ├── task_metadata.json         # Full metadata (see below)
│       ├── build-progress.txt         # Human-readable progress log
│       ├── qa_report.md               # QA validation report
│       ├── QA_FIX_REQUEST.md          # Rejection feedback (if rejected)
│       ├── mcp_build.log              # Build output log (from start_task)
│       └── attachments/               # Images (from UI only)
├── project_index.json                 # Shared project context (tech stack, ports)
├── project_map.md                     # AST-parsed project structure (auto-generated)
├── roadmap/
│   ├── roadmap.json                   # Strategic roadmap with phases and features
│   └── competitor_analysis.json       # Competitor pain points
└── ideation/
    ├── ideation.json                  # All ideas merged
    └── {type}_ideas.json              # Ideas per type
```

### task_metadata.json structure

```json
{
  "sourceType": "manual|ideation|roadmap|github",
  "category": "feature|bug_fix|refactoring|security|performance|...",
  "priority": "low|medium|high|urgent",
  "complexity": "trivial|small|medium|large|complex",
  "estimatedEffort": "trivial|small|medium|large|complex",
  "impact": "low|medium|high|critical",
  "rationale": "Why this task matters",
  "acceptanceCriteria": ["criterion 1", "criterion 2"],
  "affectedFiles": ["path/to/file.py"],
  "referencedFiles": [{"id": "path", "path": "path/to/file"}],
  "model": "haiku|sonnet|opus",
  "thinkingLevel": "low|medium|high",
  "fastMode": false,
  "baseBranch": "main",
  "useWorktree": true,
  "ideationType": "code_improvements",
  "ideaId": "ci-001",
  "featureId": "feature-1",
  "githubIssueNumber": 42
}
```

---

## Typical Workflows

### Create and build a feature
```
create_task(title="Add user auth", description="JWT-based...", category="feature", priority="high")
start_task(spec="014")
get_task_status(spec="014")     # poll until complete
approve_task(spec="014")
merge_build(spec="014")
create_pr(spec="014", target_branch="main")
```

### Monitor multiple projects
```
list_tasks(project_dir="/proj/A")
list_tasks(project_dir="/proj/B")
start_task(spec="002", project_dir="/proj/A")
get_task_status(spec="002", project_dir="/proj/A")
get_build_logs(spec="002", project_dir="/proj/A")
```

### GitHub issue → task → PR
```
list_issues()
import_issue(42)               # creates task from issue #42
start_task(spec="016")
approve_task(spec="016")
merge_build(spec="016")
create_pr(spec="016")
```

### Ideation → task
```
generate_ideas(types="security_hardening,performance_optimizations")
get_ideas()
accept_idea("sh-002")          # creates task with metadata from idea
start_task(spec="015")
```

### Roadmap → task
```
get_roadmap()                  # see [feature-1], [feature-2], ...
accept_roadmap_feature("feature-4")  # creates task with rationale
start_task(spec="017")
```

### Review and merge
```
review_build(spec="005")       # see diff
merge_preview(spec="005")      # check conflicts
merge_build(spec="005")
```

### Reject and re-run
```
reject_task(spec="005", feedback="Tests fail on edge case X, need to handle null input")
start_task(spec="005")         # re-runs with QA_FIX_REQUEST.md context
```

---

## Important Notes

- `start_task` is **non-blocking** — returns immediately. Use `get_task_status` to poll progress
- `run_qa` and `generate_roadmap` and `generate_ideas` are **blocking** — wait up to 10 minutes
- `discard_build` is **irreversible** — deletes worktree and branch
- Builds run in **isolated git worktrees** by default (safe, won't affect main branch)
- The server uses Aperant's own Python venv — no additional setup needed
- `list_issues`, `get_issue`, `list_prs` are convenience wrappers around `gh` CLI — use `gh` directly for advanced queries
- `accept_idea` and `accept_roadmap_feature` auto-set `sourceType`, `category`, `rationale`, and other metadata from the source data
- All fields except `title`, `description`, `spec`, `feedback`, `idea_id`, `feature_id`, `issue_number` are optional
