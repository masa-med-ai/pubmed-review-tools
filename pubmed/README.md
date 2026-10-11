# pubmed (Claude Code plugin)

A PubMed search toolkit for Claude Code: a local PubMed MCP server (10 tools) plus three skills and one agent.
PubMed を Claude Code から使うための検索ツール群です。ローカルの PubMed MCP サーバー（10ツール）、スキル3つ、エージェント1つで構成されています。

| Component / 種類 | Name / 名前 |
|---|---|
| MCP server | `pubmed` — [`pubmed_mcp_server2`](https://github.com/masa-med-ai/pubmed_mcp_server2)@2.0.3 via `npx` |
| Skill | `pubmed-search` — everyday searching with hyperlinked citations / 出典リンク付きの文献検索 |
| Skill | `pubmed-reference-verifier` — checks a manuscript's references against PubMed / 原稿の参考文献チェック |
| Skill | `pubmed-literature-review` — PubMed-only, review-style numeric extraction to Excel/slides / PubMed のみを対象にした数値抽出と表・スライド化 |
| Agent | `literature-scout` — quick literature scan / 文献の下調べ |

Install / インストール:

```
/plugin marketplace add masa-med-ai/pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

Requires Node.js 18+. `NCBI_API_KEY` (optional) is read from the environment.
Node.js 18 以上が必要です。`NCBI_API_KEY`（任意）は環境変数から読み込みます。

Full documentation / 詳しい説明:
**[English](../README.md)** | **[日本語](../README.ja.md)**
