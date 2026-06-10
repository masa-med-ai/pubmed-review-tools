---
name: pubmed-systematic-review
description: >
  PubMedから文献を系統的に検索し、各論文の抄録から正確な数値データ（N数、アウトカム、P値など）を
  抽出してExcelやスライドにまとめるスキル。「PubMedで検索してまとめて」「文献検索してExcelに」
  「RCTをPubMedで調べてスライドに」「系統的レビューのデータ収集」「文献の数値をまとめたい」
  「○○のエビデンスを一覧表にして」のように、PubMed検索＋データ抽出＋表/スライド化の
  一連の作業が含まれる要求で必ず使用する。PubMed MCP toolsを使う文献検索全般に適用。
  単に1件の論文を検索・要約する場合には不要だが、複数文献の比較・集計が含まれる場合は使うこと。
---

# PubMed Systematic Review — 正確な文献データ収集のためのワークフロー

## なぜこのスキルが必要か

PubMedから複数論文の数値データを抽出する際、**最大の落とし穴はデータ切断による数値の捏造**である。
バッチ取得ツール（`fetch_batch`）で多数の論文を一括取得すると、レスポンスが大きすぎて途中で
切断されることがある。切断されたデータの断片から「それっぽい数値」を推定してしまうと、
N数・アウトカム値・P値・有意性判定がすべて誤った表ができあがる。

このスキルは、そうした事故を防ぐための5段階ワークフローを定義する。

---

## 使用する MCP ツール（pubmed_mcp_server2 v2.0.0）

このスキルは同梱の PubMed MCP サーバー（`pubmed_mcp_server2` v2.0.0）の10ツールを前提とする。
本ワークフローで主に使うツールは以下である。ツール名は v2.0.0 の正式名称に一致させること。

| ツール | 用途 |
|---|---|
| `count` | 検索式の件数のみを高速取得（検索式の妥当性検証用） |
| `search` | PubMed検索。MeSH対応、`retmax`/`retstart`ページング、`sort`、`output_mode`（minimal/compact/full）、構造化`filters` |
| `fetch` | 単一PMIDの抄録を取得（最も安全。1件ずつ確実に読む） |
| `fetch_batch` | 複数PMIDの抄録を一括取得。`include_abstract: true`で抄録本文を含める |
| `get_full_text` | PMC全文（JATS XML）をセクション指定で取得（abstract/methods/results等、最大20 PMCID） |
| `find_similar_articles` | 類似論文の検索 |
| `get_citation_counts` | 被引用数（iCite または elink） |
| `convert_ids` | PMID ↔ PMCID ↔ DOI 変換 |
| `export_to_ris` | EndNote/Zotero/Mendeley向けRIS出力 |
| `batch_process` | 同一PMID集合に対し複数処理を一括実行 |

> 注: 旧バージョン（v1.x）の `get_full_abstract` / `search_pubmed` というツール名は
> v2.0.0 には存在しない。抄録の取得には `fetch`（1件）または `fetch_batch`（複数）を使う。

---

## Phase 1: 検索式の設計と検証

### 1-1. MeSH検索式を構築する

ユーザーの要求から、以下の要素を特定して検索式を組み立てる：

- **対象疾患/手技**: MeSH termで指定（例: `"Colonoscopy"[MeSH]`）
- **介入/技術**: MeSH + 自由語の組み合わせ（例: `"Artificial Intelligence"[MeSH] OR "CADe"[tiab]`）
- **研究デザイン**: Publication Typeで限定（例: `"Randomized Controlled Trial"[pt]`）
- **期間**: Date of Publication で指定（例: `"2023/01/01"[dp] : "2026/03/31"[dp]`）

検索式の例：
```
("Colonoscopy"[MeSH] OR "Colorectal Neoplasms"[MeSH])
AND ("Artificial Intelligence"[MeSH] OR "Deep Learning"[MeSH] OR "CADe"[tiab])
AND "Randomized Controlled Trial"[pt]
AND ("2023/01/01"[dp] : "2026/03/31"[dp])
```

### 1-2. count で件数を検証する

検索式を実行する前に、`count` ツールで件数を確認する。

- **0件**: 検索式が厳しすぎる → MeSH termの拡大、自由語の追加を検討
- **1-50件**: 個別抄録取得で十分に処理できる理想的な件数
- **51-200件**: 処理可能だが時間がかかる。ユーザーに件数を報告し、絞り込みの要否を確認
- **200件超**: 条件の追加で絞り込みを推奨

件数が適切であることを確認してからPhase 2に進む。

---

## Phase 2: 検索の実行とPMIDリスト取得

`search` ツールで検索を実行し、PMIDのリストを取得する。
この段階ではタイトルと基本情報のみを確認し、対象外の論文を除外する。
（PMIDだけ取れれば十分なら `output_mode: "minimal"` を使うとトークン効率がよい）

### スクリーニング基準

タイトルと基本情報から、テーマに無関係な論文を除外する：
- 対象外の介入（例: CADe検索なのにロボット手術や薬物療法の論文）
- 対象外のデザイン（例: RCT検索なのにメタアナリシスやレビュー）
- 対象外のアウトカム（例: 検出率の検索なのに費用対効果分析）

除外した場合はその理由を記録し、最終的にいくつの論文を採用するかユーザーに報告する。

---

## Phase 3: 抄録の個別取得（最重要フェーズ）

### 絶対原則: バッチ取得でJSONを丸ごと読もうとしない

> **`fetch_batch` で20件以上を一度に取得すると、レスポンスが途中で切れるリスクがある。**
> 切断されたデータから数値を「推定」「補完」「記憶から引用」することは絶対に禁止する。
> 抄録に明示的に書かれていない数値は「記載なし」とする。

### 推奨取得方法

**方法A: `fetch_batch` で5-6件ずつ取得（推奨）**

`fetch_batch` に `include_abstract: true` を指定すると、複数PMIDの抄録本文を一括取得できる。
**1回あたり5-6件まで**に制限し、各バッチの内容を完全に処理してから次のバッチに進む。
バッチを小さく保つことでレスポンス切断による数値の取りこぼしを防ぐ。

```
Batch 1: PMIDs 1-6  → fetch_batch(include_abstract:true) → 全文を読み、データを抽出・記録
Batch 2: PMIDs 7-12 → fetch_batch(include_abstract:true) → 全文を読み、データを抽出・記録
...
```

**方法B: `fetch` で1件ずつ取得（最も安全だが時間がかかる）**

件数が少ない場合（10件以下）、または方法Aでデータが不完全な場合に使用する。
`fetch` は単一PMIDの抄録を返すため、切断リスクが最も低い。

> 全文の数値（methods/resultsの詳細）が必要な場合は、PMCIDに `convert_ids` で変換してから
> `get_full_text` でセクション指定取得する。ただし抄録だけで足りる場合は使わない。

### 各抄録から抽出すべきフィールド

以下のフィールドを、**抄録に記載されている文言そのまま**から抽出する：

| フィールド | 説明 | 注意点 |
|---|---|---|
| PMID | PubMed ID | |
| 1st Author | 筆頭著者 | |
| Journal | 雑誌名 | |
| Year | 発刊年 | |
| Study Name | 試験名/略称 | 抄録に記載されていれば |
| N (analyzed) | 解析対象患者数 | 登録数ではなく最終解析対象のN数 |
| Design | 研究デザイン | Parallel / Tandem / Factorial / Multi-arm |
| Intervention | 介入内容 | 具体的なデバイス名・方法 |
| Primary Outcome | 主要評価項目 | 何が primary endpoint か |
| Intervention Result | 介入群の結果 | 抄録記載の数値そのまま |
| Control Result | 対照群の結果 | 抄録記載の数値そのまま |
| P-value / Effect Size | 統計量 | P値、RR、OR、IRR等 |
| Significance | 有意性判定 | Sig / NS / Borderline |
| Key Finding | 主要所見 | 1文で要約 |

### 数値抽出時の鉄則

1. **抄録に書かれている数値だけを使う**。メモリから「たしか…」で補完しない。
2. **Primary outcomeとSecondary outcomeを混同しない**。抄録で"primary outcome"や
   "primary endpoint"と明示されている指標を記録する。
3. **介入群と対照群を取り違えない**。どちらがどちらか、抄録の文脈から慎重に判断する。
   （例: 「ADR was 54.5% in the control group and 50.7% in the CADe group」のように
   対照群の方が高い場合がある）
4. **解析対象N数を使う**。登録数（enrolled）ではなく、最終解析に含まれた数を記録する。
   （例: 「1228 enrolled, 70 excluded → 1158 analyzed」なら1,158を記録）
5. **数値が切り捨てや丸めなしの原文のままか確認する**。

---

## Phase 4: データの構造化と自己検証

### 4-1. 中間データ構造の作成

抽出した全データを、Pythonの辞書リストやJSON形式で一旦まとめる。
この段階でExcel/PPTXを作り始めない。まず中間データの正確性を確認する。

### 4-2. 自己検証チェックリスト

出力ファイルを作成する前に、以下を確認する：

- [ ] 各論文のN数は、抄録に記載された解析対象数と一致しているか？
- [ ] Primary outcomeは、抄録で明示的にprimaryと書かれた指標か？
- [ ] 介入群と対照群の数値が入れ替わっていないか？
- [ ] P値と有意性判定（Sig/NS）が整合しているか？
      （p<0.05でNS、p>0.05でSigになっていないか）
- [ ] 抄録に記載のない数値を補完していないか？
      （記載なしなら「NR (not reported)」と明記する）
- [ ] 同一著者の異なる研究を混同していないか？
- [ ] CADe system名はデバイスの正式名称か？

特に怪しい場合は、`fetch` で当該論文を再取得して照合する。

---

## Phase 5: 出力ファイルの生成

中間データが検証済みであることを確認した上で、ユーザーが要求した形式で出力する。

### Excel出力時

- ヘッダー行にフィルター・フリーズペインを適用
- Significance列に色分け（Sig=緑, NS=赤, Borderline=黄）
- 「Key Finding」列はwrap_textで十分な列幅を確保
- 各PMIDにPubMedへのハイパーリンクを付与

### PPTX出力時

- 表スライドでは、抄録から確認済みの数値のみを記載
- 数値が多い場合、Significant / Non-significant に分けたスライドを作成
- Key Takeaways スライドには具体的な数値を引用
- 引用は「Author Year」形式で、具体的数値とともに記載

### 引用表記ルール（ユーザー設定に従う）

テキスト内で文献に言及する際は、1st author, 雑誌名, 発刊年を記載し、
PubMedへのハイパーリンク (`https://pubmed.ncbi.nlm.nih.gov/{PMID}/`) を付ける：

```
[Lau LHS, Clin Gastroenterol Hepatol, 2023](https://pubmed.ncbi.nlm.nih.gov/37918685/)
```

Excel内のPMID列にも同様にハイパーリンクを埋め込む：
```python
# openpyxlの場合
cell.value = '=HYPERLINK("https://pubmed.ncbi.nlm.nih.gov/37918685/", 37918685)'
```

---

## アンチパターン集（やってはいけないこと）

以下は、過去に発生した実際のエラーパターンである。これらを避けることがこのスキルの存在意義。

### 1. バッチ取得の切断を無視する

❌ `fetch_batch` で30件取得 → "Output too large (72.8KB)" → 先頭数件しか読めていない
   のに、残りの論文の数値を記憶やそれらしい推定で埋める

✅ `fetch_batch`（`include_abstract:true`）で5-6件ずつ取得 → 各バッチを完全に読み取り → データ抽出。
   それでも不完全なら `fetch` で1件ずつ取り直す

### 2. Primary と Secondary の混同

❌ [Spada C, United Eur Gastroenterol J, 2026](https://pubmed.ncbi.nlm.nih.gov/41563802/):
   「ADR 67.6% vs 59.8% p=0.012 → Sig」と記録
   （実際のPrimary endpointはAADR 21.3% vs 20.5% p=0.794 → NS）

✅ 抄録で "primary endpoint was AADR" と明記されている → AADR をPrimary列に記録

### 3. 介入群と対照群の取り違え

❌ [Yabuuchi Y, Dig Endosc, 2025](https://pubmed.ncbi.nlm.nih.gov/40611562/):
   「CADe ADR 53.5% vs Control 48.3% → Sig」
   （実際は Control 54.5% vs CADe 50.7% → NS、CADe群の方が低い）

✅ 抄録原文 "ADR was 54.5% in the control group and 50.7% in the CADe group" →
   Control が高いことを正確に記録

### 4. N数の間違い（登録数 vs 解析数、桁違い）

❌ [Xu X, Surg Endosc, 2025](https://pubmed.ncbi.nlm.nih.gov/40897874/): N=2,128（実際は N=390）
   [Maas MHJ, Endoscopy, 2024](https://pubmed.ncbi.nlm.nih.gov/38749482/): N=3,602（実際は N=497）
   [Gimeno-Garcia AZ, Gastrointest Endosc, 2023](https://pubmed.ncbi.nlm.nih.gov/36228695/): N=2,230（実際は N=370）

✅ 抄録の "included in the final analysis" や "analyzed" の数字を使う

### 5. 有意性の誤判定

❌ [Thiruvengadam NR, Clin Gastroenterol Hepatol, 2024](https://pubmed.ncbi.nlm.nih.gov/38437999/):
   「ADR 40.1% vs 37.7% p=0.36 → NS」
   （実際は ADR 42.5% vs 34.4% p=0.005 → Sig）

✅ 抄録のP値をそのまま転記し、p<0.05ならSig、p≥0.05ならNSと機械的に判定

---

## まとめ: ワークフロー全体像

```
[Phase 1] MeSH検索式構築 → count で検証
     ↓
[Phase 2] search でPMID取得 → タイトルスクリーニング
     ↓
[Phase 3] fetch_batch（include_abstract:true）で5-6件ずつ取得 → 各抄録から数値を逐語的に抽出
          （不完全なら fetch で1件ずつ取り直す）
     ↓
[Phase 4] 中間データを構造化 → 自己検証チェックリストで照合
     ↓
[Phase 5] Excel / PPTX / 他の形式で出力
```

各Phaseの完了をユーザーに報告しながら進めること。
特にPhase 3は最も時間がかかるが、最も重要なフェーズである。ここを省略しない。
