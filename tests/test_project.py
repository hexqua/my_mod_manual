from __future__ import annotations

import json
import shutil
from pathlib import Path

from my_mod_manual.project import build_patchouli, sync_en_us_stubs, validate_repository


def copy_fixture_repo(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "mods.toml", tmp_path / "mods.toml")
    shutil.copytree(root / "manuscripts", tmp_path / "manuscripts")
    return tmp_path


def append_shared_page_without_en_us_translation(root: Path) -> Path:
    entry_path = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "shared"
        / "entries"
        / "equipment_and_accessories"
        / "explorers_codex.yml"
    )
    page_path = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "shared"
        / "pages"
        / "equipment_and_accessories"
        / "explorers_codex"
        / "01-extra-note.md"
    )

    entry_path.write_text(
        entry_path.read_text(encoding="utf-8").rstrip()
        + "\n"
        + "\n".join(
            [
                "  - type: text",
                "    source: 01-extra-note.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        "\n".join(
            [
                "---",
                'title: "追加メモ"',
                "---",
                "",
                "日本語の追加メモです。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return page_path


def test_validate_repository_passes_for_sample(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    sync_en_us_stubs(root, "apprenticecodex")
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


def test_build_patchouli_skips_non_en_us_json_when_only_text_differs(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    sync_en_us_stubs(root, "apprenticecodex")
    written_files = build_patchouli(root, "apprenticecodex")

    output_root = root / "docs" / "apprenticecodex" / "patchouli"
    expected = {
        output_root / "data" / "apprenticecodex" / "patchouli_books" / "apprentice_codex" / "book.json",
        output_root
        / "assets"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "en_us"
        / "categories"
        / "equipment_and_accessories.json",
        output_root
        / "assets"
        / "apprenticecodex"
        / "patchouli_books"
        / "apprentice_codex"
        / "en_us"
        / "entries"
        / "equipment_and_accessories"
        / "explorers_codex.json",
        output_root / "assets" / "apprenticecodex" / "lang" / "en_us.json",
        output_root / "assets" / "apprenticecodex" / "lang" / "ja_jp.json",
    }
    assert expected.issubset(set(written_files))
    assert output_root.joinpath("assets", "apprenticecodex", "patchouli_books", "apprentice_codex", "ja_jp").exists() is False


def test_build_patchouli_preserves_book_translation_keys(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    sync_en_us_stubs(root, "apprenticecodex")
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


def test_build_patchouli_generates_lang_entries_from_source_locale_and_override(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    sync_en_us_stubs(root, "apprenticecodex")
    build_patchouli(root, "apprenticecodex")

    en_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "en_us.json"
    ja_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "ja_jp.json"
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
        / "equipment_and_accessories"
        / "explorers_codex.json"
    )

    en_lang = json.loads(en_lang_path.read_text(encoding="utf-8"))
    ja_lang = json.loads(ja_lang_path.read_text(encoding="utf-8"))
    en_entry = json.loads(en_entry_path.read_text(encoding="utf-8"))

    assert en_lang["patchouli.apprenticecodex.apprentice_codex.name"] == "Apprentice's Codex"
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.subtitle"] == "testtest"
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"] == "Equipment & Accessories"
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"] == "防具・装飾具"
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"] == "Explorer's Codex"
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"] == "探索者の写本"
    assert en_entry["pages"][0]["text"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.00_spotlight.text"
    assert en_entry["pages"][0]["item"] == "apprenticecodex:explorers_codex"


def test_validate_repository_detects_missing_page(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    missing_page = (
        root
        / "manuscripts"
        / "examplemod"
        / "patchouli"
        / "shared"
        / "pages"
        / "getting_started"
        / "first_steps"
        / "01-next-steps.md"
    )
    missing_page.unlink()

    errors = validate_repository(root, "examplemod")
    assert any("Missing page source" in error for error in errors)


def test_locale_override_can_replace_page_list_and_emit_locale_json(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    sync_en_us_stubs(root, "apprenticecodex")
    override_entry = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "locales"
        / "ja_jp"
        / "entries"
        / "equipment_and_accessories"
        / "explorers_codex.yml"
    )
    override_entry.parent.mkdir(parents=True, exist_ok=True)
    override_entry.write_text(
        "\n".join(
            [
                "id: explorers_codex",
                'name: "探索者の写本"',
                "pages:",
                "  - type: spotlight",
                "    source: 00-spotlight.md",
                "  - type: text",
                "    source: 01-extra-note.md",
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
        / "equipment_and_accessories"
        / "explorers_codex"
        / "01-extra-note.md"
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
        / "equipment_and_accessories"
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
        / "equipment_and_accessories"
        / "explorers_codex.json"
    )

    en_entry = json.loads(en_entry_path.read_text(encoding="utf-8"))
    ja_entry = json.loads(ja_entry_path.read_text(encoding="utf-8"))

    assert len(en_entry["pages"]) == 1
    assert len(ja_entry["pages"]) == 2
    assert ja_entry["pages"][1]["text"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.01_extra_note.text"


def test_validate_repository_requires_en_us_page_for_non_en_us_source_locale(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    append_shared_page_without_en_us_translation(root)

    errors = validate_repository(root, "apprenticecodex")

    assert any("missing default locale page source" in error for error in errors)


def test_sync_en_us_stubs_creates_missing_stub_and_validate_flag_controls_it(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    append_shared_page_without_en_us_translation(root)

    created = sync_en_us_stubs(root, "apprenticecodex")

    stub_path = (
        root
        / "manuscripts"
        / "apprenticecodex"
        / "patchouli"
        / "locales"
        / "en_us"
        / "pages"
        / "equipment_and_accessories"
        / "explorers_codex"
        / "01-extra-note.md"
    )
    assert stub_path in created

    stub_text = stub_path.read_text(encoding="utf-8")
    assert "translation_status: stub" in stub_text
    assert "TODO: Translate - 追加メモ" in stub_text
    assert "TODO: This page is not translated yet. Source locale: ja_jp." in stub_text

    strict_errors = validate_repository(root, "apprenticecodex")
    allowed_errors = validate_repository(root, "apprenticecodex", allow_en_us_stubs=True)

    assert any("en_us stub remains" in error for error in strict_errors)
    assert allowed_errors == []


def test_build_patchouli_requires_synced_en_us_pages_for_non_en_us_source_locale(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    append_shared_page_without_en_us_translation(root)

    try:
        build_patchouli(root, "apprenticecodex")
    except Exception as exc:
        message = str(exc)
    else:
        raise AssertionError("build_patchouli should fail when en_us page translation is missing")

    assert "Missing default locale page source" in message

    sync_en_us_stubs(root, "apprenticecodex")
    build_patchouli(root, "apprenticecodex")
