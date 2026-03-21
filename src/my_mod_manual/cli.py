from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .project import (
    ManualError,
    build_patchouli,
    scaffold_category,
    scaffold_entry,
    scaffold_mod,
    validate_repository,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path.cwd()

    try:
        if args.command == "validate":
            return run_validate(root, args.mod)
        if args.command == "build":
            return run_build(root, args.format, args.mod)
        if args.command == "scaffold":
            return run_scaffold(root, args)
    except ManualError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mod-manual")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate manuscripts for one or all mods.")
    validate_parser.add_argument("--mod", help="Only validate the selected modid.")

    build_parser = subparsers.add_parser("build", help="Build generated assets.")
    build_subparsers = build_parser.add_subparsers(dest="format", required=True)
    patchouli_build = build_subparsers.add_parser("patchouli", help="Build Patchouli JSON files.")
    patchouli_build.add_argument("--mod", help="Only build the selected modid.")

    scaffold_parser = subparsers.add_parser("scaffold", help="Create manuscript skeletons.")
    scaffold_subparsers = scaffold_parser.add_subparsers(dest="scaffold_target", required=True)

    scaffold_mod_parser = scaffold_subparsers.add_parser("mod", help="Create a new mod skeleton.")
    scaffold_mod_parser.add_argument("modid")
    scaffold_mod_parser.add_argument("--name", required=True, help="Display name for the mod.")

    scaffold_category_parser = scaffold_subparsers.add_parser("category", help="Create a category file.")
    scaffold_category_parser.add_argument("modid")
    scaffold_category_parser.add_argument("category_id")
    scaffold_category_parser.add_argument("--name", required=True)
    scaffold_category_parser.add_argument("--locale", default="en_us")

    scaffold_entry_parser = scaffold_subparsers.add_parser("entry", help="Create an entry and first page.")
    scaffold_entry_parser.add_argument("modid")
    scaffold_entry_parser.add_argument("entry_id")
    scaffold_entry_parser.add_argument("--category", required=True)
    scaffold_entry_parser.add_argument("--name", required=True)
    scaffold_entry_parser.add_argument("--locale", default="en_us")

    return parser


def run_validate(root: Path, modid: str | None) -> int:
    errors = validate_repository(root, modid)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    scope = modid or "all mods"
    print(f"Validation passed for {scope}.")
    return 0


def run_build(root: Path, format_name: str, modid: str | None) -> int:
    if format_name != "patchouli":
        raise ManualError(f"Unsupported build target: {format_name}")

    written_files = build_patchouli(root, modid)
    for path in written_files:
        print(path.relative_to(root))
    if not written_files:
        print("No files were written.")
    return 0


def run_scaffold(root: Path, args: argparse.Namespace) -> int:
    if args.scaffold_target == "mod":
        created = scaffold_mod(root, args.modid, args.name)
    elif args.scaffold_target == "category":
        created = [scaffold_category(root, args.modid, args.category_id, args.name, args.locale)]
    elif args.scaffold_target == "entry":
        created = scaffold_entry(root, args.modid, args.entry_id, args.category, args.name, args.locale)
    else:
        raise ManualError(f"Unsupported scaffold target: {args.scaffold_target}")

    for path in created:
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
