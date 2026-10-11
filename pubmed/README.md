# PubMed (Claude plugin)

PubMed を Claude から効率よく・正確に使うための検索ツール群です。ローカルで動く
PubMed MCP サーバーと、検索・引用照合・文献レビュー用のスキルを1つにまとめています。

## 含まれるもの

- **MCP サーバー `pubmed`**: [`pubmed_mcp_server2`](https://github.com/masa-med-ai/pubmed_mcp_server2)
  （npm 公開）を `npx -y pubmed_mcp_server2@2.0.3` で stdio 起動。10ツール
  （`search` / `fetch` / `fetch_batch` / `get_full_text` / `count` /
  `find_similar_articles` / `export_to_ris` / `get_citation_counts` /
  `convert_ids` / `batch_process`）を提供。PubMed へはお使いの PC から直接アクセスします。
- **スキル `pubmed-search`**: MeSH＋自由語の検索式設計 → `count` で件数較正 → 検索 → 抄録確認、の基本ワークフロー。
  回答に文献を使うときは `[*First Author, 雑誌名, Year*](PubMedリンク)` 形式で出典を示す。
  MCP が使えない環境向けに、Python 標準ライブラリだけで動く CLI（`scripts/pubmed_eutils.py`）を同梱。
- **スキル `pubmed-reference-verifier`**: 原稿の本文中引用と参考文献リストの整合性チェックと、PubMed での書誌照合。
- **スキル `pubmed-literature-review`**: PubMed 検索結果から複数論文の数値（N数・アウトカム・効果量・P値）を
  原文照合しながら抽出し、Excel / スライドにまとめる。カバレッジ台帳で漏れを防ぎ、メタ解析用データ（2x2表など）の収集にも対応。
  **検索対象は PubMed のみ**のため、正式な系統的レビュー（複数データベース検索）の代わりにはなりません。
- **エージェント `literature-scout`**: 文献の下調べをメイン会話から切り離して行い、要約と出典リストを返す。

利用者側で手動インストールは不要です。`npx` が PubMed サーバーを自動取得・起動します。

## 前提

- **Node.js ≥ 18**（`npx` 用）
- *(任意)* NCBI APIキー … なくても動きますが、レート制限が 3 req/s → 10 req/s に上がります。

## NCBI APIキーの設定（任意・推奨）

1. NCBI アカウントでサインイン: https://account.ncbi.nlm.nih.gov/
2. Account settings → 下部の **API Key Management** → **Create an API Key**
3. 生成された36文字のキーを、環境変数 `NCBI_API_KEY` に設定する。

`.mcp.json` は `NCBI_API_KEY` を環境変数から読み込みます（`"${NCBI_API_KEY:-}"`）。
キーをファイルに直接書き込まないでください。キーが未設定でもサーバーは動作します
（レート制限が低くなるだけ）。

macOS の例:

```bash
echo 'export NCBI_API_KEY="あなたのキー"' >> ~/.zshrc && source ~/.zshrc
```

## 使い方

インストール（Claude Code 2.1.275 以降は1行で可）:

```
/plugin install pubmed --marketplace masa-med-ai/pubmed-review-tools
```

プラグインを有効化して Claude Code を再起動し、`/mcp` で `pubmed` が connected になっていることを確認します。
そのうえで、たとえば次のように話しかけるとスキルが自動的に使われます。

- 「SGLT2阻害薬と心不全入院のエビデンスを PubMed で調べて」（pubmed-search）
- 「この原稿の参考文献をチェックして」（pubmed-reference-verifier）
- 「大腸内視鏡AI（CADe）のRCTを PubMed で集めて、主要評価項目を Excel にまとめて」（pubmed-literature-review）

## ライセンス

MIT
