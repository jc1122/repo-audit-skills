# SP11 Launch Prompt — paste into a fresh Codex gpt-5.5 session

Paste the block below into a fresh **Codex gpt-5.5** session started inside
`/home/jakub/projects/repo-audit-skills`. It drives the PREP stage only:
goal-config verification → goal-preflight → emit the exact `/goal` bootloader
text. The prep session must NOT launch `/goal` itself (goal-preflight is
prompt-prep only); the human pastes the rendered bootloader into the next
session, and from that point the run is fully unattended.

Authority chain the bundle must preserve:

- Plan (single authority): `docs/superpowers/plans/2026-06-11-sp11-unattended-dogfood-loop.md`
- Brief (preflight source): `docs/superpowers/SP11-GOAL-BRIEF.md`
- Both on repo-A `main` with CI green (plan review-fixed at `b7cb74f`).

---

```
You are the SP11 PREP session for the unattended dogfood loop of the
repo-audit skill family, in /home/jakub/projects/repo-audit-skills. Your ONLY
deliverable is a lint-clean, readiness-green /goal bundle and the exact
goal-bootloader.md text. You prepare; you do NOT launch /goal, do not start
branch orchestrators, do not edit any repo source. Fail closed at every step:
on any failure, print the failing command + output + the fix-and-recheck
command, then STOP.

PRE-FLIGHT (any failure -> STOP and report):
- repo-A /home/jakub/projects/repo-audit-skills clean, main at b7cb74f or
  later with CI green; repo-B /home/jakub/projects/repo-audit-refactor-optimize
  clean at 7c23276 or later; repo-P /home/jakub/projects/perf-benchmark-skill
  clean at ac89675 or later.
- The plan and brief exist at the paths above; read BOTH in full. The plan's
  contracts C-1..C-9, branch groups B0-B5, DoD, and DONE/BLOCKED terminals are
  FROZEN — the bundle must carry them verbatim, never paraphrased weaker.
- Installed skills resolve: goal-config, goal-preflight, opencode-worker-bridge
  under ${CODEX_HOME:-$HOME/.codex}/skills or ~/.agents/skills.

STEP 1 — goal-config (fail-closed smoke):
Use the goal-config skill. Create or reuse a profile at
/home/jakub/projects/goal-bundles/sp11-unattended-dogfood/goal.config.json:
- main + branch orchestrators: Codex gpt-5.5, approvals DISABLED (unattended;
  authorized by the human 2026-06-11 — recorded in the plan's Authorization
  section).
- worker routes: opencode (via opencode-worker-bridge) FIRST; the native
  worker ladder as fallback, per plan C-7.
- effort profile: thorough; validation mode: smoke.
Run check_goal_config.py --for-preflight with the smoke test. If NO worker
route is green, STOP (do not silently fall back at config time — the C-7
fallback is a runtime decision recorded per packet). Record which routes the
smoke accepted; if opencode is not among them, say so explicitly in your
final output so the human can decide before launch.

STEP 2 — goal-preflight (bundle creation):
Use the goal-preflight skill with the brief as source material:
- brief source: /home/jakub/projects/repo-audit-skills/docs/superpowers/SP11-GOAL-BRIEF.md
  (digest the plan it points to; keep branch boundaries, DoD, contracts, and
  the DONE/BLOCKED terminal semantics verbatim).
- out-dir: /home/jakub/projects/goal-bundles/sp11-unattended-dogfood/
  (OUTSIDE the three repos — they self-audit docs for path tokens; never
  write bundle files into any of the three repos).
- Branch groups exactly as the brief's rolling schedule: Group 1 serial
  B0.1 -> B0.2 -> B1 with B0.3/B0.4 concurrent to B1; Group 2 parallel B2/B3/B4
  single-writer per repo; Group 3 serial B5.
- Run the guided pipeline (prepare_goal_bundle.py with the goal config), then
  lint and the readiness check. If readiness is blocked, return the blocked
  readiness fix/recheck command and STOP — do not hand-edit generated
  manifests to force green.

STEP 3 — handoff (your final output, in this order):
1. The readiness --json payload (compact).
2. Which worker routes the smoke accepted (opencode green: yes/no).
3. The EXACT rendered goal-bootloader.md text in one fenced block, ready to
   paste into a fresh /goal session.
4. One line stating what the next session will do: run goal-main-orchestrator
   on this bundle, unattended, until every DoD row is met (DONE) or a C-8
   condition ends it (BLOCKED with complete ledger evidence) — both valid
   terminals, nothing pushed past a red gate, no human gate anywhere in the
   loop.

CONSTRAINTS: never edit the plan, the brief, or any repo source; never launch
/goal, orchestrators, or workers (the B0.2 bridge smoke belongs to the runtime
session, not to you); bundle artifacts only under the out-dir; if any skill,
script, or route is missing, STOP and report rather than improvising a
substitute.
```

---

## Launch at a glance

```
Session 1 (this prompt):  goal-config smoke -> goal-preflight -> bundle + bootloader text
Human:                    paste bootloader into a fresh /goal session
Session 2 (/goal):        goal-main-orchestrator consumes the bundle, unattended
                          Group 1: B0.1 gate -> B0.2 bridge smoke -> B1 precision (ship 0.5.2)
                          Group 2: B2 (A: 92->0) || B3 (B: 9->0) || B4 (P: 55->0)
                          Group 3: B5 purge + final report, repo-A 0.6.0
Terminals:                DONE (all DoD rows) or BLOCKED (C-8, evidence complete)
```
