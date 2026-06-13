#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const root = path.resolve(__dirname, "..");
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
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
  "coverage-gap-audit",
  "hotspot-audit",
  "dependency-audit",
  "repo-hygiene-audit",
  "docs-consistency-audit",
  "security-audit",
  "test-effectiveness-audit",
  "exec-audit",
  "growth-audit",
];

function usage() {
  return [
    "Usage: install-repo-audit-skills [--dest DIR] [--force] [--dry-run] [--list] [--version]",
    "",
    "Installs repo-audit skills into $CODEX_HOME/skills or ~/.codex/skills by default.",
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
