# Agent memory (continual learning)

## Learned User Preferences

- Use gstack `/browse` for web browsing when gstack is installed; do not use `mcp__claude-in-chrome__*` or similar MCP browser tools when gstack is available.
- When git reports "multiple upstream branches" on push, set a single upstream (e.g. `git branch --set-upstream-to=origin/main main`) instead of leaving duplicate `branch.main.remote` / `branch.main.merge`.
- Prefer minimal, focused edits when cleaning AI-generated code; keep behavior unchanged unless fixing a clear bug.

## Learned Workspace Facts

- This repo focuses on LLM internal-state geometric visualization; browser-first WebGL (e.g. Three.js), not matplotlib, for the primary viz.
- `viz_server` serves `/` and `/viz.js` via explicit routes so WebSocket `/ws` is not handled by a static file mount; use `stream_mock: true` in tests to avoid loading the model.
- gstack is available as a project skill at `.cursor/skills/gstack`; teammates run `cd .cursor/skills/gstack && ./setup` once.
