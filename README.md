# pubmed-review-tools

Claude Code 用のマーケットプレイス。ローカル PubMed MCP サーバーと、
PubMed 検索・引用照合・文献レビューのスキルを束ねたプラグインを配布しています。

## 収録プラグイン

| プラグイン | 内容 |
|---|---|
| **pubmed** | PubMed MCPサーバー（10ツール）＋スキル3種（`pubmed-search` / `pubmed-reference-verifier` / `pubmed-literature-review`）＋下調べエージェント `literature-scout` |

## インストール（利用者向け）

このリポジトリをマーケットプレイスとして追加し、プラグインを有効化します。

```
/plugin marketplace add masa-med-ai/pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

インストール後に Claude Code を再起動し、`/mcp` で `pubmed` が connected になっていれば完了です。

有効化後、PubMed の10ツールと検索ワークフローがセットで使えるようになります。
MCP サーバーは `npx -y pubmed_mcp_server2@2.0.3` で自動起動するため、手動インストールは不要です（**Node.js 18 以上が必要**）。

## NCBI APIキー（任意・推奨）

各利用者が自分の `NCBI_API_KEY` を環境変数に設定すると、レート制限が
3 req/s → 10 req/s に上がります。キーはプラグインに同梱しません。
詳細は `pubmed/README.md` を参照してください。

## ライセンス

MIT
