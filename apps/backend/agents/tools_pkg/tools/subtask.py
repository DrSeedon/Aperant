"""
Subtask Management Tools
========================

Tools for managing subtask status in implementation_plan.json.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.file_utils import write_json_atomic
from spec.validate_pkg.auto_fix import auto_fix_plan

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def _update_subtask_in_plan(
    plan: dict[str, Any],
    subtask_id: str,
    status: str,
    notes: str,
) -> bool:
    """
    Update a subtask in the plan.

    Args:
        plan: The implementation plan dict
        subtask_id: ID of the subtask to update
        status: New status (pending, in_progress, completed, failed)
        notes: Optional notes to add

    Returns:
        True if subtask was found and updated, False otherwise
    """
    subtask_found = False
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if subtask.get("id") == subtask_id:
                subtask["status"] = status
                if notes:
                    subtask["notes"] = notes
                subtask["updated_at"] = datetime.now(timezone.utc).isoformat()
                subtask_found = True
                break
        if subtask_found:
            break

    if subtask_found:
        plan["last_updated"] = datetime.now(timezone.utc).isoformat()

    return subtask_found


def create_subtask_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create subtask management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of subtask tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: update_subtask_status
    # -------------------------------------------------------------------------
    @tool(
        "update_subtask_status",
        "Update the status of a subtask in implementation_plan.json. Use this when completing or starting a subtask.",
        {"subtask_id": str, "status": str, "notes": str},
    )
    async def update_subtask_status(args: dict[str, Any]) -> dict[str, Any]:
        """Update subtask status in the implementation plan."""
        subtask_id = args["subtask_id"]
        status = args["status"]
        notes = args.get("notes", "")

        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if status not in valid_statuses:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid status '{status}'. Must be one of: {valid_statuses}",
                    }
                ]
            }

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: implementation_plan.json not found",
                    }
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            subtask_found = _update_subtask_in_plan(plan, subtask_id, status, notes)

            if not subtask_found:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Subtask '{subtask_id}' not found in implementation plan",
                        }
                    ]
                }

            # Use atomic write to prevent file corruption
            write_json_atomic(plan_file, plan, indent=2)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully updated subtask '{subtask_id}' to status '{status}'",
                    }
                ]
            }

        except json.JSONDecodeError as e:
            # Attempt to auto-fix the plan and retry
            if auto_fix_plan(spec_dir):
                # Retry after fix
                try:
                    with open(plan_file, encoding="utf-8") as f:
                        plan = json.load(f)

                    subtask_found = _update_subtask_in_plan(
                        plan, subtask_id, status, notes
                    )

                    if subtask_found:
                        write_json_atomic(plan_file, plan, indent=2)
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Successfully updated subtask '{subtask_id}' to status '{status}' (after auto-fix)",
                                }
                            ]
                        }
                    else:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error: Subtask '{subtask_id}' not found in implementation plan (after auto-fix)",
                                }
                            ]
                        }
                except Exception as retry_err:
                    logging.warning(
                        f"Subtask update retry failed after auto-fix: {retry_err}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Subtask update failed after auto-fix: {retry_err}",
                            }
                        ]
                    }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid JSON in implementation_plan.json: {e}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error updating subtask status: {e}"}
                ]
            }

    tools.append(update_subtask_status)

    # -------------------------------------------------------------------------
    # Tool: get_next_subtask
    # -------------------------------------------------------------------------
    @tool(
        "get_next_subtask",
        "Get full details of the next pending subtask: id, description, files_to_modify, files_to_create, patterns_from, verification, phase name. Use this instead of reading implementation_plan.json manually.",
        {},
    )
    async def get_next_subtask(args: dict[str, Any]) -> dict[str, Any]:
        """Get next pending subtask with all details."""
        plan_file = spec_dir / "implementation_plan.json"

        if not plan_file.exists():
            return {
                "content": [
                    {"type": "text", "text": "Error: implementation_plan.json not found"}
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            phases = plan.get("phases", [])

            # Build set of completed phase IDs
            completed_phases = set()
            for phase in phases:
                phase_id = phase.get("id", "")
                all_done = all(
                    s.get("status") == "completed"
                    for s in phase.get("subtasks", [])
                )
                if all_done and phase.get("subtasks"):
                    completed_phases.add(phase_id)

            # Find next pending subtask respecting dependencies
            for phase in phases:
                phase_id = phase.get("id", "")
                phase_name = phase.get("name", phase_id)
                depends_on = phase.get("depends_on", [])

                # Check if dependencies are met
                deps_met = all(
                    dep in completed_phases
                    for dep in depends_on
                )
                if not deps_met:
                    continue

                for subtask in phase.get("subtasks", []):
                    if subtask.get("status") in ("pending", "in_progress"):
                        result = {
                            "id": subtask.get("id", ""),
                            "description": subtask.get("description", ""),
                            "phase": phase_name,
                            "phase_id": phase_id,
                            "service": subtask.get("service", ""),
                            "files_to_modify": subtask.get("files_to_modify", []),
                            "files_to_create": subtask.get("files_to_create", []),
                            "patterns_from": subtask.get("patterns_from", []),
                            "verification": subtask.get("verification", {}),
                        }
                        return {
                            "content": [
                                {"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}
                            ]
                        }

            # All done
            total = sum(len(p.get("subtasks", [])) for p in phases)
            return {
                "content": [
                    {"type": "text", "text": f"All {total} subtasks completed. Build ready for QA."}
                ]
            }

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error reading plan: {e}"}
                ]
            }

    tools.append(get_next_subtask)

    # -------------------------------------------------------------------------
    # Tool: run_verification
    # -------------------------------------------------------------------------
    @tool(
        "run_verification",
        "Run the verification command for a subtask. Reads verification from implementation_plan.json, executes the command, compares output with expected result. Returns pass/fail.",
        {"subtask_id": str},
    )
    async def run_verification(args: dict[str, Any]) -> dict[str, Any]:
        """Run subtask verification command and check result."""
        import subprocess

        subtask_id = args["subtask_id"]
        plan_file = spec_dir / "implementation_plan.json"

        if not plan_file.exists():
            return {
                "content": [
                    {"type": "text", "text": "Error: implementation_plan.json not found"}
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            # Find subtask
            verification = None
            for phase in plan.get("phases", []):
                for subtask in phase.get("subtasks", []):
                    if subtask.get("id") == subtask_id:
                        verification = subtask.get("verification", {})
                        break
                if verification is not None:
                    break

            if verification is None:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Subtask '{subtask_id}' not found"}
                    ]
                }

            v_type = verification.get("type", "")
            if v_type == "none" or not verification:
                return {
                    "content": [
                        {"type": "text", "text": f"PASS: No verification required for {subtask_id}"}
                    ]
                }

            if v_type != "command":
                return {
                    "content": [
                        {"type": "text", "text": f"Verification type '{v_type}' requires manual execution. Command: {verification.get('command', 'N/A')}"}
                    ]
                }

            command = verification.get("command", "")
            expected = verification.get("expected", "")

            if not command:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: No command in verification for {subtask_id}"}
                    ]
                }

            # Execute command from project directory
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(project_dir),
                )
                output = result.stdout.strip()
                stderr = result.stderr.strip()

                if expected and expected in output:
                    return {
                        "content": [
                            {"type": "text", "text": f"PASS: Verification for {subtask_id}\nCommand: {command}\nExpected: {expected}\nGot: {output}"}
                        ]
                    }
                elif result.returncode == 0 and not expected:
                    return {
                        "content": [
                            {"type": "text", "text": f"PASS: Command exited 0 for {subtask_id}\nOutput: {output[:500]}"}
                        ]
                    }
                else:
                    return {
                        "content": [
                            {"type": "text", "text": f"FAIL: Verification for {subtask_id}\nCommand: {command}\nExpected: {expected}\nGot: {output}\nStderr: {stderr}\nExit code: {result.returncode}"}
                        ]
                    }

            except subprocess.TimeoutExpired:
                return {
                    "content": [
                        {"type": "text", "text": f"FAIL: Command timed out (30s) for {subtask_id}: {command}"}
                    ]
                }

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error running verification: {e}"}
                ]
            }

    tools.append(run_verification)

    # -------------------------------------------------------------------------
    # Tool: complete_subtask
    # -------------------------------------------------------------------------
    @tool(
        "complete_subtask",
        "Complete a subtask in one call: marks status as completed, appends progress to build-progress.txt, commits changes with git, and returns the next pending subtask. Use this instead of manually doing update_subtask_status + append_progress + git commit.",
        {"subtask_id": str, "summary": str},
    )
    async def complete_subtask(args: dict[str, Any]) -> dict[str, Any]:
        """Complete subtask: update plan + progress + git commit + return next."""
        import subprocess

        subtask_id = args["subtask_id"]
        summary = args.get("summary", "Completed")

        plan_file = spec_dir / "implementation_plan.json"
        progress_file = spec_dir / "build-progress.txt"

        if not plan_file.exists():
            return {
                "content": [
                    {"type": "text", "text": "Error: implementation_plan.json not found"}
                ]
            }

        try:
            # 1. Update status in plan
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            found = _update_subtask_in_plan(plan, subtask_id, "completed", summary)
            if not found:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Subtask '{subtask_id}' not found"}
                    ]
                }

            write_json_atomic(plan_file, plan, indent=2)

            # 2. Append progress
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            entry = f"\n{subtask_id} — {timestamp}\n{summary}\n"
            with open(progress_file, "a", encoding="utf-8") as f:
                f.write(entry)

            # 3. Git commit
            try:
                subprocess.run(
                    "git add . ':!.auto-claude'",
                    shell=True, cwd=str(project_dir),
                    capture_output=True, timeout=15,
                )
                subprocess.run(
                    f'git commit -m "auto-claude: {subtask_id} - {summary[:60]}"',
                    shell=True, cwd=str(project_dir),
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass  # Git commit is best-effort

            # 4. Find next subtask
            phases = plan.get("phases", [])
            completed_phases = set()
            for phase in phases:
                pid = phase.get("id", "")
                if all(s.get("status") == "completed" for s in phase.get("subtasks", [])):
                    completed_phases.add(pid)

            next_info = "All subtasks completed. Build ready for QA."
            for phase in phases:
                pid = phase.get("id", "")
                pname = phase.get("name", pid)
                deps = phase.get("depends_on", [])
                if not all(d in completed_phases for d in deps):
                    continue
                for s in phase.get("subtasks", []):
                    if s.get("status") in ("pending", "in_progress"):
                        next_info = json.dumps({
                            "id": s.get("id"),
                            "description": s.get("description", ""),
                            "phase": pname,
                            "files_to_modify": s.get("files_to_modify", []),
                            "files_to_create": s.get("files_to_create", []),
                            "patterns_from": s.get("patterns_from", []),
                            "verification": s.get("verification", {}),
                        }, indent=2, ensure_ascii=False)
                        break
                else:
                    continue
                break

            return {
                "content": [
                    {"type": "text", "text": f"✅ {subtask_id} completed and committed.\n\nNext subtask:\n{next_info}"}
                ]
            }

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error completing subtask: {e}"}
                ]
            }

    tools.append(complete_subtask)

    return tools
