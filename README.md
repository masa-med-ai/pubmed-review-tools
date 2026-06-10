# pubmed-review-tools

Claude 用のマーケットプレイス。PubMed の系統的文献レビューを支援する
スキルと、ローカル PubMed MCP サーバーを束ねた再頒布可能なプラグイン集です。

## 収録プラグイン

| プラグイン | 内容 |
|---|---|
| **pubmed-systematic-review** | PubMed系統的検索＋抄録からの正確な数値抽出（N数・アウトカム・P値）をExcel/スライド化するスキル＋PubMed MCPサーバー（10ツール）を同梱 |

## インストール（利用者向け）

このリポジトリをマーケットプレイスとして追加し、プラグインを有効化します。

```
/plugin marketplace add masa-med-ai/pubmed-review-tools
/plugin install pubmed-systematic-review@pubmed-review-tools
```

> `masa-med-ai/pubmed-review-tools` の部分は、実際に公開した GitHub の
> `ユーザー名/リポジトリ名` に置き換えてください。

有効化後、PubMed の10ツールと検索ワークフローがセットで使えるようになります。
MCP サーバーは `npx -y pubmed_mcp_server2` で自動起動するため、手動インストールは不要です。

## NCBI APIキー（任意・推奨）

各利用者が自分の `NCBI_API_KEY` を環境変数に設定すると、レート制限が
3 req/s → 10 req/s に上がります。キーはプラグインに同梱しません。
詳細は `pubmed-systematic-review/README.md` を参照してください。

## ライセンス

MIT
