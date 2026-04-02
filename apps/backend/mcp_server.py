#!/usr/bin/env python3
"""
Aperant MCP Server — external control of Aperant from Claude Code.

One server manages multiple projects — pass project_dir to any tool.
See MCP_GUIDE.md for setup instructions and workflows.

Setup (global, all projects):
  Add to ~/.claude/settings.json:
  {
    "mcpServers": {
      "aperant": {
        "command": "/path/to/Aperant/apps/backend/.venv/bin/python",
        "args": ["/path/to/Aperant/apps/backend/mcp_server.py"]
      }
    }
  }
"""

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

BACKEND_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
RUN_PY = BACKEND_DIR / "run.py"
SPEC_RUNNER = BACKEND_DIR / "runners" / "spec_runner.py"

mcp = FastMCP(
    "aperant",
    instructions=(
        "Aperant — autonomous multi-agent coding framework. "
        "Use these tools to create tasks, run builds, check status, merge, and create PRs. "
        "One server manages multiple projects — pass project_dir to switch between them. "
        "If APERANT_PROJECT env is set, it's the default project_dir."
    ),
)

_running_processes: dict[str, subprocess.Popen] = {}


def _get_project_dir(project_dir: str | None = None) -> Path:
    d = project_dir or os.environ.get("APERANT_PROJECT") or os.getcwd()
    return Path(d).resolve()


def _get_python() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def _specs_dir(project_dir: Path) -> Path:
    return project_dir / ".auto-claude" / "specs"


def _run_cli(args: list[str], project_dir: Path, timeout: int = 300) -> dict:
    cmd = [_get_python(), str(RUN_PY)] + args
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _format_result(result: dict) -> str:
    parts = []
    if result.get("success"):
        parts.append("✓ OK")
    else:
        parts.append("✗ Failed")
        if result.get("error"):
            parts.append(f"Error: {result['error']}")
    if result.get("stdout"):
        parts.append(result["stdout"])
    if result.get("stderr"):
        parts.append(f"Stderr: {result['stderr']}")
    return "\n".join(parts)


def _read_plan(spec_dir: Path) -> dict | None:
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None
    try:
        return json.loads(plan_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _task_summary(spec_dir: Path) -> dict:
    plan = _read_plan(spec_dir)
    if not plan:
        return {"name": spec_dir.name, "status": "no_plan"}

    subtasks = []
    for phase in plan.get("phases", []):
        subtasks.extend(phase.get("subtasks", []))

    total = len(subtasks)
    completed = sum(1 for s in subtasks if s.get("status") == "completed")
    failed = sum(1 for s in subtasks if s.get("status") == "failed")
    in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")

    status = plan.get("status") or plan.get("planStatus") or "unknown"
    qa = plan.get("qa_signoff") or {}

    return {
        "name": spec_dir.name,
        "status": status,
        "subtasks": f"{completed}/{total}",
        "failed": failed,
        "in_progress": in_progress,
        "qa_status": qa.get("status", "none"),
        "updated": plan.get("last_updated", plan.get("updated_at", "")),
    }


# ── Project & Task listing ────────────────────────────────────────


@mcp.tool()
def list_tasks(project_dir: str | None = None) -> str:
    """List all tasks/specs in a project with status and progress."""
    pd = _get_project_dir(project_dir)
    sd = _specs_dir(pd)
    if not sd.exists():
        return f"No specs found in {pd}"

    tasks = []
    for spec_folder in sorted(sd.iterdir()):
        if not spec_folder.is_dir():
            continue
        tasks.append(_task_summary(spec_folder))

    if not tasks:
        return "No tasks found."

    lines = [f"Tasks in {pd.name} ({len(tasks)}):", ""]
    for t in tasks:
        qa = f" | QA: {t['qa_status']}" if t["qa_status"] != "none" else ""
        lines.append(
            f"  {t['name']}  [{t['status']}]  subtasks: {t['subtasks']}{qa}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_task_details(spec: str, project_dir: str | None = None) -> str:
    """Get full details of a task: spec, plan, subtasks, QA report.

    Args:
        spec: Spec identifier (e.g., '001' or '001-feature-name')
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found in {pd}"

    parts = [f"# Task: {spec_dir.name}", ""]

    spec_md = spec_dir / "spec.md"
    if spec_md.exists():
        content = spec_md.read_text(encoding="utf-8")[:3000]
        parts.append("## Specification")
        parts.append(content)
        parts.append("")

    plan = _read_plan(spec_dir)
    if plan:
        parts.append("## Subtasks")
        for phase in plan.get("phases", []):
            parts.append(f"\n### {phase.get('name', 'Phase')}")
            for st in phase.get("subtasks", []):
                status_icon = {"completed": "✓", "failed": "✗", "in_progress": "→"}.get(st.get("status", ""), "○")
                model = f" [{st.get('model', '')}]" if st.get("model") else ""
                parts.append(f"  {status_icon} {st['id']}: {st.get('description', '')[:100]}{model}")

    qa_report = spec_dir / "qa_report.md"
    if qa_report.exists():
        parts.append("\n## QA Report")
        parts.append(qa_report.read_text(encoding="utf-8")[:2000])

    return "\n".join(parts)


@mcp.tool()
def get_task_status(spec: str, project_dir: str | None = None) -> str:
    """Get current execution status of a task (progress, phase, running process).

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    summary = _task_summary(spec_dir)
    pid_key = f"{pd}:{spec_dir.name}"
    is_running = pid_key in _running_processes and _running_processes[pid_key].poll() is None

    progress_file = spec_dir / "build-progress.txt"
    last_progress = ""
    if progress_file.exists():
        lines = progress_file.read_text(encoding="utf-8").strip().splitlines()
        last_progress = lines[-1] if lines else ""

    parts = [
        f"Task: {summary['name']}",
        f"Status: {summary['status']}",
        f"Subtasks: {summary['subtasks']}",
        f"QA: {summary['qa_status']}",
        f"Running: {'yes (PID ' + str(_running_processes[pid_key].pid) + ')' if is_running else 'no'}",
    ]
    if last_progress:
        parts.append(f"Last progress: {last_progress}")

    return "\n".join(parts)


# ── Task creation ────────────────────────────────────────────────


@mcp.tool()
def create_task(
    title: str,
    description: str,
    project_dir: str | None = None,
) -> str:
    """Create a new task. This creates the spec directory and starts spec generation.

    Args:
        title: Short task title
        description: Detailed task description
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    sd = _specs_dir(pd)
    sd.mkdir(parents=True, exist_ok=True)

    existing = sorted([d.name for d in sd.iterdir() if d.is_dir()])
    next_num = 1
    if existing:
        try:
            nums = [int(n.split("-")[0]) for n in existing]
            next_num = max(nums) + 1
        except ValueError:
            next_num = len(existing) + 1

    slug = title.lower().replace(" ", "-")[:40]
    spec_name = f"{next_num:03d}-{slug}"
    spec_dir = sd / spec_name
    spec_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "feature": title,
        "spec_name": spec_name,
        "workflow_type": "standard",
        "phases": [],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    (spec_dir / "implementation_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    req = {
        "title": title,
        "description": description,
        "workflow_type": "standard",
    }
    (spec_dir / "requirements.json").write_text(
        json.dumps(req, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    (spec_dir / "spec.md").write_text(
        f"# {title}\n\n{description}\n", encoding="utf-8"
    )

    return f"✓ Task created: {spec_name}\nPath: {spec_dir}\nUse start_task to begin spec creation and build."


# ── Execution ────────────────────────────────────────────────────


@mcp.tool()
def start_task(
    spec: str,
    project_dir: str | None = None,
    model: str | None = None,
    skip_qa: bool = False,
    direct: bool = False,
) -> str:
    """Start a task (spec creation → build → QA). Non-blocking — runs in background.

    Args:
        spec: Spec identifier (e.g., '001')
        project_dir: Project directory path
        model: Claude model override
        skip_qa: Skip QA validation after build
        direct: Build directly without worktree isolation
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    pid_key = f"{pd}:{spec_dir.name}"
    if pid_key in _running_processes and _running_processes[pid_key].poll() is None:
        return f"Task {spec_dir.name} is already running (PID {_running_processes[pid_key].pid})"

    args = [
        _get_python(), str(RUN_PY),
        "--spec", spec_dir.name,
        "--project-dir", str(pd),
        "--auto-continue", "--force",
    ]
    if model:
        args.extend(["--model", model])
    if skip_qa:
        args.append("--skip-qa")
    if direct:
        args.append("--direct")
    else:
        args.append("--isolated")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    log_file = spec_dir / "mcp_build.log"
    log_fh = open(log_file, "w", encoding="utf-8")

    proc = subprocess.Popen(
        args,
        cwd=str(pd),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    _running_processes[pid_key] = proc

    return (
        f"✓ Task {spec_dir.name} started (PID {proc.pid})\n"
        f"Log: {log_file}\n"
        f"Use get_task_status to check progress."
    )


@mcp.tool()
def stop_task(spec: str, project_dir: str | None = None) -> str:
    """Stop a running task.

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    pid_key = f"{pd}:{spec_dir.name}"
    proc = _running_processes.get(pid_key)
    if not proc or proc.poll() is not None:
        return "Task is not running."

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        proc.kill()

    del _running_processes[pid_key]
    return f"✓ Task {spec_dir.name} stopped."


@mcp.tool()
def recover_task(spec: str, project_dir: str | None = None) -> str:
    """Recover a stuck task (restart from last checkpoint).

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_cli(
        ["--spec", spec, "--project-dir", str(pd), "--auto-continue", "--force"],
        pd,
        timeout=60,
    )
    return _format_result(result)


# ── QA ───────────────────────────────────────────────────────────


@mcp.tool()
def run_qa(spec: str, project_dir: str | None = None, model: str | None = None) -> str:
    """Run QA validation on a completed build. Blocking — waits for completion.

    Args:
        spec: Spec identifier
        model: Claude model override
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    args = ["--spec", spec, "--project-dir", str(pd), "--qa"]
    if model:
        args.extend(["--model", model])
    result = _run_cli(args, pd, timeout=600)
    return _format_result(result)


@mcp.tool()
def qa_status(spec: str, project_dir: str | None = None) -> str:
    """Show QA validation status for a task.

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_cli(["--spec", spec, "--project-dir", str(pd), "--qa-status"], pd)
    return _format_result(result)


# ── Workspace / Merge ────────────────────────────────────────────


@mcp.tool()
def list_worktrees(project_dir: str | None = None) -> str:
    """List all build worktrees and their status."""
    pd = _get_project_dir(project_dir)
    result = _run_cli(["--list-worktrees", "--project-dir", str(pd)], pd)
    return _format_result(result)


@mcp.tool()
def review_build(spec: str, project_dir: str | None = None) -> str:
    """Show what a build contains (diff of changes).

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_cli(["--spec", spec, "--project-dir", str(pd), "--review"], pd)
    return _format_result(result)


@mcp.tool()
def merge_preview(spec: str, project_dir: str | None = None, base_branch: str | None = None) -> str:
    """Preview merge conflicts without merging.

    Args:
        spec: Spec identifier
        project_dir: Project directory path
        base_branch: Base branch for merge
    """
    pd = _get_project_dir(project_dir)
    args = ["--spec", spec, "--project-dir", str(pd), "--merge-preview"]
    if base_branch:
        args.extend(["--base-branch", base_branch])
    result = _run_cli(args, pd)
    return _format_result(result)


@mcp.tool()
def merge_build(
    spec: str,
    project_dir: str | None = None,
    no_commit: bool = False,
    base_branch: str | None = None,
) -> str:
    """Merge a completed build into the main project.

    Args:
        spec: Spec identifier
        project_dir: Project directory path
        no_commit: Stage only, don't commit
        base_branch: Base branch for merge
    """
    pd = _get_project_dir(project_dir)
    args = ["--spec", spec, "--project-dir", str(pd), "--merge"]
    if no_commit:
        args.append("--no-commit")
    if base_branch:
        args.extend(["--base-branch", base_branch])
    result = _run_cli(args, pd)
    return _format_result(result)


@mcp.tool()
def discard_build(spec: str, project_dir: str | None = None) -> str:
    """Discard a build (delete worktree). Irreversible!

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_cli(["--spec", spec, "--project-dir", str(pd), "--discard", "--force"], pd)
    return _format_result(result)


@mcp.tool()
def create_pr(
    spec: str,
    project_dir: str | None = None,
    target_branch: str | None = None,
    title: str | None = None,
    draft: bool = False,
) -> str:
    """Create a GitHub pull request from a completed build.

    Args:
        spec: Spec identifier
        project_dir: Project directory path
        target_branch: Target branch for PR
        title: PR title
        draft: Create as draft PR
    """
    pd = _get_project_dir(project_dir)
    args = ["--spec", spec, "--project-dir", str(pd), "--create-pr"]
    if target_branch:
        args.extend(["--pr-target", target_branch])
    if title:
        args.extend(["--pr-title", title])
    if draft:
        args.append("--pr-draft")
    result = _run_cli(args, pd, timeout=120)
    return _format_result(result)


# ── Logs ─────────────────────────────────────────────────────────


@mcp.tool()
def get_build_logs(spec: str, lines: int = 50, project_dir: str | None = None) -> str:
    """Get recent build log output for a task.

    Args:
        spec: Spec identifier
        lines: Number of lines to return (default 50)
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    log_file = spec_dir / "mcp_build.log"
    if not log_file.exists():
        progress = spec_dir / "build-progress.txt"
        if progress.exists():
            content = progress.read_text(encoding="utf-8")
            return content[-3000:] if len(content) > 3000 else content
        return "No logs available."

    content = log_file.read_text(encoding="utf-8")
    log_lines = content.splitlines()
    return "\n".join(log_lines[-lines:])


# ── Review (approve / reject) ────────────────────────────────────


@mcp.tool()
def approve_task(spec: str, project_dir: str | None = None) -> str:
    """Approve a completed task (mark as done, ready to merge).

    Args:
        spec: Spec identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    plan = _read_plan(spec_dir)
    if not plan:
        return "No implementation plan found."

    plan["status"] = "done"
    plan["qa_signoff"] = plan.get("qa_signoff") or {}
    plan["qa_signoff"]["status"] = "approved"
    plan["qa_signoff"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    plan["last_updated"] = datetime.now(timezone.utc).isoformat()

    (spec_dir / "implementation_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return f"✓ Task {spec_dir.name} approved."


@mcp.tool()
def reject_task(spec: str, feedback: str, project_dir: str | None = None) -> str:
    """Reject a task and send it back for fixes with feedback.

    Args:
        spec: Spec identifier
        feedback: What needs to be fixed (written to QA_FIX_REQUEST.md)
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    spec_dir = _find_spec_dir(pd, spec)
    if not spec_dir:
        return f"Spec '{spec}' not found"

    # Write feedback file
    fix_request = spec_dir / "QA_FIX_REQUEST.md"
    fix_request.write_text(
        f"# Fix Request\n\n{feedback}\n\n_Generated: {datetime.now(timezone.utc).isoformat()}_\n",
        encoding="utf-8",
    )

    # Update plan status
    plan = _read_plan(spec_dir)
    if plan:
        plan["status"] = "in_progress"
        plan["qa_signoff"] = plan.get("qa_signoff") or {}
        plan["qa_signoff"]["status"] = "rejected"
        plan["last_updated"] = datetime.now(timezone.utc).isoformat()
        (spec_dir / "implementation_plan.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return f"✓ Task {spec_dir.name} rejected. Feedback saved to QA_FIX_REQUEST.md.\nUse start_task to re-run with fixes."


# ── GitHub ───────────────────────────────────────────────────────


def _run_gh(args: list[str], project_dir: Path, timeout: int = 30) -> dict:
    """Run a gh CLI command."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except FileNotFoundError:
        return {"success": False, "error": "gh CLI not found. Install: https://cli.github.com"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_issues(
    project_dir: str | None = None,
    state: str = "open",
    limit: int = 20,
    labels: str | None = None,
) -> str:
    """List GitHub issues for the project.

    Args:
        project_dir: Project directory path
        state: Issue state: open, closed, all
        limit: Max issues to return
        labels: Comma-separated label filter
    """
    pd = _get_project_dir(project_dir)
    args = ["issue", "list", "--state", state, "--limit", str(limit), "--json", "number,title,state,labels,assignees,updatedAt"]
    if labels:
        args.extend(["--label", labels])
    result = _run_gh(args, pd)
    if not result["success"]:
        return _format_result(result)

    try:
        issues = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return result["stdout"]

    if not issues:
        return f"No {state} issues found."

    lines = [f"GitHub Issues ({len(issues)}):", ""]
    for issue in issues:
        labels_str = ", ".join(l["name"] for l in issue.get("labels", [])) if issue.get("labels") else ""
        lines.append(f"  #{issue['number']}  {issue['title']}" + (f"  [{labels_str}]" if labels_str else ""))
    return "\n".join(lines)


@mcp.tool()
def get_issue(issue_number: int, project_dir: str | None = None) -> str:
    """Get details of a specific GitHub issue.

    Args:
        issue_number: Issue number
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_gh(["issue", "view", str(issue_number)], pd)
    return _format_result(result)


@mcp.tool()
def import_issue(issue_number: int, project_dir: str | None = None) -> str:
    """Import a GitHub issue as an Aperant task (creates spec from issue).

    Args:
        issue_number: Issue number to import
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    result = _run_gh(
        ["issue", "view", str(issue_number), "--json", "title,body,labels"],
        pd,
    )
    if not result["success"]:
        return _format_result(result)

    try:
        issue = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return f"Failed to parse issue #{issue_number}"

    title = issue.get("title", f"Issue #{issue_number}")
    body = issue.get("body", "")
    description = f"GitHub Issue #{issue_number}\n\n{body}"

    # Reuse create_task
    return create_task(title=title, description=description, project_dir=project_dir)


@mcp.tool()
def list_prs(
    project_dir: str | None = None,
    state: str = "open",
    limit: int = 20,
) -> str:
    """List GitHub pull requests for the project.

    Args:
        project_dir: Project directory path
        state: PR state: open, closed, merged, all
        limit: Max PRs to return
    """
    pd = _get_project_dir(project_dir)
    args = ["pr", "list", "--state", state, "--limit", str(limit), "--json", "number,title,state,headRefName,isDraft,reviewDecision,updatedAt"]
    result = _run_gh(args, pd)
    if not result["success"]:
        return _format_result(result)

    try:
        prs = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return result["stdout"]

    if not prs:
        return f"No {state} PRs found."

    lines = [f"Pull Requests ({len(prs)}):", ""]
    for pr in prs:
        draft = " [DRAFT]" if pr.get("isDraft") else ""
        review = f" ({pr['reviewDecision']})" if pr.get("reviewDecision") else ""
        lines.append(f"  #{pr['number']}  {pr['title']}{draft}{review}  ← {pr.get('headRefName', '')}")
    return "\n".join(lines)


# ── Roadmap ───────────────────────────────────────────────────────


@mcp.tool()
def get_roadmap(project_dir: str | None = None) -> str:
    """Get the project roadmap (phases, features, milestones).

    Args:
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    roadmap_file = pd / ".auto-claude" / "roadmap" / "roadmap.json"
    if not roadmap_file.exists():
        return "No roadmap found. Use generate_roadmap to create one."

    try:
        data = json.loads(roadmap_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return f"Error reading roadmap: {e}"

    features_map = {f["id"]: f for f in data.get("features", []) if isinstance(f, dict)}

    lines = [f"# Roadmap: {data.get('project_name', 'Unknown')}", ""]
    if data.get("vision"):
        lines.append(f"**Vision:** {data['vision']}")
        lines.append("")

    for phase in data.get("phases", []):
        status = phase.get("status", "planned")
        lines.append(f"## Phase {phase.get('order', '?')}: {phase.get('name', '')}  [{status}]")
        lines.append(f"  {phase.get('description', '')}")

        phase_features = phase.get("features", [])
        for fref in phase_features:
            fid = fref if isinstance(fref, str) else fref.get("id", "")
            feat = features_map.get(fid)
            if feat:
                f_status = feat.get("status", "planned")
                lines.append(f"  [{fid}] {feat.get('title', '')}  ({f_status})")

        for ms in phase.get("milestones", []):
            ms_status = ms.get("status", "planned")
            lines.append(f"  ◆ {ms.get('title', '')}  [{ms_status}]")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def generate_roadmap(
    project_dir: str | None = None,
    refresh: bool = False,
    competitor_analysis: bool = False,
    model: str | None = None,
) -> str:
    """Generate or refresh a strategic roadmap for the project. Long-running operation.

    Args:
        project_dir: Project directory path
        refresh: Force regeneration if roadmap exists
        competitor_analysis: Include competitor analysis phase
        model: Claude model override
    """
    pd = _get_project_dir(project_dir)
    cmd = [_get_python(), str(BACKEND_DIR / "runners" / "roadmap_runner.py"), "--project", str(pd)]
    if refresh:
        cmd.append("--refresh")
    if competitor_analysis:
        cmd.append("--competitor-analysis")
    if model:
        cmd.extend(["--model", model])

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(cmd, cwd=str(pd), capture_output=True, text=True, timeout=600, env=env)
        if result.returncode == 0:
            return "✓ Roadmap generated. Use get_roadmap to view."
        return f"✗ Roadmap generation failed.\n{result.stderr[-1000:]}"
    except subprocess.TimeoutExpired:
        return "✗ Roadmap generation timed out (10 min limit)."


@mcp.tool()
def accept_roadmap_feature(feature_id: str, project_dir: str | None = None) -> str:
    """Accept a roadmap feature and create an Aperant task from it.

    Args:
        feature_id: Feature identifier (e.g., 'feature-1')
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    roadmap_file = pd / ".auto-claude" / "roadmap" / "roadmap.json"
    if not roadmap_file.exists():
        return "No roadmap found."

    try:
        data = json.loads(roadmap_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Error reading roadmap."

    features = data.get("features", [])
    feature = next((f for f in features if f.get("id") == feature_id), None)
    if not feature:
        return f"Feature '{feature_id}' not found. Use get_roadmap to see available features."

    result = create_task(
        title=feature.get("title", f"Feature {feature_id}"),
        description=f"{feature.get('description', '')}\n\n**Rationale:** {feature.get('rationale', '')}",
        project_dir=project_dir,
    )

    feature["status"] = "in_progress"
    feature["outcome"] = "accepted"
    data["metadata"] = data.get("metadata") or {}
    data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    roadmap_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"✓ Feature '{feature_id}' accepted.\n{result}"


# ── Ideation ─────────────────────────────────────────────────────


@mcp.tool()
def get_ideas(
    project_dir: str | None = None,
    idea_type: str | None = None,
) -> str:
    """Get generated ideas for the project.

    Args:
        project_dir: Project directory path
        idea_type: Filter by type: code_improvements, ui_ux_improvements, documentation_gaps, security_hardening, performance_optimizations, code_quality
    """
    pd = _get_project_dir(project_dir)
    ideation_dir = pd / ".auto-claude" / "ideation"

    if idea_type:
        idea_file = ideation_dir / f"{idea_type}_ideas.json"
        if not idea_file.exists():
            return f"No {idea_type} ideas found. Use generate_ideas to create."
        try:
            data = json.loads(idea_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return f"Error reading {idea_type} ideas."
        ideas = data.get("ideas", data) if isinstance(data, dict) else data
    else:
        main_file = ideation_dir / "ideation.json"
        if not main_file.exists():
            return "No ideas found. Use generate_ideas to create."
        try:
            data = json.loads(main_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return "Error reading ideation data."
        ideas = data.get("ideas", [])

    if not ideas:
        return "No ideas found."

    lines = [f"Ideas ({len(ideas)}):", ""]
    for idea in ideas if isinstance(ideas, list) else [ideas]:
        if not isinstance(idea, dict):
            continue
        effort = idea.get("estimated_effort", "?")
        status = idea.get("status", "draft")
        idea_id = idea.get("id", "?")
        lines.append(f"  [{idea_id}] {idea.get('title', 'Untitled')}  ({effort}, {status})")
        lines.append(f"    {idea.get('description', '')[:120]}")
        if idea.get("rationale"):
            lines.append(f"    Why: {idea['rationale'][:100]}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def generate_ideas(
    project_dir: str | None = None,
    types: str | None = None,
    max_ideas: int = 5,
    refresh: bool = False,
    model: str | None = None,
) -> str:
    """Generate improvement ideas for the project. Long-running operation.

    Args:
        project_dir: Project directory path
        types: Comma-separated ideation types (code_improvements,ui_ux_improvements,security_hardening,performance_optimizations,documentation_gaps,code_quality)
        max_ideas: Max ideas per type (default 5)
        refresh: Force regeneration
        model: Claude model override
    """
    pd = _get_project_dir(project_dir)
    cmd = [_get_python(), str(BACKEND_DIR / "runners" / "ideation_runner.py"), "--project", str(pd), "--max-ideas", str(max_ideas)]
    if types:
        cmd.extend(["--types", types])
    if refresh:
        cmd.append("--refresh")
    if model:
        cmd.extend(["--model", model])

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(cmd, cwd=str(pd), capture_output=True, text=True, timeout=600, env=env)
        if result.returncode == 0:
            return "✓ Ideas generated. Use get_ideas to view."
        return f"✗ Ideation failed.\n{result.stderr[-1000:]}"
    except subprocess.TimeoutExpired:
        return "✗ Ideation timed out (10 min limit)."


@mcp.tool()
def accept_idea(idea_id: str, project_dir: str | None = None) -> str:
    """Accept an idea and create an Aperant task from it.

    Args:
        idea_id: Idea identifier (e.g., 'ci-001')
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    ideation_file = pd / ".auto-claude" / "ideation" / "ideation.json"
    if not ideation_file.exists():
        return "No ideation data found."

    try:
        data = json.loads(ideation_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Error reading ideation data."

    ideas = data.get("ideas", [])
    idea = next((i for i in ideas if i.get("id") == idea_id), None)
    if not idea:
        return f"Idea '{idea_id}' not found."

    result = create_task(
        title=idea.get("title", f"Idea {idea_id}"),
        description=f"{idea.get('description', '')}\n\n**Rationale:** {idea.get('rationale', '')}\n\n**Approach:** {idea.get('implementation_approach', '')}",
        project_dir=project_dir,
    )

    idea["status"] = "accepted"
    idea["linked_task_id"] = result.split(":")[1].strip().split("\n")[0] if ":" in result else None
    ideation_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"✓ Idea '{idea_id}' accepted.\n{result}"


@mcp.tool()
def dismiss_idea(idea_id: str, project_dir: str | None = None) -> str:
    """Dismiss/archive an idea (won't be shown in future).

    Args:
        idea_id: Idea identifier
        project_dir: Project directory path
    """
    pd = _get_project_dir(project_dir)
    ideation_file = pd / ".auto-claude" / "ideation" / "ideation.json"
    if not ideation_file.exists():
        return "No ideation data found."

    try:
        data = json.loads(ideation_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Error reading ideation data."

    ideas = data.get("ideas", [])
    idea = next((i for i in ideas if i.get("id") == idea_id), None)
    if not idea:
        return f"Idea '{idea_id}' not found."

    idea["status"] = "archived"
    ideation_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"✓ Idea '{idea_id}' archived."


# ── Helpers ──────────────────────────────────────────────────────


def _find_spec_dir(project_dir: Path, spec: str) -> Path | None:
    sd = _specs_dir(project_dir)
    if not sd.exists():
        return None

    exact = sd / spec
    if exact.is_dir():
        return exact

    for folder in sd.iterdir():
        if folder.is_dir() and folder.name.startswith(spec):
            return folder

    return None


if __name__ == "__main__":
    mcp.run()
