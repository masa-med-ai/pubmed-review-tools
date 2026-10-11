---
name: pubmed-search
description: PubMed で効率的で質の高い医学文献検索を行うためのスキル。PubMed MCP ツール群（search / count / fetch_batch / find_similar_articles / get_citation_counts / get_full_text / convert_ids など）があればそれを使い、MCP が無い環境では同梱 CLI（scripts/pubmed_eutils.py、NCBI E-utilities 直叩き・Python 3 標準ライブラリのみ）で同じワークフローを実行する。ユーザーが医学・生物学・臨床の文献を「調べて」「探して」「エビデンスを」「論文を」と依頼したとき、また PubMed・MeSH・PICO・RCT・PMID・DOI に言及したときは、明示的に「PubMedで検索して」と言われなくてもこのスキルを使うこと。検索結果を提示する際の引用フォーマット（ハイパーリンク付き）もこのスキルで規定する。ただし、複数文献の数値抽出・比較表・Excel/スライド化は pubmed-literature-review を、原稿の本文中引用と参考文献リストの整合性検証は pubmed-reference-verifier を優先する。
---

# PubMed Search

医学文献を PubMed で検索・精査し、**ハイパーリンク付きの出典**とともに提示するためのスキル。目的は 3 つ: (1) 検索の「質」と「効率」を両立させること、(2) 出典を必ず決められた形式で提示すること、(3) **PubMed MCP の有無に関わらず同じ作法で動くこと**。

---

## 0. 最優先ルール: 出典は捏造しない

医学文献では誤情報が実害につながる。**PMID・著者名・雑誌名・年・タイトルは、必ずツール（MCP または同梱 CLI）の実際の返り値からのみ引用する。** 記憶から論文を「思い出して」提示してはならない。ツールを呼ばずに具体的な PMID や引用を書くことは禁止。該当がなければ「見つからなかった」と正直に述べる。**MCP も CLI もどちらも使えない場合は、検索を実行できない旨を報告して止まる**（記憶で代用しない）。

---

## 1. バックエンド選択（最初に一度だけ判断する）

このスキルの検索操作は、環境に応じて次の優先順位でバックエンドを選ぶ。

1. **PubMed MCP ツールが利用可能** → MCP を使う。ツール名のプレフィックスは環境依存（プラグイン同梱なら `mcp__plugin_pubmed_pubmed__search`、ほか `mcp__pubmed__search`, `mcp__pubmed-remote__search`, `mcp__claude_ai_PubMed__search`, `PubMed:search` など）。レート制限・リトライはサーバー側が処理する。
2. **MCP が無い／呼び出しに失敗する**、かつシェル（Bash 等のコード実行）と外部ネットワークが使える → **同梱 CLI** を使う。この `SKILL.md` の絶対パスからスキルディレクトリを解決し、`scripts/pubmed_eutils.py` を絶対パスで呼ぶ:

   ```bash
   SCRIPT="<skill-dir>/scripts/pubmed_eutils.py"
   python3 "$SCRIPT" --help
   ```

   CLI は公式 NCBI E-utilities / iCite / PMC API のみを使用し、Python 3 標準ライブラリだけで動く。レート制御（キー無し約3リクエスト/秒、`NCBI_API_KEY` 環境変数があれば約10リクエスト/秒）・指数バックオフのリトライを内蔵する。API キーを出力・保存コマンドに書かないこと。継続利用時は `NCBI_EMAIL` の設定を推奨。
3. **どちらも不可** → §0 に従い、検索できない旨を報告して止まる。

### 操作の対応表

ワークフロー（§3 以降）は操作名で書く。実行時はこの表で選んだバックエンドに読み替える。

| 操作 | PubMed MCP | 同梱 CLI |
|---|---|---|
| 件数確認 | `count` | `python3 "$SCRIPT" count 'QUERY'`（`search` と同じフィルタフラグを併用可） |
| 検索 | `search` | `python3 "$SCRIPT" search 'QUERY' --retmax 20 --output-mode compact --sort relevance` |
| 1件取得 | `fetch` | `python3 "$SCRIPT" fetch PMID` |
| 一括取得 | `fetch_batch` | `python3 "$SCRIPT" fetch-batch PMID1 PMID2 ...`（抄録不要なら `--no-abstract`） |
| 類似論文 | `find_similar_articles` | `python3 "$SCRIPT" find-similar-articles PMID --retmax 20` |
| 被引用数 | `get_citation_counts` | `python3 "$SCRIPT" get-citation-counts PMID... --source icite`（前向き引用は `--source pubmed --include-citing-pmids`） |
| PMC 全文 | `get_full_text` | `python3 "$SCRIPT" get-full-text PMCID... --sections methods results discussion` |
| ID 変換 | `convert_ids` | `python3 "$SCRIPT" convert-ids --from-type pmid --to-type pmcid ID...` |
| RIS 出力 | `export_to_ris` | `python3 "$SCRIPT" export-to-ris PMID...` |
| 一括処理 | `batch_process` | `python3 "$SCRIPT" batch-process PMID... --operations abstract citations similar` |

構造化フィルタの対応: MCP の `filters` は CLI では個別フラグになり、**`count` と `search` の両方で同じフラグが使える**（件数較正と本検索を同一条件にするため、count 時にもフィルタを付けること）— `date_range` → `--start-date` / `--end-date`（`YYYY/MM/DD`・`YYYY-MM-DD`・`YYYY/MM`・`YYYY` のいずれの形式でも可）、`publication_types` → `--publication-type '...'`、`languages` → `--language eng`、`humans_only` → `--humans-only`、`has_abstract` → `--has-abstract`、`free_full_text` → `--free-full-text`。`output_mode`（minimal / compact / full）と `sort`（relevance / pub_date / first_author）、`retmax` / `retstart` は両バックエンドで同じ意味を持つ。

CLI 利用時のエンドポイント選択・件数上限・結果の解釈は [references/capabilities.md](references/capabilities.md) を参照。回答の中でバックエンドを切り替えた場合も、出典契約（§2）は同一に保つ。

---

## 2. 出典の提示フォーマット（必須の出力契約）

検索結果として論文を挙げるときは、**必ず次のハイパーリンク付き Markdown 形式**で提示する。リンクが張られていないと利用者が原著にアクセスできず不便なため、プレーンテキストの引用は不可。

**基本形:**

```
[*First Author, 雑誌名, Year*](https://pubmed.ncbi.nlm.nih.gov/{PMID}/)
```

- `First Author` = 第一著者（ツールの `authors` 配列の先頭。例: `Yamada T`）。第二著者以降は書かない。
- `雑誌名` = `journal`（標準略誌名があればそれを優先。例: `N Engl J Med`）。
- `Year` = `year`（出版年）。
- `{PMID}` = `id`（PMID）。**PMID はリンク先 URL に埋め込む**ことで「出典に PMID を含める」要件を満たす。
- 囲みの `*...*` により斜体で表示する。

**レンダリング例**（フォーマット説明のための架空の書誌。実際の提示では必ずツールの返り値を使う）:

> [*Yamada T, J Example Med, 2025*](https://pubmed.ncbi.nlm.nih.gov/00000001/)

**PMID を本文にも明示したい場合**（利用者が希望したとき、または引用リストを作るとき）は末尾に付す:

```
[*Yamada T, J Example Med, 2025*](https://pubmed.ncbi.nlm.nih.gov/00000001/). PMID: 00000001
```

**運用ルール:**
- 本文中で論文に言及するたびに、その場でこの形式のリンクを付ける。
- 複数論文を列挙するときは箇条書きにし、各項目をこの形式にする。
- `search` の `compact`（既定）モードは `authors / journal / year / doi / pmcid / id / url` を返すので、**追加のフェッチなしでこの引用を組み立てられる**。効率のため、引用だけが目的なら `full` にしない。

---

## 3. ワークフロー（5 ステップ）

### Step 1. 問いを概念に分解する（臨床質問なら PICO）

いきなりキーワードを投げず、まず問いを独立した概念ブロックに分ける。臨床質問は PICO が有効:
- **P**opulation / Problem（対象・疾患）
- **I**ntervention（介入・曝露）
- **C**omparison（比較対照。無いことも多い）
- **O**utcome（アウトカム）

各概念ごとに「同義語・関連 MeSH」をまとめて OR で束ね、概念どうしを AND でつなぐのが質の高い検索の基本骨格。

### Step 2. 構造化クエリを組む（MeSH + フリーワード + フィールドタグ）

**MeSH（統制語）と自由語（tiab）を併用する。** MeSH だけだと索引付け前の新しい論文を取りこぼし、自由語だけだと表記ゆれで漏れる。両方を OR で束ねると感度が上がる。

概念ブロックの書き方（例: 「2型糖尿病」概念）:
```
("Diabetes Mellitus, Type 2"[Mesh] OR "type 2 diabetes"[tiab] OR T2DM[tiab])
```

概念どうしを AND で結合:
```
("Diabetes Mellitus, Type 2"[Mesh] OR "type 2 diabetes"[tiab])
AND ("SGLT2 Inhibitors"[Mesh] OR SGLT2[tiab] OR gliflozin*[tiab])
AND (cardiovascular[tiab] OR "heart failure"[tiab])
```

主要フィールドタグ:
| タグ | 意味 | 使いどころ |
|---|---|---|
| `[Mesh]` | MeSH 用語 | 統制語での網羅検索 |
| `[Majr]` | MeSH 主要トピック | 主題を絞りたいとき |
| `[tiab]` | タイトル＋抄録 | 自由語・新語・略語 |
| `[ti]` | タイトルのみ | 精度を上げたいとき |
| `[au]` | 著者 | 既知著者の検索 |
| `[ta]` | 雑誌略誌名 | 特定誌に限定 |
| `[dp]` | 出版日 | 期間指定（下記フィルタ推奨） |
| `[pt]` | 出版タイプ | RCT・総説など |
| `[la]` | 言語 | 英語限定など |

補足: 語尾の揺れは `gliflozin*` のように切り捨て（truncation）で吸収。フレーズは `"..."` で囲む。

### Step 3. `count` で件数を較正する

**本検索の前に必ず `count` で件数を確認する。** データを取得しないため高速・低コスト。返り値の `query_translation`（PubMed の自動用語マッピング結果）と `warnings` も確認し、意図と違う解釈をされていたら検索式を修正する。目安:
- 数千件以上 → 広すぎる。概念を追加、`[Majr]`/`[ti]` で絞る、フィルタを足す。
- 0〜数件 → 狭すぎる。同義語を足す、`[Mesh]` を加える、`AND` を減らす、truncation を使う。
- **おおむね 20〜200 件**に収まると、本検索とスクリーニングが現実的。

必要なら概念を出し入れして 2〜3 回 `count` を回し、クエリを最適化してから Step 4 へ。

### Step 4. `search` で効率よく取得する

較正済みクエリで本検索。効率のためパラメータを意図的に選ぶ:

- **`output_mode`**（トークン節約の要）:
  - `minimal` = id/title/url のみ。大量スクリーニングの一次通過に。
  - `compact`(既定) = それに authors/journal/year/doi/pmcid を追加。**引用作成にはこれで十分。**
  - `full` = さらに abstract/mesh_terms/publication_types。抄録精読・選別が必要な少数の論文にだけ使う。
- **`sort`**: 探索は `relevance`、最新性重視は `pub_date`、既知論文の同定は `first_author`。
- **`retmax` / `retstart`**: ページング。まず `retmax` を控えめ（例 20〜30）にし、必要に応じて `retstart` で次ページ。
- **構造化フィルタ**（クエリに AND される。文字列に詰め込むより明快）: 期間・出版タイプ・言語・ヒト限定・抄録あり・フリー全文あり（§1 の対応表を参照）。

### Step 5. 深掘りして提示する

- 抄録が必要な候補は **`fetch_batch`**（複数 PMID を一括）で取得。1 件だけなら `fetch`。一括取得は 5〜10 件ずつに分け、**要求した PMID がすべて返っているか確認してから**次に進む（返っていない PMID の内容を推定しない）。
- 影響度の目安が欲しいときは **`get_citation_counts`**（既定 `icite` は被引用数のみ・高速）。
- 全文が要るときは **`get_full_text`**（PMC ID を渡す。`sections` で必要章のみに絞りトークン節約）。PMC ID が無ければ `convert_ids` で PMID→PMCID。
- 最後に、選んだ論文を **§2 の引用形式**で提示。臨床質問ではエビデンス階層（メタアナリシス／システマティックレビュー ＞ RCT ＞ 観察研究）を意識して並べ、各論文が何を示したかを一言添える。

---

## 4. 検索の拡張（スノーボーリング）

初回検索で取りこぼしを減らすための追補:
- **`find_similar_articles`**（PMID 指定）: MeSH・タイトル類似で関連論文を発見。良い 1 本が見つかったら横に広げる。
- **`get_citation_counts`** の `citing_source='pubmed'`（CLI: `--source pubmed`）＋ citing PMIDs 取得: その論文を**引用している**論文（前向き引用）を取得。新しい発展を追える。
- システマティックレビュー的に複数 PMID へ一括処理したいときは **`batch_process`**（`operations` に abstract/citations/similar/ris_export/full_text）。

---

## 5. 付随タスク

- **ID 変換**: `convert_ids`（pmid↔pmcid↔doi）。DOI しか手元にないとき等。DOI→PMID が失敗しても「PubMed に存在しない」とは限らない（変換 API は PMC 収録論文が主対象）。その場合は `"10.xxxx/..."[doi]` のフィールド検索を試す。
- **引用管理ソフト**: `export_to_ris`（EndNote/Zotero/Mendeley 用 RIS）。利用者が「文献管理に取り込みたい」と言ったら提案。

---

## 6. よくある落とし穴

- **記憶で引用しない** → 必ずツール結果から（§0）。
- **MeSH のみ / 自由語のみ** → 併用する。特に直近 1〜2 年の論文は MeSH 未索引のことがあり `[tiab]` が要る。
- **`humans_only`・`[pt]` フィルタの過信** → これらは MeSH 索引に依存するため、索引前の新着論文がフィルタで落ちる。最新文献の網羅が目的のときはフィルタ無しの結果と件数を見比べる。
- **`full` の乱用** → 大量結果に `full` を使うとトークンを浪費。まず `minimal`/`compact` で絞る。
- **件数を見ずに本検索** → 先に `count`。0 件や数千件のまま突き進まない。
- **フィルタの二重掛け** → 構造化フィルタはクエリに AND されるので、文字列側と重複させない。
- **一括取得の欠落を無視** → `fetch_batch` の返却件数が要求 PMID 数より少ないことがある。欠落分は再取得し、それでも取れなければ「取得できなかった」と明示する。
- **第一著者以外を出典に混ぜる** → §2 の形式は第一著者のみ。

---

## 7. 通し例

質問: 「2型糖尿病患者で SGLT2 阻害薬は心不全入院を減らすか？」

1. 分解: P=2型糖尿病 / I=SGLT2阻害薬 / O=心不全入院。
2. クエリ:
   ```
   ("Diabetes Mellitus, Type 2"[Mesh] OR "type 2 diabetes"[tiab])
   AND ("Sodium-Glucose Transporter 2 Inhibitors"[Mesh] OR SGLT2[tiab] OR gliflozin*[tiab])
   AND ("Heart Failure"[Mesh] OR "heart failure"[tiab] OR "hospitalization"[tiab])
   ```
3. `count` → 件数と `query_translation` を確認。多ければ出版タイプ（RCT・メタアナリシス）と期間のフィルタを追加して再 `count`。
4. `search`（`compact`, `sort=relevance`, `retmax=20`, 上記フィルタ）。
5. 上位数本を `fetch_batch` で抄録確認、必要なら `get_citation_counts` で影響度。
6. 提示（各行が §2 の形式。**以下は書式を示すための架空の書誌**であり、実際の提示では必ずツールの返り値を使う）:
   > - [*Sato K, J Example Med, 2025*](https://pubmed.ncbi.nlm.nih.gov/00000001/) — 架空試験A。SGLT2 阻害薬群で心不全入院が有意に減少。
   > - [*Suzuki M, Example Heart J, 2024*](https://pubmed.ncbi.nlm.nih.gov/00000002/) — 架空試験B。同様の結果。
