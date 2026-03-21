# my_mod_manual

Minecraft の複数 MOD 向け説明書原稿を管理し、まず `Patchouli` 向け JSON を生成するための Python プロジェクトです。

## 方針

- 原稿の正本は `manuscripts/` 配下に置く
- 生成物は `docs/<modid>/patchouli/...` に出す
- `Modonomicon` は将来対応を見据えてディレクトリだけ先に切る
- 生成物の対象リポジトリへの反映は当面手動で行う
- Patchouli 1.20 系に合わせ、`book.json` は `data/`、locale 別カテゴリ・エントリは `assets/` に出す

## ディレクトリ構成

```text
manuscripts/<modid>/patchouli/
  book.yml
  shared/
    categories/*.yml
    entries/**/*.yml
    pages/<entry_id>/*.md
  locales/<locale>/
    categories/*.yml        # 任意 override
    entries/**/*.yml        # 任意 override
    pages/<entry_id>/*.md   # 任意 override

docs/<modid>/patchouli/
  data/<namespace>/patchouli_books/<book_id>/book.json
  assets/<namespace>/patchouli_books/<book_id>/<locale>/
    categories/*.json
    entries/**/*.json
  assets/<namespace>/lang/<locale>.json
docs/<modid>/modonomicon/
```

## セットアップ

`uv` が PATH に入っていない環境でも動くよう、以下では `python -m uv` を使います。

```powershell
python -m uv sync
python -m uv run mod-manual validate
python -m uv run mod-manual build patchouli --mod examplemod
```

## 主なコマンド

```powershell
python -m uv run mod-manual validate
python -m uv run mod-manual build patchouli --mod <modid>
python -m uv run mod-manual scaffold mod <modid> --name "My Mod"
python -m uv run mod-manual scaffold category <modid> <category_id> --name "Getting Started"
python -m uv run mod-manual scaffold entry <modid> <entry_id> --category <category_id> --name "First Steps"
python -m uv run mod-manual scaffold category <modid> <category_id> --name "はじめに" --locale ja_jp
```

## 原稿フォーマット

- `book.yml`: 書籍メタデータ、`book_id`、`book_namespace`、`locales`
- `shared/categories/*.yml`: locale 共通のカテゴリ定義
- `shared/entries/**/*.yml`: locale 共通のエントリ構造
- `shared/pages/<entry_id>/*.md`: locale 共通のページ front matter + 本文
- `locales/<locale>/...`: 必要な差分だけを上書きする override

`build patchouli` では `book.json` に `i18n: true` を出し、カテゴリ名・説明・エントリ名・ページ title/text は `assets/<namespace>/lang/<locale>.json` に展開します。通常の翻訳では `shared/` は触らず、`locales/<locale>/` に文言差分だけ置けば足ります。

ページ Markdown の例:

```md
---
title: Welcome
---
この本文は現在そのまま Patchouli の `text` に入ります。
```

`Patchouli` 向けの本文は、当面 CommonMark 変換をせず、そのまま Patchouli テキストとして扱います。
