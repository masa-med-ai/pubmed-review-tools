# pubmed-review-tools

[English](README.md) | **日本語**

Claude Code 用のプラグイン・マーケットプレイスです。PubMed 検索ツール群のプラグイン **`pubmed`** を配布しています。
ローカルで動く PubMed MCP サーバーに、次の3つのスキルを組み合わせています。

- 出典リンク付きで PubMed を検索する
- 原稿の参考文献を照合する
- 複数論文の数値を表にまとめる（PubMed のみを対象にした、系統的レビュー風のワークフロー）

- MCP サーバーは**お使いの PC 上で動き**、NCBI に直接アクセスします。検索内容が第三者のサーバーを経由することはありません。
- サーバーを手動でインストールする必要はありません。プラグインを有効にすると、Claude Code が `npx` で自動起動します。

> 研究支援ツールです。重要な数値や引用は、必ず原著論文で確認してください。
> 正式な系統的レビューや臨床判断の代わりにはなりません。

---

## 目次

- [含まれるもの](#含まれるもの)
- [動作環境](#動作環境)
- [インストール](#インストール)
- [NCBI APIキー（任意・推奨）](#ncbi-apiキー任意推奨)
- [使い方](#使い方)
  - [pubmed-search：ふだんの文献検索](#pubmed-searchふだんの文献検索)
  - [pubmed-reference-verifier：原稿の参考文献チェック](#pubmed-reference-verifier原稿の参考文献チェック)
  - [pubmed-literature-review：複数論文の数値を表にまとめる](#pubmed-literature-review複数論文の数値を表にまとめる)
  - [literature-scout エージェント](#literature-scout-エージェント)
  - [MCP の10ツール](#mcp-の10ツール)
- [出典の表記](#出典の表記)
- [プライバシーとデータの流れ](#プライバシーとデータの流れ)
- [制限事項](#制限事項)
- [更新・アンインストール・0.1.x からの移行](#更新アンインストール01x-からの移行)
- [トラブルシューティング](#トラブルシューティング)
- [MCP サーバーだけを使う場合](#mcp-サーバーだけを使う場合)
- [ライセンス](#ライセンス)

---

## 含まれるもの

| 種類 | 名前 | 内容 |
|---|---|---|
| MCP サーバー | `pubmed` | [`pubmed_mcp_server2`](https://github.com/masa-med-ai/pubmed_mcp_server2) v2.0.3（`npx -y pubmed_mcp_server2@2.0.3` で起動）。PubMed・PubMed Central（PMC）・iCite を使う10ツールを提供 |
| スキル | `pubmed-search` | ふだんの PubMed 検索。MeSH と自由語で検索式を組み、件数を確認し、抄録を読んで、出典リンク付きで答える |
| スキル | `pubmed-reference-verifier` | 原稿の本文中引用と参考文献リストの対応をチェックし、各文献を PubMed で照合する（実在・著者・年・タイトル・雑誌・DOI） |
| スキル | `pubmed-literature-review` | PubMed を系統的に検索してスクリーニングし、抄録や PMC 全文から数値（N数・アウトカム・効果量・95%CI・P値）を抜き出して Excel・CSV・スライドにまとめる。メタ解析用データの収集にも対応 |
| エージェント | `literature-scout` | 文献の下調べを別の文脈で行い、要約と出典リストを返す |

スキルは、依頼内容に合えば自動で使われます。`/pubmed:pubmed-search` のように明示的に呼び出すこともできます。

## 動作環境

- **Claude Code**（後述の1行インストールは 2.1.275 以降）
- **Node.js 18 以上**：`npx` で MCP サーバーを起動するために使います。`node -v` で確認し、未導入なら <https://nodejs.org/> からインストールしてください。
- `eutils.ncbi.nlm.nih.gov`、`pmc.ncbi.nlm.nih.gov`、`icite.od.nih.gov` へのインターネット接続
- *（任意）* NCBI APIキー：NCBI のレート制限が毎秒3回から10回に上がります
- *（任意・`.docx` の原稿を扱う場合）* [pandoc](https://pandoc.org/)：`pubmed-reference-verifier` が Word ファイルを読むのに使います

## インストール

Claude Code で次を実行します。

```
/plugin marketplace add masa-med-ai/pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

Claude Code 2.1.275 以降なら、1行でもインストールできます。

```
/plugin install pubmed --marketplace masa-med-ai/pubmed-review-tools
```

インストールしたら Claude Code を再起動し、サーバーの状態を確認します。

```
/mcp
```

`pubmed` が **connected** と表示されれば完了です。
初回だけ、`npx` がサーバーをダウンロードするため10〜20秒ほどかかります。2回目以降はキャッシュを使います。

## NCBI APIキー（任意・推奨）

キーがなくても動きますが、NCBI へのアクセスは毎秒3回までに制限されます。無料のキーを設定すると毎秒10回になり、大量の検索や一括取得が速くなります。

1. NCBI にサインインします：<https://account.ncbi.nlm.nih.gov/>
2. **Account settings** を開き、下部の **API Key Management** で **Create an API Key** を押します。
3. 発行されたキーを環境変数 `NCBI_API_KEY` に設定し、Claude Code を再起動します。

macOS / Linux（zsh）の場合：

```bash
echo 'export NCBI_API_KEY="あなたのキー"' >> ~/.zshrc
source ~/.zshrc
```

bash の場合は `~/.bashrc` に書きます。

Windows（PowerShell）の場合：

```powershell
setx NCBI_API_KEY "あなたのキー"
```

設定後は、新しいターミナルを開いてから Claude Code を起動します。

プラグインは環境変数からキーを読み込みます（`.mcp.json` の `"NCBI_API_KEY": "${NCBI_API_KEY:-}"`）。プラグインにキーが保存されることはありません。キーを git にコミットしたり、他人と共有したりしないでください。

## 使い方

ふだんの言葉で Claude に頼むだけです。依頼に合ったスキルが自動で使われます。

### pubmed-search：ふだんの文献検索

依頼の例：

- 「SGLT2阻害薬と心不全入院のエビデンスを PubMed で調べて」
- 「大腸内視鏡の CADe の最近の RCT を探して」
- 「GLP-1受容体作動薬の長期安全性について、主要な論文を教えて」

Claude は次の順に進めます。

1. 問いを概念に分けます（臨床の問いなら PICO）。
2. MeSH と自由語（`[tiab]`）を組み合わせた検索式を作ります。
3. `count` でヒット件数と PubMed の検索語の展開を確認し、検索式を調整します。
4. 検索して関連する抄録を読み、[出典リンク付き](#出典の表記)で答えます。

検索を広げたり絞ったりするコツ：

- 「もっと」「新しいものだけ」「RCT だけ」と頼むと、検索を絞り込みます。
- 「PMID 12345678 に似た論文」「この論文を引用している論文」と頼むと、良い論文を起点に広げられます。
- 「RIS で出力して」と頼むと、EndNote・Zotero・Mendeley に取り込めるファイルを作ります。

### pubmed-reference-verifier：原稿の参考文献チェック

依頼の例：

- 「`draft.md` の参考文献をチェックして」
- 「`~/papers/manuscript.docx` の引用を PubMed で照合して」
- 「`draft.md` の参考文献リストを直して」（修正案を見せ、確認してから反映します）

モード：

| モード | 内容 | PubMed の利用 |
|---|---|---|
| `verify`（既定） | 本文中引用と参考文献リストを突き合わせ、各文献を PubMed で照合 | あり |
| `check` | 突き合わせのみ（オフライン） | なし |
| `fix` | `verify` の後に修正案を作り、確認後に反映 | あり |

Vancouver 形式（`[1]`、`[1-3]`）、Pandoc 形式（`[@key]`）、本文に埋め込んだ PMID（`{12345678}`、`{PMID:12345678}`）に対応しています。
レポートには次のものが一覧で出ます。

- エラー（参考文献リストにない引用、年や著者が PubMed と食い違う文献など）
- 警告
- PMID・DOI の候補

注意：サーバーが返す PubMed のデータには、巻・号・ページが含まれません。確認できなかった場合は、推測せずにレポートにその旨を書きます。

### pubmed-literature-review：複数論文の数値を表にまとめる

依頼の例：

- 「大腸内視鏡 CADe の RCT を PubMed で集めて、主要評価項目を Excel にまとめて」
- 「○○のエビデンスを、N数・アウトカム・効果量・P値の一覧表にして」
- 「○○ vs △△ の□□について、メタ解析用の2x2表データを集めて」

進め方：

1. **方針の確認**：最初に2つのことを質問します。
   - まとめ表だけでよいか、メタ解析用のデータ（2x2表、mean/SD/N、効果量と95%CI）も集めるか
   - 抄録だけを使うか、全文も使うか（全文は PMC 収録の論文と、ユーザーが渡す PDF に限られます）
2. **プロトコル**：問い（PICO）、採用・除外基準、アウトカムを `protocol.md` に書き、確認を求めます。
3. **検索**：検索式を作って調整し、全件の PMID を取得します。全ページを2回取得し、PMID の集合が一致することを確認して、取りこぼしがないことを確かめます。
4. **スクリーニング**：
   - タイトルと抄録で、各論文を採用・除外・保留に分けます。除外には必ず理由を記録します。
   - 撤回された論文は除外し、同じ研究の複数の報告はまとめます。
   - 全文モードでは、さらに全文で採用を判定します。
5. **抽出**：採用した論文を5〜6件ずつ読みます。数値ごとに出典の場所と原文の一節を記録し、記載がない値は推測せず `NR` とします。
6. **点検**：
   - 採用したすべての論文と、事前に決めたすべてのアウトカムがデータに入っているかを確認します。
   - 続いて自己点検をします（登録数ではなく解析数か、primary と secondary の区別、群の向き、P値と有意性の整合）。
7. **出力**：Excel・CSV・スライドを作り、PRISMA 2020 の件数と検索記録を添えます。

1回のレビューのファイルは、すべて `review-YYYYMMDD/` フォルダに保存されます。

| ファイル | 中身 |
|---|---|
| `protocol.md` | 問い、基準、方針、検索記録（データベース、日付、検索式そのもの、PubMed による展開、ヒット件数） |
| `search_pages.csv` | 検索の各ページで返った PMID の生記録 |
| `ledger.csv` | 1 PMID 1行の台帳（スクリーニングの判定、採否、理由、フラグ、研究ID、抽出状況） |
| `data.csv` | 抽出データ（1行 = 論文 × アウトカム × 時点 × 解析集団） |
| 成果物 | Excel / CSV / PowerPoint（依頼があればメタ解析用シートも） |

台帳があるので、長いレビューが途中で中断しても、`ledger.csv` を読んで続きから再開できます。

このスキルが検索するのは **PubMed だけ**です。

- 正式な系統的レビューには、複数のデータベース（Embase や CENTRAL など）と試験登録の検索が必要です。
- このスキルの結果は「PubMed に基づくラピッドレビュー」「エビデンスマップ」「レビューのデータ収集段階」などと表現し、データベースが1つだけである限界を明記してください。成果物でもスキルがそのことを促します。
- メタ解析用のデータは集めますが、統合効果量・I²・forest plot は計算しません。それらは R（`meta`、`metafor`）や RevMan などで行ってください。

### literature-scout エージェント

メインの会話を検索結果で埋めずに、ざっと全体像をつかみたいときに使います。

- 「literature-scout エージェントで○○の文献を下調べして」

次の4つを返します。

- 検索式とヒット件数
- 主要論文の短いリスト（出典、研究デザイン、N数、1行要約）
- エビデンスの全体像
- ギャップと注意点

### MCP の10ツール

直接呼び出すことはほとんどありません。スキルが代わりに使います。

| ツール | 用途 |
|---|---|
| `search` | PubMed 検索。MeSH、フィルタ（期間、出版タイプ、言語、ヒト限定、抄録あり、無料全文）、並べ替え、ページ送り |
| `count` | ヒット件数と PubMed の検索語の展開だけを取得（高速） |
| `fetch` | 1件の PMID の抄録と書誌情報 |
| `fetch_batch` | 複数 PMID の抄録、MeSH、出版タイプ |
| `get_full_text` | PubMed Central の全文を章ごとに取得（PMC 収録論文のみ） |
| `find_similar_articles` | ある PMID に関連する論文 |
| `get_citation_counts` | 被引用数（iCite）、または PubMed 上でその論文を引用している PMID |
| `convert_ids` | PMID・PMCID・DOI の相互変換 |
| `export_to_ris` | 文献管理ソフト用の RIS ファイル |
| `batch_process` | 同じ PMID の集合に上記の処理をまとめて実行 |

## 出典の表記

Claude が回答に論文を使うときは、第一著者・雑誌名・発刊年に PubMed へのリンクを付けて示します。

```
[*Yamada T, N Engl J Med, 2025*](https://pubmed.ncbi.nlm.nih.gov/12345678/)
```

著者・雑誌名・年・PMID は必ずツールの結果から取り、記憶から補うことはありません。別の表記がよければ、そう伝えてください。

## プライバシーとデータの流れ

- MCP サーバーはローカルで（stdio で）動きます。通信は**お使いの PC から直接** NCBI E-utilities、PubMed Central、iCite（NIH）へ送られます。
- 検索内容がプラグインの作者や他の第三者に送られることはありません。
- `NCBI_API_KEY` はお使いの環境に置かれ、送信先は NCBI だけです。
- NCBI の[利用規約](https://www.ncbi.nlm.nih.gov/home/about/policies/)が適用されます。

## 制限事項

- **PubMed のみ**：Embase、CENTRAL、Web of Science、Scopus、試験登録は検索しません。
- **全文**は PubMed Central 収録の論文だけです。それ以外は抄録を使うか、PDF を渡してください。
- **抄録と全文は食い違うことがあります**：重要な数値は全文で確認してください。
- **著者が多い論文**（31名以上）は、先頭10名と「et al.」で返ります。
- **出版タイプ**は PubMed の索引付けに依存し、新しい論文では付いていないことがあります。スキルでは自由語と組み合わせて補っています。
- **検索結果を固定する機能（WebEnv）がありません**：非常に件数が多いと、ページ送りの途中で順位がずれることがあります。literature-review スキルは全ページを2回取得してこれを検出しますが、完全性は保証できません。
- **AI による二重チェックは、独立した人間のレビューと同等ではありません**：literature-review スキルは怪しい数値を別のエージェントで再確認できますが、独立した2名のレビュアーによる判定と同じではありません。

## 更新・アンインストール・0.1.x からの移行

最新版に更新するには、次を実行してから Claude Code を再起動します。

```
/plugin marketplace update pubmed-review-tools
```

アンインストール：

```
/plugin uninstall pubmed@pubmed-review-tools
```

**0.1.x からの移行**：0.1.x のプラグインは `pubmed-systematic-review` という名前でした。0.2.0 で `pubmed` に変わったため、入れ直しが必要です。

```
/plugin marketplace update pubmed-review-tools
/plugin uninstall pubmed-systematic-review@pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

同じスキルの古いコピーが別の場所（個人用スキルや claude.ai にアップロードしたスキル）にある場合は、プラグインと同時に呼ばれないよう削除してください。

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `/mcp` で `pubmed` が failed になる | `node -v` で 18 以上か確認します。nvm を使っている場合は、Claude Code を起動する環境で Node.js が使えるか確認します。Claude Code を再起動します。 |
| 初回だけ失敗する | `npx` がまだサーバーをダウンロード中の可能性があります。Claude Code を再起動します。社内プロキシ環境では npm のプロキシ設定をしてください。 |
| 「429 Too Many Requests」が出る、一括取得が遅い | [NCBI APIキー](#ncbi-apiキー任意推奨)を設定します。 |
| PubMed のツールが表示されない | `/plugin` でプラグインが有効か確認し、Claude Code を再起動します。 |
| スキルが自動で使われない | `/pubmed:pubmed-search` のように明示的に呼ぶか、依頼文に「PubMed」と入れます。 |
| 似たスキルが2つ反応する | 古いスキルのコピーを削除します（[0.1.x からの移行](#更新アンインストール01x-からの移行)を参照）。 |
| verifier が `.docx` を読めない | [pandoc](https://pandoc.org/) をインストールするか、原稿を Markdown で保存します。 |

## MCP サーバーだけを使う場合

スキルなしで、サーバーだけを使うこともできます。

- **Claude Desktop**：[pubmed_mcp_server2 のリリース](https://github.com/masa-med-ai/pubmed_mcp_server2/releases)から `.mcpb` ファイルをインストールします。Node.js の準備は不要です。
- **その他の MCP クライアント**：`npx -y pubmed_mcp_server2` で起動します（[npm](https://www.npmjs.com/package/pubmed_mcp_server2)）。

詳しくは [pubmed_mcp_server2 の README](https://github.com/masa-med-ai/pubmed_mcp_server2) を参照してください。

## ライセンス

MIT © Masashi Misawa
