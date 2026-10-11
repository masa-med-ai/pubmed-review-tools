# メタ解析モード（モードB）— 追加フィールドと出力仕様

このファイルは **Phase 0 でメタ解析モード（B）を選んだ場合のみ** 読む。
まとめモード（A）では不要。本スキルの責務は「メタ解析に投入できる形式でのデータ収集と整形」までで、
統合効果量・I²・τ²・forest plot の算出は行わない（R の `meta`/`metafor`、RevMan、CMA 等に渡す前段）。

## 目次

1. Phase 3 で追加抽出するフィールド（二値／連続／効果量フォールバック）
2. メタ解析データ抽出時の鉄則
3. Phase 4 追加チェック
4. Phase 5 メタ解析投入可能データの出力仕様

---

## 1. Phase 3 で追加抽出するフィールド

標準フィールドに加えて、**統合計算に直接投入できる生データ**を抽出する。
アウトカムタイプ（二値／連続）ごとに必要なフィールドが異なる。
論文によってタイプが混在し得るため、**論文ごとに該当する方を埋める**。

### 二値アウトカム（2x2表）

| フィールド | 説明 | 注意点 |
|---|---|---|
| outcome_name | 統合対象アウトカム名 | 全論文で同一定義に揃える |
| events_int | 介入群のイベント数 | 例: 腺腫が検出された患者数 |
| n_int | 介入群の解析対象総数 | 分母。per-patient/per-lesionを統一 |
| events_ctrl | 対照群のイベント数 | |
| n_ctrl | 対照群の解析対象総数 | |
| data_source | 生数か率からの逆算か | `reported`（原文に数値）/ `derived`（率×Nで逆算） |

> 抄録が **率（%）しか報告していない**場合、`events = round(率 × N)` で逆算してよいが、
> 必ず `data_source=derived` と記録し、丸め誤差が生じることを明示する。
> 逆算した `events` は整数に丸める（イベント数は整数のため）。
> 例: 「ADR 53.5% (n=300)」→ events = round(0.535 × 300) = 161、data_source=derived。

### 連続アウトカム（mean/SD/N）

| フィールド | 説明 | 注意点 |
|---|---|---|
| outcome_name | 統合対象アウトカム名 | 全論文で同一定義・同一単位に揃える |
| mean_int / mean_ctrl | 各群の平均 | |
| sd_int / sd_ctrl | 各群の標準偏差 | 抄録はSEや95%CIしか報告しないことが多い → 下記で換算 |
| n_int / n_ctrl | 各群の解析対象数 | |
| sd_source | SDの出所 | `reported` / `from_SE` / `from_CI` / `NR` |

> **SD が直接報告されていない場合の換算**（換算したら `sd_source` に記録する）：
> - SE から: `SD = SE × √N`
> - 95%CI（mean の CI）から: `SD = √N × (upper − lower) / (2 × 1.96)`
> - IQR/median しか無い等で換算不能なら `NR` とし、**勝手に正規分布を仮定して埋めない**。

### どちらでも取れない場合のフォールバック（generic inverse variance 用）

2x2 も mean/SD/N も抄録から取れないが、**効果推定値と95%CIは報告されている**ことは多い。
その場合は効果量を log スケールで保持し、SE を逆算しておくと generic inverse variance 法で統合できる。

| フィールド | 説明 |
|---|---|
| effect_measure | 効果指標（RR / OR / HR / IRR / MD / SMD） |
| effect_estimate | 点推定値（原文のまま） |
| ci_lower / ci_upper | 95%CI の下限・上限 |
| effect_source | `reported`（原文）/ `NR` |

> 比（RR/OR/HR/IRR）の場合の SE 逆算（メタ解析ソフトに渡す前の参考値）：
> `SE(lnEffect) = (ln(ci_upper) − ln(ci_lower)) / (2 × 1.96)`
> 平均差（MD）の場合：`SE = (ci_upper − ci_lower) / (2 × 1.96)`
> これは記録用（統合計算は行わない）。

---

## 2. メタ解析データ抽出時の鉄則（標準の鉄則に加えて）

- **逆算・換算した値には必ず `*_source` フラグ（reported / derived / from_SE 等）を立てる**。
  原文値か推定値かを区別できないと、メタ解析の信頼性評価・感度分析ができない。
- 標準フィールドの鉄則（抄録の数値だけを使う・取れない値は `NR` と明記）はそのまま適用する。
- 定義・単位・N の整合は Phase 4 のチェックリストで確認する。

---

## 3. Phase 4 追加チェック（自己検証チェックリストに追加）

- [ ] 統合対象アウトカムの**定義が全論文で揃っている**か？（per-patient/per-lesionの混在なし）
- [ ] 二値: 各論文で `events_int ≤ n_int` および `events_ctrl ≤ n_ctrl` を満たすか？
- [ ] 率から逆算した行は `data_source=derived` になっているか？（原文値と推定値が区別可能か）
- [ ] 連続: SDを換算した行は `sd_source` に出所（from_SE/from_CI）が記録されているか？
- [ ] 効果量フォールバックを使った行は、点推定値と95%CIの上下限が揃っているか？
- [ ] 各群の N が標準フィールドの N（解析対象数）と整合しているか？
- [ ] 単位（%、絶対数、平均の単位）が論文間で統一されているか？

---

## 4. Phase 5 メタ解析投入可能データの出力仕様

まとめ表に加えて、**統合ソフトにそのまま読み込める整形済みデータ**を出力する
（統合計算は行わず、このデータ作成までで完了）。

- **二値アウトカム**は、Excelの専用シート（または専用CSV）に次の列で1論文1行：
  `study_id, author, year, pmid, outcome_name, events_int, n_int, events_ctrl, n_ctrl, data_source`
  → R の `meta::metabin()` や RevMan の dichotomous 入力にそのまま対応。
- **連続アウトカム**は別シートに：
  `study_id, author, year, pmid, outcome_name, n_int, mean_int, sd_int, n_ctrl, mean_ctrl, sd_ctrl, sd_source`
  → `meta::metacont()` / RevMan の continuous 入力に対応。
- **効果量フォールバック**は別シートに：
  `study_id, author, year, pmid, effect_measure, effect_estimate, ci_lower, ci_upper, effect_source`
  → generic inverse variance（`meta::metagen()`）用。
- いずれのシートも `study_id` は `Author Year`（例: `Wallace 2022`）で統一し、
  同一著者・同一年が複数ある場合は `2022a / 2022b` で区別する。
- `*_source` 列（data_source / sd_source / effect_source）は必ず残す。
  原文値か派生値かが、メタ解析のリスクオブバイアス／感度分析の判断に直結する。
- 出力後、ユーザーに一言添える：「これは統合ソフト投入用の整形データです。
  pooled推定・forest plotの算出が必要なら別途R等で実行します（このスキルの範囲外）。」

> CSVで渡すと R/RevMan への取り込みが容易。ユーザーがExcelを希望する場合は、
> 上記をそれぞれ別シートに分け、まとめ表シートと同じブックに同梱する。
