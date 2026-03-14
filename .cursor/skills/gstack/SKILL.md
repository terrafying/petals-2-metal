---
name: gstack
description: >-
  Installs and uses Garry Tan's gstack workflow (plan, review, ship, browse, qa, retro).
  Use when the user asks to install gstack, use /browse for web browsing, or when
  using gstack skills /plan-ceo-review, /plan-eng-review, /review, /ship, /browse,
  /qa, /setup-browser-cookies, /retro.
---

# gstack

Opinionated workflow skills: CEO/eng plan review, code review, one-command ship, browser automation, QA, and retros. Use gstack for web browsing and these workflows instead of generic or MCP browser tools.

## Install (personal)

1. Clone and run setup:
   ```bash
   git clone https://github.com/garrytan/gstack.git ~/.cursor/skills/gstack && cd ~/.cursor/skills/gstack && ./setup
   ```
2. Ensure this Cursor skill is in place: the clone may not include a Cursor `SKILL.md`. If `~/.cursor/skills/gstack/SKILL.md` is missing, copy it from a project that has `.cursor/skills/gstack/SKILL.md`, or use this file as the contents for `~/.cursor/skills/gstack/SKILL.md`.

**Requirements:** Git, [Bun](https://bun.sh/) v1.0+. `/browse` builds a native binary (macOS and Linux x64/arm64).

## Web browsing and tools

- **Use the gstack `/browse` skill for all web browsing** when gstack is installed. Prefer it over other browser or in-browser automation tools.
- **Do not use** `mcp__claude-in-chrome__*` tools (or other MCP browser/Chrome tools) when gstack is available; use gstack's `/browse` instead.

## Available gstack skills

| Skill | Purpose |
|-------|--------|
| `/plan-ceo-review` | Founder/CEO mode: rethink the problem, find the 10-star product in the request. |
| `/plan-eng-review` | Eng manager: lock in architecture, data flow, diagrams, edge cases, tests. |
| `/review` | Paranoid staff engineer: bugs that pass CI but fail in prod; triage review comments. |
| `/ship` | Release engineer: sync main, run tests, resolve reviews, push, open PR (ready branch). |
| `/browse` | QA engineer: log in, click through app, screenshots, catch breakage. Use for all web browsing. |
| `/qa` | QA lead: analyze diff, affected pages, test on feature branch; exploration, smoke, regression. |
| `/setup-browser-cookies` | Import cookies from Comet/Chrome/Arc/Brave/Edge into headless session for authenticated testing. |
| `/retro` | Engineering manager: team retro with per-person praise and growth opportunities. |

## After installing: project setup for teammates

Ask the user:

**Do you want to add gstack to this project so teammates get it?**

If yes:

1. Copy gstack into the repo and run setup:
   ```bash
   cp -Rf ~/.cursor/skills/gstack .cursor/skills/gstack && rm -rf .cursor/skills/gstack/.git && cd .cursor/skills/gstack && ./setup
   ```
2. Commit the skill files (not `.git`, not `node_modules`, not `browse/dist`). Teammates run once: `cd .cursor/skills/gstack && ./setup`.
3. If gstack skills aren’t working in this project, run `cd .cursor/skills/gstack && ./setup` to build the binary and register skills.
