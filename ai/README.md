# AI Tooling Configuration

This project uses a centralized AI context strategy. All AI tools (Cursor, Copilot, Cline, Opencode, etc.) should reference the shared context located in `./ai`.

## Rules & Context
- **Centralized Rules:** `./ai/context/rules.md`
- **Skills:** `./ai/skills/`

## Cursor Specifics
Cursor should look for its rules in `.cursorrules`. We symlink or copy the centralized rules here.

*Note: Since Cursor expects `.cursorrules` in the root, we will create a symlink or keep a pointer file.*
