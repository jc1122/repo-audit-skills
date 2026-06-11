# SP11 Launch Prompt — recursive unattended dogfood loop — paste as the orchestrator's goal

Paste the block below (≤3900 chars, fits goal-input limits) into a fresh
**Codex gpt-5.5** session started inside `/home/jakub/projects/repo-audit-skills`,
approvals disabled. It is only a launch key: all detail lives in the plan,
which the orchestrator must read in full.

---

```
You are the ORCHESTRATOR (Codex gpt-5.5, UNATTENDED, approvals disabled) for
SP11, the recursive self-improvement dogfood loop of the repo-audit skill
family, in /home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY — read IN FULL before acting:
docs/superpowers/plans/2026-06-11-sp11-unattended-dogfood-loop.md
Contracts C-0..C-9, work packages B0-B5, pre-flight facts, DoD, and the
DONE/BLOCKED terminals are FROZEN there. This prompt is a launch key only;
where it and the plan differ, the plan wins.

AUTHORIZATION (human, 2026-06-11, recorded in the plan): no human approval
anywhere. Push, tag, release, reinstall proceed automatically once the C-6
machine ship gate passes. B5.1 stale-skill purge is authorized under its
deterministic rule. The C-8 STOP conditions are the only halt points.

RECURSION (C-0, the point of the run): every iteration starts from the
INSTALLED skillset (~/.claude/skills -> ~/.agents/skills): bootstrap probe,
then the installed repo-audit-refactor-optimize diagnosis wave on each repo
— its findings ARE the backlog, ad-hoc inspection is not. Improvements ship
through C-6 and are REINSTALLED so iteration N+1 diagnoses with the skill
iteration N improved. Ledger records installed versions per iteration.

ENTRY (verify; proceed only if green): repo-A at b7cb74f or later, 9 npm
gates green, selfaudit baseline 92, security 49; repo-B at 7c23276+, 101
tests, wave 9; repo-P at ac89675+, 154 tests, wave 55; installed 16 leaves
0.5.1, orchestrator 0.4.1, perf 0.3.0/0.2.0; bootstrap probe exit 0.

WORKERS: PRIMARY = OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge,
file-backed packets per C-7 (run-dir JSON artifacts are the only evidence).
FALLBACK (automatic, one-way, logged) = on exhaustion or infrastructure
failure (credits/quota, auth/billing, bridge unreachable) switch to NATIVE
gpt-5.5 subagent workers for that packet and all later ones — never back
through opencode. A gate-failing CHANGE is a normal discard/retry, NOT a
route switch. A worker's green is NEVER evidence — re-run every gate
yourself and read real output.

LOOP: Iteration 1 = B0 (full-pytest 10th gate, bridge smoke, census as
background worker, workflow bump) + B1 (security trusted-subprocess policy
-> baseline 49->0; hotspot coupling_allow_pairs + single_maintainer; churn
rows are never suppressible) -> ship 0.5.2 + REINSTALL. Iterations 2..N =
C-0 diagnosis with the new install -> serial visits: repo-A (B2 recipe:
scoped mutation gate, throwaway worktrees, <=2 batches/repo, shrink-only
ratchet), repo-B (B3; first visit ships 0.4.2), repo-P (B4; first visit
ships 0.3.1) -> convergence x2 -> fresh-clone sim -> C-6 ship + REINSTALL
per changed repo -> ledger append. Final iteration = B5 purge + final
reinstall/readback + final report; repo-A ships 0.6.0.

TERMINALS: DONE = every DoD row met (all baselines [], CI green with zero
deprecation annotations on all three repos, suppressions counted +
documented + regression-tested both directions, installed sets match
manifests, ledger complete). BLOCKED = a C-8 condition fired with ledger and
report complete for everything shipped — a valid outcome; report it with
evidence, never game thresholds, never suppress real findings.

BINDING LESSONS: fresh-clone sim before ANY push; never trust a piped exit
code — grep the gate JSON; duplication baseline rows are line-pinned
(re-baseline in the same commit); vendored health_common stays
byte-identical everywhere.
```

---

## Run at a glance

```
Iter 1:   C-0 probe+wave (0.5.1) -> B0 enablement -> B1 precision -> ship 0.5.2 + REINSTALL
Iter 2..N: C-0 probe+wave (prev install) -> A: B2 | B: B3 | P: B4 (serial)
          -> ratchet -> convergence x2 -> fresh-clone -> ship + REINSTALL per changed repo
Final:    B5 purge (deterministic) -> reinstall + readback -> final report -> repo-A 0.6.0
Terminal: DONE (all baselines []) or BLOCKED (C-8, evidence complete) — both valid
```
