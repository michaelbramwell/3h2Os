# AGENTS.md

AI agent configuration index for the 3h2Os project. This file is the canonical entry point -- agents should load the referenced files for full context.

## Project Context

| File | Purpose |
|---|---|
| [.ai/context.md](.ai/context.md) | Architecture, services, guidelines, env config, deployment, integrations |
| [.ai/skills/3h2os/SKILL.md](.ai/skills/3h2os/SKILL.md) | Operational skills: plan builder, sync, testing, Docker commands |
| [ai/context/rules.md](ai/context/rules.md) | Coding rules, tech stack, dev workflow, key files |

## Feature Context

| File | Purpose |
|---|---|
| [.ai/plan-builder-wizard.md](.ai/plan-builder-wizard.md) | Plan builder wizard design and implementation details |
| [.ai/strava-integration.md](.ai/strava-integration.md) | Strava OAuth, webhooks, sync architecture |
| [.ai/code-cleanup.md](.ai/code-cleanup.md) | Code cleanup guidance and patterns |

## Tool-Specific Config

| Tool | Config | Notes |
|---|---|---|
| **Cursor** | [.cursorrules](.cursorrules) | Tech stack, architecture, dev workflow, operational rules |
| **GitHub Copilot** | [.github/copilot-instructions.md](.github/copilot-instructions.md) | Pointer to `.ai/context.md` and skills |
| **OpenCode** | [.opencode/](.opencode/) | Plugin config; plans in `.opencode/plans/` |

## Memory Palace (MemPalace MCP)

This project uses [MemPalace](https://github.com/anomalyco/mempalace) as a persistent memory layer for AI agents via MCP.

- **Config**: [mempalace.yaml](mempalace.yaml)
- **Wing**: `3h2os`
- **Rooms**: `migrations`, `app`, `frontend`, `backend`, `documentation`, `certs`, `testing`, `scripts`, `general`

### Agent expectations

- **Read from palace** at session start to recall prior context, decisions, and lessons learned.
- **Write to palace** when completing significant work: architecture decisions, bug fixes with root causes, new patterns established, integration learnings.
- **Use the knowledge graph** to track entity relationships (services, features, integrations).
- **Search before asking** -- the palace may already contain the answer.

## Key Rules

1. **No emojis** in code, docs, or responses.
2. **No commits** without explicit user permission.
3. **Project name**: "3h2os" (lowercase o and s).
4. **Docker-first**: the app runs in containers. Use `docker exec running_app uv run ...` for backend commands.
5. **PostgreSQL is the single source of truth**. No legacy JSON.
6. **AWST (UTC+8)** for all date/time logic.
