from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

from .models import Manifest, ModSpec

DEFAULT_LOCALE = "en_us"
SUPPORTED_FORMATS = {"patchouli", "modonomicon"}
SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")


class ManualError(Exception):
    """Raised for repository-level manual authoring errors."""


def load_manifest(root: Path) -> Manifest:
    manifest_path = root / "mods.toml"
    if not manifest_path.exists():
        raise ManualError(f"Missing manifest: {manifest_path}")

    payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    mods = []
    for index, raw_mod in enumerate(payload.get("mods", []), start=1):
        modid = require_slug(raw_mod.get("modid"), f"mods[{index}].modid")
        display_name = str(raw_mod.get("display_name") or modid)
        enabled_formats = tuple(str(item) for item in raw_mod.get("enabled_formats", []))
        unknown_formats = sorted(set(enabled_formats) - SUPPORTED_FORMATS)
        if unknown_formats:
            raise ManualError(
                f"mods[{index}].enabled_formats contains unsupported formats: {', '.join(unknown_formats)}"
            )
        mods.append(ModSpec(modid=modid, display_name=display_name, enabled_formats=enabled_formats))

    version = int(payload.get("version", 1))
    return Manifest(version=version, mods=tuple(mods))


def write_manifest(root: Path, manifest: Manifest) -> None:
    lines = [f"version = {manifest.version}", ""]
    for mod in manifest.mods:
        enabled_formats = ", ".join(f'"{item}"' for item in mod.enabled_formats)
        lines.extend(
            [
                "[[mods]]",
                f'modid = "{mod.modid}"',
                f'display_name = "{mod.display_name}"',
                f"enabled_formats = [{enabled_formats}]",
                "",
            ]
        )
    (root / "mods.toml").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def select_mods(manifest: Manifest, modid: str | None) -> tuple[ModSpec, ...]:
    if modid is None:
        return manifest.mods

    selected = [item for item in manifest.mods if item.modid == modid]
    if not selected:
        raise ManualError(f"Unknown modid: {modid}")
    return tuple(selected)


def validate_repository(root: Path, modid: str | None = None) -> list[str]:
    manifest = load_manifest(root)
    errors: list[str] = []

    for mod in select_mods(manifest, modid):
        if "patchouli" in mod.enabled_formats:
            errors.extend(validate_patchouli(root, mod))

    return errors


def build_patchouli(root: Path, modid: str | None = None) -> list[Path]:
    manifest = load_manifest(root)
    written_files: list[Path] = []

    for mod in select_mods(manifest, modid):
        if "patchouli" not in mod.enabled_formats:
            continue

        book, book_namespace, book_id, locales = load_book_settings(root, mod.modid)
        book_output_path = patchouli_book_output_path(root, mod.modid, book_namespace, book_id)
        book_output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(book_output_path, book)
        written_files.append(book_output_path)

        for locale in locales:
            categories_root = patchouli_categories_output_dir(root, mod.modid, book_namespace, book_id, locale)
            entries_root = patchouli_entries_output_dir(root, mod.modid, book_namespace, book_id, locale)
            categories_root.mkdir(parents=True, exist_ok=True)
            entries_root.mkdir(parents=True, exist_ok=True)

            for category_path in category_paths(root, mod.modid, locale):
                category = load_yaml_dict(category_path)
                category_id = require_slug(category.pop("id"), f"{category_path}: id")
                output_path = categories_root / f"{category_id}.json"
                write_json(output_path, category)
                written_files.append(output_path)

            category_ids = existing_category_ids(root, mod.modid, locale)
            entries_dir = locale_entries_dir(root, mod.modid, locale)
            for entry_path in entry_paths(root, mod.modid, locale):
                entry = load_yaml_dict(entry_path)
                entry_id = require_slug(entry.pop("id"), f"{entry_path}: id")
                category_id = require_slug(entry.get("category"), f"{entry_path}: category")
                if category_id not in category_ids:
                    raise ManualError(f"{entry_path}: unknown category '{category_id}'")

                pages = []
                for raw_page in entry.get("pages", []):
                    pages.append(resolve_page(entry_path, raw_page, root, mod.modid, locale, entry_id))

                entry["category"] = f"{book_namespace}:{category_id}"
                entry["pages"] = pages

                relative_path = entry_path.relative_to(entries_dir).with_suffix(".json")
                output_path = entries_root / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                write_json(output_path, entry)
                written_files.append(output_path)

    return written_files


def load_book_settings(root: Path, modid: str) -> tuple[dict[str, Any], str, str, tuple[str, ...]]:
    book_path = patchouli_dir(root, modid) / "book.yml"
    book = load_yaml_dict(book_path)
    book_namespace = require_slug(book.pop("book_namespace", modid), f"{book_path}: book_namespace")
    book_id = require_slug(book.pop("book_id", modid), f"{book_path}: book_id")
    locales = parse_book_locales(book, book_path)
    return book, book_namespace, book_id, locales


def parse_book_locales(book: dict[str, Any], book_path: Path) -> tuple[str, ...]:
    raw_locales = book.pop("locales", None)
    if raw_locales is None:
        legacy_locale = book.get("i18n")
        if isinstance(legacy_locale, str):
            book.pop("i18n")
            return (require_slug(legacy_locale, f"{book_path}: i18n"),)
        return (DEFAULT_LOCALE,)

    if not isinstance(raw_locales, list) or not raw_locales:
        raise ManualError(f"{book_path}: locales must be a non-empty list")

    locales = tuple(require_slug(item, f"{book_path}: locales[{index}]") for index, item in enumerate(raw_locales, start=1))
    if len(set(locales)) != len(locales):
        raise ManualError(f"{book_path}: locales contains duplicates")
    return locales


def scaffold_mod(root: Path, modid: str, display_name: str) -> list[Path]:
    modid = require_slug(modid, "modid")
    manifest = load_manifest(root)
    if any(item.modid == modid for item in manifest.mods):
        raise ManualError(f"Mod already exists in manifest: {modid}")

    updated = Manifest(
        version=manifest.version,
        mods=manifest.mods + (ModSpec(modid=modid, display_name=display_name, enabled_formats=("patchouli",)),),
    )
    write_manifest(root, updated)

    patchouli_root = patchouli_dir(root, modid)
    default_locale_root = locale_root(root, modid, DEFAULT_LOCALE)
    (default_locale_root / "categories").mkdir(parents=True, exist_ok=True)
    (default_locale_root / "entries").mkdir(parents=True, exist_ok=True)
    (default_locale_root / "pages").mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "patchouli").mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "modonomicon").mkdir(parents=True, exist_ok=True)

    book_path = patchouli_root / "book.yml"
    if not book_path.exists():
        book_path.write_text(
            "\n".join(
                [
                    f"book_id: {modid}",
                    f"book_namespace: {modid}",
                    f'name: "{display_name} Manual"',
                    "landing_text: |",
                    f"  Welcome to the {display_name} manual.",
                    "version: 1",
                    "locales:",
                    f"  - {DEFAULT_LOCALE}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    modonomicon_keep = root / "docs" / modid / "modonomicon" / ".gitkeep"
    modonomicon_keep.write_text("", encoding="utf-8")
    return [root / "mods.toml", book_path, modonomicon_keep]


def scaffold_category(root: Path, modid: str, category_id: str, name: str, locale: str = DEFAULT_LOCALE) -> Path:
    modid = require_slug(modid, "modid")
    category_id = require_slug(category_id, "category_id")
    locale = require_slug(locale, "locale")
    path = locale_categories_dir(root, modid, locale) / f"{category_id}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_missing(path)
    path.write_text(
        "\n".join(
            [
                f"id: {category_id}",
                f'name: "{name}"',
                "description: |",
                f"  Overview for {name}.",
                "icon: minecraft:book",
                "sortnum: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def scaffold_entry(
    root: Path, modid: str, entry_id: str, category_id: str, name: str, locale: str = DEFAULT_LOCALE
) -> list[Path]:
    modid = require_slug(modid, "modid")
    entry_id = require_slug(entry_id, "entry_id")
    category_id = require_slug(category_id, "category_id")
    locale = require_slug(locale, "locale")

    entry_path = locale_entries_dir(root, modid, locale) / category_id / f"{entry_id}.yml"
    page_dir = locale_pages_dir(root, modid, locale) / entry_id
    page_path = page_dir / "00-introduction.md"

    ensure_missing(entry_path)
    ensure_missing(page_path)
    page_dir.mkdir(parents=True, exist_ok=True)
    entry_path.parent.mkdir(parents=True, exist_ok=True)

    entry_path.write_text(
        "\n".join(
            [
                f"id: {entry_id}",
                f'name: "{name}"',
                f"category: {category_id}",
                "icon: minecraft:paper",
                "sortnum: 0",
                "pages:",
                "  - type: text",
                "    source: 00-introduction.md",
                "",
            ]
        ),
        encoding="utf-8",
    )

    page_path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{name}"',
                "---",
                "",
                f"Write the first page for {name} here.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return [entry_path, page_path]


def validate_patchouli(root: Path, mod: ModSpec) -> list[str]:
    errors: list[str] = []
    book_path = patchouli_dir(root, mod.modid) / "book.yml"
    if not book_path.exists():
        errors.append(f"{mod.modid}: missing {book_path}")
        return errors

    try:
        _, _, _, locales = load_book_settings(root, mod.modid)
    except ManualError as exc:
        errors.append(str(exc))
        return errors

    for locale in locales:
        try:
            category_ids = validate_patchouli_locale(root, mod.modid, locale)
        except ManualError as exc:
            errors.append(str(exc))
            continue

        entries_seen: set[str] = set()
        for entry_path in entry_paths(root, mod.modid, locale):
            try:
                entry = load_yaml_dict(entry_path)
                entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
                if entry_id in entries_seen:
                    errors.append(f"{entry_path}: duplicated entry id '{entry_id}'")
                entries_seen.add(entry_id)

                category_id = require_slug(entry.get("category"), f"{entry_path}: category")
                if category_id not in category_ids:
                    errors.append(f"{entry_path}: category '{category_id}' is not defined")

                seen_sources: set[str] = set()
                pages = entry.get("pages")
                if not isinstance(pages, list) or not pages:
                    errors.append(f"{entry_path}: pages must be a non-empty list")
                    continue

                for page_index, raw_page in enumerate(pages, start=1):
                    if not isinstance(raw_page, dict):
                        errors.append(f"{entry_path}: pages[{page_index}] must be a mapping")
                        continue

                    page_type = str(raw_page.get("type") or "")
                    if not page_type:
                        errors.append(f"{entry_path}: pages[{page_index}] is missing type")

                    source_name = raw_page.get("source")
                    if source_name:
                        source_path = locale_pages_dir(root, mod.modid, locale) / entry_id / str(source_name)
                        if source_name in seen_sources:
                            errors.append(f"{entry_path}: duplicated page source '{source_name}'")
                        seen_sources.add(str(source_name))
                        if not source_path.exists():
                            errors.append(f"{entry_path}: page source does not exist: {source_path}")
                        else:
                            try:
                                load_markdown_document(source_path)
                            except ManualError as exc:
                                errors.append(str(exc))
            except ManualError as exc:
                errors.append(str(exc))

    return errors


def validate_patchouli_locale(root: Path, modid: str, locale: str) -> set[str]:
    categories: dict[str, Path] = {}
    for category_path in category_paths(root, modid, locale):
        category = load_yaml_dict(category_path)
        category_id = require_slug(category.get("id"), f"{category_path}: id")
        if category_id in categories:
            raise ManualError(f"{category_path}: duplicated category id '{category_id}'")
        categories[category_id] = category_path
    return set(categories)


def patchouli_dir(root: Path, modid: str) -> Path:
    return root / "manuscripts" / modid / "patchouli"


def locale_root(root: Path, modid: str, locale: str) -> Path:
    return patchouli_dir(root, modid) / "locales" / locale


def locale_categories_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "categories"


def locale_entries_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "entries"


def locale_pages_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "pages"


def category_paths(root: Path, modid: str, locale: str) -> list[Path]:
    return sorted(locale_categories_dir(root, modid, locale).glob("*.yml"), key=lambda path: path.as_posix())


def entry_paths(root: Path, modid: str, locale: str) -> list[Path]:
    return sorted(locale_entries_dir(root, modid, locale).rglob("*.yml"), key=lambda path: path.as_posix())


def existing_category_ids(root: Path, modid: str, locale: str) -> set[str]:
    ids = set()
    for category_path in category_paths(root, modid, locale):
        category = load_yaml_dict(category_path)
        ids.add(require_slug(category.get("id"), f"{category_path}: id"))
    return ids


def patchouli_book_output_path(root: Path, modid: str, namespace: str, book_id: str) -> Path:
    return root / "docs" / modid / "patchouli" / "data" / namespace / "patchouli_books" / book_id / "book.json"


def patchouli_assets_output_dir(root: Path, modid: str, namespace: str, book_id: str) -> Path:
    return root / "docs" / modid / "patchouli" / "assets" / namespace / "patchouli_books" / book_id


def patchouli_categories_output_dir(root: Path, modid: str, namespace: str, book_id: str, locale: str) -> Path:
    return patchouli_assets_output_dir(root, modid, namespace, book_id) / locale / "categories"


def patchouli_entries_output_dir(root: Path, modid: str, namespace: str, book_id: str, locale: str) -> Path:
    return patchouli_assets_output_dir(root, modid, namespace, book_id) / locale / "entries"


def resolve_page(
    entry_path: Path, raw_page: dict[str, Any], root: Path, modid: str, locale: str, entry_id: str
) -> dict[str, Any]:
    page = dict(raw_page)
    source_name = page.pop("source", None)
    if source_name:
        source_path = locale_pages_dir(root, modid, locale) / entry_id / str(source_name)
        frontmatter, body = load_markdown_document(source_path)
        for key, value in frontmatter.items():
            page.setdefault(key, value)
        if body and "text" not in page:
            page["text"] = body

    page_type = str(page.get("type") or "")
    if not page_type:
        raise ManualError(f"{entry_path}: page is missing type")
    if ":" not in page_type:
        page["type"] = f"patchouli:{page_type}"
    return page


def load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ManualError(f"Missing YAML file: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ManualError(f"{path}: expected a YAML mapping")
    return payload


def load_markdown_document(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        raise ManualError(f"Missing page source: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text.strip()

    _, _, remainder = text.partition("---\n")
    frontmatter_text, separator, body = remainder.partition("\n---\n")
    if not separator:
        raise ManualError(f"{path}: markdown front matter is not closed")

    frontmatter = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(frontmatter, dict):
        raise ManualError(f"{path}: front matter must be a YAML mapping")
    return frontmatter, body.strip()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def require_slug(value: Any, label: str) -> str:
    candidate = str(value or "")
    if not candidate:
        raise ManualError(f"{label} is required")
    if not SLUG_PATTERN.fullmatch(candidate):
        raise ManualError(f"{label} must match {SLUG_PATTERN.pattern}")
    return candidate


def ensure_missing(path: Path) -> None:
    if path.exists():
        raise ManualError(f"Refusing to overwrite existing file: {path}")
