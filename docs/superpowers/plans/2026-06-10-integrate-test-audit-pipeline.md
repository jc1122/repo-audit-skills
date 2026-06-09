# Integrate the test-audit pipeline into `repo-audit-skills` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift-and-shift the three test-audit skills into the code-health package, rename the package to `repo-audit-skills`, register the new skills in the existing release gates, then take over the directory + GitHub identity and decommission the old placeholder repo.

**Architecture:** Pure migration + configuration. No code in the migrated skills changes; we copy three skill directories in, then update the package's installer and three gate scripts to know about them, then rename the package identity. Because this is migration rather than feature work, each task's "test" is a **gate/verification command** (`npm run check`, installer round-trip, `--help` smoke) run before and after the change — there are no new unit tests to write. The migrated skills ship no `tests/` or `pyproject.toml`, so their verification is functional smoke only.

**Tech Stack:** Node installer (`bin/`), Python gate scripts (`scripts/check_*.py`), npm `package.json`, git.

**Source of the migrated skills:** `/home/jakub/projects/repo-audit-skills/skills/{test-audit-pipeline,test-quality-assurance,test-redundancy-triage}` (exact file lists in Task 1).

**Spec:** `docs/superpowers/specs/2026-06-10-integrate-test-audit-pipeline-design.md`

> **Working directory:** Run every command from the package root `/home/jakub/projects/code-health-skills` (it is renamed to `repo-audit-skills` only in Task 4). Use absolute paths for anything touching the *old* repo so a reset shell cwd can't bite you.

---

## File map

**Copied in (Task 1), unchanged:**
- `skills/test-audit-pipeline/` ← `agents/openai.yaml`, `scripts/audit_pipeline.py`, `SKILL.md`
- `skills/test-quality-assurance/` ← `agents/openai.yaml`, `references/{question-bank,rubric,sample-report}.md`, `scripts/audit_test_quality.py`, `scripts/.gitignore`, `SKILL.md`
- `skills/test-redundancy-triage/` ← `agents/openai.yaml`, `LICENSE`, `references/decision-rubric.md`, `scripts/triage_redundancy.py`, `SKILL.md`

**Modified:**
- `package.json` — name, description, `bin`, repository URL (Task 2)
- `bin/install-code-health-skills.js` → `bin/install-repo-audit-skills.js` — rename, usage text (Task 2), `skills[]` (Task 3)
- `scripts/check_release.py` — name/installer-path refs (Task 2), `REQUIRED_SKILLS`/`REQUIRED_SCRIPTS` (Task 3)
- `scripts/check_skill_fixtures.py` — `HELP_COMMANDS` (Task 3)
- `README.md` — title/name/install/coexistence (Task 2), skill list (Task 3)

**Not touched:** `scripts/check_vendored_common.py` (auto-scopes via glob), `shared/health_common.py`, all existing code-health leaves, migrated skills' internals.

---

## Task 1: Copy the three test-audit skill directories in (additive)

**Files:**
- Create: `skills/test-audit-pipeline/**`, `skills/test-quality-assurance/**`, `skills/test-redundancy-triage/**`

- [ ] **Step 1: Confirm the current green baseline**

Run:
```bash
cd /home/jakub/projects/code-health-skills && npm run check
```
Expected: all three checks `"status": "pass"`; `check:release` lists exactly the six existing skills.

- [ ] **Step 2: Copy the three directories from the old repo**

Run:
```bash
cd /home/jakub/projects/code-health-skills
for s in test-audit-pipeline test-quality-assurance test-redundancy-triage; do
  cp -r "/home/jakub/projects/repo-audit-skills/skills/$s" "skills/$s"
done
# strip any stray caches that should never be committed
find skills/test-audit-pipeline skills/test-quality-assurance skills/test-redundancy-triage \
  -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) \
  -prune -exec rm -rf {} +
```

- [ ] **Step 3: Verify the copied files landed exactly**

Run:
```bash
find skills/test-audit-pipeline skills/test-quality-assurance skills/test-redundancy-triage -type f | sort
```
Expected (15 files, in `sort` order):
```
skills/test-audit-pipeline/SKILL.md
skills/test-audit-pipeline/agents/openai.yaml
skills/test-audit-pipeline/scripts/audit_pipeline.py
skills/test-quality-assurance/SKILL.md
skills/test-quality-assurance/agents/openai.yaml
skills/test-quality-assurance/references/question-bank.md
skills/test-quality-assurance/references/rubric.md
skills/test-quality-assurance/references/sample-report.md
skills/test-quality-assurance/scripts/.gitignore
skills/test-quality-assurance/scripts/audit_test_quality.py
skills/test-redundancy-triage/LICENSE
skills/test-redundancy-triage/SKILL.md
skills/test-redundancy-triage/agents/openai.yaml
skills/test-redundancy-triage/references/decision-rubric.md
skills/test-redundancy-triage/scripts/triage_redundancy.py
```

- [ ] **Step 4: Smoke the three scripts answer `--help` from the new location**

Run:
```bash
for s in test-audit-pipeline/scripts/audit_pipeline.py \
         test-quality-assurance/scripts/audit_test_quality.py \
         test-redundancy-triage/scripts/triage_redundancy.py; do
  python3 "skills/$s" --help >/dev/null && echo "OK $s" || echo "FAIL $s"
done
```
Expected: three `OK` lines.

- [ ] **Step 5: Verify the gates are still green and unchanged**

Run: `npm run check`
Expected: all pass; `check:release` still lists **only the six** existing skills (the copy is additive — the new dirs are present but not yet registered, and `check_vendored_common` ignores them because they have no `scripts/health_common.py`).

- [ ] **Step 6: Commit**

```bash
git add skills/test-audit-pipeline skills/test-quality-assurance skills/test-redundancy-triage
git commit -m "chore: vendor in test-audit pipeline skills (pre-registration)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Rename the package identity to `repo-audit-skills`

All edits in this task must be applied together before the gate is run (the release gate cross-checks the package name against the installer path). Nothing here registers the new skills yet — that is Task 3.

**Files:**
- Rename: `bin/install-code-health-skills.js` → `bin/install-repo-audit-skills.js`
- Modify: `package.json`, `bin/install-repo-audit-skills.js`, `scripts/check_release.py`, `README.md`

- [ ] **Step 1: Rename the installer file (preserve git history)**

Run:
```bash
git mv bin/install-code-health-skills.js bin/install-repo-audit-skills.js
```

- [ ] **Step 2: Update `package.json` identity**

In `package.json`, replace lines 2, 4, 6-9, and 35.

Name (line 2):
```json
  "name": "repo-audit-skills",
```
Description (line 4):
```json
  "description": "Deterministic, advisory repo-audit skills: a code-health family (complexity, duplication, dead-code, structure, quality) with the code-health-audit-pipeline umbrella, plus a test-audit family (test-quality-assurance, test-redundancy-triage) with the test-audit-pipeline umbrella.",
```
`bin` block (lines 6-9):
```json
  "bin": {
    "repo-audit-skills": "./bin/install-repo-audit-skills.js",
    "install-repo-audit-skills": "./bin/install-repo-audit-skills.js"
  },
```
Repository URL (line 35):
```json
    "url": "git+https://github.com/jc1122/repo-audit-skills.git"
```

- [ ] **Step 3: Update the installer's usage text**

In `bin/install-repo-audit-skills.js`, replace the `usage()` body (lines 19-25):
```javascript
function usage() {
  return [
    "Usage: install-repo-audit-skills [--dest DIR] [--force] [--dry-run] [--list] [--version]",
    "",
    "Installs repo-audit skills into $CODEX_HOME/skills or ~/.codex/skills by default.",
  ].join("\n");
}
```

- [ ] **Step 4: Update `scripts/check_release.py` name + installer-path references**

In `scripts/check_release.py`:

Line 64-65 (name assertion):
```python
    if package.get("name") != "repo-audit-skills":
        defects.append("package.json name must be repo-audit-skills")
```
Lines 66-68 (required release files list) — change the installer filename:
```python
    for path in ["bin/install-repo-audit-skills.js", "scripts/check_release.py",
                 "scripts/check_skill_fixtures.py", "scripts/check_vendored_common.py",
                 "shared/health_common.py"]:
```
Lines 96-100 (`check_installer` commands) — change the three installer paths and the temp dest:
```python
    checks = [
        ["node", "bin/install-repo-audit-skills.js", "--version"],
        ["node", "bin/install-repo-audit-skills.js", "--list"],
        ["node", "bin/install-repo-audit-skills.js", "--dry-run", "--dest", "/tmp/repo-audit-skills-release-check", "--force"],
    ]
```

- [ ] **Step 5: Update `README.md` (rename + drop the now-false coexistence note)**

Replace the title (line 1):
```markdown
# Repo Audit Skills
```
Replace the install command (line 24):
```markdown
node bin/install-repo-audit-skills.js --dest /absolute/path/to/skills --force
```
Delete the entire `## Coexistence` section (lines 36-40 inclusive) — after the merge this package *is* `repo-audit-skills`, so a note about coexisting with it is incorrect. (The skill list is updated in Task 3.)

- [ ] **Step 6: Verify the gates are green under the new identity**

Run: `npm run check`
Expected: all pass; `check:release` prints `"version": "0.1.0"` and still the six skills. The release check now asserts `name == repo-audit-skills` and shells out to `bin/install-repo-audit-skills.js` — both must succeed.

- [ ] **Step 7: Commit**

```bash
git add package.json bin/install-repo-audit-skills.js scripts/check_release.py README.md
git commit -m "refactor: rename package identity to repo-audit-skills

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Register the three migrated skills in the gates

**Files:**
- Modify: `bin/install-repo-audit-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`, `README.md`

- [ ] **Step 1: Add the three skills to the installer's `skills` array**

In `bin/install-repo-audit-skills.js`, replace the `skills` array (originally lines 10-17):
```javascript
const skills = [
  "complexity-audit",
  "duplication-audit",
  "dead-code-audit",
  "structure-audit",
  "quality-audit",
  "code-health-audit-pipeline",
  "test-audit-pipeline",
  "test-quality-assurance",
  "test-redundancy-triage",
];
```

- [ ] **Step 2: Add the three skills to `check_release.py`**

In `scripts/check_release.py`, extend `REQUIRED_SKILLS` (lines 16-23) and `REQUIRED_SCRIPTS` (lines 24-31):
```python
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
    "dead-code-audit": "dead-code-audit",
    "structure-audit": "structure-audit",
    "quality-audit": "quality-audit",
    "code-health-audit-pipeline": "code-health-audit-pipeline",
    "test-audit-pipeline": "test-audit-pipeline",
    "test-quality-assurance": "test-quality-assurance",
    "test-redundancy-triage": "test-redundancy-triage",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
    "structure-audit": ["scripts/structure_audit.py"],
    "quality-audit": ["scripts/quality_audit.py"],
    "code-health-audit-pipeline": ["scripts/code_health_pipeline.py"],
    "test-audit-pipeline": ["scripts/audit_pipeline.py"],
    "test-quality-assurance": ["scripts/audit_test_quality.py"],
    "test-redundancy-triage": ["scripts/triage_redundancy.py"],
}
```

- [ ] **Step 3: Add the three `--help` smokes to `check_skill_fixtures.py`**

In `scripts/check_skill_fixtures.py`, extend `HELP_COMMANDS` (lines 14-21):
```python
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
    ["python3", "skills/dead-code-audit/scripts/dead_code_audit.py", "--help"],
    ["python3", "skills/structure-audit/scripts/structure_audit.py", "--help"],
    ["python3", "skills/quality-audit/scripts/quality_audit.py", "--help"],
    ["python3", "skills/code-health-audit-pipeline/scripts/code_health_pipeline.py", "--help"],
    ["python3", "skills/test-audit-pipeline/scripts/audit_pipeline.py", "--help"],
    ["python3", "skills/test-quality-assurance/scripts/audit_test_quality.py", "--help"],
    ["python3", "skills/test-redundancy-triage/scripts/triage_redundancy.py", "--help"],
]
```

- [ ] **Step 4: Update the README skill list to show both families**

In `README.md`, replace the `Umbrella:` block (lines 13-16) with the following, so both umbrellas and the test-audit family are listed:
```markdown
Umbrellas:

- `code-health-audit-pipeline` — runs the code-health leaves in parallel, merges and
  ranks findings, and emits a supervisor decision with exit codes 0/1/2.
- `test-audit-pipeline` — orchestrates coverage collection, test-quality scoring, and
  redundancy triage into a unified test-health report.

Test-audit family:

- `test-quality-assurance` — scores a suite against an 8-dimension TDD rubric.
- `test-redundancy-triage` — classifies tests DELETE / MERGE / KEEP with confidence tiers.
```

- [ ] **Step 5: Verify the gate is green and lists all nine skills**

Run: `npm run check`
Expected: all pass; `check:release` `"skills"` array contains all nine, sorted:
`code-health-audit-pipeline, complexity-audit, dead-code-audit, duplication-audit, quality-audit, structure-audit, test-audit-pipeline, test-quality-assurance, test-redundancy-triage`.

- [ ] **Step 6: Functional smoke — install round-trip + sibling-discovery**

Run:
```bash
node bin/install-repo-audit-skills.js --dest /tmp/ras-install --force
python3 /tmp/ras-install/test-audit-pipeline/scripts/audit_pipeline.py --help >/dev/null && echo "INSTALL OK"
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location(
    "audit_pipeline",
    "skills/test-audit-pipeline/scripts/audit_pipeline.py",
)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
assert mod.DEFAULT_TQA_SCRIPT.exists(), mod.DEFAULT_TQA_SCRIPT
assert mod.DEFAULT_TRIAGE_SCRIPT.exists(), mod.DEFAULT_TRIAGE_SCRIPT
print("SIBLING DISCOVERY OK")
PY
```
Expected: `INSTALL OK` then `SIBLING DISCOVERY OK` — confirming the umbrella resolves its leaf scripts from the new `skills/` layout and the installer carries all nine skills.

- [ ] **Step 7: Commit**

```bash
git add bin/install-repo-audit-skills.js scripts/check_release.py scripts/check_skill_fixtures.py README.md
git commit -m "feat: register test-audit pipeline skills in package machinery

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Directory rename, GitHub takeover, decommission old repo (IRREVERSIBLE — human-confirmed)

> **Stop and read.** This task force-pushes over `github.com/jc1122/repo-audit-skills`, overwriting the old placeholder (abandoning `perf-benchmark` + `repo-audit-refactor-optimize`), renames the working directory, and deletes the old local repo. These are intentional and authorized, but irreversible. Do **not** run the destructive steps (5, 7, 8) without an explicit go-ahead from the user at that moment. Run everything with absolute paths and from the parent directory so a stale shell cwd cannot point inside a directory being moved.

**Files:** git remote/branch config; filesystem.

- [ ] **Step 1: Pre-flight — clean tree, green gates, expected branch**

Run:
```bash
cd /home/jakub/projects/code-health-skills
git status --short            # expect: empty
npm run check                 # expect: all pass, nine skills
git branch --show-current     # expect: master
git remote -v                 # expect: empty (no remote yet)
```

- [ ] **Step 2: Normalize the local branch to `main`**

Run: `git branch -m master main`
Verify: `git branch --show-current` → `main`.

- [ ] **Step 3: Point `origin` at the GitHub repo to take over**

Run:
```bash
git remote add origin https://github.com/jc1122/repo-audit-skills.git
git remote -v
```
Expected: `origin` shows the `repo-audit-skills.git` URL for fetch and push.

- [ ] **Step 4: Inspect what currently lives on the remote (so the overwrite is eyes-open)**

Run:
```bash
git fetch origin
git log --oneline origin/main -5
```
Expected: the old placeholder's history (perf-benchmark / refactor-optimize commits). This is what the force-push will replace.

- [ ] **Step 5: Force-push to overwrite the placeholder — REQUIRES USER CONFIRMATION**

> Confirm with the user before running this. It is the irreversible external action.

Run:
```bash
git push --force -u origin main
```
Expected: push succeeds; `origin/main` now points at this package's history.

- [ ] **Step 6: Verify the remote takeover**

Run:
```bash
git log --oneline origin/main -3
git status -sb
```
Expected: `origin/main` matches local `main`; branch is up to date with `origin/main`.

- [ ] **Step 7: Remove the old local placeholder repo — REQUIRES USER CONFIRMATION**

> Confirm before deleting. Run from the parent dir so the shell cwd is not inside the target.

Run:
```bash
cd /home/jakub/projects
rm -rf /home/jakub/projects/repo-audit-skills
```

- [ ] **Step 8: Rename the working directory to match the package**

Run:
```bash
cd /home/jakub/projects
mv /home/jakub/projects/code-health-skills /home/jakub/projects/repo-audit-skills
cd /home/jakub/projects/repo-audit-skills
```

- [ ] **Step 9: Final verification from the renamed directory**

Run:
```bash
cd /home/jakub/projects/repo-audit-skills
git remote -v                 # origin -> repo-audit-skills.git
git branch --show-current     # main
git status --short            # empty
npm run check                 # all pass, nine skills
ls /home/jakub/projects/repo-audit-skills/skills | sort   # nine skill dirs
test ! -e /home/jakub/projects/code-health-skills && echo "OLD DIR GONE"
```
Expected: gates green, nine skills, old path absent.

There is no separate commit for Task 4 — it is git-remote/branch and filesystem operations, not file edits.

---

## Definition of Done

1. `npm run check` green from `/home/jakub/projects/repo-audit-skills`, `check:release` listing all nine skills.
2. `node bin/install-repo-audit-skills.js --dest /tmp/ras-install --force` installs all nine; a migrated script answers `--help` from the install.
3. The three migrated scripts answer `--help`; `audit_pipeline.py`'s `DEFAULT_TQA_SCRIPT` and `DEFAULT_TRIAGE_SCRIPT` resolve to existing files in the new layout.
4. `origin` is `github.com/jc1122/repo-audit-skills` on `main`, force-pushed; the working directory is `/home/jakub/projects/repo-audit-skills`; the old local repo is gone.
5. Git history shows three focused commits (Tasks 1-3); Task 4 is config/filesystem only.

## Out of scope (Sub-project 2)

Finding-schema conformance, CLI unification, timestamp/runtime determinism, subprocess timeouts, guarded parsing, version pinning, the dogfooding self-audit gate (ratchet/baseline), and adding real test suites for the migrated skills.
