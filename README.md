# my_mod_manual

Minecraft の複数 MOD 向け説明書原稿を管理し、まず `Patchouli` 向け JSON を生成するための Python プロジェクトです。

## 方針

- 原稿の正本は `manuscripts/` 配下に置く
- 生成物は `docs/<modid>/patchouli/...` に出す
- `Modonomicon` は将来対応を見据えてディレクトリだけ先に切る
- 生成物の対象リポジトリへの反映は当面手動で行う

## ディレクトリ構成

```text
manuscripts/<modid>/patchouli/
  book.yml
  categories/*.yml
  entries/*.yml
  pages/<entry_id>/*.md

docs/<modid>/patchouli/<locale>/
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
```

## 原稿フォーマット

- `book.yml`: 書籍メタデータ
- `categories/*.yml`: Patchouli のカテゴリ定義
- `entries/*.yml`: エントリ定義
- `pages/<entry_id>/*.md`: YAML front matter + 本文

ページ Markdown の例:

```md
---
title: Welcome
---
この本文は現在そのまま Patchouli の `text` に入ります。
```

`Patchouli` 向けの本文は、当面 CommonMark 変換をせず、そのまま Patchouli テキストとして扱います。
