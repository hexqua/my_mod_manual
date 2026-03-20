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

        book = load_yaml_dict(patchouli_dir(root, mod.modid) / "book.yml")
        locale = str(book.pop("i18n", DEFAULT_LOCALE))
        output_root = root / "docs" / mod.modid / "patchouli" / locale
        categories_root = output_root / "categories"
        entries_root = output_root / "entries"
        categories_root.mkdir(parents=True, exist_ok=True)
        entries_root.mkdir(parents=True, exist_ok=True)

        write_json(output_root / "book.json", book)
        written_files.append(output_root / "book.json")

        for category_path in sorted((patchouli_dir(root, mod.modid) / "categories").glob("*.yml")):
            category = load_yaml_dict(category_path)
            category_id = require_slug(category.get("id"), f"{category_path}: id")
            write_json(categories_root / f"{category_id}.json", category)
            written_files.append(categories_root / f"{category_id}.json")

        category_ids = existing_category_ids(root, mod.modid)
        for entry_path in sorted((patchouli_dir(root, mod.modid) / "entries").glob("*.yml")):
            entry = load_yaml_dict(entry_path)
            entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
            category_id = require_slug(entry.get("category"), f"{entry_path}: category")
            if category_id not in category_ids:
                raise ManualError(f"{entry_path}: unknown category '{category_id}'")

            pages = []
            for raw_page in entry.get("pages", []):
                pages.append(resolve_page(entry_path, raw_page, root, mod.modid, entry_id))

            entry["category"] = f"{mod.modid}:{category_id}"
            entry["pages"] = pages
            write_json(entries_root / f"{entry_id}.json", entry)
            written_files.append(entries_root / f"{entry_id}.json")

    return written_files


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
    (patchouli_root / "categories").mkdir(parents=True, exist_ok=True)
    (patchouli_root / "entries").mkdir(parents=True, exist_ok=True)
    (patchouli_root / "pages").mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "patchouli").mkdir(parents=True, exist_ok=True)
    (root / "docs" / modid / "modonomicon").mkdir(parents=True, exist_ok=True)

    book_path = patchouli_root / "book.yml"
    if not book_path.exists():
        book_path.write_text(
            "\n".join(
                [
                    f'name: "{display_name} Manual"',
                    "landing_text: |",
                    f"  Welcome to the {display_name} manual.",
                    "version: 1",
                    f"i18n: {DEFAULT_LOCALE}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    modonomicon_keep = root / "docs" / modid / "modonomicon" / ".gitkeep"
    modonomicon_keep.write_text("", encoding="utf-8")
    return [root / "mods.toml", book_path, modonomicon_keep]


def scaffold_category(root: Path, modid: str, category_id: str, name: str) -> Path:
    modid = require_slug(modid, "modid")
    category_id = require_slug(category_id, "category_id")
    path = patchouli_dir(root, modid) / "categories" / f"{category_id}.yml"
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


def scaffold_entry(root: Path, modid: str, entry_id: str, category_id: str, name: str) -> list[Path]:
    modid = require_slug(modid, "modid")
    entry_id = require_slug(entry_id, "entry_id")
    category_id = require_slug(category_id, "category_id")

    entry_path = patchouli_dir(root, modid) / "entries" / f"{entry_id}.yml"
    page_dir = patchouli_dir(root, modid) / "pages" / entry_id
    page_path = page_dir / "00-introduction.md"

    ensure_missing(entry_path)
    ensure_missing(page_path)
    page_dir.mkdir(parents=True, exist_ok=True)

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
    base_dir = patchouli_dir(root, mod.modid)
    book_path = base_dir / "book.yml"
    if not book_path.exists():
        errors.append(f"{mod.modid}: missing {book_path}")
        return errors

    try:
        load_yaml_dict(book_path)
    except ManualError as exc:
        errors.append(str(exc))

    categories = {}
    for category_path in sorted((base_dir / "categories").glob("*.yml")):
        try:
            category = load_yaml_dict(category_path)
            category_id = require_slug(category.get("id"), f"{category_path}: id")
            if category_id in categories:
                errors.append(f"{category_path}: duplicated category id '{category_id}'")
            categories[category_id] = category_path
        except ManualError as exc:
            errors.append(str(exc))

    for entry_path in sorted((base_dir / "entries").glob("*.yml")):
        try:
            entry = load_yaml_dict(entry_path)
            entry_id = require_slug(entry.get("id"), f"{entry_path}: id")
            category_id = require_slug(entry.get("category"), f"{entry_path}: category")
            if category_id not in categories:
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
                    source_path = base_dir / "pages" / entry_id / str(source_name)
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


def patchouli_dir(root: Path, modid: str) -> Path:
    return root / "manuscripts" / modid / "patchouli"


def existing_category_ids(root: Path, modid: str) -> set[str]:
    category_dir = patchouli_dir(root, modid) / "categories"
    ids = set()
    for category_path in sorted(category_dir.glob("*.yml")):
        category = load_yaml_dict(category_path)
        ids.add(require_slug(category.get("id"), f"{category_path}: id"))
    return ids


def resolve_page(
    entry_path: Path, raw_page: dict[str, Any], root: Path, modid: str, entry_id: str
) -> dict[str, Any]:
    page = dict(raw_page)
    source_name = page.pop("source", None)
    if source_name:
        source_path = patchouli_dir(root, modid) / "pages" / entry_id / str(source_name)
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

