# Frozen security-audit findings

Residual findings from the `check:security` gate (bandit over the production scope),
each justified individually. Zero blanket freezes — every entry names its own file.

Each entry: path :: leaf/metric :: symbol :: reason.

## Round log

- **SP8 G4-R1** (seed): pre-seed 64 bandit findings (50 low / 1 medium / 13 high). FIXED 15
  outright — 13 hashlib B324 highs (`stable_id` sha1 is a finding-id hash, not security;
  `usedforsecurity=False` added once in `shared/health_common.py`, re-vendored byte-identical
  into all 12 leaf copies, `check:vendored` green); 1 B108 hardcoded `/tmp` dest in
  `scripts/check_release.py` (→ `tempfile.gettempdir()`); 1 B112 try/except/continue in
  `skills/test-quality-assurance/scripts/audit_test_quality.py` (narrowed to typed exceptions).
  The residual 49 are frozen per-finding below. Baseline seeded at 49; zero unjustified.
- **SP8 G4-R2** (shrink attempt — no honest shrink): examined the 2 B105 false positives (the
  boolean dict field deselect_suite_pass — bandit over-matches the "pass" substring) and the 47
  subprocess findings. No real fix exists without either a schema-breaking key rename that would
  churn the triage golden suite, or a "# nosec" suppression (not a fix). The B603/B404/B607
  residual is intrinsic to an audit toolkit that wraps pinned external binaries. Baseline
  unchanged at 49; zero unjustified.

### A. subprocess import (B404 `blacklist`) — 17
**Reason:** Each audit leaf shells out to its pinned external tool (bandit / mutmut / jscpd / ruff / git / node). `import subprocess` is required; it is used only with list-args and never `shell=True`.
- `scripts/check_coverage_gap.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `scripts/check_release.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `scripts/check_skill_fixtures.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `scripts/gate_common.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `scripts/self_audit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/complexity-audit/scripts/complexity_audit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/duplication-audit/scripts/duplication_audit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/hotspot-audit/scripts/_audit_git.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/quality-audit/scripts/quality_audit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/repo-hygiene-audit/scripts/_git_utils.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/security-audit/scripts/_bandit.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/test-effectiveness-audit/scripts/_evidence.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/test-effectiveness-audit/scripts/_pipeline.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: security/bandit_B404 :: blacklist :: required subprocess import for a pinned-tool wrapper; list-args only, never shell=True

### B. subprocess call without shell=True (B603) — 26
**Reason:** Deliberate subprocess wrapper: `subprocess.run`/`Popen` is called with a list argv and `shell=False` over a pinned tool. Arguments are repo-internal paths and constant tool flags, so there is no shell-injection surface.
- `scripts/check_coverage_gap.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/check_coverage_gap.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/check_coverage_gap.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/check_release.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/check_skill_fixtures.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/gate_common.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `scripts/self_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/complexity-audit/scripts/complexity_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/duplication-audit/scripts/duplication_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/hotspot-audit/scripts/_audit_git.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/hotspot-audit/scripts/_audit_git.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/quality-audit/scripts/quality_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/quality-audit/scripts/quality_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/quality-audit/scripts/quality_audit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/repo-hygiene-audit/scripts/_git_utils.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/repo-hygiene-audit/scripts/_git_utils.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/security-audit/scripts/_bandit.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-effectiveness-audit/scripts/_evidence.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-effectiveness-audit/scripts/_evidence.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-effectiveness-audit/scripts/_pipeline.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-effectiveness-audit/scripts/_pipeline.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: security/bandit_B603 :: subprocess_without_shell_equals_true :: list-argv subprocess, shell=False, pinned tool; no shell-injection surface

### C. start process with partial path (B607) — 4
**Reason:** The pinned tool is resolved via PATH by design (e.g. `node` / `git` / `python3` / `ruff`). Hardcoding an absolute path would be environment-fragile across installs (nvm, venvs, distro layouts).
- `skills/hotspot-audit/scripts/_audit_git.py` :: security/bandit_B607 :: start_process_with_partial_path :: pinned tool resolved via PATH by design; an absolute path would be environment-fragile
- `skills/hotspot-audit/scripts/_audit_git.py` :: security/bandit_B607 :: start_process_with_partial_path :: pinned tool resolved via PATH by design; an absolute path would be environment-fragile
- `skills/repo-hygiene-audit/scripts/_git_utils.py` :: security/bandit_B607 :: start_process_with_partial_path :: pinned tool resolved via PATH by design; an absolute path would be environment-fragile
- `skills/repo-hygiene-audit/scripts/_git_utils.py` :: security/bandit_B607 :: start_process_with_partial_path :: pinned tool resolved via PATH by design; an absolute path would be environment-fragile

### D. hardcoded password false positive (B105) — 2
**Reason:** Bandit false positive: the flagged literal is the string `'False'` (a config/default value compared as text), not a credential.
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: security/bandit_B105 :: hardcoded_password_string :: bandit false positive: literal 'False' is a config value, not a credential
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: security/bandit_B105 :: hardcoded_password_string :: bandit false positive: literal 'False' is a config value, not a credential

