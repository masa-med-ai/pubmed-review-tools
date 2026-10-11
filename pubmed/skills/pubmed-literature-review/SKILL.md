---
name: pubmed-literature-review
description: >
  PubMedで複数文献を系統的に検索し、各論文の抄録（PMC収録分は全文）から正確な数値データ
  （N数、アウトカム、効果量、95%CI、P値など）を抽出してExcel・CSV・スライドにまとめるスキル。
  systematic review（系統的レビュー）風の文献収集・スクリーニング・データ抽出、エビデンス一覧表、
  PRISMA風の件数整理、メタ解析（meta-analysis）用データ（2x2表、mean/SD/N、効果量+95%CI）の収集に使う。
  「PubMedで検索してまとめて」「文献検索してExcelに」「RCTを調べてスライドに」「系統的レビューのデータ収集」
  「○○のエビデンスを一覧表にして」「メタ解析用に2x2表を作って」「forest plot用のデータ」
  「漏れなく網羅的に集計したい」など、検索＋複数文献の比較・数値抽出・表/スライド化を伴う要求で使用する。
  1件〜少数の文献を探して答えるだけなら pubmed-search、原稿の引用照合は pubmed-reference-verifier を使う。
  検索対象はPubMedのみで、統合効果量・I²・forest plotの算出は行わない（R/RevMan等に渡す前段まで）。
---

# PubMed Literature Review — 正確な文献データ収集のためのワークフロー

> **位置づけ**: 本スキルは **PubMedのみ** を検索対象とする文献収集・データ抽出ワークフローである。
> Cochrane / PRISMA / AMSTAR 2 が求める複数データベース検索や試験登録の網羅検索は行わないため、
> 成果物を「系統的レビュー」と呼ぶ場合は、PubMed単独検索であることを限界として明記するよう利用者に伝える
> （rapid review、evidence map、SRのデータ収集段階などの表現が適切）。

## 使用する PubMed MCP ツール

同梱の PubMed MCP サーバー（`pubmed_mcp_server2`）のツールを使う。ツール名の接頭辞は環境により異なる
（プラグイン経由なら `mcp__plugin_pubmed_pubmed__search` など）。現在のセッションのツール一覧から
`search` / `count` / `fetch` / `fetch_batch` 等の名前で終わるものを選ぶ。

| ツール | 本スキルでの用途 |
|---|---|
| `count` | 検索式の件数・`query_translation`・`warnings` の確認 |
| `search` | PMID取得。`retmax`（最大500）/`retstart` でページング、`sort`、`output_mode`、`filters` |
| `fetch` | 単一PMIDの抄録・書誌（著者・雑誌・年・DOI）を取得（再確認用。最も確実） |
| `fetch_batch` | 複数PMIDの抄録・書誌・MeSH・出版タイプを一括取得（`include_abstract: true`）。5〜6件ずつ使う |
| `convert_ids` / `get_full_text` | PMID→PMCID変換と、PMC収録論文の全文（`sections` で章を限定） |
| `export_to_ris` | 採用文献のRIS出力（文献管理ソフト用） |

## なぜこのスキルが必要か

複数論文からの数値収集には2種類の失敗が潜む。

- **① 捏造・取り違え**: 一括取得の欠落や切断、primary/secondary・群の取り違え、登録数と解析数の混同。
  → Phase 3 の**逐次原文照合**と、根拠箇所・原文引用の記録で防ぐ。
- **② 漏れ**: 検索のページング漏れ、context 飽和による進捗喪失、重複排除の巻き添え。
  → **台帳（ledger）と照合ゲート**で防ぐ。

## 作業ディレクトリ

1回のレビューの成果物はすべて `./review-YYYYMMDD/`（作業開始日）にまとめ、context ではなくディスクを正本にする。

| ファイル | 中身 |
|---|---|
| `protocol.md` | 問い・採否基準・方針・検索記録（Phase 0〜1で固定） |
| `search_pages.csv` | 検索の各ページで返った PMID の生記録 |
| `ledger.csv` | PMID 1件1行の台帳（スクリーニング・採否・抽出状況） |
| `data.csv` | 抽出データ（1行 = 1論文 × アウトカム × 時点 × 解析集団） |
| 成果物 | Excel / CSV / PPTX など |

列定義・状態の値・PRISMA件数の計算式・照合ゲートの実装例は **`references/ledger-and-prisma.md`** を参照する。
件数が少なく（〜15件程度）単発の作業なら台帳を簡略化してよいが、Phase 4 の照合は省略しない。

## サブエージェント運用ルール

サブエージェントからメインに返るのは要約された最終報告だけで、メインは原文を見られない。
原文照合がこのスキルの核なので、役割を次のように分ける。

| 工程 | 実行主体 |
|---|---|
| Phase 0〜2（方針・検索・スクリーニング・採否） | メイン |
| **Phase 3（抽出）** | **メイン（逐次）。PMIDを分割して並列抽出させない** |
| Phase 4（照合ゲート・自己検証） | メイン |
| Phase 4 後の再照合（任意） | サブエージェント可。怪しい論文だけ再取得・照合させ、食い違いだけ報告させる |
| Phase 5（検証済みデータからのファイル生成） | サブエージェント可 |

サブエージェントによる再照合は**AIによる二重チェック**であり、独立した2名のレビュアーによる判定とは同等ではない。
成果物でもそのように表現する。ユーザーが明示的に Phase 3 の並列化を求めた場合は、精度リスクを一言添えてから従う。

---

## Phase 0: 方針の確認（検索の前に必ず実行）

ユーザーへの質問ツール（Claude Code では `AskUserQuestion`、claude.ai では `ask_user_input`。
無ければ選択肢付きの質問文）で、次の2点を確定する。既に会話で明言されている項目は省略してよい。

1. **目的**: 「まとめ表/スライドのみ（モードA）」か「メタ解析用データも収集（モードB）」か。
   モードBなら主要アウトカムのタイプ（二値 / 連続 / 混在）も聞く。
2. **抽出の深さ**: 「抄録のみ」か「全文も使う（PMC収録分＋ユーザーが渡すPDF）」か。
   全文を選ぶと Phase 2 で全文での適格性判定（2-6）を行う。PMC外の全文は自動取得できないことを伝える。

モードBを選んだら `references/meta-analysis-mode.md` を読む。統合効果量・I²・forest plot は算出しない
（必要なら別タスクとしてR等で行うか確認する）。

## Phase 1: プロトコルと検索式

### 1-1. protocol.md を作る

検索の前に次を `protocol.md` に書き、ユーザーに確認する（非対話実行などで確認できない場合は、その旨を記録して進む）。後から基準を変えたら、変更日と理由を追記する。

- 問い（PICO/PECO）、対象研究デザイン、期間、言語
- 採否基準（inclusion / exclusion）
- 抽出するアウトカムと時点、Phase 0 で決めたモードと抽出の深さ
- （モードBのみ）統合対象アウトカムの定義、per-patient / per-lesion などの解析単位

### 1-2. 検索式を組み、count で較正する

- 概念ごとに MeSH と自由語（`[tiab]`）を OR で束ね、概念間を AND で結ぶ。MeSHだけでは索引前の新しい論文を落とす。
- `count` で件数・`query_translation`・`warnings` を確認し、意図と違う展開があれば修正する。

検索式の例：
```
("Colonoscopy"[MeSH] OR "Colorectal Neoplasms"[MeSH])
AND ("Artificial Intelligence"[MeSH] OR "Deep Learning"[MeSH] OR "CADe"[tiab])
AND ("Randomized Controlled Trial"[pt] OR randomi*[tiab])
AND ("2023/01/01"[dp] : "2026/03/31"[dp])
```

- 出版タイプ（`[pt]`）は索引付けに依存し、新しい論文や索引の遅れた論文には付いていないことがある（RCTが "Journal Article" だけのこともある）。
  研究デザインで絞るときは `[pt]` 単独にせず、自由語（例: `randomi*[tiab]`）と OR で併用する。レビュー等の除外も `[pt]` だけに頼らずスクリーニングで確認する。
- `[dp]` は出版日で、電子版の日付で一致することがある（ツールが返す `year` と食い違う場合がある）。期間をどの日付フィールドで切ったかを検索記録に残す。

件数は**絞るためではなく運用を決めるため**に見る（pubmed-search の「20〜200件に収める」目安は本スキルでは適用しない）。

| 件数 | 運用 |
|---|---|
| 0件 | 検索式を見直す（同義語・MeSHを追加） |
| 1〜15件 | 逐次処理。台帳は簡略化可 |
| 16〜250件 | 台帳必須。10バッチごとにチェックポイント照合 |
| 250件超 | 台帳必須。全件抽出が現実的でなければ、PICOの再定義かスクリーニングでの絞り込みをユーザーと相談 |

### 1-3. 検索記録（PRISMA-S）

最終検索式が決まったら `protocol.md` に記録する：データベース（PubMed）、インターフェース（NCBI E-utilities 経由の MCP）、
検索日時、実行した検索式そのものと `query_translation`、適用したフィルタ、ヒット件数。「その他の情報源: なし」と明記する。

## Phase 2: 検索の実行・スクリーニング・採否

### 2-1. 全件の PMID を取得する（漏れ防止の第一関門）

MCP の `search` は検索結果のスナップショット（WebEnv）を返さないため、ページング中に新しい論文が追加されると順位がずれる。次の規則で取りこぼしを防ぐ。

1. `sort` を固定する（`pub_date` 推奨）。`retmax` は最大500。`output_mode: "compact"` で取得すると、台帳の著者・年・タイトルもここで埋められる。
2. `retstart` を `retmax` ずつ進め、**返ってきた件数が `retmax` 未満になるまで**取得を続ける（最初の `total` から必要ページ数を決め打ちしない）。
3. 各ページの PMID を `search_pages.csv` に追記する（クエリID・取得日時・retstart・PMIDリスト。ツールは時刻を返さないので取得日時はローカル時刻でよい）。
4. 取得後にもう一度 `count` する。**総件数が増えていたら全ページを取り直して和集合をとる**。
5. 重複を除いたユニーク PMID 数が最終の `count` と一致することを確認する。**ユニーク数が `count` より少なければ、全ページを取り直して和集合をとる**
   （ページング中に出版日が更新された論文が、取得済みのページへ移って漏れることがあるため）。それでも合わなければ、差分の件数と再取得の経過を `protocol.md` に記録してユーザーに報告する。
6. 件数が 9,999 件を超える場合、E-utilities はそれ以上 `retstart` を進められない。`[dp]` の期間で相互に重ならない区間へ分割し、区間ごとに取得して和集合をとる。

### 2-2. 複数の検索式を使う場合

全式の PMID を集めてから重複排除する。`ledger.csv` の `source_query` に由来を残し、**重複排除の前後の件数を両方記録する**。

### 2-3. 台帳を初期化する

ユニーク PMID をすべて `ledger.csv` に書く（`screen_tiab=pending`）。この行数が以降の照合の基準線になる。

### 2-4. タイトル・抄録スクリーニング

`fetch_batch`（`include_abstract: true`）で抄録を5〜10件ずつ取得しながら、`protocol.md` の採否基準に照らして判定する。

- 判定は `include` / `exclude` / `uncertain`。**迷ったら残す**（この段階の目的は明らかな対象外の除外）。
- **抄録を読まずに除外しない**。タイトルだけで明らかに対象外でも、除外理由は抄録確認後に記録する。
- 除外は `tiab_exclude_reason` に理由を1つ記録する。
- `publication_types` に `Retracted Publication` / `Retraction of Publication` / `Published Erratum` を含む要素があれば `flags` に記録し、ユーザーに報告する。撤回論文は原則採用せず、`eligibility=excluded`、`eligibility_exclude_reason=retracted` とする（モードによらない）。
  撤回・訂正の検出は出版タイプだけに依存しており、撤回通知との相互リンクまでは確認できないことを限界として扱う。
- `uncertain` の扱い: 全文モードでは 2-6 の全文判定へ進める。抄録のみモードでは採用候補として残し、`notes` に「適格性不確実」と書いて成果物で区別する。**`uncertain` を除外で片付けない**。

### 2-5. 同一研究の複数報告をまとめる

試験名、NCT番号（抄録中の記載、または `"NCT01234567"[si]` で検索）、著者・施設・登録期間の一致から、同じ研究の別報告（主論文・二次解析・長期追跡など）を見つけ、
同じ `study_id` を付ける。**重複を理由に削除しない**（報告は残し、研究単位で束ねる）。
`[si]` は NCT 番号などの登録番号で引けるが、登録番号の記載がない論文や、一部の登録形式（例: UMIN）は引けないことがある。見つからなくても「別報告がない」とは結論しない。

### 2-6. 全文での適格性判定（全文モードのみ）

`include` と `uncertain` について全文を探す：`convert_ids` で PMCID を得て `get_full_text`、なければユーザーに PDF を依頼する。
入手経路を `full_text_source`（pmc / pdf / none）に記録し、入手できなければ `ft_status=not_retrieved` とする（推測で埋めない）。
全文で判定し、`eligibility` を `included` / `excluded`（理由を `eligibility_exclude_reason`）に確定する。
抄録のみモードでは、2-4 の判定をもって `eligibility` を確定する。

### 2-7. PRISMA の件数を報告する

台帳から PRISMA 2020 の件数を計算し、ユーザーに報告する（計算式は `references/ledger-and-prisma.md`）。
抄録のみモードでは「適格性は抄録レベルで判定」と明記し、全文段階を行ったように見せない。

## Phase 3: 抽出（最重要フェーズ）

### 絶対原則

> 一括取得の欠落・切断を推測で埋めない。抄録/全文に明示されていない数値は `NR` とする。
> **このフェーズはサブエージェントに分担させない。** メイン自身が原文を逐語的に照合する。

### 取得方法

- `fetch_batch`（`include_abstract: true`）で **5〜6件ずつ**取得し、各バッチを完全に処理してから次へ進む。
  返却件数が要求した PMID 数と一致するか必ず確認し、欠落分は `fetch` で個別に再取得する。
- 全文モードで全文がある論文は、`get_full_text` の `sections`（methods / results など）で必要な章だけ取得する。
- 大きな出力がファイルに保存された場合は、そのファイルを最後まで読んでから抽出する（一部だけ読んで埋めない）。

### 抽出フィールド（data.csv）

1行は「論文 × アウトカム × 時点 × 解析集団」。キー `(pmid, outcome_name, timepoint, population)` は重複させない。

| フィールド | 説明・注意点 |
|---|---|
| pmid / study_id | 台帳と一致させる |
| first_author / journal / year | ツールの返り値からのみ |
| study_name / design | 試験名（記載があれば）、Parallel / Tandem / Factorial / Multi-arm など |
| n_analyzed | 解析対象数（登録数ではない）。登録数は別列 `n_enrolled` |
| population | ITT / mITT / PP など、原文に記載があれば |
| intervention / comparator | デバイス名・用量・手順を具体的に |
| outcome_name / timepoint | primary か secondary かを `outcome_role` に記録 |
| intervention_result / control_result | 原文の数値・単位のまま |
| effect / ci / p_value | RR・OR・HR・差など。調整済みか未調整かを `adjusted` に記録 |
| significance | Sig / NS / Borderline |
| source_location | abstract / methods / results / Table 2 など |
| verbatim_quote | 数値の根拠になった原文の一節（短く） |
| notes | NR、欠落、曖昧さ、別報告との関係 |

### 抽出の鉄則

1. 原文に書かれた数値だけを使う。記憶から補わない。
2. Primary と Secondary を混同しない（原文で "primary outcome/endpoint" と明示されたものを primary とする）。
3. 介入群と対照群を取り違えない（対照群の方が高い結果もある）。
4. 解析対象 N を使う（enrolled ではなく analyzed）。
5. 数値を丸めず、原文のまま写す。

### 大量文献での運用

- 毎バッチ、`data.csv` に追記し、台帳の `extraction_status` を `extracted` に更新してディスクに保存する。
- 毎バッチ進捗を表示する（例：`Batch 7/34 完了 — 抽出済み 42/198 報告、残り 156`）。
- 10バッチごとに、台帳の `extracted` の PMID 集合と `data.csv` の PMID 集合が一致するか照合する。
- 中断したら `ledger.csv` を読み、`eligibility=included` かつ `extraction_status=pending` の PMID だけ再開する。

モードBでは `references/meta-analysis-mode.md` の追加フィールドも抽出する。

## Phase 4: 照合ゲートと自己検証

### 4-0. 照合ゲート（必ず最初に通す）

行の正しさを見る前に、**全件が揃っているか**を集合で照合する（行数では照合しない。1論文が複数行になるため）。

- [ ] (a) `eligibility=included` の全 PMID が `data.csv` に1行以上ある
- [ ] (b) `data.csv` の全 PMID が included の集合に含まれる（除外したはずの PMID が紛れていない）
- [ ] (c) `data.csv` のキー `(pmid, outcome_name, timepoint, population)` が重複していない
- [ ] (d) included の全 `study_id` に、抽出済みの報告が1件以上ある

一致しなければ、不足・余剰の PMID を列挙して処理し直し、再度ゲートを通す。

### 4-1. 自己検証チェックリスト

- [ ] N は解析対象数か。群別 N と合計は整合するか
- [ ] Primary outcome は原文で primary と明示された指標か。時点は正しいか
- [ ] 介入群と対照群の数値が入れ替わっていないか
- [ ] P値と有意性判定が整合しているか（p<0.05 で NS、p≥0.05 で Sig になっていないか）
- [ ] 原文にない数値を補っていないか（`NR` が明記されているか）。`verbatim_quote` が数値と一致するか
- [ ] 同一研究の別報告を別研究として二重に数えていないか（`study_id`）
- [ ] 介入（デバイス・薬剤など）の名称は原文の表記どおりか

モードBの追加チェックは `references/meta-analysis-mode.md` の「3. Phase 4 追加チェック」を参照。
怪しい論文は `fetch` で1件ずつ再取得して照合する。

### 4-2. 再照合（任意・推奨）

件数が多い、または学会・論文用の場合、4-1 の後にサブエージェントを1つ起動し、次に該当する論文だけを
`fetch` で再取得して原文と照合させ、食い違いだけを報告させる。メインは食い違った箇所を自分で原文確認して修正する。

- N が他論文と桁違いに大きい/小さい
- P値が 0.05 付近
- 介入群 < 対照群など、直感に反する結果

## Phase 5: 出力

照合ゲートを通過した `data.csv` だけを使い、要求された形式で出力する。

- **必ず添える情報**: PRISMA の件数、検索記録（1-3）、Phase 0 で決めたモードと抽出の深さ、「PubMedのみ」の限界、
  `uncertain` や `not_retrieved` の扱い、AIによる二重チェックの有無。`ledger.csv` も成果物として残す。
- **Excel**: ヘッダーにフィルターとフリーズペイン、Significance 列の色分け（Sig=緑, NS=赤, Borderline=黄）、
  Key Finding 列の折り返し、PMID 列に PubMed へのハイパーリンク（`=HYPERLINK("https://pubmed.ncbi.nlm.nih.gov/37918685/", 37918685)`）。`NR` を空欄や0にしない。
- **PPTX**: 検証済みの数値だけを載せ、具体的な数値の近くに引用を置く。研究間の異質性を無視した単純な優劣の結論にしない。
- **モードB**: `references/meta-analysis-mode.md` の「4. Phase 5」の仕様でメタ解析投入用データも出力する。

### 引用表記

本文で文献に触れるときは、第一著者・雑誌名・発刊年に PubMed へのハイパーリンクを付ける（すべてツールの返り値から）：

```
[Lau LHS, Clin Gastroenterol Hepatol, 2023](https://pubmed.ncbi.nlm.nih.gov/37918685/)
```

---

## アンチパターン集（過去に実際に起きたエラー）

### 0. 抽出をサブエージェントに並列分担する
❌ PMIDを10件ずつ3つのサブエージェントに分けて並列抽出 → 要約しか返らず、切断・取り違えが検出されないまま表が完成
✅ 抽出はメインが逐次処理し、再照合だけサブエージェントで補助する

### 1. 一括取得の欠落・切断を無視する
❌ `fetch_batch` で30件取得 → 出力が大きすぎて先頭数件しか読めていないのに、残りの数値を記憶や推定で埋める
✅ `fetch_batch` で5〜6件ずつ取得し、返却件数を確認してから全件を読む

### 2. Primary と Secondary の混同
❌ [Spada C, United Eur Gastroenterol J, 2026](https://pubmed.ncbi.nlm.nih.gov/41563802/):
   「ADR 67.6% vs 59.8% p=0.012 → Sig」と記録（実際の Primary endpoint は AADR 21.3% vs 20.5% p=0.794 → NS）
✅ 抄録で "primary endpoint was AADR" と明記されている → AADR を primary として記録

### 3. 介入群と対照群の取り違え
❌ [Yabuuchi Y, Dig Endosc, 2025](https://pubmed.ncbi.nlm.nih.gov/40611562/):
   「CADe ADR 53.5% vs Control 48.3% → Sig」（実際は Control 54.5% vs CADe 50.7% → NS）
✅ 原文 "ADR was 54.5% in the control group and 50.7% in the CADe group" のとおり記録

### 4. N数の間違い（登録数 vs 解析数、桁違い）
❌ [Xu X, Surg Endosc, 2025](https://pubmed.ncbi.nlm.nih.gov/40897874/): N=2,128（実際は N=390）
   [Maas MHJ, Endoscopy, 2024](https://pubmed.ncbi.nlm.nih.gov/38749482/): N=3,602（実際は N=497）
   [Gimeno-Garcia AZ, Gastrointest Endosc, 2023](https://pubmed.ncbi.nlm.nih.gov/36228695/): N=2,230（実際は N=370）
✅ "included in the final analysis" や "analyzed" の数字を使う

### 5. 有意性の誤判定
❌ [Thiruvengadam NR, Clin Gastroenterol Hepatol, 2024](https://pubmed.ncbi.nlm.nih.gov/38437999/):
   「ADR 40.1% vs 37.7% p=0.36 → NS」（実際は ADR 42.5% vs 34.4% p=0.005 → Sig）
✅ 原文のP値をそのまま転記し、p<0.05 なら Sig、p≥0.05 なら NS と判定する

### 6. 大量文献での「漏れ」を見逃す
❌ count が218件なのに `search` の1ページ目（100件）だけを「全件」として処理
❌ 抽出の途中で context が飽和し初期の結果が消えたのに、included の PMID 集合と data.csv を照合せずに出力
✅ 2-1 の規則で全ページを取得し、毎バッチ data.csv に追記し、4-0 の照合ゲートを集合で通してから出力する

---

## ワークフロー全体像

```
[Phase 0] 目的（モードA/B）と抽出の深さ（抄録のみ/全文）を確認            … メイン
[Phase 1] protocol.md → 検索式 → count で較正 → 検索記録                  … メイン
[Phase 2] 全ページ取得（件数照合）→ 台帳 → TiAbスクリーニング（撤回確認）
          → 同一研究の束ね → （全文モード）全文判定 → PRISMA件数         … メイン
[Phase 3] fetch_batch 5〜6件ずつ → 逐語的に抽出 → data.csv 追記・進捗表示  … メイン（並列化しない）
[Phase 4] 照合ゲート（集合で4項目）→ 自己検証 →（任意）再照合              … メイン＋サブ
[Phase 5] Excel / PPTX / CSV 出力（PRISMA件数・限界・方針を同梱）          … メイン or サブ
```

**抽出はメイン・再照合はサブ**の分担が正確性を、**台帳と集合での照合ゲート**が網羅性を担保する。
