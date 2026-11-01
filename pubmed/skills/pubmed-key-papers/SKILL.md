---
name: pubmed-key-papers
description: >
  ユーザーのCQ（クリニカルクエスチョン）に対して、影響度の高い鍵論文をPubMedから短時間で探すスキル。
  検索結果をiCiteの指標（RCR・被引用数）で順位付けし、CQへの適合と研究デザインを判定したうえで、
  参考文献と被引用を前後にたどって検索式の外の重要文献も拾う。
  「鍵論文を探して」「このCQで影響度の高い論文は？」「この分野の代表的な文献」「必読論文」「重要文献を教えて」
  「インパクトの高い論文」「まず読むべき論文」など、数本の重要文献を選びたい要求で使う。
  通常の文献検索は pubmed-search、網羅的な収集や数値抽出は pubmed-literature-review を使う。
---

# PubMed Key Papers

CQ に答えるうえで影響度の高い論文を5〜10本選ぶ。網羅性ではなく、見落としたくない論文を短時間で見つけるためのスキルで、結果は「影響度の高い候補」として示す。被引用の多さは研究の質や結論の正しさを保証しないので、「最良のエビデンス」とは書かない。

出典の扱いは `pubmed-search` の §0（ツールの返り値だけを使う）と §2（ハイパーリンク形式）に従う。

## コマンド

`<skill-dir>` はこの SKILL.md があるフォルダ。候補の集計は件数が多く、MCP の返り値を会話に載せると文脈を圧迫するので、同梱 CLI で行う。

```bash
SCRIPT="<skill-dir>/../pubmed-search/scripts/pubmed_eutils.py"
python3 -I "$SCRIPT" impact-candidates 'QUERY' --output ./key-papers-YYYYMMDD/candidates.csv
python3 -I "$SCRIPT" chain-candidates PMID1 PMID2 ... --known ./key-papers-YYYYMMDD/candidates.csv
```

`impact-candidates` は保存先フォルダを作らないので、先に作っておく。`search` と同じフィルタ（`--start-date`、`--language` など）が使える。

シェルが使えない環境では、`search` で得た数十件を MCP の `get_citation_counts` に渡して代用する。`relative_citation_ratio` が返らないサーバー版では被引用数と出版年で比べ、前後の引用追跡は `find_similar_articles` と `citing_source='pubmed'` で行う。この場合は候補の範囲が狭いことを結果に書く。

## 手順

### 1. CQ を適合条件に分解する

PICO に分け、「CQ に直接答える論文」の条件を1〜2文で書く。この条件が順位付けの最上位になる。CQ が曖昧で条件が書けないときだけ、ユーザーに確認する。

### 2. 検索式を作って候補を集める

`pubmed-search` の Step 1〜3 で検索式を作る。後で絞り込むので、感度を優先する（20〜200件の目安は適用しない）。研究デザインのフィルタは付けない。ガイドラインや総説も候補にするためである。

`impact-candidates` を実行する。結果の見方:

| 項目 | 内容 |
|---|---|
| `total` / `retrieved` / `truncated` | ヒット数と取得数。`truncated: true` なら関連度の上位だけを見ている。検索式を絞るか `--max-records` を増やし、それでも残れば結果に書く |
| `rcr_unavailable` | RCR がない、または暫定値の論文の数 |
| `shortlist[].routes` | `top_rcr`、`top_citations`、`relevance`、`recent_cited`（新しい論文の暫定 RCR 上位）、`recent`（新しい論文の関連度上位）のどの経路で選ばれたか |
| `shortlist[].publication_types` / `retracted` | PubMed の出版タイプと、撤回論文かどうか |

全候補は `--output` の CSV に残る。shortlist に足りない領域があれば CSV から探す。

### 3. 指標を見る前に CQ への適合を判定する

被引用の多い論文には CQ から外れたものが混ざるので、順位より先に適合で分ける。

1. タイトルと出版タイプで、明らかに対象外の論文を外す。`retracted: true` の論文は候補から除き、撤回されたことを結果に書く。
2. 残りの抄録を `fetch_batch` で読み、`direct`（CQ に直接答える）、`indirect`（背景や関連領域）、`off`（対象外）に分ける。
3. 判定は抄録の内容で行う。読んでいない論文を `direct` にしない。

### 4. 引用を前後にたどる

`direct` の論文3〜10本を種にして `chain-candidates` を実行する。

- `backward`: 種のうち `shared_seeds` 本以上が参考文献に挙げている論文。背景の基礎研究やガイドラインが多い。
- `forward`: 種の `shared_seeds` 本以上を引用している論文。新しい試験や総説が多い。

`min_shared` の既定は2。結果が多すぎれば `--min-shared 3` に上げる。新しい候補も手順3と同じように判定する。新しい `direct` が見つかれば、それを種に加えて1回だけ繰り返す。新しい `direct` が出なくなるか2周したら止める。

### 5. 順位を付ける

次の順で比べる。上の基準で差がつけば、下の基準は使わない。

1. CQ への適合: `direct` を先に、`indirect` は背景文献として別に分ける
2. 研究デザイン: 診療ガイドライン、質の高い系統的レビュー・メタ解析、主要な RCT、大規模な観察研究、その他の順
3. RCR: 高い順。RCR がなければ `citation_count` と出版年で比べる

`provisional: true` の RCR、RCR がない論文、`recent_cited` と `recent` 経路の論文は、値の小ささで落とさず新着枠で扱う。発表から日が浅く、引用がまだ集まっていないためである。

### 6. 提示する

次の4部で返す。

1. **影響度の高い候補**（5〜10本）: `pubmed-search` §2 の出典、研究デザイン、RCR または被引用数、CQ との関係を1行で
2. **新着枠**（あれば）: 指標が未確定だが CQ に直接関わる論文
3. **対象外にした高被引用論文**: RCR が上位なのに外した論文と理由
4. **探し方と限界**: 検索式、ヒット数、種の本数、`truncated` の有無、撤回の有無

限界として、次の点を必要に応じて書く。

- iCite は PubMed 中心で、更新にも遅れがある
- 引用には批判的なものも含まれ、分野や時代による差は RCR でも補正しきれない
- 撤回の検出は PubMed の出版タイプに依存する
- 検索対象は PubMed のみで、網羅的なレビューの代わりにはならない
