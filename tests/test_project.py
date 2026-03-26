from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from my_mod_manual.project import build_patchouli, sync_en_us_stubs, validate_repository


def write_text(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip("\n") + "\n", encoding="utf-8")
    return path


def create_fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path
    write_text(
        root,
        "mods.toml",
        """
        version = 1

        [[mods]]
        modid = "examplemod"
        display_name = "Example Mod"
        enabled_formats = ["patchouli"]

        [[mods]]
        modid = "apprenticecodex"
        display_name = "Apprentice's Codex"
        enabled_formats = ["patchouli"]
        """,
    )
    create_examplemod_fixture(root)
    create_apprenticecodex_fixture(root)
    return root


def create_examplemod_fixture(root: Path) -> None:
    # ここは build/validate の最小 fixture です。
    # 本文の意味はテストしておらず、「改行がどう処理されるか」だけを見ます。
    write_text(
        root,
        "manuscripts/examplemod/patchouli/book.yml",
        """
        book_id: examplemod
        book_namespace: examplemod
        source_locale: en_us
        name: "Example Mod Manual"
        landing_text: "Example landing text."
        version: "1"
        use_resource_pack: true
        model: patchouli:book_brown
        locales:
          - en_us
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/categories/getting_started.yml",
        """
        id: getting_started
        name: "Getting Started"
        description: |
          Example category line 1.
          Example category line 2.
        icon: minecraft:book
        sortnum: 0
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/categories/paragraphs.yml",
        """
        id: paragraphs
        name: "Paragraphs"
        description: |
          First block.

          Second block.
        icon: minecraft:paper
        sortnum: 1
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/categories/raw_notes.yml",
        """
        id: raw_notes
        name: "Raw Notes"
        description_breaks: false
        description: |
          Example raw notes line 1.
          Example raw notes line 2.
        icon: minecraft:paper
        sortnum: 2
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/entries/first_steps.yml",
        """
        id: first_steps
        name: "First Steps"
        category: getting_started
        icon: minecraft:paper
        sortnum: 0
        pages:
          - type: text
            source: 00-introduction.md
          - type: text
            source: 01-next-steps.md
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/pages/getting_started/first_steps/00-introduction.md",
        """
        ---
        title: "Intro"
        ---

        Example page line 1.
        Example page line 2.
        """,
    )
    write_text(
        root,
        "manuscripts/examplemod/patchouli/shared/pages/getting_started/first_steps/01-next-steps.md",
        """
        ---
        title: "Next"
        ---

        Example next line 1.
        Example next line 2.
        """,
    )


def create_apprenticecodex_fixture(root: Path) -> None:
    # apprenticecodex 側は source_locale != en_us の分岐確認用です。
    # 本文はダミーで、検証では「キーがどう出るか」「改行が消えるか」だけを見ます。
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/book.yml",
        """
        book_id: apprentice_codex
        book_namespace: apprenticecodex
        source_locale: ja_jp
        name: "Source Book"
        landing_text: |
          Source book line 1.
          Source book line 2.
        subtitle: "Source subtitle"
        version: "1"
        use_resource_pack: true
        model: patchouli:book_brown
        locales:
          - en_us
          - ja_jp
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/en_us/book.yml",
        """
        name: "English Book"
        landing_text: |
          English book line 1.
          English book line 2.
        subtitle: |
          English subtitle line 1.
          English subtitle line 2.
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/shared/categories/equipment_and_accessories.yml",
        """
        id: equipment_and_accessories
        name: "Source Category"
        description: |
          Source category line 1.
          Source category line 2.
        icon: apprenticecodex:explorers_codex
        sortnum: 0
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/en_us/categories/equipment_and_accessories.yml",
        """
        id: equipment_and_accessories
        name: "English Category"
        description: |
          English category line 1.
          English category line 2.
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/shared/entries/equipment_and_accessories/explorers_codex.yml",
        """
        id: explorers_codex
        name: "Source Entry"
        category: equipment_and_accessories
        icon: apprenticecodex:explorers_codex
        sortnum: 0
        pages:
          - type: spotlight
            source: 00-spotlight.md
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/en_us/entries/equipment_and_accessories/explorers_codex.yml",
        """
        id: explorers_codex
        name: "English Entry"
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/shared/pages/equipment_and_accessories/explorers_codex/00-spotlight.md",
        """
        ---
        title: "Source Page"
        item: apprenticecodex:explorers_codex
        ---

        Source page line 1.
        Source page line 2.
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/en_us/pages/equipment_and_accessories/explorers_codex/00-spotlight.md",
        """
        ---
        title: "English Page"
        item: apprenticecodex:explorers_codex
        ---

        English page line 1.
        English page line 2.
        """,
    )


def add_apprenticecodex_extra_shared_page(root: Path) -> None:
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/shared/entries/equipment_and_accessories/explorers_codex.yml",
        """
        id: explorers_codex
        name: "Source Entry"
        category: equipment_and_accessories
        icon: apprenticecodex:explorers_codex
        sortnum: 0
        pages:
          - type: spotlight
            source: 00-spotlight.md
          - type: text
            source: 01-extra-note.md
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/shared/pages/equipment_and_accessories/explorers_codex/01-extra-note.md",
        """
        ---
        title: "Extra Note"
        ---

        Extra note line 1.
        Extra note line 2.
        """,
    )


def add_apprenticecodex_ja_jp_page_override(root: Path) -> None:
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/ja_jp/entries/equipment_and_accessories/explorers_codex.yml",
        """
        id: explorers_codex
        name: "Source Entry - Override"
        pages:
          - type: spotlight
            source: 00-spotlight.md
          - type: text
            source: 01-extra-note.md
        """,
    )
    write_text(
        root,
        "manuscripts/apprenticecodex/patchouli/locales/ja_jp/pages/equipment_and_accessories/explorers_codex/01-extra-note.md",
        """
        ---
        title: "Extra Note"
        ---

        Extra note override line 1.
        Extra note override line 2.
        """,
    )


def test_validate_repository_passes_for_sample(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)

    assert validate_repository(root) == []


def test_build_patchouli_writes_expected_files(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
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
    root = create_fixture_repo(tmp_path)
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
    root = create_fixture_repo(tmp_path)
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
    assert payload["subtitle"] == "patchouli.apprenticecodex.apprentice_codex.subtitle"
    assert payload["i18n"] is True


def test_build_patchouli_generates_lang_entries_from_source_locale_and_override(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
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

    # 文章の中身は固定していません。ここでは locale ごとに別の値が出ているかだけを確認します。
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.name"]
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.subtitle"]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"]
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"]
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"] != ja_lang[
        "patchouli.apprenticecodex.apprentice_codex.category.equipment_and_accessories.name"
    ]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"] != ja_lang[
        "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.name"
    ]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.subtitle"] != ja_lang[
        "patchouli.apprenticecodex.apprentice_codex.subtitle"
    ]
    assert en_entry["pages"][0]["text"] == "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.00_spotlight.text"
    assert en_entry["pages"][0]["item"] == "apprenticecodex:explorers_codex"


def test_build_patchouli_flattens_newlines_out_of_lang_values(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
    build_patchouli(root, "apprenticecodex")

    en_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "en_us.json"
    ja_lang_path = root / "docs" / "apprenticecodex" / "patchouli" / "assets" / "apprenticecodex" / "lang" / "ja_jp.json"
    en_lang = json.loads(en_lang_path.read_text(encoding="utf-8"))
    ja_lang = json.loads(ja_lang_path.read_text(encoding="utf-8"))

    # ここでは本文の意味を見ません。改行が最終 JSON に残らないことだけを見ます。
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.landing_text"]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.subtitle"]
    assert en_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.00_spotlight.text"]
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.landing_text"]
    assert ja_lang["patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page.00_spotlight.text"]
    assert all("\n" not in value and "\r" not in value for value in en_lang.values())
    assert all("\n" not in value and "\r" not in value for value in ja_lang.values())


def test_build_patchouli_converts_category_description_breaks(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)

    build_patchouli(root, "examplemod")

    lang_path = root / "docs" / "examplemod" / "patchouli" / "assets" / "examplemod" / "lang" / "en_us.json"
    raw_category_path = (
        root
        / "docs"
        / "examplemod"
        / "patchouli"
        / "assets"
        / "examplemod"
        / "patchouli_books"
        / "examplemod"
        / "en_us"
        / "categories"
        / "raw_notes.json"
    )
    lang = json.loads(lang_path.read_text(encoding="utf-8"))
    raw_category = json.loads(raw_category_path.read_text(encoding="utf-8"))

    # description の本文は自由に変えられます。ここで重要なのは、段落境界が $(br)/$(br2) に変換されることです。
    assert "$(br)" in lang["patchouli.examplemod.examplemod.category.getting_started.description"]
    assert "$(br2)" in lang["patchouli.examplemod.examplemod.category.paragraphs.description"]
    assert "$(br)" not in lang["patchouli.examplemod.examplemod.category.raw_notes.description"]
    assert "$(br2)" not in lang["patchouli.examplemod.examplemod.category.raw_notes.description"]
    assert "description_breaks" not in raw_category


def test_validate_repository_detects_missing_page(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
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
    root = create_fixture_repo(tmp_path)
    add_apprenticecodex_ja_jp_page_override(root)

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
    assert ja_entry["pages"][1]["text"].startswith(
        "patchouli.apprenticecodex.apprentice_codex.entry.explorers_codex.page."
    )


def test_validate_repository_requires_en_us_page_for_non_en_us_source_locale(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
    add_apprenticecodex_extra_shared_page(root)

    errors = validate_repository(root, "apprenticecodex")

    assert any("missing default locale page source" in error for error in errors)


def test_sync_en_us_stubs_creates_missing_stub_and_validate_flag_controls_it(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
    add_apprenticecodex_extra_shared_page(root)

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
    # stub は本文そのものではなく、翻訳未了であることを示すメタ情報を見るだけです。
    assert "translation_status: stub" in stub_text
    assert "TODO: Translate - " in stub_text
    assert "TODO: This page is not translated yet. Source locale:" in stub_text

    strict_errors = validate_repository(root, "apprenticecodex")
    allowed_errors = validate_repository(root, "apprenticecodex", allow_en_us_stubs=True)

    assert any("en_us stub remains" in error for error in strict_errors)
    assert allowed_errors == []


def test_build_patchouli_requires_synced_en_us_pages_for_non_en_us_source_locale(tmp_path: Path) -> None:
    root = create_fixture_repo(tmp_path)
    add_apprenticecodex_extra_shared_page(root)

    try:
        build_patchouli(root, "apprenticecodex")
    except Exception as exc:
        message = str(exc)
    else:
        raise AssertionError("build_patchouli should fail when en_us page translation is missing")

    assert "Missing default locale page source" in message

    sync_en_us_stubs(root, "apprenticecodex")
    build_patchouli(root, "apprenticecodex")
