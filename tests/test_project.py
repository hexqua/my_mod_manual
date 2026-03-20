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

    output_root = root / "docs" / "examplemod" / "patchouli" / "en_us"
    expected = {
        output_root / "book.json",
        output_root / "categories" / "getting_started.json",
        output_root / "entries" / "first_steps.json",
    }
    assert expected.issubset(set(written_files))


def test_validate_repository_detects_missing_page(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path)
    missing_page = root / "manuscripts" / "examplemod" / "patchouli" / "pages" / "first_steps" / "01-next-steps.md"
    missing_page.unlink()

    errors = validate_repository(root, "examplemod")
    assert any("page source does not exist" in error for error in errors)
