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
- Keep book-level locale text in `book.yml` for the `source_locale`, and use `locales/<locale>/book.yml` for translated book title, subtitle, or landing text overrides when needed.
- For Patchouli entries, treat `shared/` as the `source_locale` manuscript and place locale-specific overrides under `locales/<locale>/`.
- Keep scaffolds readable and minimal. Do not invent extra abstraction layers.
- Preserve the current repository bias: Patchouli first, Modonomicon later.

## Common Tasks

### New mod skeleton

Create or update:

- `mods.toml`
- `manuscripts/<modid>/patchouli/book.yml`
- `docs/<modid>/modonomicon/.gitkeep`

### New category

Create `manuscripts/<modid>/patchouli/shared/categories/<category_id>.yml` for the `source_locale` manuscript, or `locales/<locale>/categories/<category_id>.yml` when adding a translation override.

### New entry

Create or update:

- `manuscripts/<modid>/patchouli/shared/entries/<entry_id>.yml`
- `manuscripts/<modid>/patchouli/shared/pages/<entry_id>/00-*.md`

Use `locales/<locale>/entries/...` and `locales/<locale>/pages/...` only when a translation or locale-specific structure override is needed.

Set the entry `category` to the bare category ID used in this repository, not a namespaced value. The builder adds the `modid:` prefix during generation.

## References

- For file layout and manuscript snippets, read [references/repo-patterns.md](references/repo-patterns.md).
