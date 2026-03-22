from __future__ import annotations

import json
import re
import shutil
import tomllib
from pathlib import Path
from typing import Any

import yaml

from .models import Manifest, ModSpec

DEFAULT_LOCALE = "en_us"
SUPPORTED_FORMATS = {"patchouli", "modonomicon"}
SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")
TRANSLATION_KEY_PATTERN = re.compile(r"^[a-z0-9_.-]+$")
NON_SLUG_CHARS_PATTERN = re.compile(r"[^a-z0-9]+")
BOOK_TRANSLATABLE_FIELDS = ("name", "landing_text", "subtitle")
CATEGORY_TRANSLATABLE_FIELDS = ("name", "description")
ENTRY_TRANSLATABLE_FIELDS = ("name",)
PAGE_TRANSLATABLE_FIELDS = ("title", "text")


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

        book_path = patchouli_dir(root, mod.modid) / "book.yml"
        book, book_namespace, book_id, source_locale, locales = load_book_settings(root, mod.modid)
        shared_categories = load_shared_categories(root, mod.modid)
        shared_entries = load_shared_entries(root, mod.modid)
        book_payload, source_book_values = normalize_book_payload(book, book_path, book_namespace, book_id)

        cleanup_patchouli_outputs(root, mod.modid, book_namespace, book_id)

        book_output_path = patchouli_book_output_path(root, mod.modid, book_namespace, book_id)
        book_output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(book_output_path, book_payload)
        written_files.append(book_output_path)

        locale_outputs: dict[str, tuple[dict[str, dict[str, Any]], dict[Path, dict[str, Any]], dict[str, str]]] = {}
        ordered_locales = ordered_patchouli_locales(locales)
        for locale in ordered_locales:
            book_override = load_locale_book_override(root, mod.modid, locale)
            seed_book_lang = resolve_book_lang_entries(
                book_payload,
                source_book_values,
                book_override,
                locale,
                source_locale,
            )
            locale_outputs[locale] = build_patchouli_locale_outputs(
                root,
                mod.modid,
                locale,
                source_locale,
                book_namespace,
                book_id,
                shared_categories,
                shared_entries,
                seed_book_lang,
            )

        default_category_payloads, default_entry_payloads, _ = locale_outputs[DEFAULT_LOCALE]
        for locale in ordered_locales:
            category_payloads, entry_payloads, lang_entries = locale_outputs[locale]

            if locale != DEFAULT_LOCALE:
                category_payloads = {
                    category_id: payload
                    for category_id, payload in category_payloads.items()
                    if payload != default_category_payloads[category_id]
                }
                entry_payloads = {
                    relative_path: payload
                    for relative_path, payload in entry_payloads.items()
                    if payload != default_entry_payloads[relative_path]
                }

            lang_output_path = patchouli_lang_output_path(root, mod.modid, book_namespace, locale)
            lang_output_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(lang_output_path, lang_entries)
            written_files.append(lang_output_path)

            if category_payloads:
                categories_root = patchouli_categories_output_dir(root, mod.modid, book_namespace, book_id, locale)
                categories_root.mkdir(parents=True, exist_ok=True)
                for category_id, payload in category_payloads.items():
                    output_path = categories_root / f"{category_id}.json"
                    write_json(output_path, payload)
                    written_files.append(output_path)

            if entry_payloads:
                entries_root = patchouli_entries_output_dir(root, mod.modid, book_namespace, book_id, locale)
                entries_root.mkdir(parents=True, exist_ok=True)
                for relative_path, payload in entry_payloads.items():
                    output_path = entries_root / relative_path.with_suffix(".json")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    write_json(output_path, payload)
                    written_files.append(output_path)

    return written_files


def build_patchouli_locale_outputs(
    root: Path,
    modid: str,
    locale: str,
    source_locale: str,
    namespace: str,
    book_id: str,
    shared_categories: dict[str, tuple[Path, dict[str, Any]]],
    shared_entries: dict[Path, tuple[Path, dict[str, Any]]],
    seed_book_lang: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[Path, dict[str, Any]], dict[str, str]]:
    category_overrides = load_locale_category_overrides(root, modid, locale, shared_categories)
    entry_overrides = load_locale_entry_overrides(root, modid, locale, shared_entries)
    lang_entries = dict(seed_book_lang)
    category_payloads: dict[str, dict[str, Any]] = {}
    entry_payloads: dict[Path, dict[str, Any]] = {}

    for category_id in sorted(shared_categories):
        _, shared_category = shared_categories[category_id]
        category = merge_patchouli_document(shared_category, category_overrides.get(category_id))
        payload = dict(category)
        payload.pop("id", None)
        localize_mapping_field(
            payload,
            "name",
            build_translation_key(namespace, book_id, "category", category_id, "name"),
            lang_entries,
        )
        localize_mapping_field(
            payload,
            "description",
            build_translation_key(namespace, book_id, "category", category_id, "description"),
            lang_entries,
        )
        category_payloads[category_id] = payload

    category_ids = set(shared_categories)
    for relative_path in sorted(shared_entries, key=lambda item: item.as_posix()):
        entry_path, shared_entry = shared_entries[relative_path]
        entry = merge_patchouli_document(shared_entry, entry_overrides.get(relative_path))
        entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
        category_id = require_slug(entry.get("category"), f"{entry_path}: category")
        if category_id not in category_ids:
            raise ManualError(f"{entry_path}: unknown category '{category_id}'")

        pages = entry.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ManualError(f"{entry_path}: pages must be a non-empty list")

        payload = dict(entry)
        payload.pop("id", None)
        payload["category"] = f"{namespace}:{category_id}"
        localize_mapping_field(
            payload,
            "name",
            build_translation_key(namespace, book_id, "entry", entry_id, "name"),
            lang_entries,
        )

        resolved_pages = []
        for page_index, raw_page in enumerate(pages, start=1):
            page, source_name = resolve_page(
                entry_path,
                raw_page,
                root,
                modid,
                locale,
                source_locale,
                category_id,
                entry_id,
            )
            page_identifier = page_translation_identifier(source_name, page_index)
            localize_mapping_field(
                page,
                "title",
                build_translation_key(namespace, book_id, "entry", entry_id, "page", page_identifier, "title"),
                lang_entries,
            )
            localize_mapping_field(
                page,
                "text",
                build_translation_key(namespace, book_id, "entry", entry_id, "page", page_identifier, "text"),
                lang_entries,
            )
            resolved_pages.append(page)

        payload["pages"] = resolved_pages
        entry_payloads[relative_path] = payload

    return category_payloads, entry_payloads, lang_entries


def load_book_settings(root: Path, modid: str) -> tuple[dict[str, Any], str, str, str, tuple[str, ...]]:
    book_path = patchouli_dir(root, modid) / "book.yml"
    book = load_yaml_dict(book_path)
    book_namespace = require_slug(book.pop("book_namespace", modid), f"{book_path}: book_namespace")
    book_id = require_slug(book.pop("book_id", modid), f"{book_path}: book_id")
    locales = parse_book_locales(book, book_path)
    source_locale = parse_book_source_locale(book, book_path, locales)
    if DEFAULT_LOCALE not in locales:
        raise ManualError(f"{book_path}: locales must include {DEFAULT_LOCALE}")
    return book, book_namespace, book_id, source_locale, locales


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


def parse_book_source_locale(book: dict[str, Any], book_path: Path, locales: tuple[str, ...]) -> str:
    source_locale = require_slug(book.pop("source_locale", DEFAULT_LOCALE), f"{book_path}: source_locale")
    if source_locale not in locales:
        raise ManualError(f"{book_path}: source_locale '{source_locale}' must be included in locales")
    return source_locale


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
    (shared_categories_dir(root, modid)).mkdir(parents=True, exist_ok=True)
    (shared_entries_dir(root, modid)).mkdir(parents=True, exist_ok=True)
    (shared_pages_dir(root, modid)).mkdir(parents=True, exist_ok=True)
    (patchouli_root / "locales" / DEFAULT_LOCALE).mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "patchouli").mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "modonomicon").mkdir(parents=True, exist_ok=True)

    book_path = patchouli_root / "book.yml"
    if not book_path.exists():
        book_path.write_text(
            "\n".join(
                [
                    f"book_id: {modid}",
                    f"book_namespace: {modid}",
                    f"source_locale: {DEFAULT_LOCALE}",
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


def scaffold_category(root: Path, modid: str, category_id: str, name: str, locale: str | None = None) -> Path:
    modid = require_slug(modid, "modid")
    category_id = require_slug(category_id, "category_id")
    locale = require_optional_slug(locale, "locale")

    if locale is None:
        path = shared_categories_dir(root, modid) / f"{category_id}.yml"
        lines = [
            f"id: {category_id}",
            f'name: "{name}"',
            "description: |",
            f"  Overview for {name}.",
            "icon: minecraft:book",
            "sortnum: 0",
            "",
        ]
    else:
        path = locale_categories_dir(root, modid, locale) / f"{category_id}.yml"
        lines = [
            f"id: {category_id}",
            f'name: "{name}"',
            "description: |",
            f"  Localized overview for {name}.",
            "",
        ]

    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_missing(path)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def scaffold_entry(
    root: Path, modid: str, entry_id: str, category_id: str, name: str, locale: str | None = None
) -> list[Path]:
    modid = require_slug(modid, "modid")
    entry_id = require_slug(entry_id, "entry_id")
    category_id = require_slug(category_id, "category_id")
    locale = require_optional_slug(locale, "locale")

    if locale is None:
        entry_path = shared_entries_dir(root, modid) / category_id / f"{entry_id}.yml"
        page_dir = shared_pages_dir(root, modid) / category_id / entry_id
        entry_lines = [
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
    else:
        entry_path = locale_entries_dir(root, modid, locale) / category_id / f"{entry_id}.yml"
        page_dir = locale_pages_dir(root, modid, locale) / category_id / entry_id
        entry_lines = [
            f"id: {entry_id}",
            f'name: "{name}"',
            "",
        ]

    page_path = page_dir / "00-introduction.md"
    ensure_missing(entry_path)
    ensure_missing(page_path)
    page_dir.mkdir(parents=True, exist_ok=True)
    entry_path.parent.mkdir(parents=True, exist_ok=True)

    entry_path.write_text("\n".join(entry_lines), encoding="utf-8")
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
        book, book_namespace, book_id, source_locale, locales = load_book_settings(root, mod.modid)
        shared_categories = load_shared_categories(root, mod.modid)
        shared_entries = load_shared_entries(root, mod.modid)
        normalize_book_payload(book, book_path, book_namespace, book_id)
    except ManualError as exc:
        errors.append(str(exc))
        return errors

    for relative_path, (entry_path, entry) in shared_entries.items():
        try:
            validate_entry_document(entry_path, entry, set(shared_categories))
            validate_entry_pages(root, mod.modid, source_locale, entry_path, entry)
        except ManualError as exc:
            errors.append(str(exc))

    for locale in locales:
        try:
            load_locale_book_override(root, mod.modid, locale)
            category_overrides = load_locale_category_overrides(root, mod.modid, locale, shared_categories)
            entry_overrides = load_locale_entry_overrides(root, mod.modid, locale, shared_entries)
        except ManualError as exc:
            errors.append(str(exc))
            continue

        entries_seen: set[str] = set()
        for relative_path in sorted(shared_entries, key=lambda item: item.as_posix()):
            shared_path, shared_entry = shared_entries[relative_path]
            entry = merge_patchouli_document(shared_entry, entry_overrides.get(relative_path))

            try:
                entry_id = require_slug(entry.get("id"), f"{shared_path}: id")
                if entry_id in entries_seen:
                    errors.append(f"{shared_path}: duplicated entry id '{entry_id}'")
                entries_seen.add(entry_id)
                validate_entry_document(shared_path, entry, set(shared_categories))
                validate_entry_pages(root, mod.modid, locale, shared_path, entry, source_locale)
            except ManualError as exc:
                errors.append(str(exc))

        for category_id, override in category_overrides.items():
            if category_id not in shared_categories:
                errors.append(f"{override[0]}: category '{category_id}' is not defined in shared")

    return errors


def validate_entry_document(entry_path: Path, entry: dict[str, Any], category_ids: set[str]) -> None:
    category_id = require_slug(entry.get("category"), f"{entry_path}: category")
    if category_id not in category_ids:
        raise ManualError(f"{entry_path}: category '{category_id}' is not defined")

    pages = entry.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ManualError(f"{entry_path}: pages must be a non-empty list")

    for page_index, raw_page in enumerate(pages, start=1):
        if not isinstance(raw_page, dict):
            raise ManualError(f"{entry_path}: pages[{page_index}] must be a mapping")
        page_type = str(raw_page.get("type") or "")
        if not page_type:
            raise ManualError(f"{entry_path}: pages[{page_index}] is missing type")


def validate_entry_pages(
    root: Path,
    modid: str,
    locale: str,
    entry_path: Path,
    entry: dict[str, Any],
    source_locale: str | None = None,
) -> None:
    entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
    category_id = require_slug(entry.get("category"), f"{entry_path}: category")
    page_dir = page_dir_for_entry(category_id, entry_id)
    seen_sources: set[str] = set()
    for raw_page in entry.get("pages", []):
        source_name = raw_page.get("source")
        if not source_name:
            continue

        source_text = str(source_name)
        if source_text in seen_sources:
            raise ManualError(f"{entry_path}: duplicated page source '{source_text}'")
        seen_sources.add(source_text)

        source_path = resolve_page_source_path(root, modid, locale, source_locale or locale, page_dir, source_text)
        try:
            load_markdown_document(source_path)
        except ManualError as exc:
            raise ManualError(str(exc)) from exc


def load_shared_categories(root: Path, modid: str) -> dict[str, tuple[Path, dict[str, Any]]]:
    categories: dict[str, tuple[Path, dict[str, Any]]] = {}
    for category_path in shared_category_paths(root, modid):
        category = load_yaml_dict(category_path)
        category_id = require_slug(category.get("id"), f"{category_path}: id")
        if category_id in categories:
            raise ManualError(f"{category_path}: duplicated category id '{category_id}'")
        categories[category_id] = (category_path, category)
    return categories


def load_shared_entries(root: Path, modid: str) -> dict[Path, tuple[Path, dict[str, Any]]]:
    entries: dict[Path, tuple[Path, dict[str, Any]]] = {}
    entry_ids: dict[str, Path] = {}
    entries_dir = shared_entries_dir(root, modid)
    for entry_path in shared_entry_paths(root, modid):
        entry = load_yaml_dict(entry_path)
        entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
        if entry_id in entry_ids:
            raise ManualError(f"{entry_path}: duplicated entry id '{entry_id}'")
        relative_path = entry_path.relative_to(entries_dir)
        entries[relative_path] = (entry_path, entry)
        entry_ids[entry_id] = entry_path
    return entries


def load_locale_category_overrides(
    root: Path, modid: str, locale: str, shared_categories: dict[str, tuple[Path, dict[str, Any]]]
) -> dict[str, tuple[Path, dict[str, Any]]]:
    overrides: dict[str, tuple[Path, dict[str, Any]]] = {}
    for category_path in locale_category_paths(root, modid, locale):
        category = load_yaml_dict(category_path)
        fallback_id = category_path.stem
        category_id = require_slug(category.get("id", fallback_id), f"{category_path}: id")
        if category_id not in shared_categories:
            raise ManualError(f"{category_path}: category '{category_id}' is not defined in shared")
        shared_id = require_slug(shared_categories[category_id][1].get("id"), f"{shared_categories[category_id][0]}: id")
        if category_id != shared_id:
            raise ManualError(f"{category_path}: id must match shared category '{shared_id}'")
        if category_id in overrides:
            raise ManualError(f"{category_path}: duplicated category override '{category_id}'")
        overrides[category_id] = (category_path, category)
    return overrides


def load_locale_book_override(root: Path, modid: str, locale: str) -> dict[str, str]:
    path = locale_root(root, modid, locale) / "book.yml"
    if not path.exists():
        return {}

    payload = load_yaml_dict(path)
    unknown_keys = sorted(set(payload) - set(BOOK_TRANSLATABLE_FIELDS))
    if unknown_keys:
        raise ManualError(f"{path}: unsupported keys: {', '.join(unknown_keys)}")

    override: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(value, str) or not value:
            raise ManualError(f"{path}: {key} must be a non-empty string")
        if looks_like_translation_key(value):
            raise ManualError(f"{path}: {key} must be raw localized text, not a translation key")
        override[key] = value
    return override


def load_locale_entry_overrides(
    root: Path, modid: str, locale: str, shared_entries: dict[Path, tuple[Path, dict[str, Any]]]
) -> dict[Path, tuple[Path, dict[str, Any]]]:
    overrides: dict[Path, tuple[Path, dict[str, Any]]] = {}
    entries_dir = locale_entries_dir(root, modid, locale)
    for entry_path in locale_entry_paths(root, modid, locale):
        relative_path = entry_path.relative_to(entries_dir)
        if relative_path not in shared_entries:
            raise ManualError(f"{entry_path}: locale entry override does not exist in shared")

        entry = load_yaml_dict(entry_path)
        shared_path, shared_entry = shared_entries[relative_path]
        shared_id = require_slug(shared_entry.get("id"), f"{shared_path}: id")
        override_id = entry.get("id", shared_id)
        if require_slug(override_id, f"{entry_path}: id") != shared_id:
            raise ManualError(f"{entry_path}: id must match shared entry '{shared_id}'")
        overrides[relative_path] = (entry_path, entry)
    return overrides


def normalize_book_payload(
    book: dict[str, Any], book_path: Path, namespace: str, book_id: str
) -> tuple[dict[str, Any], dict[str, str]]:
    payload = dict(book)
    source_values: dict[str, str] = {}

    for field in BOOK_TRANSLATABLE_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            continue
        if looks_like_translation_key(value):
            continue

        key = build_book_translation_key(namespace, book_id, field)
        source_values[field] = value
        payload[field] = key

    payload["i18n"] = True
    return payload, source_values


def merge_patchouli_document(
    shared_document: dict[str, Any], override: tuple[Path, dict[str, Any]] | None
) -> dict[str, Any]:
    merged = dict(shared_document)
    if override is None:
        return merged

    _, override_document = override
    merged.update(override_document)
    if "id" in shared_document:
        merged["id"] = shared_document["id"]
    return merged


def resolve_page(
    entry_path: Path,
    raw_page: dict[str, Any],
    root: Path,
    modid: str,
    locale: str,
    source_locale: str,
    category_id: str,
    entry_id: str,
) -> tuple[dict[str, Any], str | None]:
    if not isinstance(raw_page, dict):
        raise ManualError(f"{entry_path}: page must be a mapping")

    page = dict(raw_page)
    source_name = page.pop("source", None)
    source_text = str(source_name) if source_name else None

    if source_text:
        frontmatter, body = load_resolved_markdown_document(
            root,
            modid,
            locale,
            source_locale,
            page_dir_for_entry(category_id, entry_id),
            source_text,
        )
        for key, value in frontmatter.items():
            page.setdefault(key, value)
        if body and "text" not in page:
            page["text"] = body

    page_type = str(page.get("type") or "")
    if not page_type:
        raise ManualError(f"{entry_path}: page is missing type")
    if ":" not in page_type:
        page["type"] = f"patchouli:{page_type}"
    return page, source_text


def resolve_page_source_path(
    root: Path, modid: str, locale: str, source_locale: str, entry_page_dir: Path, source_name: str
) -> Path:
    locale_path = locale_pages_dir(root, modid, locale) / entry_page_dir / source_name
    if locale_path.exists():
        return locale_path

    shared_path = shared_pages_dir(root, modid) / entry_page_dir / source_name
    if shared_path.exists():
        return shared_path

    if source_locale != locale:
        source_locale_path = locale_pages_dir(root, modid, source_locale) / entry_page_dir / source_name
        if source_locale_path.exists():
            return source_locale_path

    raise ManualError(f"Missing page source: {locale_path} (fallback: {shared_path})")


def load_resolved_markdown_document(
    root: Path, modid: str, locale: str, source_locale: str, entry_page_dir: Path, source_name: str
) -> tuple[dict[str, Any], str]:
    shared_path = shared_pages_dir(root, modid) / entry_page_dir / source_name
    shared_frontmatter: dict[str, Any] = {}
    shared_body = ""
    if shared_path.exists():
        shared_frontmatter, shared_body = load_markdown_document(shared_path)

    locale_path = locale_pages_dir(root, modid, locale) / entry_page_dir / source_name
    if locale_path.exists():
        locale_frontmatter, locale_body = load_markdown_document(locale_path)
        shared_frontmatter.update(locale_frontmatter)
        return shared_frontmatter, locale_body

    if shared_path.exists():
        return shared_frontmatter, shared_body

    source_locale_path = locale_pages_dir(root, modid, source_locale) / entry_page_dir / source_name
    if source_locale_path.exists():
        return load_markdown_document(source_locale_path)

    raise ManualError(f"Missing page source: {locale_path} (fallback: {shared_path})")


def localize_mapping_field(payload: dict[str, Any], field: str, key: str, lang_entries: dict[str, str]) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        return
    if looks_like_translation_key(value):
        return
    payload[field] = key
    lang_entries[key] = value


def resolve_book_lang_entries(
    book_payload: dict[str, Any],
    source_book_values: dict[str, str],
    locale_override: dict[str, str],
    locale: str,
    source_locale: str,
) -> dict[str, str]:
    lang_entries: dict[str, str] = {}
    for field in BOOK_TRANSLATABLE_FIELDS:
        key = book_payload.get(field)
        if not isinstance(key, str) or not looks_like_translation_key(key):
            continue

        raw_value = locale_override.get(field)
        if raw_value is None and locale == source_locale:
            raw_value = source_book_values.get(field)
        if raw_value is None:
            continue
        lang_entries[key] = raw_value
    return lang_entries


def build_translation_key(namespace: str, book_id: str, *parts: str) -> str:
    return ".".join(("patchouli", namespace, book_id, *parts))


def build_book_translation_key(namespace: str, book_id: str, field: str) -> str:
    return ".".join(("patchouli", namespace, book_id, field))


def page_translation_identifier(source_name: str | None, page_index: int) -> str:
    if source_name:
        stem = Path(source_name).stem.lower()
        normalized = NON_SLUG_CHARS_PATTERN.sub("_", stem).strip("_")
        if normalized:
            return normalized
    return f"page_{page_index:02d}"


def looks_like_translation_key(value: str) -> bool:
    return "." in value and " " not in value and bool(TRANSLATION_KEY_PATTERN.fullmatch(value))


def ordered_patchouli_locales(locales: tuple[str, ...]) -> tuple[str, ...]:
    return (DEFAULT_LOCALE,) + tuple(locale for locale in locales if locale != DEFAULT_LOCALE)


def cleanup_patchouli_outputs(root: Path, modid: str, namespace: str, book_id: str) -> None:
    paths = [
        patchouli_book_output_path(root, modid, namespace, book_id).parent,
        patchouli_assets_output_dir(root, modid, namespace, book_id),
        patchouli_lang_output_path(root, modid, namespace, DEFAULT_LOCALE).parent,
    ]
    for path in paths:
        if path.exists():
            shutil.rmtree(path)


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


def require_optional_slug(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return require_slug(value, label)


def ensure_missing(path: Path) -> None:
    if path.exists():
        raise ManualError(f"Refusing to overwrite existing file: {path}")


def patchouli_dir(root: Path, modid: str) -> Path:
    return root / "manuscripts" / modid / "patchouli"


def shared_dir(root: Path, modid: str) -> Path:
    return patchouli_dir(root, modid) / "shared"


def shared_categories_dir(root: Path, modid: str) -> Path:
    return shared_dir(root, modid) / "categories"


def shared_entries_dir(root: Path, modid: str) -> Path:
    return shared_dir(root, modid) / "entries"


def shared_pages_dir(root: Path, modid: str) -> Path:
    return shared_dir(root, modid) / "pages"


def locale_root(root: Path, modid: str, locale: str) -> Path:
    return patchouli_dir(root, modid) / "locales" / locale


def locale_categories_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "categories"


def locale_entries_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "entries"


def locale_pages_dir(root: Path, modid: str, locale: str) -> Path:
    return locale_root(root, modid, locale) / "pages"


def page_dir_for_entry(category_id: str, entry_id: str) -> Path:
    return Path(category_id) / entry_id


def shared_category_paths(root: Path, modid: str) -> list[Path]:
    return sorted(shared_categories_dir(root, modid).glob("*.yml"), key=lambda path: path.as_posix())


def locale_category_paths(root: Path, modid: str, locale: str) -> list[Path]:
    return sorted(locale_categories_dir(root, modid, locale).glob("*.yml"), key=lambda path: path.as_posix())


def shared_entry_paths(root: Path, modid: str) -> list[Path]:
    return sorted(shared_entries_dir(root, modid).rglob("*.yml"), key=lambda path: path.as_posix())


def locale_entry_paths(root: Path, modid: str, locale: str) -> list[Path]:
    return sorted(locale_entries_dir(root, modid, locale).rglob("*.yml"), key=lambda path: path.as_posix())


def patchouli_book_output_path(root: Path, modid: str, namespace: str, book_id: str) -> Path:
    return root / "docs" / modid / "patchouli" / "data" / namespace / "patchouli_books" / book_id / "book.json"


def patchouli_assets_output_dir(root: Path, modid: str, namespace: str, book_id: str) -> Path:
    return root / "docs" / modid / "patchouli" / "assets" / namespace / "patchouli_books" / book_id


def patchouli_categories_output_dir(root: Path, modid: str, namespace: str, book_id: str, locale: str) -> Path:
    return patchouli_assets_output_dir(root, modid, namespace, book_id) / locale / "categories"


def patchouli_entries_output_dir(root: Path, modid: str, namespace: str, book_id: str, locale: str) -> Path:
    return patchouli_assets_output_dir(root, modid, namespace, book_id) / locale / "entries"


def patchouli_lang_output_path(root: Path, modid: str, namespace: str, locale: str) -> Path:
    return root / "docs" / modid / "patchouli" / "assets" / namespace / "lang" / f"{locale}.json"
