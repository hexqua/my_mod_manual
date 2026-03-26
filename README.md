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
    pages/<category_id>/<entry_id>/*.md
  locales/<locale>/
    book.yml                # 任意 override
    categories/*.yml        # 任意 override
    entries/**/*.yml        # 任意 override
    pages/<category_id>/<entry_id>/*.md   # 任意 override

docs/<modid>/patchouli/
  data/<namespace>/patchouli_books/<book_id>/book.json
  assets/<namespace>/patchouli_books/<book_id>/en_us/
    categories/*.json
    entries/**/*.json
  assets/<namespace>/patchouli_books/<book_id>/<locale>/   # 構造差分がある locale のみ
    categories/*.json
    entries/**/*.json
  assets/<namespace>/lang/<locale>.json
docs/<modid>/modonomicon/
```

## セットアップ

このリポジトリでは、日常の作業コマンドはプロジェクトの `.venv` を前提にします。`uv` は `.venv` の作成と依存同期にだけ使います。

```powershell
uv sync
.\.venv\Scripts\python.exe -m my_mod_manual.cli validate
.\.venv\Scripts\python.exe -m my_mod_manual.cli build patchouli --mod examplemod
```

PyCharm を使う場合は、Project Interpreter を `$PROJECT_DIR$/.venv/Scripts/python.exe` に設定してください。

## 主なコマンド

```powershell
.\.venv\Scripts\python.exe -m my_mod_manual.cli validate
.\.venv\Scripts\python.exe -m my_mod_manual.cli validate --allow-en-us-stubs
.\.venv\Scripts\python.exe -m my_mod_manual.cli build patchouli --mod <modid>
.\.venv\Scripts\python.exe -m my_mod_manual.cli sync en-us-stubs --mod <modid>
.\.venv\Scripts\python.exe -m my_mod_manual.cli scaffold mod <modid> --name "My Mod"
.\.venv\Scripts\python.exe -m my_mod_manual.cli scaffold category <modid> <category_id> --name "Getting Started"
.\.venv\Scripts\python.exe -m my_mod_manual.cli scaffold entry <modid> <entry_id> --category <category_id> --name "First Steps"
.\.venv\Scripts\python.exe -m my_mod_manual.cli scaffold category <modid> <category_id> --name "はじめに" --locale ja_jp
.\.venv\Scripts\python.exe -m pytest
```

## 原稿フォーマット

- `book.yml`: 書籍メタデータ、`book_id`、`book_namespace`、`source_locale`、`locales`
- `locales/<locale>/book.yml`: 書籍タイトルや導入文の locale 別 override
- `shared/categories/*.yml`: `source_locale` で書かれたカテゴリ正本
- `shared/entries/**/*.yml`: `source_locale` で書かれたエントリ構造
- `shared/pages/<category_id>/<entry_id>/*.md`: `source_locale` で書かれたページ front matter + 本文
- `locales/<locale>/...`: 必要な差分だけを上書きする override

`build patchouli` では `book.json` に `i18n: true` を出し、カテゴリ名・説明・エントリ名・ページ title/text は `assets/<namespace>/lang/<locale>.json` に展開します。`shared/` は `source_locale` の原稿として扱われ、`en_us` は常に完全な JSON を生成します。`en_us` と構造差分がない locale では、lang だけを出し、カテゴリ・エントリ JSON は省略します。

`source_locale` が `en_us` 以外のとき、ページ本文や title を持つ `shared/pages/.../*.md` を追加したら、対応する `locales/en_us/pages/.../*.md` も必要です。未作成のまま通常 `validate` や `build patchouli` を実行すると失敗します。

翻訳前の表示確認には、次の補助フローを使います。

```powershell
.\.venv\Scripts\python.exe -m my_mod_manual.cli sync en-us-stubs --mod <modid>
.\.venv\Scripts\python.exe -m my_mod_manual.cli validate --mod <modid> --allow-en-us-stubs
.\.venv\Scripts\python.exe -m my_mod_manual.cli build patchouli --mod <modid>
```

この補助コマンドは、不足している `locales/en_us/pages/.../*.md` に `translation_status: stub` 付きの仮ページを作ります。通常の `validate` はこの stub が残っていると失敗するため、英訳忘れを release 前に検出できます。

ページ Markdown の例:

```md
---
title: Welcome
---
この本文は現在そのまま Patchouli の `text` に入ります。
```

`description` は YAML で複数行にすると、生成時に Patchouli の改行マクロへ変換されます。
デフォルトでは有効で、カテゴリ YAML に `description_breaks: false` を書くとこの変換を止められます。

- 1 行の改行は `$(br)` に変換されます。
- 空行を含む 2 行以上の連続改行は `$(br2)` にまとめられます。

`Patchouli` 向けの本文は、当面 CommonMark 変換をせず、そのまま Patchouli テキストとして扱います。
