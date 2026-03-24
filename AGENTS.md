# AGENTS.md

このファイルは、このリポジトリで作業する人間/AI エージェント向けの共通ルールを定義します。

## 1. 目的

- このリポジトリは、複数の Minecraft MOD 向け説明書原稿を一元管理する。
- 当面の主目的は、`Patchouli` 向け JSON をローカル生成できる状態を維持すること。
- `Modonomicon` は将来対応を見据えるが、初期実装の基準は `Patchouli` とする。

## 2. 言語ポリシー

- 作業メモ、レビューコメント、ドキュメント本文は原則として日本語で扱う。
- ファイル名、CLI 引数、設定キーなどは英語ベースの識別子を使う。
- `modid`、カテゴリ ID、エントリ ID、生成ファイル名は `snake_case` を使う。

## 3. 正本と出力

- 原稿の正本は `manuscripts/` 配下に置く。
- 生成物は `docs/<modid>/<format>/...` 配下に置く。
- 生成物 JSON を手で直接編集しない。修正は必ず `manuscripts/` 側に戻す。
- MOD 一覧と有効な出力形式の正本はルートの `mods.toml` とする。

## 4. 現在の構成方針

- `Patchouli` の原稿は次の構成を前提とする。

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
```

- `shared/` が説明書構造の正本で、`locales/<locale>/` は差分だけを持つ。
- `shared/` は `book.yml` の `source_locale` で書かれた正本として扱う。
- `locales/<locale>/book.yml` では書籍タイトルや導入文の翻訳差分を持てる。
- `pages/*.md` は YAML front matter と本文を持つ。
- `book.yml` は共有メタデータを持ち、`source_locale` と `locales` で原稿言語と生成対象 locale を列挙する。
- 本文は当面 CommonMark 変換せず、Patchouli の `text` としてそのまま扱う。
- `Modonomicon` への対応を意識しても、初期段階では強い抽象化を入れすぎない。

- `Patchouli` の生成物は次の構成を前提とする。

```text
docs/<modid>/patchouli/
  data/<namespace>/patchouli_books/<book_id>/book.json
  assets/<namespace>/patchouli_books/<book_id>/en_us/
    categories/*.json
    entries/**/*.json
  assets/<namespace>/patchouli_books/<book_id>/<locale>/   # 構造差分がある locale のみ
    categories/*.json
    entries/**/*.json
  assets/<namespace>/lang/<locale>.json
```

## 5. 変更時の優先順位

1. 原稿の編集しやすさ
2. 生成物の再現性
3. Python 初学者でも追える実装
4. 将来の `Modonomicon` 拡張余地

複雑な抽象化、過剰な継承、不要なメタプログラミングは避ける。

## 6. CLI 作業ルール

- `.venv` の作成と依存同期には `uv sync` を使う。
- 日常の `validate`、`build`、`sync en-us-stubs`、`scaffold`、`pytest` はプロジェクトの `.venv` を直接使う。
- PyCharm では Project Interpreter を `$PROJECT_DIR$/.venv/Scripts/python.exe` に固定する。
- 実装追加時は、可能なら `validate` と `build patchouli` が通るサンプルを維持する。

基本コマンド:

```powershell
uv sync
.\.venv\Scripts\python.exe -m my_mod_manual.cli validate
.\.venv\Scripts\python.exe -m my_mod_manual.cli build patchouli --mod <modid>
.\.venv\Scripts\python.exe -m pytest
```

## 7. エージェント向け実務ルール

- まず `mods.toml` を見て対象 MOD と有効形式を確認する。
- `Patchouli` 作業では、`book.yml`、`shared/categories`、`shared/entries`、`shared/pages`、`locales/<locale>/...` のどれを変えるかを明示する。
- `source_locale` が `en_us` 以外でも、生成物の基底は `en_us` として扱う。
- `source_locale` が `en_us` 以外で `shared/pages/...` に本文付きページを足した場合、通常ビルド前に `.\.venv\Scripts\python.exe -m my_mod_manual.cli sync en-us-stubs --mod <modid>` で `locales/en_us/pages/...` の不足 stub を補う。
- `translation_status: stub` が付いた `locales/en_us/pages/...` は暫定原稿として扱い、最終的には翻訳して marker を消してから通常 `validate` を通す。
- ID を変更する場合は、参照元も合わせて確認する。
- スキャフォールド追加時は、将来の手修正前提で読みやすいテンプレートを優先する。
- `Modonomicon` のための構造を先回りして入れすぎず、必要になった時点で差分を増やす。

## 8. 最低限の確認

- 原稿追加や更新後は `validate` を実行する。
- 暫定 `en_us` stub で表示確認する間だけ `validate --allow-en-us-stubs` を使い、通常確認では stub 残存をエラーとして扱う。
- `Patchouli` 向け変更後は `build patchouli` を実行し、`docs/` 配下の出力を確認する。
- 新しい原稿パターンを導入した場合は、最低 1 件のサンプルを追加する。

## 9. Git 運用

- Codex はローカルでの `git status`、`git diff`、`git add`、`git commit` までは行ってよい。
- Codex がコミットする場合、初心者が後から読んでも意図が追いやすい日本語コミットメッセージを書く。
- コミットメッセージでは「何を追加したか」だけでなく、「何のための土台か」が分かる表現を優先する。
- リモートへの読み取り系操作は許可する。例: `git fetch`、`git pull --ff-only`、リモート参照の確認。
- リモートへの書き込み系操作は人間のみが行う。例: `git push`、PR 作成、レビュー送信、issue/comment の投稿、remote ブランチの更新。
- 情報漏洩防止のため、Codex は remote に対して GET 相当を超える操作を提案なく実行しない。
