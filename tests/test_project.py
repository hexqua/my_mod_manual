from __future__ import annotations

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
    payload = book_path.read_text(encoding="utf-8")
    assert '"name": "patchouli.apprenticecodex.apprentice_codex.name"' in payload
    assert '"landing_text": "patchouli.apprenticecodex.apprentice_codex.landing_text"' in payload


def test_validate_repository_detects_missing_page(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    missing_page = (
        root
        / "manuscripts"
        / "examplemod"
        / "patchouli"
        / "locales"
        / "en_us"
        / "pages"
        / "first_steps"
        / "01-next-steps.md"
    )
    missing_page.unlink()

    errors = validate_repository(root, "examplemod")
    assert any("page source does not exist" in error for error in errors)
