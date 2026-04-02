"""
Prompt Generator
================

Generates minimal, focused prompts for each subtask.
Instead of a 900-line mega-prompt, each subtask gets a tailored ~100-line prompt
with only the context it needs.

This approach:
- Reduces token usage by ~80%
- Keeps the agent focused on ONE task
- Moves bookkeeping to Python orchestration
"""

import json
import re
from pathlib import Path

# Worktree path patterns for detection
# Matches paths like: .auto-claude/worktrees/tasks/{spec-name}/
WORKTREE_PATH_PATTERNS = [
    r"[/\\]\.auto-claude[/\\]worktrees[/\\]tasks[/\\]",
    r"[/\\]\.auto-claude[/\\]github[/\\]pr[/\\]worktrees[/\\]",  # PR review worktrees
    r"[/\\]\.worktrees[/\\]",  # Legacy worktree location
]


def detect_worktree_isolation(project_dir: Path) -> tuple[bool, Path | None]:
    """
    Detect if the project_dir is inside an isolated worktree.

    When running in a worktree, the agent should NOT escape to the parent project.
    This function detects worktree mode and extracts the forbidden parent path.

    Args:
        project_dir: The working directory for the AI

    Returns:
        Tuple of (is_worktree, parent_project_path)
        - is_worktree: True if running in an isolated worktree
        - parent_project_path: The forbidden parent project path (None if not in worktree)
    """
    # Resolve the path first for consistent matching across platforms
    # This handles Windows drive letters, symlinks, and relative paths
    resolved_dir = project_dir.resolve()
    project_str = str(resolved_dir)

    for pattern in WORKTREE_PATH_PATTERNS:
        match = re.search(pattern, project_str)
        if match:
            # Extract the parent project path (everything before the worktree marker)
            parent_path = project_str[: match.start()]
            # Handle edge case where worktree is at filesystem root
            if not parent_path:
                parent_path = resolved_dir.anchor
            return True, Path(parent_path)

    return False, None


def generate_worktree_isolation_warning(
    project_dir: Path, parent_project_path: Path
) -> str:
    """
    Generate the worktree isolation warning section for prompts.

    This warning explicitly tells the agent that it's in an isolated worktree
    and must NOT escape to the parent project directory.

    Args:
        project_dir: The worktree directory (agent's working directory)
        parent_project_path: The forbidden parent project path

    Returns:
        Markdown string with isolation warning
    """
    return f"""## ⛔ ISOLATED WORKTREE - CRITICAL

You are in an **ISOLATED GIT WORKTREE** - a complete copy of the project for safe development.

**YOUR LOCATION:** `{project_dir}`
**FORBIDDEN PATH:** `{parent_project_path}`

### Rules:
1. **NEVER** use `cd {parent_project_path}` or any path starting with `{parent_project_path}`
2. **NEVER** use absolute paths that reference the parent project
3. **ALL** project files exist HERE via relative paths

### Why This Matters:
- Git commits made in the parent project go to the WRONG branch
- File changes in the parent project escape isolation
- This defeats the entire purpose of safe, isolated development

### Correct Usage:
```bash
# ✅ CORRECT - Use relative paths from your worktree
./prod/src/file.ts
./apps/frontend/src/component.tsx

# ❌ WRONG - These escape isolation!
cd {parent_project_path}
{parent_project_path}/prod/src/file.ts
```

If you see absolute paths in spec.md or context.json that reference `{parent_project_path}`,
convert them to relative paths from YOUR current location.

---

"""


def get_relative_spec_path(spec_dir: Path, project_dir: Path) -> str:
    """
    Get the spec directory path relative to the project/working directory.

    This ensures the AI gets a usable path regardless of absolute locations.

    Args:
        spec_dir: Absolute path to spec directory
        project_dir: Absolute path to project/working directory

    Returns:
        Relative path string (e.g., "./auto-claude/specs/003-new-spec")
    """
    try:
        # Try to make path relative to project_dir
        relative = spec_dir.relative_to(project_dir)
        return f"./{relative}"
    except ValueError:
        # If spec_dir is not under project_dir, return the name only
        # This shouldn't happen if workspace.py correctly copies spec files
        return f"./auto-claude/specs/{spec_dir.name}"


def generate_environment_context(project_dir: Path, spec_dir: Path) -> str:
    """
    Generate environment context header for prompts.

    This explicitly tells the AI where it is working, preventing path confusion.
    When running in a worktree, includes an isolation warning to prevent escaping.

    Args:
        project_dir: The working directory for the AI
        spec_dir: The spec directory (may be absolute or relative)

    Returns:
        Markdown string with environment context
    """
    relative_spec = get_relative_spec_path(spec_dir, project_dir)

    # Check if we're in an isolated worktree
    is_worktree, parent_project_path = detect_worktree_isolation(project_dir)

    # Start with worktree isolation warning if applicable
    sections = []
    if is_worktree and parent_project_path:
        sections.append(
            generate_worktree_isolation_warning(project_dir, parent_project_path)
        )

    # Load project_index for venv/run info
    # Try shared context first (.auto-claude/project_index.json), then per-spec fallback
    venv_info = ""
    shared_project_index = spec_dir.parent.parent / "project_index.json" if spec_dir.parent.name == "specs" else None
    project_index_file = spec_dir / "project_index.json"
    if shared_project_index and shared_project_index.exists():
        project_index_file = shared_project_index
    if project_index_file.exists():
        try:
            pi = json.load(open(project_index_file, encoding="utf-8"))
            parts = []
            for svc in pi.get("services", {}).values() if isinstance(pi.get("services"), dict) else pi.get("services", []):
                if isinstance(svc, dict):
                    if svc.get("dev_command"):
                        parts.append(f"- Dev command: `{svc['dev_command']}`")
                    if svc.get("venv_path"):
                        parts.append(f"- Venv: `{svc['venv_path']}`")
                    if svc.get("port"):
                        parts.append(f"- Port: {svc['port']}")
            if parts:
                venv_info = "\n**Project Environment:**\n" + "\n".join(parts) + "\n"
        except Exception:
            pass

    # Inject project map (auto-generated, contains full project structure)
    project_map_content = ""
    project_map_file = (spec_dir.parent.parent / "project_map.md") if spec_dir.parent.name == "specs" else None
    if project_map_file:
        if not project_map_file.exists():
            try:
                from core.project_map import update_project_map
                update_project_map(project_dir)
            except Exception:
                pass
        if project_map_file.exists():
            try:
                pm_text = project_map_file.read_text(encoding="utf-8")
                if len(pm_text) > 8000:
                    pm_text = pm_text[:8000] + "\n\n... (truncated, full map in .auto-claude/project_map.md)"
                project_map_content = f"\n## PROJECT MAP\n\n{pm_text}\n\n---\n\n"
            except Exception:
                pass

    sections.append(f"""{project_map_content}## YOUR ENVIRONMENT

**Working Directory:** `{project_dir}`
**Spec Location:** `{relative_spec}/`
{"**Isolation Mode:** WORKTREE (changes are isolated from main project)" if is_worktree else ""}
{venv_info}
---

""")

    return "".join(sections)


def generate_subtask_prompt(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    phase: dict,
    attempt_count: int = 0,
    recovery_hints: list[str] | None = None,
) -> str:
    """
    Generate a minimal, focused prompt for implementing a single subtask.

    Args:
        spec_dir: Directory containing spec files
        project_dir: Root project directory (working directory)
        subtask: The subtask to implement
        phase: The phase containing this subtask
        attempt_count: Number of previous attempts (for retry context)
        recovery_hints: Hints from previous failed attempts

    Returns:
        A focused prompt string (~100 lines instead of 900)
    """
    subtask_id = subtask.get("id", "unknown")
    description = subtask.get("description", "No description")
    service = subtask.get("service", "all")
    files_to_modify = subtask.get("files_to_modify", [])
    files_to_create = subtask.get("files_to_create", [])
    patterns_from = subtask.get("patterns_from", [])
    verification = subtask.get("verification", {})

    # Get relative spec path
    relative_spec = get_relative_spec_path(spec_dir, project_dir)

    # Build the prompt
    sections = []

    # Environment context first
    sections.append(generate_environment_context(project_dir, spec_dir))

    # Inject spec summary (spec.md never changes — inject once, don't make agent Read it)
    spec_summary = ""
    spec_file = spec_dir / "spec.md"
    if spec_file.exists():
        try:
            spec_text = spec_file.read_text(encoding="utf-8")
            # Take first 2000 chars as summary (title + requirements + key decisions)
            if len(spec_text) > 2000:
                spec_summary = spec_text[:2000] + "\n... (truncated)"
            else:
                spec_summary = spec_text
        except Exception:
            pass

    # Inject build progress summary (so agent knows what's done without reading file)
    progress_summary = ""
    try:
        plan_file = spec_dir / "implementation_plan.json"
        if plan_file.exists():
            plan_data = json.load(open(plan_file, encoding="utf-8"))
            completed = sum(
                1 for p in plan_data.get("phases", [])
                for s in p.get("subtasks", [])
                if s.get("status") == "completed"
            )
            total = sum(
                len(p.get("subtasks", []))
                for p in plan_data.get("phases", [])
            )
            progress_summary = f"**Progress:** {completed}/{total} subtasks completed"
    except Exception:
        pass

    # Header
    sections.append(f"""# Subtask Implementation Task

**Subtask ID:** `{subtask_id}`
**Phase:** {phase.get("name", phase.get("id", "Unknown"))}
**Service:** {service}
**Model:** {subtask.get("model", "default")}
{progress_summary}

## Description

{description}
""")

    # Spec context (injected so agent doesn't need to Read spec.md)
    if spec_summary:
        sections.append(f"""## Spec Summary (read-only context)

{spec_summary}

---
""")

    # Recovery context if this is a retry
    if attempt_count > 0:
        sections.append(f"""
## ⚠️ RETRY ATTEMPT ({attempt_count + 1})

This subtask has been attempted {attempt_count} time(s) before without success.
You MUST use a DIFFERENT approach than previous attempts.
""")
        if recovery_hints:
            sections.append("**Previous attempt insights:**")
            for hint in recovery_hints:
                sections.append(f"- {hint}")
            sections.append("")

    # Files section
    sections.append("## Files\n")

    if files_to_modify:
        sections.append("**Files to Modify:**")
        for f in files_to_modify:
            sections.append(f"- `{f}`")
        sections.append("")

    if files_to_create:
        sections.append("**Files to Create:**")
        for f in files_to_create:
            sections.append(f"- `{f}`")
        sections.append("")

    if patterns_from:
        sections.append("**Pattern Files (study these first):**")
        for f in patterns_from:
            sections.append(f"- `{f}`")
        sections.append("")

    # Verification
    sections.append("## Verification\n")
    v_type = verification.get("type", "manual")

    if v_type == "command":
        sections.append(f"""Run this command to verify:
```bash
{verification.get("command", 'echo "No command specified"')}
```
Expected: {verification.get("expected", "Success")}
""")
    elif v_type == "api":
        method = verification.get("method", "GET")
        url = verification.get("url", "http://localhost")
        body = verification.get("body", {})
        expected_status = verification.get("expected_status", 200)
        sections.append(f"""Test the API endpoint:
```bash
curl -X {method} {url} -H "Content-Type: application/json" {f"-d '{json.dumps(body)}'" if body else ""}
```
Expected status: {expected_status}
""")
    elif v_type == "browser":
        url = verification.get("url", "http://localhost:3000")
        checks = verification.get("checks", [])
        sections.append(f"""Open in browser: {url}

Verify:""")
        for check in checks:
            sections.append(f"- [ ] {check}")
        sections.append("")
    elif v_type == "e2e":
        steps = verification.get("steps", [])
        sections.append("End-to-end verification steps:")
        for i, step in enumerate(steps, 1):
            sections.append(f"{i}. {step}")
        sections.append("")
    else:
        instructions = verification.get("instructions", "Manual verification required")
        sections.append(f"**Manual Verification:**\n{instructions}\n")

    # Instructions
    sections.append(f"""## Instructions

1. Read pattern files and files to modify to understand conventions
2. Implement the subtask
3. Run verification: `mcp__auto-claude__run_verification({{"subtask_id": "{subtask_id}"}})`
4. If FAIL — fix and re-run. If PASS — complete:
5. `mcp__auto-claude__complete_subtask({{"subtask_id": "{subtask_id}", "summary": "what was done"}})`

**DO NOT** manually update plan, commit, or write progress — complete_subtask handles all of it.
Focus ONLY on this subtask — don't modify unrelated code.
""")

    # Note: Linear updates are now handled by Python orchestrator via linear_updater.py
    # Agents no longer need to call Linear MCP tools directly

    return "\n".join(sections)


def generate_planner_prompt(spec_dir: Path, project_dir: Path | None = None) -> str:
    """
    Generate the planner prompt (used only once at start).
    This is a simplified version that focuses on plan creation.

    Args:
        spec_dir: Directory containing spec.md
        project_dir: Working directory (for relative paths)

    Returns:
        Planner prompt string
    """
    # Load the full planner prompt from file.
    candidate_dirs = [
        Path(__file__).parent.parent / "prompts",  # current layout
        Path(__file__).parent / "prompts",  # legacy fallback (if any)
    ]
    planner_file = next(
        (
            (candidate_dir / "planner.md")
            for candidate_dir in candidate_dirs
            if (candidate_dir / "planner.md").exists()
        ),
        None,
    )

    if planner_file:
        prompt = planner_file.read_text(encoding="utf-8")
    else:
        prompt = (
            "Read spec.md and create implementation_plan.json with phases and subtasks."
        )

    # Use project_dir for relative paths, or infer from spec_dir
    if project_dir is None:
        # Infer: spec_dir is typically project/auto-claude/specs/XXX
        project_dir = spec_dir.parent.parent.parent

    # Get relative path for spec directory
    relative_spec = get_relative_spec_path(spec_dir, project_dir)

    # Build header with environment context
    header = generate_environment_context(project_dir, spec_dir)

    # Add spec-specific instructions
    header += f"""## SPEC LOCATION

Your spec file is located at: `{relative_spec}/spec.md`

Store all build artifacts in this spec directory:
- `{relative_spec}/implementation_plan.json` - Subtask-based implementation plan
- `{relative_spec}/build-progress.txt` - Progress notes
- `{relative_spec}/init.sh` - Environment setup script

The project root is your current working directory. Implement code in the project root,
not in the spec directory.

---

"""
    # Note: Linear task creation and updates are now handled by Python orchestrator
    # via linear_updater.py - agents no longer need Linear instructions in prompts

    return header + prompt


def load_subtask_context(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    max_file_lines: int = 200,
) -> dict:
    """
    Load minimal context needed for a subtask.

    Args:
        spec_dir: Spec directory
        project_dir: Project root
        subtask: The subtask being implemented
        max_file_lines: Maximum lines to include per file

    Returns:
        Dict with file contents and relevant context
    """
    context = {
        "patterns": {},
        "files_to_modify": {},
        "spec_excerpt": None,
    }

    # Load pattern files (truncated)
    for pattern_path in subtask.get("patterns_from", []):
        full_path = project_dir / pattern_path
        if full_path.exists():
            try:
                lines = full_path.read_text(encoding="utf-8").split("\n")
                if len(lines) > max_file_lines:
                    content = "\n".join(lines[:max_file_lines])
                    content += (
                        f"\n\n... (truncated, {len(lines) - max_file_lines} more lines)"
                    )
                else:
                    content = "\n".join(lines)
                context["patterns"][pattern_path] = content
            except Exception:
                context["patterns"][pattern_path] = "(Could not read file)"

    # Load files to modify (truncated)
    for file_path in subtask.get("files_to_modify", []):
        full_path = project_dir / file_path
        if full_path.exists():
            try:
                lines = full_path.read_text(encoding="utf-8").split("\n")
                if len(lines) > max_file_lines:
                    content = "\n".join(lines[:max_file_lines])
                    content += (
                        f"\n\n... (truncated, {len(lines) - max_file_lines} more lines)"
                    )
                else:
                    content = "\n".join(lines)
                context["files_to_modify"][file_path] = content
            except Exception:
                context["files_to_modify"][file_path] = "(Could not read file)"

    return context


def format_context_for_prompt(context: dict) -> str:
    """
    Format loaded context into a prompt section.

    Args:
        context: Dict from load_subtask_context

    Returns:
        Formatted string to append to prompt
    """
    sections = []

    if context.get("patterns"):
        sections.append("## Reference Files (Patterns to Follow)\n")
        for path, content in context["patterns"].items():
            sections.append(f"### `{path}`\n```\n{content}\n```\n")

    if context.get("files_to_modify"):
        sections.append("## Current File Contents (To Modify)\n")
        for path, content in context["files_to_modify"].items():
            sections.append(f"### `{path}`\n```\n{content}\n```\n")

    return "\n".join(sections)
