---
name: minecraft-manual-authoring
description: Scaffold and update Minecraft manual manuscript sources for this repository, especially when creating or editing Patchouli-oriented files under `manuscripts/{modid}/patchouli/`, proposing category or entry IDs, drafting page front matter, or expanding manual structure from a rough content request.
---

# Minecraft Manual Authoring

## Overview

Use this skill to add or expand manual source files in this repository.
Prefer it when the task is about drafting manuscript YAML or Markdown, choosing IDs, or placing content in the correct `manuscripts/<modid>/patchouli/` location.

## Workflow

1. Read `mods.toml` and confirm the target `modid`.
2. Read `AGENTS.md` and any existing files under `manuscripts/<modid>/patchouli/`.
3. Reuse existing naming and file placement patterns before creating new ones.
4. Update manuscript sources, not generated JSON under `docs/`.
5. After edits, recommend or run `python -m uv run mod-manual validate` and `python -m uv run mod-manual build patchouli --mod <modid>`.

## Authoring Rules

- Keep IDs in `snake_case`.
- Treat `manuscripts/` as the source of truth and `docs/` as generated output.
- For Patchouli entries, store page bodies in `pages/<entry_id>/*.md` and reference them from `entries/*.yml`.
- Keep scaffolds readable and minimal. Do not invent extra abstraction layers.
- Preserve the current repository bias: Patchouli first, Modonomicon later.

## Common Tasks

### New mod skeleton

Create or update:

- `mods.toml`
- `manuscripts/<modid>/patchouli/book.yml`
- `docs/<modid>/modonomicon/.gitkeep`

### New category

Create `manuscripts/<modid>/patchouli/categories/<category_id>.yml` with a short description, icon, and sort order.

### New entry

Create or update:

- `manuscripts/<modid>/patchouli/entries/<entry_id>.yml`
- `manuscripts/<modid>/patchouli/pages/<entry_id>/00-*.md`

Set the entry `category` to the bare category ID used in this repository, not a namespaced value. The builder adds the `modid:` prefix during generation.

## References

- For file layout and manuscript snippets, read [references/repo-patterns.md](references/repo-patterns.md).
