#!/usr/bin/env bash
# worker_worktree_setup.sh — R7 automation escalation of binding lesson L1
# ("run `npm ci` in fresh worktrees or jscpd/node-dependent tests fail").
#
# A fresh git worktree does not inherit node_modules. Any worker whose batch
# touches jscpd/node-dependent checks MUST run this first. Idempotent and safe
# to call in a Python-only worktree (no package.json -> no-op, exit 0).
#
# Usage: scripts/worker_worktree_setup.sh [worktree_dir]   (default: cwd)
set -euo pipefail

dir="${1:-$(pwd)}"
cd "$dir"

if [ -f package-lock.json ]; then
    npm ci
elif [ -f package.json ]; then
    npm install
else
    echo "worker_worktree_setup: no package.json in $dir; nothing to install (Python-only worktree)."
fi
