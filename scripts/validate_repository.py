#!/usr/bin/env python3
"""Validate the workshop package without installing or changing anything."""
import argparse
import ast
import json
from pathlib import Path
import re
import sys

SKILL_FILES = {
    "russian-natural-voice.md", "knowledge-state-corrections.md",
    "meeting-transcript-analysis.md", "book-library-setup.md",
    "document-feedback-learning.md", "telegram-thread-title-icon.md",
}
# Detect data shapes rather than retaining the author's private identifiers.
PRIVATE_PATTERNS = (
    ("absolute home path", r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)[^\s`<>]+"),
    ("numeric messaging ID", r"(?i)\b(?:chat_id|message_thread_id|user_id|TELEGRAM_ALLOWED_USERS|TELEGRAM_HOME_CHANNEL)\b[\"'\s:=]+-?\d{5,}"),
    ("bot token", r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
)


def fenced_blocks(text):
    opened = None
    blocks = []
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if opened is None:
            if match:
                opened = (match.group(1), match.group(2).strip(), number)
                lines = []
        elif match and match.group(1) == opened[0] and not match.group(2).strip():
            blocks.append((opened[1], "\n".join(lines), opened[2]))
            opened = None
        else:
            lines.append(line)
    return blocks, opened


def validate(root):
    root = Path(root).resolve()
    errors = []
    skills = []
    try:
        catalog = json.loads((root / "modules.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": [f"modules.json: {exc}"], "modules": 0, "skills": []}
    modules = catalog.get("modules", [])
    if catalog.get("schema_version") != 1:
        errors.append("Unsupported catalog schema")
    if catalog.get("installation_policy") != "explicit-selection-only":
        errors.append("Explicit selection policy missing")
    if not isinstance(modules, list) or not modules:
        return {"ok": False, "errors": errors + ["Nonempty module list required"], "modules": 0, "skills": []}
    ids = [row.get("id") for row in modules if isinstance(row, dict)]
    if len(ids) != len(modules) or len(ids) != len(set(ids)):
        errors.append("Invalid or duplicate module IDs")
    filenames = [row.get("file") for row in modules if isinstance(row, dict)]
    if len(filenames) != len(set(filenames)):
        errors.append("Duplicate module files")
    try:
        readme = (root / "README.md").read_text(encoding="utf-8")
    except OSError:
        readme = ""
        errors.append("README.md missing")
    texts = {"README.md": readme, "modules.json": json.dumps(catalog, ensure_ascii=False)}
    for path in root.glob("*.md"):
        if path.is_file() and path.resolve().parent == root:
            texts[path.name] = path.read_text(encoding="utf-8")
    graph = {}
    for row in modules:
        if not isinstance(row, dict):
            continue
        mid, filename = row.get("id"), row.get("file")
        if not isinstance(mid, str) or not re.fullmatch(r"[a-z0-9-]+", mid):
            errors.append(f"Invalid ID: {mid!r}")
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".md"):
            errors.append(f"Unsafe module path: {filename!r}")
            continue
        if row.get("default_selected") is not False:
            errors.append(f"{mid}: module selected by default")
        if row.get("risk") == "high" and row.get("recommended_for_start"):
            errors.append(f"{mid}: high-risk module recommended by default")
        dependencies = row.get("requires", [])
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
            errors.append(f"{mid}: invalid dependencies")
            dependencies = []
        graph[mid] = dependencies
        for dep in dependencies:
            if dep not in ids:
                errors.append(f"{mid}: unknown dependency {dep}")
        if f"]({filename})" not in readme:
            errors.append(f"{mid}: README link missing")
        path = root / filename
        if not path.is_file() or path.resolve().parent != root:
            errors.append(f"{mid}: module missing or outside root")
            continue
        text = path.read_text(encoding="utf-8")
        texts[filename] = text
        blocks, unclosed = fenced_blocks(text)
        if unclosed:
            errors.append(f"{filename}: unclosed fence at line {unclosed[2]}")
        embedded = []
        for language, block, line in blocks:
            if language == "markdown" and block.startswith("---\n"):
                parts = block.split("\n---\n", 1)
                if len(parts) != 2 or not parts[1].strip():
                    errors.append(f"{filename}:{line}: invalid skill frontmatter/body")
                    continue
                header = parts[0][4:]
                if not re.search(r"^name:", header, re.M):
                    continue
                name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", header, re.M)
                desc = re.search(r"^description:\s*\S.+$", header, re.M)
                if not name or not desc:
                    errors.append(f"{filename}:{line}: skill name/description missing")
                else:
                    embedded.append(name.group(1))
                    skills.append({"file": filename, "name": name.group(1)})
            if language == "python":
                try:
                    ast.parse(block)
                except SyntaxError as exc:
                    errors.append(f"{filename}:{line}: Python example syntax: {exc}")
        if filename in SKILL_FILES and len(embedded) != 1:
            errors.append(f"{filename}: expected one complete embedded skill; got {len(embedded)}")
    visiting, visited = set(), set()

    def visit(mid):
        if mid in visiting:
            errors.append(f"Dependency cycle at {mid}")
            return
        if mid in visited:
            return
        visiting.add(mid)
        for dep in graph.get(mid, []):
            visit(dep)
        visiting.remove(mid)
        visited.add(mid)

    for mid in graph:
        visit(mid)
    for filename, text in texts.items():
        for label, pattern in PRIVATE_PATTERNS:
            if re.search(pattern, text):
                errors.append(f"{filename}: possible private data ({label})")
    for target in re.findall(r"\]\(([^)]+)\)", readme):
        if "://" in target or target.startswith("#"):
            continue
        path = root / target.split("#", 1)[0]
        if not path.exists() or not path.resolve().is_relative_to(root):
            errors.append(f"README.md: broken/unsafe local link {target}")
    return {"ok": not errors, "modules": len(modules), "skills": skills, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
