# Repository Patterns

## Layout

```text
mods.toml
manuscripts/<modid>/patchouli/
  book.yml
  categories/*.yml
  entries/*.yml
  pages/<entry_id>/*.md
docs/<modid>/patchouli/<locale>/
docs/<modid>/modonomicon/
```

## ID Rules

- Use `snake_case` for `modid`, category IDs, entry IDs, and filenames.
- Keep entry `category` values unnested and unqualified, for example `getting_started`.
- Let the builder expand entry categories to `<modid>:<category_id>` during JSON generation.

## Minimal File Patterns

### `book.yml`

```yaml
name: "Example Mod Manual"
landing_text: |
  Welcome text here.
version: 1
i18n: en_us
```

### `categories/<category_id>.yml`

```yaml
id: getting_started
name: "Getting Started"
description: |
  Short category summary.
icon: minecraft:book
sortnum: 0
```

### `entries/<entry_id>.yml`

```yaml
id: first_steps
name: "First Steps"
category: getting_started
icon: minecraft:paper
sortnum: 0
pages:
  - type: text
    source: 00-introduction.md
```

### `pages/<entry_id>/00-introduction.md`

```md
---
title: "Welcome"
---
Write Patchouli text here.
```

## Editing Guidance

- Modify manuscript sources instead of generated files.
- Reuse the repository sample under `manuscripts/examplemod/patchouli/` when unsure.
- Keep scaffolds compact so the user can revise them manually.
