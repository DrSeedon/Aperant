"""
Project Map Generator — builds .auto-claude/project_map.md from project source.

Scans project files, AST-parses Python, regex-parses TS/JS,
extracts DB tables from ORM models. Preserves AI-written descriptions
on incremental updates.
"""

import ast
import re
from datetime import datetime, timezone
from pathlib import Path

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".auto-claude", "auto-claude", ".worktrees", "out", "dist",
    "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "egg-info",
}

IGNORE_FILES = {
    "__init__.py", "conftest.py", ".DS_Store",
}

CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}


def update_project_map(
    project_dir: Path,
    spec_name: str | None = None,
    changed_files: list[str] | None = None,
) -> Path:
    map_file = project_dir / ".auto-claude" / "project_map.md"
    existing_descriptions = _parse_existing_descriptions(map_file) if map_file.exists() else {}
    existing_task_tags = _parse_existing_task_tags(map_file) if map_file.exists() else {}

    all_files = _scan_project(project_dir)
    tree = _build_dir_tree(all_files, project_dir)
    modules = _analyze_modules(all_files, project_dir)
    db_tables = _extract_db_tables(all_files, project_dir)

    if spec_name and changed_files:
        for cf in changed_files:
            rel = cf.lstrip("/")
            if rel in existing_task_tags:
                if spec_name not in existing_task_tags[rel]:
                    existing_task_tags[rel].append(spec_name)
            else:
                existing_task_tags[rel] = [spec_name]

    md = _render_md(
        tree, modules, db_tables,
        existing_descriptions, existing_task_tags,
        spec_name, project_dir.name,
    )

    map_file.parent.mkdir(parents=True, exist_ok=True)
    map_file.write_text(md, encoding="utf-8")
    return map_file


def _scan_project(project_dir: Path) -> list[Path]:
    files = []
    for path in sorted(project_dir.rglob("*")):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in CODE_EXTENSIONS and path.name not in IGNORE_FILES:
            files.append(path)
    return files


def _build_dir_tree(files: list[Path], project_dir: Path) -> dict[str, int]:
    dirs: dict[str, int] = {}
    for f in files:
        rel = f.relative_to(project_dir)
        parts = rel.parts[:-1]
        for i in range(1, len(parts) + 1):
            d = "/".join(parts[:i])
            dirs[d] = dirs.get(d, 0)
        parent = "/".join(parts) if parts else "."
        dirs[parent] = dirs.get(parent, 0) + 1
    return dirs


def _analyze_modules(files: list[Path], project_dir: Path) -> dict[str, dict]:
    modules = {}
    for f in files:
        rel = str(f.relative_to(project_dir))
        info: dict = {"functions": [], "classes": [], "imports": []}

        if f.suffix == ".py":
            info = _parse_python(f)
        elif f.suffix in (".ts", ".tsx", ".js", ".jsx"):
            info = _parse_typescript(f)

        if info["functions"] or info["classes"]:
            modules[rel] = info

    return modules


def _parse_python(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return {"functions": [], "classes": [], "imports": []}

    functions = []
    classes = []
    imports = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__init__":
                continue
            args = [a.arg for a in node.args.args if a.arg != "self"]
            functions.append(f"{node.name}({', '.join(args)})")

        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            base_str = f"({', '.join(bases)})" if bases else ""
            classes.append(f"{node.name}{base_str}")

            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    functions.append(f"{node.name}.{item.name}({', '.join(args)})")

        elif isinstance(node, ast.ImportFrom) and node.module:
            if not node.module.startswith(("typing", "pathlib", "os", "sys", "json", "re", "datetime")):
                imports.append(node.module)

    return {"functions": functions[:15], "classes": classes[:10], "imports": imports[:10]}


def _parse_typescript(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {"functions": [], "classes": [], "imports": []}

    functions = []
    classes = []

    for m in re.finditer(r'export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', source):
        name = m.group(1)
        params = m.group(2).strip()
        params_short = ", ".join(p.split(":")[0].strip() for p in params.split(",") if p.strip())[:60]
        functions.append(f"{name}({params_short})")

    for m in re.finditer(r'export\s+(?:default\s+)?class\s+(\w+)', source):
        classes.append(m.group(1))

    for m in re.finditer(r'export\s+const\s+(\w+)\s*=\s*(?:memo\s*\()?\s*function', source):
        functions.append(m.group(1))

    return {"functions": functions[:15], "classes": classes[:10], "imports": []}


def _extract_db_tables(files: list[Path], project_dir: Path) -> list[dict]:
    tables = []
    model_files = [f for f in files if f.name == "models.py" or "model" in f.name.lower()]

    for f in model_files:
        if f.suffix != ".py":
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue

        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            tablename = None
            columns = []

            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "__tablename__":
                            if isinstance(item.value, ast.Constant):
                                tablename = item.value.value

                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    col_name = item.target.id
                    if not col_name.startswith("_"):
                        columns.append(col_name)

            if tablename:
                tables.append({
                    "table": tablename,
                    "class": node.name,
                    "columns": columns[:12],
                    "file": str(f.relative_to(project_dir)),
                })

    return tables


def _parse_existing_descriptions(map_file: Path) -> dict[str, str]:
    descriptions = {}
    try:
        content = map_file.read_text(encoding="utf-8")
    except OSError:
        return descriptions

    current_module = None
    for line in content.splitlines():
        if line.startswith("### "):
            current_module = line[4:].strip()
        elif line.startswith("> ") and current_module:
            descriptions[current_module] = line[2:].strip()
            current_module = None
        elif not line.startswith("> "):
            current_module = None

    return descriptions


def _parse_existing_task_tags(map_file: Path) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    try:
        content = map_file.read_text(encoding="utf-8")
    except OSError:
        return tags

    current_module = None
    for line in content.splitlines():
        if line.startswith("### "):
            current_module = line[4:].strip()
        elif line.startswith("> ") and current_module:
            task_matches = re.findall(r'task[s]?\s+([\w, -]+)', line, re.IGNORECASE)
            if task_matches:
                task_list = []
                for m in task_matches:
                    task_list.extend(t.strip() for t in m.split(",") if t.strip())
                tags[current_module] = task_list
            current_module = None

    return tags


def _render_md(
    tree: dict[str, int],
    modules: dict[str, dict],
    db_tables: list[dict],
    descriptions: dict[str, str],
    task_tags: dict[str, list[str]],
    spec_name: str | None,
    project_name: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    task_label = f"task {spec_name}" if spec_name else "full scan"

    lines = [
        f"# Project Map: {project_name}",
        f"> Last update: {task_label} ({now})",
        "",
        "## Structure",
        "",
    ]

    top_dirs = sorted(set(d.split("/")[0] for d in tree if "/" in d or tree.get(d, 0) > 0))
    for td in top_dirs:
        count = sum(v for k, v in tree.items() if k == td or k.startswith(td + "/"))
        subdirs = sorted(d for d in tree if d.startswith(td + "/") and d.count("/") == 1)
        lines.append(f"- `{td}/` — {count} files")
        for sd in subdirs:
            sd_count = sum(v for k, v in tree.items() if k == sd or k.startswith(sd + "/"))
            sd_name = sd.split("/")[-1]
            lines.append(f"  - `{sd_name}/` — {sd_count} files")

    root_count = tree.get(".", 0)
    if root_count:
        lines.append(f"- root — {root_count} files")

    lines.extend(["", "## Modules", ""])

    for rel_path in sorted(modules.keys()):
        info = modules[rel_path]
        lines.append(f"### {rel_path}")

        desc = descriptions.get(rel_path, "")
        tasks = task_tags.get(rel_path, [])
        if spec_name and rel_path in (task_tags or {}):
            pass

        tag_str = f"Tasks: {', '.join(tasks)}. " if tasks else ""
        if desc:
            lines.append(f"> {tag_str}{desc}")
        elif tag_str:
            lines.append(f"> {tag_str}")

        for cls in info.get("classes", []):
            lines.append(f"- class `{cls}`")
        for func in info.get("functions", []):
            lines.append(f"- `{func}`")
        if info.get("imports"):
            lines.append(f"- Imports: {', '.join(info['imports'])}")
        lines.append("")

    if db_tables:
        lines.extend(["## Database Tables", ""])
        for t in db_tables:
            cols = ", ".join(t["columns"][:8])
            more = f", ... +{len(t['columns']) - 8}" if len(t["columns"]) > 8 else ""
            lines.append(f"- **{t['table']}** (`{t['class']}` in `{t['file']}`) — {cols}{more}")
        lines.append("")

    return "\n".join(lines)
