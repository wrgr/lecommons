#!/usr/bin/env python3
"""Repository SWE guardrail checks.

This is intentionally lightweight (stdlib only) so it can run in local shells and CI.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

DOC_REQUIREMENTS = {
    "docs/tech-stack.md": ["# Tech Stack", "## Frontend", "## Data Pipeline", "## RAG/Backend"],
    "docs/architecture.md": ["# Architecture", "## System Overview", "## Module Boundaries", "## Data Flow"],
    "docs/progress.md": ["# Progress", "## Current Status", "## Next Steps", "## Risks"],
}

SOURCE_TARGETS = {
    "js": [ROOT / "app", ROOT / "web/knowledge-graph-sigma-starter/src", ROOT / "app.js"],
    "py": [ROOT / "scripts", ROOT / "rag", ROOT / "tests"],
    "ui": [ROOT / "styles.css", ROOT / "index.html"],
}

MAX_FILE_LINES = {
    ".js": 350,
    ".py": 350,
    ".css": 450,
    ".html": 250,
}

FILE_LINE_OVERRIDES = {
    "scripts/swe_lint.py": 550,
}

MAX_PY_FUNCTION_LINES = 90
MAX_JS_FUNCTION_LINES = 120

MARKDOWN_PATH_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".css", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}


@dataclass
class Issue:
    severity: str
    code: str
    path: str
    message: str


class SweLint:
    def __init__(self, check_outdated: bool = False, strict: bool = False) -> None:
        self.check_outdated = check_outdated
        self.strict = strict
        self.issues: list[Issue] = []

    def add(self, severity: str, code: str, path: str, message: str) -> None:
        self.issues.append(Issue(severity=severity, code=code, path=path, message=message))

    def run(self) -> int:
        js_files = self._collect_files((".js",))
        py_files = self._collect_files((".py",))
        ui_files = [path for path in (ROOT / "styles.css", ROOT / "index.html") if path.exists()]

        self.check_memory_bank_docs()
        self.check_file_sizes(js_files + py_files + ui_files)
        self.check_python_complexity(py_files)
        self.check_js_complexity(js_files)
        self.check_mixed_concerns(js_files)
        self.check_js_import_integrity(js_files)
        self.check_python_relative_imports(py_files)
        self.check_unused_js_exports(js_files)
        self.check_dependency_hygiene(js_files)
        self.check_markdown_paths()

        if self.check_outdated:
            self.check_outdated_dependencies()

        return self.report()

    def _collect_files(self, suffixes: tuple[str, ...]) -> list[Path]:
        files: list[Path] = []
        seen: set[Path] = set()
        for targets in SOURCE_TARGETS.values():
            for target in targets:
                if not target.exists():
                    continue
                if target.is_file() and target.suffix in suffixes and target not in seen:
                    files.append(target)
                    seen.add(target)
                if target.is_dir():
                    for path in target.rglob("*"):
                        if not path.is_file() or path.suffix not in suffixes:
                            continue
                        if any(part in {"node_modules", "dist", "__pycache__", ".venv"} for part in path.parts):
                            continue
                        if path not in seen:
                            files.append(path)
                            seen.add(path)
        return sorted(files)

    def check_memory_bank_docs(self) -> None:
        for rel_path, headings in DOC_REQUIREMENTS.items():
            path = ROOT / rel_path
            if not path.exists():
                self.add("ERROR", "DOC_MISSING", rel_path, "Required memory-bank doc is missing.")
                continue

            text = path.read_text(encoding="utf-8")
            if not text.strip():
                self.add("ERROR", "DOC_EMPTY", rel_path, "Doc file is empty.")
                continue

            for heading in headings:
                if heading not in text:
                    self.add("ERROR", "DOC_HEADING", rel_path, f"Missing required heading: {heading}")

            if rel_path.endswith("progress.md") and "Last Updated:" not in text:
                self.add("WARN", "DOC_STALE_SIGNAL", rel_path, "Add a 'Last Updated: YYYY-MM-DD' line to track recency.")

    def check_file_sizes(self, files: Iterable[Path]) -> None:
        for path in files:
            line_count = self._line_count(path)
            rel = self._rel(path)
            budget = FILE_LINE_OVERRIDES.get(rel, MAX_FILE_LINES.get(path.suffix))
            if budget and line_count > budget:
                self.add(
                    "WARN",
                    "FILE_TOO_LARGE",
                    rel,
                    f"{line_count} lines exceeds budget of {budget}. Refactor into smaller modules.",
                )

    def check_python_complexity(self, py_files: Iterable[Path]) -> None:
        for path in py_files:
            text = path.read_text(encoding="utf-8")
            rel = self._rel(path)
            try:
                tree = ast.parse(text)
            except SyntaxError as exc:
                self.add("ERROR", "PY_SYNTAX", rel, f"Syntax error: {exc}")
                continue

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue

                if not hasattr(node, "end_lineno") or node.end_lineno is None:
                    continue

                length = node.end_lineno - node.lineno + 1
                if length > MAX_PY_FUNCTION_LINES:
                    self.add(
                        "WARN",
                        "PY_FUNC_LONG",
                        f"{rel}:{node.lineno}",
                        f"Function '{node.name}' is {length} lines; split into smaller functions.",
                    )

    def check_js_complexity(self, js_files: Iterable[Path]) -> None:
        function_starts = re.compile(
            r"^\s*(?:export\s+)?(?:function\s+(?P<fn>[A-Za-z_$][\w$]*)\s*\(|const\s+(?P<const>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:function\s*\(|\([^)]*\)\s*=>\s*\{))"
        )

        for path in js_files:
            rel = self._rel(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines, start=1):
                match = function_starts.match(line)
                if not match:
                    continue
                name = match.group("fn") or match.group("const") or "anonymous"
                length = self._estimate_js_block_length(lines, index)
                if length > MAX_JS_FUNCTION_LINES:
                    self.add(
                        "WARN",
                        "JS_FUNC_LONG",
                        f"{rel}:{index}",
                        f"Function '{name}' is about {length} lines; split into smaller functions.",
                    )

    def _estimate_js_block_length(self, lines: list[str], start_line: int) -> int:
        start_index = start_line - 1
        brace_depth = 0
        started = False

        for idx in range(start_index, len(lines)):
            current = lines[idx]
            for char in current:
                if char == "{":
                    brace_depth += 1
                    started = True
                elif char == "}" and started:
                    brace_depth -= 1
                    if brace_depth == 0:
                        return idx - start_index + 1

        return len(lines) - start_index

    def check_mixed_concerns(self, js_files: Iterable[Path]) -> None:
        for path in js_files:
            text = path.read_text(encoding="utf-8")
            concerns = set()
            if "fetch(" in text or "DATA_FILES" in text:
                concerns.add("data_access")
            if "d3." in text:
                concerns.add("graph_rendering")
            if "html`" in text or "className=" in text or "<${" in text:
                concerns.add("ui_rendering")
            if "cleanText(" in text or "normalize" in text:
                concerns.add("normalization")

            if len(concerns) >= 3 and self._line_count(path) > 200:
                self.add(
                    "WARN",
                    "MIXED_CONCERNS",
                    self._rel(path),
                    f"File mixes {sorted(concerns)}; consider splitting by responsibility.",
                )

    def check_js_import_integrity(self, js_files: Iterable[Path]) -> None:
        import_re = re.compile(r"^\s*import\s+[^;]*?\s+from\s+[\"']([^\"']+)[\"']", re.MULTILINE)

        for path in js_files:
            rel = self._rel(path)
            text = path.read_text(encoding="utf-8")
            for specifier in import_re.findall(text):
                if not specifier.startswith("."):
                    continue
                if not self._resolve_js_local_import(path, specifier):
                    self.add("ERROR", "JS_IMPORT_MISSING", rel, f"Local import does not resolve: {specifier}")

    def _resolve_js_local_import(self, source: Path, specifier: str) -> bool:
        base = (source.parent / specifier).resolve()
        candidates = []
        if base.suffix:
            candidates.append(base)
        else:
            candidates.extend([base.with_suffix(".js"), base.with_suffix(".mjs"), base / "index.js"])
        return any(candidate.exists() for candidate in candidates)

    def check_python_relative_imports(self, py_files: Iterable[Path]) -> None:
        for path in py_files:
            rel = self._rel(path)
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if not node.level:
                    continue

                resolved = self._resolve_python_relative(path, node.module, node.level)
                if resolved is None:
                    continue
                if not resolved.exists() and not (resolved.with_suffix(".py").exists() or (resolved / "__init__.py").exists()):
                    self.add(
                        "ERROR",
                        "PY_IMPORT_MISSING",
                        f"{rel}:{node.lineno}",
                        f"Relative import does not resolve: from {'.' * node.level}{node.module or ''} import ...",
                    )

    def _resolve_python_relative(self, source: Path, module: str | None, level: int) -> Path | None:
        current = source.parent
        for _ in range(level - 1):
            current = current.parent
        if module:
            return current / module.replace(".", "/")
        return current

    def check_unused_js_exports(self, js_files: Iterable[Path]) -> None:
        export_re = re.compile(r"^\s*export\s+(?:function|const|class)\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
        all_text = {path: path.read_text(encoding="utf-8") for path in js_files}

        for path, text in all_text.items():
            rel = self._rel(path)
            if not (rel == "app.js" or rel.startswith("app/")):
                continue

            for symbol in export_re.findall(text):
                # Ignore symbols that are used internally in the same module.
                same_file_uses = len(re.findall(rf"\b{re.escape(symbol)}\b", text))
                if same_file_uses > 1:
                    continue

                used_elsewhere = False
                probe = re.compile(rf"\b{re.escape(symbol)}\b")
                for other_path, other_text in all_text.items():
                    if other_path == path:
                        continue
                    if probe.search(other_text):
                        used_elsewhere = True
                        break
                if not used_elsewhere:
                    self.add("WARN", "JS_UNUSED_EXPORT", rel, f"Export '{symbol}' appears unused in this repo.")

    def check_dependency_hygiene(self, js_files: Iterable[Path]) -> None:
        lib_path = ROOT / "app/lib.js"
        if lib_path.exists():
            text = lib_path.read_text(encoding="utf-8")
            esm_urls = re.findall(r'https://esm\.sh/([^"\']+)', text)
            for package_ref in esm_urls:
                if "@" not in package_ref:
                    self.add("WARN", "DEP_UNPINNED_ESM", self._rel(lib_path), f"Unpinned esm.sh import: {package_ref}")

        req_path = ROOT / "requirements-rag.txt"
        if req_path.exists():
            for idx, raw_line in enumerate(req_path.read_text(encoding="utf-8").splitlines(), start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "==" not in line:
                    self.add(
                        "WARN",
                        "DEP_UNPINNED_PY",
                        f"requirements-rag.txt:{idx}",
                        f"Dependency not pinned with == : {line}",
                    )

        package_json = ROOT / "web/knowledge-graph-sigma-starter/package.json"
        if package_json.exists():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self.add("ERROR", "PACKAGE_JSON_INVALID", self._rel(package_json), str(exc))
                return

            for block in ("dependencies", "devDependencies"):
                deps = payload.get(block, {})
                for dep, version in deps.items():
                    if isinstance(version, str) and version[:1] in {"^", "~", ">", "<"}:
                        self.add(
                            "WARN",
                            "DEP_RANGE_JS",
                            self._rel(package_json),
                            f"{block}.{dep} uses range '{version}'. Prefer pinning for reproducibility.",
                        )

    def check_markdown_paths(self) -> None:
        markdown_files = [ROOT / "README.md"]
        markdown_files.extend(sorted((ROOT / "docs").glob("*.md")))

        code_re = re.compile(r"`([^`]+)`")
        for path in markdown_files:
            if not path.exists():
                continue
            rel = self._rel(path)
            text = path.read_text(encoding="utf-8")

            for token in code_re.findall(text):
                candidate = token.strip()
                if not candidate or candidate.startswith("http") or candidate.startswith("/"):
                    continue
                if "\n" in candidate or "\r" in candidate:
                    continue
                if re.search(r"\s", candidate):
                    continue
                if "*" in candidate or "..." in candidate:
                    continue
                if not re.match(r"^[A-Za-z0-9._/-]+$", candidate):
                    continue
                if "/" not in candidate and not candidate.endswith(".md"):
                    continue

                suffix = Path(candidate).suffix.lower()
                if suffix and suffix not in MARKDOWN_PATH_EXTENSIONS:
                    continue

                resolved = (ROOT / candidate).resolve()
                if not resolved.exists():
                    self.add("WARN", "DOC_PATH_MISSING", rel, f"Referenced path does not exist: `{candidate}`")

    def check_outdated_dependencies(self) -> None:
        package_root = ROOT / "web/knowledge-graph-sigma-starter"
        if package_root.exists():
            self._run_outdated_cmd(
                ["npm", "outdated", "--json"],
                cwd=package_root,
                tool="npm",
                path=self._rel(package_root / "package.json"),
            )

        venv_python = ROOT / ".venv/bin/python"
        if venv_python.exists():
            self._run_outdated_cmd(
                [str(venv_python), "-m", "pip", "list", "--outdated", "--format=json"],
                cwd=ROOT,
                tool="pip",
                path="requirements-rag.txt",
            )

    def _run_outdated_cmd(self, cmd: list[str], cwd: Path, tool: str, path: str) -> None:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except FileNotFoundError:
            self.add("WARN", "OUTDATED_SKIPPED", path, f"{tool} not installed; skipping live outdated check.")
            return
        except subprocess.TimeoutExpired:
            self.add("WARN", "OUTDATED_TIMEOUT", path, f"{tool} outdated check timed out.")
            return

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode not in {0, 1}:
            reason = stderr or "non-zero exit"
            self.add("WARN", "OUTDATED_SKIPPED", path, f"{tool} outdated check failed: {reason}")
            return

        if not stdout:
            return

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            self.add("WARN", "OUTDATED_PARSE", path, f"{tool} outdated output is not valid JSON.")
            return

        count = len(payload) if isinstance(payload, (list, dict)) else 1
        self.add("WARN", "OUTDATED_FOUND", path, f"{tool} reports {count} outdated dependency entries.")

    def report(self) -> int:
        if not self.issues:
            print("swe-lint: OK (no issues found)")
            return 0

        errors = [issue for issue in self.issues if issue.severity == "ERROR"]
        warnings = [issue for issue in self.issues if issue.severity == "WARN"]

        for issue in self.issues:
            print(f"[{issue.severity}] {issue.code} {issue.path} - {issue.message}")

        print(f"\nswe-lint summary: {len(errors)} error(s), {len(warnings)} warning(s)")

        if errors:
            return 1
        if self.strict and warnings:
            return 2
        return 0

    @staticmethod
    def _line_count(path: Path) -> int:
        try:
            return len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            return 0

    @staticmethod
    def _rel(path: Path) -> str:
        return str(path.resolve().relative_to(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SWE guardrail lint checks")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as non-zero exit code.")
    parser.add_argument(
        "--check-outdated",
        action="store_true",
        help="Run live outdated dependency checks via npm/pip (may require network access).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return SweLint(check_outdated=args.check_outdated, strict=args.strict).run()


if __name__ == "__main__":
    sys.exit(main())
