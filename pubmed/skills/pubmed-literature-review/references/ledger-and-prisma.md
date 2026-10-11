# 台帳・PRISMA件数・照合ゲートの仕様

SKILL.md の「作業ディレクトリ」「Phase 2」「Phase 4-0」から参照される詳細仕様。
すべて `./review-YYYYMMDD/` 配下に置く。

## 目次

1. search_pages.csv
2. ledger.csv（列と値）
3. data.csv のキー
4. PRISMA 2020 の件数の計算
5. 照合ゲートの実装例

---

## 1. search_pages.csv

検索の各ページで返った PMID の生記録。後から「何がいつ返ったか」を再現するために残す。

| 列 | 内容 |
|---|---|
| `query_id` | 検索式のID（q1, q2 …。式そのものは protocol.md に記録） |
| `scan` | 全走査の回数（1, 2, …。2-1 の集合比較に使う） |
| `run_at` | 取得日時 |
| `sort` / `retstart` / `retmax` | そのページの取得条件 |
| `total_reported` | そのページの応答が返した総件数 |
| `pmids` | 返った PMID（`;` 区切り、返った順） |

## 2. ledger.csv（PMID 1件1行）

| 列 | 値 | 埋まる時点 |
|---|---|---|
| `pmid` | PubMed ID | 2-3 |
| `source_query` | 由来の query_id（複数なら `;` 区切り） | 2-2 / 2-3 |
| `first_author` / `year` / `title` | ツールの返り値から（`search` を compact で取得すれば 2-3 で埋まる） | 2-3 |
| `flags` | `retracted` / `retraction_notice` / `erratum` / `no_abstract` など（`;` 区切り） | 2-4 |
| `screen_tiab` | `pending` / `include` / `exclude` / `uncertain` | 2-4 |
| `tiab_exclude_reason` | 除外理由（1つ。撤回論文は `retracted`、撤回・訂正通知は `notice`） | 2-4 |
| `study_id` | 研究単位のID（同一研究の別報告は同じ値） | 2-5 |
| `ft_status` | `not_sought`（抄録のみモード・TiAb除外）/ `retrieved` / `not_retrieved` | 2-6 |
| `full_text_source` | `pmc` / `pdf` / `none`（探したが入手できず）/ `n/a`（全文を探していない） | 2-6 |
| `eligibility` | `pending` / `included` / `excluded` | 2-6（抄録のみモードは 2-4） |
| `eligibility_exclude_reason` | 全文での適格性判定の除外理由（1つ） | 2-6 |
| `extraction_status` | `pending` / `extracted` / `verified` / `n/a`（採用されなかった行） | Phase 3 / 4 |
| `extracted_batch` | 抽出したバッチ番号 | Phase 3 |
| `notes` | 「適格性不確実」、曖昧さなど | 任意 |

規則:

- **採否（`screen_tiab` / `eligibility`）と抽出状況（`extraction_status`）は別の列で管理する。** 抽出が進んでも `eligibility` は変わらない。
- `screen_tiab=exclude` の行は `eligibility=excluded`、`ft_status=not_sought` とする（除外理由は `tiab_exclude_reason` 側）。
- 抄録のみモードでは `ft_status=not_sought`、`full_text_source=n/a` のまま、2-4 の判定で `eligibility` を確定する。`uncertain` は `included` とし、`notes` に「適格性不確実」と書く。
  ただし `no_abstract` で判定できない記録は `eligibility=pending`（判定不能）のまま残す。
- 全文モードでは、`include` / `uncertain` の行だけ全文を探す。`not_retrieved` の行は `eligibility=pending` のまま残し、成果物で「全文未入手」として報告する（採否を推測しない）。
- `study_id` は既定で `pmid` と同じ値を入れ、同一研究と判明したら代表報告の値に揃える。

## 3. data.csv のキー

1行 = 1論文 × アウトカム × 時点 × 解析集団。キー `(pmid, outcome_name, timepoint, population)` を一意にする。
`population` が原文に書かれていなければ `NR` を入れる（空欄にするとキーが壊れる）。
`study_id` 列も持ち、台帳と一致させる。

## 4. PRISMA 2020 の件数の計算

台帳と検索記録から次のように数える（PubMed単独なので「Records identified from databases」は1行）。

| PRISMA 2020 の項目 | 計算 |
|---|---|
| Records identified (PubMed) | 検索式ごとのユニーク PMID 数の合計（ページングの取り直しで生じた同一検索式内の重複は数えない） |
| Duplicate records removed | Records identified − 全体のユニーク PMID 数（複数の検索式にまたがる重複） |
| Records screened | ユニーク PMID 数（= ledger の行数） |
| Records excluded | `screen_tiab=exclude` の件数（理由別の内訳も） |
| Reports sought for retrieval | （全文モード）`screen_tiab` が `include` または `uncertain` の件数 |
| Reports not retrieved | `ft_status=not_retrieved` の件数 |
| Reports assessed for eligibility | 全文モード: `ft_status=retrieved` の件数 ／ 抄録のみモード: 「抄録レベルで判定」として `screen_tiab` が `include` または `uncertain` の件数 |
| Reports excluded (with reasons) | `eligibility=excluded` かつ `screen_tiab≠exclude` の件数（`eligibility_exclude_reason` 別の内訳） |
| Reports included | `eligibility=included` の件数 |
| Studies included | `eligibility=included` の行の `study_id` のユニーク数 |

抄録のみモードでは全文段階がないため、「Reports sought for retrieval」「Reports not retrieved」は「該当なし（抄録のみで判定）」と書き、
「Reports assessed for eligibility」は抄録レベルでの件数であると明記する。`uncertain` を `included` に含め（`no_abstract` で判定不能のものは `pending`）、撤回論文は TiAb 段階で除外するため、「Reports excluded (with reasons)」は 0 になる。

算術の確認（合わなければ台帳の状態に矛盾がある）:

- 両モード共通: `Records screened − Records excluded = (screen_tiab が include または uncertain の件数)`、
  `Reports included + Reports excluded + (eligibility=pending の件数) = Records screened − Records excluded`
- 全文モード: `Reports sought − Reports not retrieved = Reports assessed`、`Reports assessed − Reports excluded = Reports included`
- 抄録のみモード: `Reports assessed（抄録レベル） = Reports included + (eligibility=pending の件数)`（Reports excluded は 0。pending は抄録がなく判定できなかった記録）

撤回論文は TiAb 段階で `tiab_exclude_reason=retracted` として除外するので、「Records excluded」の理由内訳に `retracted` として示す。

## 5. 照合ゲートの実装例

```python
import csv
from collections import Counter

ledger = list(csv.DictReader(open("ledger.csv", encoding="utf-8")))
data = list(csv.DictReader(open("data.csv", encoding="utf-8")))

included = {r["pmid"] for r in ledger if r["eligibility"] == "included"}
data_pmids = {r["pmid"] for r in data}
keys = Counter((r["pmid"], r["outcome_name"], r["timepoint"], r["population"]) for r in data)

missing = sorted(included - data_pmids)                     # (a) 抽出漏れ
extra = sorted(data_pmids - included)                       # (b) 除外したはずの PMID
dup_keys = [k for k, n in keys.items() if n > 1]            # (c) キー重複
ledger_study = {r["pmid"]: r["study_id"] for r in ledger}
wrong_study = sorted({r["pmid"] for r in data
                      if r["study_id"] != ledger_study.get(r["pmid"])})  # (d) study_id の対応違い

prespecified = {"ADR", "AMR"}   # protocol.md で指定したアウトカム名に置き換える
have = {(r["pmid"], r["outcome_name"]) for r in data}
missing_outcomes = sorted((p, o) for p in included for o in prespecified
                          if (p, o) not in have)            # (e) 指定アウトカムの行がない

print("missing:", missing)
print("extra:", extra)
print("duplicate keys:", dup_keys)
print("wrong study_id:", wrong_study)
print("missing outcomes:", missing_outcomes)
assert not (missing or extra or dup_keys or wrong_study or missing_outcomes), "照合ゲート不通過"
```

ゲートを通過したら、`included` の全 PMID の `extraction_status` が `extracted` 以上になっていることも確認する。
