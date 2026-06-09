# Code Health Skills — Foundation + complexity-audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the new standalone `code-health-skills` package (own release machinery + shared finding contract) and prove it end-to-end with the first working, tested leaf skill, `complexity-audit`.

**Architecture:** A fresh git repo `code-health-skills`, structured like `repo-audit-skills` but containing only the new skills. A single source-of-truth helper module (`shared/health_common.py`) defines the Finding type, deterministic IDs, sorting, and exit-code convention; it is **vendored** (copied) into each leaf's `scripts/` so every leaf is self-contained and independently installable, with a gate test asserting the vendored copies stay byte-identical to the source. The first leaf, `complexity-audit`, uses `lizard` (per-function cyclomatic complexity, NLOC, params, tokens) and `radon mi` (per-module maintainability index) to emit findings to the shared schema.

**Tech Stack:** Python 3.10+ (target repos), Node ≥18 (installer), `lizard`, `radon`, `ruff` (dev), `pytest` (tests), `npm` (release gate).

**Plan set:** This is Plan 1 of 6. Plans 2–5 add `duplication-audit`, `dead-code-audit`, `structure-audit`, `quality-audit`. Plan 6 adds the `code-health-audit-pipeline` umbrella. Each plan follows the leaf pattern established here.

**Spec:** `docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md` (will be relocated into the new repo in Task 1).

---

## File Structure (this plan)

```
code-health-skills/
├─ .gitignore
├─ LICENSE
├─ README.md
├─ AGENTS.md
├─ package.json
├─ bin/install-code-health-skills.js
├─ scripts/
│  ├─ check_release.py
│  ├─ check_skill_fixtures.py
│  └─ check_vendored_common.py
├─ shared/
│  └─ health_common.py                      # SOURCE OF TRUTH for the leaf helper
├─ docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md
├─ docs/superpowers/plans/2026-06-10-code-health-skills-foundation.md
└─ skills/
   └─ complexity-audit/
      ├─ SKILL.md
      ├─ LICENSE
      ├─ pyproject.toml
      ├─ scripts/
      │  ├─ health_common.py                # VENDORED copy of shared/health_common.py
      │  └─ complexity_audit.py             # leaf entrypoint (--help, --root, …)
      ├─ references/
      │  └─ rubric.md
      └─ tests/
         ├─ helpers.py
         ├─ fixtures/clean/pkg/simple.py
         ├─ fixtures/dirty/pkg/complex.py
         ├─ test_complexity_findings.py
         └─ test_complexity_cli.py
```

---

## Task 1: Create the repo and relocate planning docs

**Files:**
- Create: `/home/jakub/projects/code-health-skills/` (new git repo)
- Create: `code-health-skills/.gitignore`
- Move: spec + this plan into the new repo's `docs/`

- [ ] **Step 1: Create and init the repo**

Run:
```bash
mkdir -p /home/jakub/projects/code-health-skills
cd /home/jakub/projects/code-health-skills
git init
```
Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Add `.gitignore`**

Create `/home/jakub/projects/code-health-skills/.gitignore`:
```gitignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
node_modules/
/tmp/
```

- [ ] **Step 3: Copy planning docs into the new repo**

Run:
```bash
mkdir -p /home/jakub/projects/code-health-skills/docs/superpowers/specs
mkdir -p /home/jakub/projects/code-health-skills/docs/superpowers/plans
cp /home/jakub/projects/repo-audit-skills/docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md \
   /home/jakub/projects/code-health-skills/docs/superpowers/specs/
cp /home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-code-health-skills-foundation.md \
   /home/jakub/projects/code-health-skills/docs/superpowers/plans/
```
Expected: both files exist under the new repo's `docs/`.

- [ ] **Step 4: Commit**

```bash
cd /home/jakub/projects/code-health-skills
git add -A
git commit -m "chore: init code-health-skills repo with planning docs"
```

> All remaining tasks run with `cwd = /home/jakub/projects/code-health-skills`.

---

## Task 2: Package metadata, license, and docs

**Files:**
- Create: `package.json`, `LICENSE`, `README.md`, `AGENTS.md`

- [ ] **Step 1: Create `package.json`**

Create `package.json`:
```json
{
  "name": "code-health-skills",
  "version": "0.1.0",
  "description": "Deterministic, advisory code-health leaf skills (complexity, duplication, dead-code, structure, quality) and a code-health-audit-pipeline umbrella.",
  "license": "MIT",
  "bin": {
    "code-health-skills": "./bin/install-code-health-skills.js",
    "install-code-health-skills": "./bin/install-code-health-skills.js"
  },
  "scripts": {
    "check": "npm run check:vendored && npm run check:fixtures && npm run check:release",
    "check:vendored": "python3 scripts/check_vendored_common.py",
    "check:fixtures": "python3 scripts/check_skill_fixtures.py",
    "check:release": "python3 scripts/check_release.py",
    "pack:dry-run": "npm pack --dry-run"
  },
  "files": [
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "bin/",
    "scripts/",
    "shared/",
    "skills/",
    "!**/.git/**",
    "!**/__pycache__/**",
    "!**/*.pyc",
    "!**/*.pyo",
    "!**/.pytest_cache/**",
    "!**/.mypy_cache/**",
    "!**/.ruff_cache/**"
  ],
  "repository": {
    "type": "git",
    "url": "git+https://github.com/jc1122/code-health-skills.git"
  },
  "engines": {
    "node": ">=18"
  }
}
```

- [ ] **Step 2: Create `LICENSE`**

Run (reuse the MIT text from the reference package):
```bash
cp /home/jakub/projects/repo-audit-skills/LICENSE /home/jakub/projects/code-health-skills/LICENSE
```

- [ ] **Step 3: Create `README.md`**

Create `README.md`:
```markdown
# Code Health Skills

Standalone package of deterministic, advisory code-health skills.

Leaf skills (each independently runnable, never mutate source):

- `complexity-audit` — radon + lizard → SIMPLIFY / DECOMPOSE
- `duplication-audit` — jscpd / symilar → EXTRACT / MERGE
- `dead-code-audit` — vulture + ruff F-codes → DELETE
- `structure-audit` — grimp import graph → RESTRUCTURE
- `quality-audit` — ruff + ruff format + ty → LINT / FORMAT / TYPE

Umbrella:

- `code-health-audit-pipeline` — runs the leaves in parallel, merges and ranks
  findings, and emits a supervisor decision with exit codes 0/1/2.

Each skill emits findings to one shared schema. Skills are developed and released
here, installed once to a skills root, then run against any target repo via `--root`.

## Install

```bash
node bin/install-code-health-skills.js --dest /absolute/path/to/skills --force
```

Default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise
`~/.codex/skills`.

## Validation

```bash
npm run check
```

## Coexistence

This package installs alongside `repo-audit-skills` into the same skills root. Skill
names are disjoint and each package's installer touches only its own skills, so the
two never collide.
```

- [ ] **Step 4: Create `AGENTS.md`**

Create `AGENTS.md`:
```markdown
# Agent Start

Read `README.md` before broad repository scans. Source edits belong in this checkout;
installed copies live under the configured skills root.

`shared/health_common.py` is the source of truth for the leaf helper. Each leaf vendors
a byte-identical copy at `skills/<leaf>/scripts/health_common.py`. After editing the
source, re-sync the copies and run `npm run check` (the vendored-copy check will fail if
they drift).

For release work:

```bash
npm run check
npm run pack:dry-run
```

Do not edit installed copies under `~/.agents/skills` or `~/.codex/skills` directly.
```

- [ ] **Step 5: Commit**

```bash
git add package.json LICENSE README.md AGENTS.md
git commit -m "chore: add package metadata, license, and docs"
```

---

## Task 3: Shared finding helper (source of truth) — TDD

**Files:**
- Create: `shared/health_common.py`
- Test: `tests/test_health_common.py` (repo-level dev test)

- [ ] **Step 1: Write the failing test**

Create `tests/test_health_common.py`:
```python
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("health_common", ROOT / "shared" / "health_common.py")
hc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hc)


def make(**kw):
    base = dict(
        leaf="complexity", signal="DECOMPOSE", severity="high",
        path="pkg/a.py", line_start=10, line_end=40, symbol="f",
        metric_name="cyclomatic_complexity", metric_value=22.0, metric_threshold=10.0,
        evidence_tool="lizard", evidence_raw="f cc=22", confidence="high",
        suggested_action="Split f()",
    )
    base.update(kw)
    return hc.Finding(**base)


def test_stable_id_is_deterministic_and_short():
    f = make()
    assert f.stable_id() == make().stable_id()
    assert len(f.stable_id()) == 16


def test_stable_id_changes_with_identity_fields():
    assert make(symbol="f").stable_id() != make(symbol="g").stable_id()


def test_to_dict_shape():
    d = make().to_dict()
    assert d["id"] == make().stable_id()
    assert d["location"] == {"line_start": 10, "line_end": 40, "symbol": "f"}
    assert d["metric"] == {"name": "cyclomatic_complexity", "value": 22.0, "threshold": 10.0}
    assert d["evidence"] == {"tool": "lizard", "raw": "f cc=22"}


def test_sort_is_stable_by_path_line_signal_metric():
    a = make(path="pkg/a.py", line_start=5)
    b = make(path="pkg/a.py", line_start=1)
    c = make(path="pkg/b.py", line_start=1)
    assert hc.sort_findings([c, a, b]) == [b, a, c]


def test_write_findings_is_byte_stable(tmp_path):
    fs = [make(symbol="g"), make(symbol="f")]
    hc.write_findings(fs, tmp_path, "complexity")
    out = (tmp_path / "complexity_findings.json").read_bytes()
    hc.write_findings(list(reversed(fs)), tmp_path, "complexity")
    assert (tmp_path / "complexity_findings.json").read_bytes() == out
    data = json.loads(out)
    assert [d["location"]["symbol"] for d in data] == ["f", "g"]


def test_exit_code_constants():
    assert (hc.EXIT_CLEAN, hc.EXIT_FINDINGS, hc.EXIT_ERROR) == (0, 1, 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_health_common.py -v`
Expected: FAIL — `shared/health_common.py` does not exist (import error).

- [ ] **Step 3: Write the helper**

Create `shared/health_common.py`:
```python
"""Shared helpers for code-health leaf skills.

SOURCE OF TRUTH. This file is vendored (copied byte-for-byte) into each leaf at
``skills/<leaf>/scripts/health_common.py`` so every leaf is self-contained and
independently installable. ``scripts/check_vendored_common.py`` enforces that the
copies stay identical to this file.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SIGNALS = frozenset(
    {"SIMPLIFY", "DECOMPOSE", "EXTRACT", "MERGE", "DELETE", "RESTRUCTURE", "LINT", "FORMAT", "TYPE"}
)
SEVERITIES = ("info", "low", "medium", "high")
CONFIDENCES = ("low", "medium", "high")

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


@dataclasses.dataclass(frozen=True)
class Finding:
    leaf: str
    signal: str
    severity: str
    path: str
    line_start: int
    line_end: int
    symbol: str
    metric_name: str
    metric_value: float
    metric_threshold: float
    evidence_tool: str
    evidence_raw: str
    confidence: str
    suggested_action: str

    def stable_id(self) -> str:
        key = f"{self.leaf}|{self.path}|{self.symbol}|{self.metric_name}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.stable_id(),
            "leaf": self.leaf,
            "signal": self.signal,
            "severity": self.severity,
            "path": self.path,
            "location": {"line_start": self.line_start, "line_end": self.line_end, "symbol": self.symbol},
            "metric": {"name": self.metric_name, "value": self.metric_value, "threshold": self.metric_threshold},
            "evidence": {"tool": self.evidence_tool, "raw": self.evidence_raw},
            "confidence": self.confidence,
            "suggested_action": self.suggested_action,
        }


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.path, f.line_start, f.signal, f.metric_name))


def write_findings(findings: Iterable[Finding], out_dir: str | Path, leaf: str) -> list[dict[str, Any]]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = [f.to_dict() for f in sort_findings(findings)]
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    (out / f"{leaf}_findings.json").write_text(text, encoding="utf-8")
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_health_common.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add shared/health_common.py tests/test_health_common.py
git commit -m "feat: add shared finding helper (source of truth)"
```

---

## Task 4: Installer

**Files:**
- Create: `bin/install-code-health-skills.js`

- [ ] **Step 1: Create the installer**

Create `bin/install-code-health-skills.js` (adapted from the reference installer; `skills[]` lists only this package's skills — only `complexity-audit` exists now, later plans append):
```javascript
#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const root = path.resolve(__dirname, "..");
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const skills = [
  "complexity-audit",
];

function usage() {
  return [
    "Usage: install-code-health-skills [--dest DIR] [--force] [--dry-run] [--list] [--version]",
    "",
    "Installs code-health skills into $CODEX_HOME/skills or ~/.codex/skills by default.",
  ].join("\n");
}

function parseArgs(argv) {
  const args = { dest: null, force: false, dryRun: false, list: false, version: false, help: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--dest") {
      i += 1;
      if (i >= argv.length) throw new Error("--dest requires a value");
      args.dest = argv[i];
    } else if (arg === "--force") {
      args.force = true;
    } else if (arg === "--dry-run") {
      args.dryRun = true;
    } else if (arg === "--list") {
      args.list = true;
    } else if (arg === "--version") {
      args.version = true;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function defaultDest() {
  if (process.env.CODEX_HOME) return path.join(process.env.CODEX_HOME, "skills");
  return path.join(os.homedir(), ".codex", "skills");
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === "__pycache__" || entry.name === ".pytest_cache" || entry.name === ".mypy_cache" || entry.name === ".ruff_cache") {
      continue;
    }
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(srcPath, destPath);
      fs.chmodSync(destPath, fs.statSync(srcPath).mode);
    }
  }
}

function installSkill(skill, destRoot, force, dryRun) {
  const src = path.join(root, "skills", skill);
  const dest = path.join(destRoot, skill);
  if (!fs.existsSync(path.join(src, "SKILL.md"))) throw new Error(`Missing SKILL.md for ${skill}`);
  const exists = fs.existsSync(dest);
  if (dryRun) {
    console.log(`${exists ? "would replace" : "would install"} ${skill} -> ${dest}`);
    return;
  }
  if (exists && !force) throw new Error(`${dest} already exists; pass --force to replace it`);
  if (exists) fs.rmSync(dest, { recursive: true, force: true });
  copyDir(src, dest);
  console.log(`installed ${skill} -> ${dest}`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { console.log(usage()); return 0; }
  if (args.version) { console.log(packageJson.version); return 0; }
  if (args.list) {
    console.log(JSON.stringify({ package: packageJson.name, version: packageJson.version, skills }, null, 2));
    return 0;
  }
  const dest = path.resolve(args.dest || defaultDest());
  if (!args.dryRun) fs.mkdirSync(dest, { recursive: true });
  for (const skill of skills) installSkill(skill, dest, args.force, args.dryRun);
  return 0;
}

try {
  process.exitCode = main();
} catch (err) {
  console.error(err.message || String(err));
  process.exitCode = 1;
}
```

- [ ] **Step 2: Verify the installer answers metadata commands**

Run:
```bash
node bin/install-code-health-skills.js --version
node bin/install-code-health-skills.js --list
```
Expected: prints `0.1.0`, then JSON with `"skills": ["complexity-audit"]`.

- [ ] **Step 3: Commit**

```bash
git add bin/install-code-health-skills.js
git commit -m "feat: add package installer"
```

---

## Task 5: Vendored-copy sync check — TDD

**Files:**
- Create: `scripts/check_vendored_common.py`
- Test: `tests/test_check_vendored_common.py`

This gate fails if any leaf's vendored `health_common.py` drifts from `shared/health_common.py`. With only the source present (no leaves vendored yet), it passes vacuously; it starts protecting copies in Task 7+.

- [ ] **Step 1: Write the failing test**

Create `tests/test_check_vendored_common.py`:
```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run():
    return subprocess.run(
        [sys.executable, "scripts/check_vendored_common.py"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


def test_passes_when_no_copies_or_copies_match():
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_check_vendored_common.py -v`
Expected: FAIL — `scripts/check_vendored_common.py` does not exist.

- [ ] **Step 3: Write the checker**

Create `scripts/check_vendored_common.py`:
```python
#!/usr/bin/env python3
"""Assert each leaf's vendored health_common.py matches the shared source of truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "shared" / "health_common.py"
SKILLS = ROOT / "skills"


def main() -> int:
    if not SOURCE.exists():
        print(json.dumps({"status": "fail", "defects": ["shared/health_common.py missing"]}, indent=2))
        return 1
    source_bytes = SOURCE.read_bytes()
    defects: list[str] = []
    copies = sorted(SKILLS.glob("*/scripts/health_common.py")) if SKILLS.exists() else []
    for copy in copies:
        if copy.read_bytes() != source_bytes:
            defects.append(f"vendored copy drifted: {copy.relative_to(ROOT)}")
    if defects:
        print(json.dumps({"status": "fail", "defects": defects}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "checked": [str(c.relative_to(ROOT)) for c in copies]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_check_vendored_common.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vendored_common.py tests/test_check_vendored_common.py
git commit -m "feat: add vendored-copy sync check"
```

---

## Task 6: Release and fixtures gates

**Files:**
- Create: `scripts/check_release.py`, `scripts/check_skill_fixtures.py`

Both are registry-driven so later plans only append one entry per new skill.

- [ ] **Step 1: Create `scripts/check_release.py`**

Create `scripts/check_release.py`:
```python
#!/usr/bin/env python3
"""Release checks for the code-health-skills package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Append one entry per skill as later plans land. Name on left == skill dir == SKILL.md name.
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} does not start with YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError(f"{path} has unterminated YAML frontmatter")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        values[key.strip()] = raw.strip().strip('"')
    return values


def check_package(defects: list[str]) -> str:
    package_path = ROOT / "package.json"
    if not package_path.exists():
        defects.append("package.json missing")
        return "0.0.0"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    version = str(package.get("version", ""))
    if not SEMVER_RE.match(version):
        defects.append(f"package.json version is not semver: {version!r}")
    if package.get("name") != "code-health-skills":
        defects.append("package.json name must be code-health-skills")
    for path in ["bin/install-code-health-skills.js", "scripts/check_release.py",
                 "scripts/check_skill_fixtures.py", "scripts/check_vendored_common.py",
                 "shared/health_common.py"]:
        if not (ROOT / path).exists():
            defects.append(f"required release file missing: {path}")
    return version


def check_skills(version: str, defects: list[str]) -> None:
    for skill_dir, expected_name in REQUIRED_SKILLS.items():
        skill_root = ROOT / "skills" / skill_dir
        skill_md = skill_root / "SKILL.md"
        if not skill_md.exists():
            defects.append(f"missing SKILL.md for {skill_dir}")
            continue
        try:
            meta = frontmatter(skill_md)
        except ValueError as exc:
            defects.append(str(exc))
            continue
        if meta.get("name") != expected_name:
            defects.append(f"{skill_dir}/SKILL.md name is {meta.get('name')!r}, expected {expected_name!r}")
        if meta.get("version") != version:
            defects.append(f"{skill_dir}/SKILL.md version is {meta.get('version')!r}, expected {version!r}")
        for rel_path in REQUIRED_SCRIPTS[skill_dir]:
            if not (skill_root / rel_path).exists():
                defects.append(f"missing script for {skill_dir}: {rel_path}")


def check_installer(defects: list[str]) -> None:
    checks = [
        ["node", "bin/install-code-health-skills.js", "--version"],
        ["node", "bin/install-code-health-skills.js", "--list"],
        ["node", "bin/install-code-health-skills.js", "--dry-run", "--dest", "/tmp/code-health-skills-release-check", "--force"],
    ]
    for cmd in checks:
        result = run(cmd)
        if result.returncode != 0:
            defects.append(f"{' '.join(cmd)} failed: {result.stderr.strip() or result.stdout.strip()}")


def check_git_clean(defects: list[str]) -> None:
    result = run(["git", "status", "--short"])
    if result.returncode != 0:
        defects.append(f"git status failed: {result.stderr.strip()}")
        return
    if result.stdout.strip():
        defects.append("git tree is not clean")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true", help="Require a clean git worktree.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    defects: list[str] = []
    version = check_package(defects)
    check_skills(version, defects)
    check_installer(defects)
    if args.require_clean:
        check_git_clean(defects)
    if defects:
        print(json.dumps({"status": "fail", "defects": defects}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "version": version, "skills": sorted(REQUIRED_SKILLS)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create `scripts/check_skill_fixtures.py`**

Create `scripts/check_skill_fixtures.py`:
```python
#!/usr/bin/env python3
"""Deterministic smoke checks: every leaf script answers --help."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Append one command per skill as later plans land.
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
]


def main() -> int:
    failures: list[dict[str, str]] = []
    for cmd in HELP_COMMANDS:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            failures.append({"command": " ".join(cmd), "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:]})
    if failures:
        print(json.dumps({"status": "fail", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "commands": [" ".join(cmd) for cmd in HELP_COMMANDS]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Verify the gates fail cleanly before the leaf exists**

Run: `python3 scripts/check_release.py`
Expected: `"status": "fail"` listing `missing SKILL.md for complexity-audit` (the leaf is built in Tasks 7–11). This is expected at this point; do not commit a passing gate yet.

- [ ] **Step 4: Commit**

```bash
git add scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "feat: add release and fixtures gates"
```

---

## Task 7: Scaffold the complexity-audit skill + vendor the helper

**Files:**
- Create: `skills/complexity-audit/SKILL.md`, `skills/complexity-audit/LICENSE`, `skills/complexity-audit/pyproject.toml`, `skills/complexity-audit/references/rubric.md`
- Create (vendored): `skills/complexity-audit/scripts/health_common.py`

- [ ] **Step 1: Vendor the shared helper**

Run:
```bash
mkdir -p skills/complexity-audit/scripts skills/complexity-audit/references skills/complexity-audit/tests/fixtures
cp shared/health_common.py skills/complexity-audit/scripts/health_common.py
cp LICENSE skills/complexity-audit/LICENSE
```
Expected: `skills/complexity-audit/scripts/health_common.py` is byte-identical to `shared/health_common.py`.

- [ ] **Step 2: Create `pyproject.toml`**

Create `skills/complexity-audit/pyproject.toml`:
```toml
[project]
name = "complexity-audit"
version = "0.1.0"
description = "Deterministic complexity/maintainability audit leaf (radon + lizard)."
requires-python = ">=3.10"
dependencies = [
    "radon>=6.0",
    "lizard>=1.17",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```

- [ ] **Step 3: Create `references/rubric.md`**

Create `skills/complexity-audit/references/rubric.md`:
```markdown
# complexity-audit Rubric

Per-function metrics come from `lizard`; per-module maintainability from `radon mi`.

| Metric | Source | Threshold | Severity | Signal |
|---|---|---|---|---|
| Cyclomatic complexity | lizard | > 10 | medium | DECOMPOSE |
| Cyclomatic complexity | lizard | > 20 | high | DECOMPOSE |
| Function length (NLOC) | lizard | > 50 | medium | DECOMPOSE |
| Parameter count | lizard | > 5 | low | SIMPLIFY |
| Maintainability index | radon mi | < 65 | low | SIMPLIFY |
| Maintainability index | radon mi | < 50 | medium | SIMPLIFY |

All thresholds overridable via `--config` (JSON). Confidence is always `high` (the
metrics are deterministic). The leaf never mutates source.
```

- [ ] **Step 4: Create `SKILL.md`**

Create `skills/complexity-audit/SKILL.md`:
```markdown
---
name: complexity-audit
version: 0.1.0
description: >
  Deterministic, advisory complexity and maintainability audit for Python. Uses
  lizard (per-function cyclomatic complexity, length, parameters) and radon mi
  (per-module maintainability index) to emit SIMPLIFY / DECOMPOSE findings to the
  shared code-health finding schema. Never mutates source.
---

# complexity-audit

## Overview

A code-health leaf skill. It reports functions that are too complex or too long and
modules with low maintainability, as advisory findings. It does not refactor anything.

## Quick Start

```bash
python3 scripts/complexity_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/complexity
```

## Output

- `complexity_findings.json` — sorted list of findings (shared schema).
- `complexity_report.md` — human-readable summary grouped by signal.

## Exit Codes

- `0` — clean (no findings).
- `1` — advisory findings present.
- `2` — tool/config error (e.g. lizard or radon not installed).

## Tools and Thresholds

See `references/rubric.md`. Override thresholds with `--config thresholds.json`.

## Notes

- `--source-prefix` filters to product code (repeatable).
- Findings are deterministic: identical input yields byte-identical
  `complexity_findings.json`.
```

- [ ] **Step 5: Commit**

```bash
git add skills/complexity-audit
git commit -m "feat: scaffold complexity-audit skill (vendored helper, docs, rubric)"
```

---

## Task 8: complexity-audit test fixtures

**Files:**
- Create: `skills/complexity-audit/tests/fixtures/clean/pkg/simple.py`
- Create: `skills/complexity-audit/tests/fixtures/dirty/pkg/complex.py`
- Create: `skills/complexity-audit/tests/helpers.py`

- [ ] **Step 1: Create the clean fixture**

Create `skills/complexity-audit/tests/fixtures/clean/pkg/simple.py`:
```python
def add(a, b):
    return a + b


def greet(name):
    return f"hello {name}"
```

- [ ] **Step 2: Create the dirty fixture (one deeply nested, high-CC function)**

Create `skills/complexity-audit/tests/fixtures/dirty/pkg/complex.py`:
```python
def tangled(a, b, c, d, e, f):
    total = 0
    for i in range(a):
        if i % 2 == 0:
            if b > 0:
                total += 1
            elif c > 0:
                total += 2
            else:
                total += 3
        elif i % 3 == 0:
            if d > 0:
                total += 4
            elif e > 0:
                total += 5
            else:
                total += 6
        else:
            if f > 0:
                total += 7
            else:
                total += 8
    while total > 100:
        total -= 10
        if total % 7 == 0:
            total -= 1
    return total
```

`tangled` has cyclomatic complexity ≥ 14 (> 10 → DECOMPOSE) and 6 parameters (> 5 →
SIMPLIFY), giving two findings.

- [ ] **Step 3: Create `helpers.py`**

Create `skills/complexity-audit/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "complexity_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("complexity_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "complexity_findings.json").read_text())
```

- [ ] **Step 4: Commit**

```bash
git add skills/complexity-audit/tests
git commit -m "test: add complexity-audit fixtures and helpers"
```

---

## Task 9: complexity-audit core logic — TDD (analysis functions)

**Files:**
- Create: `skills/complexity-audit/scripts/complexity_audit.py`
- Test: `skills/complexity-audit/tests/test_complexity_findings.py`

This task builds the pure analysis functions (no CLI yet). Requires `lizard` and
`radon` installed: `pip install lizard radon pytest`.

- [ ] **Step 1: Write the failing test**

Create `skills/complexity-audit/tests/test_complexity_findings.py`:
```python
from pathlib import Path

from helpers import FIXTURES, load_module

ca = load_module()
DEFAULTS = ca.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = ca.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_flags_high_complexity_and_params():
    findings = ca.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    signals = sorted({f.signal for f in findings})
    assert "DECOMPOSE" in signals  # high cyclomatic complexity
    assert "SIMPLIFY" in signals   # too many parameters
    cc = [f for f in findings if f.metric_name == "cyclomatic_complexity"]
    assert cc and cc[0].metric_value > 10
    assert cc[0].symbol == "tangled"
    assert cc[0].confidence == "high"


def test_thresholds_are_configurable():
    relaxed = dict(DEFAULTS, cc_medium=999, cc_high=999, max_params=999, nloc_medium=9999)
    findings = ca.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=relaxed)
    # Only the maintainability-index check could still fire; complexity/params suppressed.
    assert all(f.metric_name != "cyclomatic_complexity" for f in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/complexity-audit && python3 -m pytest tests/test_complexity_findings.py -v
```
Expected: FAIL — `complexity_audit.py` does not exist.

- [ ] **Step 3: Write the analysis module**

Create `skills/complexity-audit/scripts/complexity_audit.py`:
```python
#!/usr/bin/env python3
"""complexity-audit leaf: lizard (per-function) + radon mi (per-module) → findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "complexity"

DEFAULT_THRESHOLDS = {
    "cc_medium": 10,
    "cc_high": 20,
    "nloc_medium": 50,
    "max_params": 5,
    "mi_low": 65,
    "mi_medium": 50,
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    kept = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in source_prefixes):
            kept.append(p)
    return kept


def _lizard_findings(root: Path, files: list[Path], thresholds: dict) -> list[hc.Finding]:
    try:
        import lizard
    except ImportError as exc:  # pragma: no cover - exercised via missing-tool test
        raise ToolError("lizard is not installed") from exc
    findings: list[hc.Finding] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        analysis = lizard.analyze_file(str(path))
        for fn in analysis.function_list:
            cc = fn.cyclomatic_complexity
            if cc > thresholds["cc_medium"]:
                sev = "high" if cc > thresholds["cc_high"] else "medium"
                findings.append(hc.Finding(
                    leaf=LEAF, signal="DECOMPOSE", severity=sev, path=rel,
                    line_start=fn.start_line, line_end=fn.end_line, symbol=fn.name,
                    metric_name="cyclomatic_complexity", metric_value=float(cc),
                    metric_threshold=float(thresholds["cc_medium"]),
                    evidence_tool="lizard", evidence_raw=f"{fn.long_name} CCN={cc}",
                    confidence="high",
                    suggested_action=f"Split {fn.name}() — complexity {cc} exceeds {thresholds['cc_medium']}",
                ))
            if fn.nloc > thresholds["nloc_medium"]:
                findings.append(hc.Finding(
                    leaf=LEAF, signal="DECOMPOSE", severity="medium", path=rel,
                    line_start=fn.start_line, line_end=fn.end_line, symbol=fn.name,
                    metric_name="function_nloc", metric_value=float(fn.nloc),
                    metric_threshold=float(thresholds["nloc_medium"]),
                    evidence_tool="lizard", evidence_raw=f"{fn.long_name} NLOC={fn.nloc}",
                    confidence="high",
                    suggested_action=f"Shorten {fn.name}() — {fn.nloc} lines exceeds {thresholds['nloc_medium']}",
                ))
            if fn.parameter_count > thresholds["max_params"]:
                findings.append(hc.Finding(
                    leaf=LEAF, signal="SIMPLIFY", severity="low", path=rel,
                    line_start=fn.start_line, line_end=fn.end_line, symbol=fn.name,
                    metric_name="parameter_count", metric_value=float(fn.parameter_count),
                    metric_threshold=float(thresholds["max_params"]),
                    evidence_tool="lizard", evidence_raw=f"{fn.long_name} params={fn.parameter_count}",
                    confidence="high",
                    suggested_action=f"Reduce parameters of {fn.name}() — {fn.parameter_count} exceeds {thresholds['max_params']}",
                ))
    return findings


def _radon_mi_findings(root: Path, files: list[Path], thresholds: dict) -> list[hc.Finding]:
    if not files:
        return []
    cmd = ["radon", "mi", "-j", *[str(p) for p in files]]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("radon is not installed") from exc
    if proc.returncode != 0:
        raise ToolError(f"radon mi failed: {proc.stderr.strip() or proc.stdout.strip()}")
    data = json.loads(proc.stdout or "{}")
    findings: list[hc.Finding] = []
    for fname, info in data.items():
        if not isinstance(info, dict) or "mi" not in info:
            continue
        mi = float(info["mi"])
        if mi >= thresholds["mi_low"]:
            continue
        sev = "medium" if mi < thresholds["mi_medium"] else "low"
        rel = Path(fname).resolve().relative_to(root.resolve()).as_posix()
        findings.append(hc.Finding(
            leaf=LEAF, signal="SIMPLIFY", severity=sev, path=rel,
            line_start=1, line_end=1, symbol="<module>",
            metric_name="maintainability_index", metric_value=mi,
            metric_threshold=float(thresholds["mi_low"]),
            evidence_tool="radon", evidence_raw=f"MI={mi:.1f} rank={info.get('rank', '?')}",
            confidence="high",
            suggested_action=f"Improve maintainability of {rel} — MI {mi:.1f} below {thresholds['mi_low']}",
        ))
    return findings


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    findings = _lizard_findings(root, files, thresholds)
    findings += _radon_mi_findings(root, files, thresholds)
    return hc.sort_findings(findings)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/complexity-audit && python3 -m pytest tests/test_complexity_findings.py -v
```
Expected: PASS (3 passed). If `lizard`/`radon` are missing, run `pip install lizard radon pytest` first.

- [ ] **Step 5: Commit**

```bash
git add skills/complexity-audit/scripts/complexity_audit.py skills/complexity-audit/tests/test_complexity_findings.py
git commit -m "feat: add complexity-audit analysis (lizard + radon mi)"
```

---

## Task 10: complexity-audit CLI, report, exit codes — TDD

**Files:**
- Modify: `skills/complexity-audit/scripts/complexity_audit.py` (append CLI + report + `main`)
- Test: `skills/complexity-audit/tests/test_complexity_cli.py`

- [ ] **Step 1: Write the failing test**

Create `skills/complexity-audit/tests/test_complexity_cli.py`:
```python
from helpers import FIXTURES, read_findings, run_cli


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--source-prefix" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli("--root", str(FIXTURES / "clean"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_dirty_exits_one_with_findings(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert any(d["metric"]["name"] == "cyclomatic_complexity" for d in data)
    assert (tmp_path / "complexity_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "complexity_findings.json").read_bytes() == (b / "complexity_findings.json").read_bytes()


def test_missing_tool_exits_two(tmp_path, monkeypatch):
    # Force lizard import to fail by pointing PATH/sys.path away is hard cross-process;
    # instead invoke with an env flag the script honors for testing.
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--simulate-missing-tool")
    assert result.returncode == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/complexity-audit && python3 -m pytest tests/test_complexity_cli.py -v
```
Expected: FAIL — no `main`/CLI yet (`--help` returns nonzero or arg errors).

- [ ] **Step 3: Append CLI, report, and `main` to `complexity_audit.py`**

Append to `skills/complexity-audit/scripts/complexity_audit.py`:
```python
def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# complexity-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(
                f"- `{f.path}:{f.line_start}` {f.symbol} — {f.metric_name}="
                f"{f.metric_value:g} (>{f.metric_threshold:g}) [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic complexity/maintainability audit (advisory).")
    parser.add_argument("--root", required=False, help="Target repository root.")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) (relative to --root) to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[], help="Unused placeholder for prefix excludes.")
    parser.add_argument("--out-dir", required=False, help="Directory for findings + report.")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json", help="Stdout summary format.")
    parser.add_argument("--simulate-missing-tool", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        if args.simulate_missing_tool:
            raise ToolError("simulated missing tool")
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "complexity_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/complexity-audit && python3 -m pytest tests/ -v
```
Expected: PASS (all complexity-audit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/complexity-audit/scripts/complexity_audit.py skills/complexity-audit/tests/test_complexity_cli.py
git commit -m "feat: add complexity-audit CLI, report, and exit codes"
```

---

## Task 11: Green the package gate

**Files:**
- (No new files; verifies Tasks 2–10 together.)

- [ ] **Step 1: Run the vendored-copy check**

Run: `python3 scripts/check_vendored_common.py`
Expected: `"status": "pass"`, `checked` lists `skills/complexity-audit/scripts/health_common.py`.

- [ ] **Step 2: Run the fixtures (--help) gate**

Run: `python3 scripts/check_skill_fixtures.py`
Expected: `"status": "pass"`.

- [ ] **Step 3: Run the release gate**

Run: `python3 scripts/check_release.py`
Expected: `"status": "pass"`, `skills` lists `complexity-audit`.

- [ ] **Step 4: Run the full check via npm**

Run: `npm run check`
Expected: all three checks pass (vendored, fixtures, release).

- [ ] **Step 5: Verify a real install round-trips**

Run:
```bash
node bin/install-code-health-skills.js --dry-run --dest /tmp/che-install --force
node bin/install-code-health-skills.js --dest /tmp/che-install --force
python3 /tmp/che-install/complexity-audit/scripts/complexity_audit.py --help
```
Expected: dry-run prints `would install complexity-audit`, real install prints `installed complexity-audit`, and `--help` prints usage.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: green the package gate with complexity-audit"
```

---

## Self-Review (completed during planning)

**Spec coverage (this plan's slice):**
- §2 layout — Tasks 1, 2, 7 create the repo, machinery, and first leaf. ✔
- §3 shared finding schema + leaf contract — Task 3 (`health_common.py`), Tasks 9–10 (CLI contract, exit codes). ✔
- §4 complexity-audit (lizard + radon mi, thresholds, signals) — Tasks 7–10. ✔
- §7 release/install + coexistence (own machinery, vendored-copy rule) — Tasks 2, 4, 5, 6, 11. ✔
- §3 determinism guarantee — Task 9/10 byte-stable tests + `check_vendored_common.py`. ✔
- §11 advisory-only (no mutation) — analysis functions only read; asserted by behavior. ✔
- Deferred by design (later plans): leaves 2–5, the umbrella, the shared `finding-schema.json` JSON file and `rule-ownership.md` (land with the umbrella in Plan 6, which is where they are first consumed). Noted so the gap is intentional, not an omission.

**Placeholder scan:** none — every code/test step contains complete content. The
`--simulate-missing-tool` hidden flag is a deliberate, documented test seam, not a TODO.

**Type consistency:** `Finding` fields and `hc.write_findings`/`hc.sort_findings`/
`hc.EXIT_*` names are identical across Tasks 3, 9, 10. `analyze_tree(root, source_prefixes,
thresholds)` and `DEFAULT_THRESHOLDS` keys (`cc_medium`, `cc_high`, `nloc_medium`,
`max_params`, `mi_low`, `mi_medium`) match between the implementation and both test files.

---

## Notes for Plans 2–6

- Each later leaf repeats Tasks 7–11's shape: vendor `health_common.py`, scaffold
  SKILL/pyproject/rubric, fixtures + helpers, TDD analysis, TDD CLI, then append one
  entry each to the installer `skills[]`, `check_release.py` `REQUIRED_SKILLS`/
  `REQUIRED_SCRIPTS`, and `check_skill_fixtures.py` `HELP_COMMANDS`, and bump the package
  version in lockstep across all `SKILL.md` files.
- Plan 6 adds `code-health-audit-pipeline` (with `leaf_registry.json`,
  `finding-schema.json`, `rule-ownership.md`), the parallel runner, merge/dedupe/rank,
  and the supervisor decision + 0/1/2 exit codes.
```
