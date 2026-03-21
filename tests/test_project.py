from __future__ import annotations

import json
import shutil
from pathlib import Path

from my_mod_manual.project import build_patchouli, validate_repository


def copy_fixture_repo(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "mods.toml", tmp_path / "mods.toml")
    shutil.copytree(root / "manuscripts", tmp_path / "manuscripts")
    return tmp_path


def test_validate_repository_passes_for_sample(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    assert validate_repository(root) == []


def test_build_patchouli_writes_expected_files(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    written_files = build_patchouli(root, "examplemod")

    output_root = root / "docs" / "examplemod" / "patchouli"
    expected = {
        output_root / "data" / "examplemod" / "patchouli_books" / "examplemod" / "book.json",
        output_root / "assets" / "examplemod" / "patchouli_books" / "examplemod" / "en_us" / "categories" / "getting_started.json",
        output_root / "assets" / "examplemod" / "patchouli_books" / "examplemod" / "en_us" / "entries" / "first_steps.json",
        output_root / "assets" / "examplemod" / "lang" / "en_us.json",
    }
    assert expected.issubset(set(written_files))


def test_build_patchouli_writes_multilocale_book(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    written_files = build_patchouli(root, "apprenticecodex")

    output_root = root / "docs" / "apprenticecodex" / "patchouli"
    expected = {
        output_root / "data" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "book.json",
        output_root / "assets" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "en_us" / "categories" / "items.json",
        output_root / "assets" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "en_us" / "entries" / "items" / "explorers_codex.json",
        output_root / "assets" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "ja_jp" / "categories" / "items.json",
        output_root / "assets" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "ja_jp" / "entries" / "items" / "explorers_codex.json",
        output_root / "assets" / "apprenticecodex" / "lang" / "en_us.json",
        output_root / "assets" / "apprenticecodex" / "lang" / "ja_jp.json",
    }
    assert expected.issubset(set(written_files))


def test_build_patchouli_preserves_book_translation_keys(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    build_patchouli(root, "apprenticecodex")

    book_path = (
        root
        / "docs"
        / "apprenticecodex"
        / "patchouli"
        / "data"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "book.json"
    )
    payload = json.loads(book_path.read_text(encoding="utf-8"))
    assert payload["name"] == "patchouli.apprenticecodex.apprentice_codex.name"
    assert payload["landing_text"] == "patchouli.apprenticecodex.apprentice_codex.landing_text"
    assert payload["i18n"] is True


def test_build_patchouli_generates_lang_entries_from_shared_and_locale_override(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    build_patchouli(root, "apprenticecodex")

    en_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "en_us.json"
    ja_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "ja_jp.json"
    ja_entry_path = (
        root
        / "docs"
        / "apprenticecodex"
        / "patchouli"
        / "assets"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "ja_jp"
        / "entries"
        / "items"
        / "explorers_codex.json"
    )

    en_lang = json.loads(en_lang_path.read_text(encoding="utf-8"))
    ja_lang = json.loads(ja_lang_path.read_text(encoding="utf-8"))
    ja_entry = json.loads(ja_entry_path.read_text(encoding="utf-8"))

    assert en_lang["patchouli.apprenticecodex.apprentice_codex.category.items.name"] == "Items"
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.category.items.name"] == "アイテム"
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"] == "探索者の写本"
    assert ja_entry["name"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"
    assert ja_entry["pages"][0]["text"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.00_spotlight.text"


def test_validate_repository_detects_missing_page(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    missing_page = (
        root / "manuscripts" / "examplemod" / "patchouli" / "shared" / "pages" / "first_steps" / "01-next-steps.md"
    )
    missing_page.unlink()

    errors = validate_repository(root, "examplemod")
    assert any("Missing page source" in error for error in errors)


def test_locale_override_can_replace_page_list(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    override_entry = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "locales"
        / "ja_jp"
        / "entries"
        / "items"
        / "explorers_codex.yml"
    )
    override_entry.write_text(
        "\n".join(
            [
                "id: explorers_codex",
                'name: "探索者の写本"',
                "pages:",
                "  - type: spotlight",
                "    source: 00-spotlight.md",
                "  - type: text",
                "    source: 01-sample-role.md",
                "  - type: text",
                "    source: 02-extra-note.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    extra_page = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "locales"
        / "ja_jp"
        / "pages"
        / "explorers_codex"
        / "02-extra-note.md"
    )
    extra_page.parent.mkdir(parents=True, exist_ok=True)
    extra_page.write_text(
        "\n".join(
            [
                "---",
                'title: "補足"',
                "---",
                "",
                "日本語だけで補足したい内容です。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    build_patchouli(root, "apprenticecodex")

    en_entry_path = (
        root
        / "docs"
        / "apprenticecodex"
        / "patchouli"
        / "assets"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "en_us"
        / "entries"
        / "items"
        / "explorers_codex.json"
    )
    ja_entry_path = (
        root
        / "docs"
        / "apprenticecodex"
        / "patchouli"
        / "assets"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "ja_jp"
        / "entries"
        / "items"
        / "explorers_codex.json"
    )

    en_entry = json.loads(en_entry_path.read_text(encoding="utf-8"))
    ja_entry = json.loads(ja_entry_path.read_text(encoding="utf-8"))

    assert len(en_entry["pages"]) == 2
    assert len(ja_entry["pages"]) == 3
    assert ja_entry["pages"][2]["text"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.02_extra_note.text"
