# Repository Patterns

## Layout

```text
mods.toml
manuscripts/<modid>/patchouli/
  book.yml
  shared/
    categories/*.yml
    entries/**/*.yml
    pages/<entry_id>/*.md
  locales/<locale>/
    book.yml
    categories/*.yml
    entries/**/*.yml
    pages/<entry_id>/*.md
docs/<modid>/patchouli/data/<namespace>/patchouli_books/<book_id>/book.json
docs/<modid>/patchouli/assets/<namespace>/patchouli_books/<book_id>/en_us/
docs/<modid>/patchouli/assets/<namespace>/lang/<locale>.json
docs/<modid>/modonomicon/
```

## ID Rules

- Use `snake_case` for `modid`, category IDs, entry IDs, and filenames.
- Keep entry `category` values unnested and unqualified, for example `getting_started`.
- Let the builder expand entry categories to `<modid>:<category_id>` during JSON generation.

## Minimal File Patterns

`shared/` is the manuscript written in `book.yml` `source_locale`. `locales/<locale>/book.yml` is for translated book title, subtitle, and landing text. Other `locales/<locale>/` files are only for overrides.

### `book.yml`

```yaml
book_id: examplemod
book_namespace: examplemod
source_locale: en_us
name: "Example Mod Manual"
landing_text: |
  Welcome text here.
version: 1
locales:
  - en_us
```

### `shared/categories/<category_id>.yml`

```yaml
id: getting_started
name: "Getting Started"
description: |
  Short category summary.
icon: minecraft:book
sortnum: 0
```

### `shared/entries/<entry_id>.yml`

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

### `shared/pages/<entry_id>/00-introduction.md`

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
- When only translated text changes, prefer `locales/<locale>/` overrides and let non-`en_us` JSON be omitted.
