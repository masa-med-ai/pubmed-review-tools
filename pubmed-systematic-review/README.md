# PubMed Systematic Review (Claude plugin)

PubMed の系統的文献検索と、抄録からの正確な数値抽出（N数・アウトカム・P値）を
Excel / スライドにまとめるためのスキルと、ローカルで動く PubMed MCP サーバーを
1つにまとめた Claude プラグインです。

## 含まれるもの

- **スキル `pubmed-systematic-review`**: MeSH検索式の設計 → `count`で件数検証 →
  `search`でPMID取得 → 抄録の個別取得 → 自己検証 → Excel/PPTX出力、という
  5段階ワークフロー。数値の捏造・取り違えを防ぐためのアンチパターン集を内蔵。
- **MCP サーバー `pubmed`**: [`pubmed_mcp_server2`](https://github.com/masa-med-ai/pubmed_mcp_server2)
  （npm公開）を `npx -y pubmed_mcp_server2` で stdio 起動。10ツール
  （`search` / `fetch` / `fetch_batch` / `get_full_text` / `count` /
  `find_similar_articles` / `export_to_ris` / `get_citation_counts` /
  `convert_ids` / `batch_process`）を提供。

利用者側で手動インストールは不要です。`npx` が PubMed サーバーを自動取得・起動します。

## 前提

- **Node.js ≥ 18**（`npx` 用）
- *(任意)* NCBI APIキー … なくても動きますが、レート制限が 3 req/s → 10 req/s に上がります。

## NCBI APIキーの設定（任意・推奨）

1. NCBI アカウントでサインイン: https://account.ncbi.nlm.nih.gov/
2. Account settings → 下部の **API Key Management** → **Create an API Key**
3. 生成された36文字のキーを、環境変数 `NCBI_API_KEY` に設定する。

`.mcp.json` は `NCBI_API_KEY` を環境変数から読み込みます（`"${NCBI_API_KEY}"`）。
キーをファイルに直接書き込まないでください。キーが未設定でもサーバーは動作します
（レート制限が低くなるだけ）。

macOS の例:

```bash
echo 'export NCBI_API_KEY="あなたのキー"' >> ~/.zshrc && source ~/.zshrc
```

## 使い方

プラグインを有効化したうえで、Claude にこのように話しかけます。

- 「大腸内視鏡AI（CADe）のRCTをPubMedで検索して、主要評価項目をExcelにまとめて」
- 「○○のエビデンスを一覧表にして」

スキルが自動的にトリガーされ、MeSH検索式の立案から数値抽出、表/スライド出力まで進めます。

## ライセンス

MIT
