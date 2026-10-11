# Verification Rules — 技術詳細

pubmed-reference-verifier スキルの引用パターン検出、参考文献パース、フィールド照合に関する技術仕様。

---

## 1. 引用パターンの正規表現

### 1.1 Pandoc形式

```regex
# 単独引用
\[@([\w:.#$%&\-+?<>~/]+)\]

# 複数引用（セミコロン区切り）
\[(-?@[\w:.#$%&\-+?<>~/]+(?:\s*;\s*-?@[\w:.#$%&\-+?<>~/]+)*)\]

# 抑制形式（著者名を省略）
\[-@([\w:.#$%&\-+?<>~/]+)\]
```

**引用キーの構成規則**（cite スキル準拠）:
- 形式: `{first_author}_{journal_abbrev}_{year}`
- 例: `smith_lancet_2024`, `tanaka_gastroenterology_2023`
- 許可文字: `[\w:.#$%&\-+?<>~/]`

**エッジケース**:
- `[@key, p. 10]` — locator付き引用。キーは `@key` の部分のみ
- `[@key{pp. 1-10}]` — suffix付き引用
- `[see @key]` — prefix付き引用

### 1.2 Vancouver番号形式

```regex
# 基本パターン
\[(\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*)\]
```

**曖昧性解消ヒューリスティック**:

以下のパターンは引用ではないため除外する:

| パターン | 例 | 除外理由 |
|----------|-----|---------|
| 統計指標 | `[95% CI]`, `[OR 2.3]`, `[p = 0.01]` | 角括弧内に英字・%・=を含む |
| 図表参照 | `[Figure 1]`, `[Table 2]`, `[Fig. 3]` | Figure/Table/Fig/Suppl が先行 |
| サンプルサイズ | `[n = 50]`, `[N=120]` | n/N と = を含む |
| 脚注マーカー | `[*]`, `[†]`, `[‡]` | 数字でない |
| 3桁超の数字 | `[1000]`, `[2024]` | 参考文献番号として非現実的 |

**除外判定の正規表現**:
```regex
# 以下にマッチする場合は引用ではない
\[\s*(?:
  (?:Figure|Fig\.?|Table|Tab\.?|Suppl|Appendix)\s*\d  |  # 図表参照
  \d+\s*%                                               |  # パーセント
  [A-Za-z]                                               |  # 英字を含む（純粋な数字でない）
  [=<>±]                                                 |  # 数式記号
  \d{4,}                                                    # 4桁以上の数字
)\s*\]
```

**追加コンテキストルール**:
- 前方に `p`, `=`, `CI`, `OR`, `HR`, `RR` がある場合、統計値の可能性が高い
- 文頭に出現する `[数字]` は引用の可能性が高い
- ピリオド直後の `[数字]` は引用の可能性が高い

### 1.3 Bare PMID形式

```regex
\{(\d{7,8})\}
```

**注意**: 7〜8桁の数字をブレースで囲んだもの。Vault固有の引用形式。

### 1.4 PMID prefix形式

```regex
\{PMID:(\d{7,8})\}
```

---

## 2. 参考文献パース文法

### 2.1 Vancouver形式

```
<entry> ::= <number> "." <authors> "." <title> "." <journal> "." <year> ";" <volume> "(" <issue> ")" ":" <pages> "." [<doi>] [<pmid>]

<number>  ::= \d+
<authors> ::= <author> ("," <author>)* ("," "et al.")?
<author>  ::= <surname> " " <initials>
<surname> ::= [A-Za-z\-']+
<initials>::= [A-Z]+
<title>   ::= .+          # ピリオドで終わる
<journal> ::= .+          # ピリオドで終わる（略称またはフルネーム）
<year>    ::= \d{4}
<volume>  ::= \d+
<issue>   ::= \d+
<pages>   ::= <page> "-" <page> | "e" \d+
<page>    ::= \d+
<doi>     ::= "doi:" .+
<pmid>    ::= "PMID:" \s* \d+
```

**バリエーション**:
- `et al.` は著者が6名超の場合に使用されることが多い
- 号（issue）は省略されることがある
- Epub ahead of print の場合、巻号・ページがない
- ページ範囲の短縮形: `1209-19` = `1209-1219`

### 2.2 BibTeX形式

Pandoc引用キーの場合、対応する `.bib` ファイルをパースする:

```bibtex
@article{smith_lancet_2024,
  author  = {Smith, John and Doe, Alice},
  title   = {Title of the Article},
  journal = {Lancet},
  year    = {2024},
  volume  = {403},
  number  = {10421},
  pages   = {1209--1219},
  doi     = {10.1016/S0140-6736(24)00001-0},
  pmid    = {37639719}
}
```

BibTeX フィールドの抽出:
- `author`: `and` で分割し各著者を取得
- `pages`: `--` を `-` に正規化
- `year`: 4桁数字
- `doi`: prefix (`https://doi.org/` 等) を除去して比較

### 2.3 YAML bibliography

Pandocのメタデータブロックで定義される場合:

```yaml
references:
  - id: smith_lancet_2024
    author:
      - family: Smith
        given: John
    title: Title of the Article
    container-title: Lancet
    issued:
      date-parts: [[2024]]
    volume: 403
    page: 1209-1219
    DOI: 10.1016/S0140-6736(24)00001-0
    PMID: 37639719
```

---

## 3. フィールド正規化ルール

### 3.1 タイトル正規化

```
normalize_title(s):
  1. HTMLタグ除去: <i>, <sub>, <sup> 等
  2. 末尾ピリオド除去
  3. 全角→半角変換
  4. 連続空白を単一スペースに
  5. 小文字化
  6. 特殊文字正規化: ﬁ→fi, ﬂ→fl, –→-, —→-
```

タイトル比較は正規化後の文字列で行う。完全一致でなくても、編集距離が短い場合（Levenshtein距離 ≤ 5 または類似度 ≥ 0.95）は一致と判定する。

### 3.2 著者名正規化

```
normalize_author(s):
  1. 姓のみ抽出（カンマ前 or 最後の単語）
  2. アクセント記号除去: ü→u, é→e, ö→o 等
  3. ハイフン保持: O'Brien → OBrien, Saint-Exupéry → Saint-Exupery
  4. 小文字化
```

著者比較:
- **First author**: 姓の完全一致が必須
- **全著者リスト**: 人数の比較 + 各著者の姓一致
- 「et al.」の扱い: 3名以上省略している場合はWARNINGに留める

### 3.3 ジャーナル名正規化

- NLM略称（Index Medicus形式）とフルネームの両方を許容
- 例: `Lancet` = `The Lancet`, `N Engl J Med` = `New England Journal of Medicine`
- ピリオドの有無を無視: `N. Engl. J. Med.` = `N Engl J Med`
- PubMedレコードの `Source` フィールド（略称）と `FullJournalName` フィールド（フルネーム）の両方と照合

### 3.4 ページ正規化

```
normalize_pages(s):
  1. 短縮形展開: "1209-19" → "1209-1219"
     アルゴリズム: 終了ページの桁数 < 開始ページの桁数 の場合、
     開始ページの上位桁を補完する
  2. en-dash/em-dash → hyphen: "1209–1219" → "1209-1219"
  3. スペース除去: "1209 - 1219" → "1209-1219"
  4. e-page対応: "e12345" はそのまま
```

### 3.5 DOI正規化

```
normalize_doi(s):
  1. URL prefix除去: "https://doi.org/" → ""
  2. "doi:" prefix除去
  3. 小文字化
  4. 末尾スラッシュ除去
```

---

## 4. エラー重要度分類マトリクス

| 不一致フィールド | 単独で ERROR | 単独で WARNING | 備考 |
|-----------------|-------------|---------------|------|
| 著者（first author）| E003 | — | 姓が異なる場合は確実にエラー |
| 著者数 | — | W003 | et al. の切り捨て位置の違いは許容 |
| 発行年 | E003 | — | Epub年 vs Print年の1年差はWARNINGに格下げ |
| タイトル | E003 | — | 類似度 0.90-0.95 の場合はWARNING |
| ジャーナル名 | — | W002 | 略称の揺れが多いためWARNING |
| 巻号 | E003 | — | |
| ページ | E003 | — | 最も頻出するエラー |
| DOI | — | W002 | 記載がない場合はINFOとしてDOI候補を提示 |
| PMID | — | — | PMIDの不一致は別論文の可能性 → E003 |

### 複合判定

- 2つ以上のフィールドが同時に不一致 → そのうち1つでもERRORレベルなら全体をERRORとする
- WARNING のみが複数 → 最も重要度の高いもの1つをWARNINGとして報告し、残りはINFOに格下げ

---

## 5. BibTeXデータベース探索順序

1. 対象ファイルのYAMLフロントマター `bibliography:` フィールド
2. 対象ファイルと同一ディレクトリの `.bib` ファイル
3. Vault直下の `references.bib`
4. Vault直下の `*.bib`（複数ある場合は更新日時が最新のもの）

---

## 6. PubMed MCP 使用パターン

以下の例ではツール名の接頭辞を省略している（実際は環境のもの、例: `mcp__plugin_pubmed_pubmed__fetch` に読み替える）。各ツールは構造化済みの結果を返すため、`WebFetch` のような抽出 `prompt` は不要。レート制限・リトライはサーバー側で処理される。

### 単一PMID照合（fetch）

```
fetch(id: "37639719")
```
→ title / abstract（`text`）/ journal / year / authors / doi を返す。**巻・号・ページ・PMCIDは返さない**（必要なら `convert_ids` で PMCID、巻号頁は E-utilities の esummary で補う。不可ならレポートに未照合と明記）。

### バッチ照合（5件以上の場合に推奨）

```
fetch_batch(
  pmids: ["37639719", "38012345", "39876543"]
)
```

PMIDは1回のバッチで複数指定可能。著者リスト・年・雑誌・DOIのみ照合し抄録が不要な場合は `include_abstract: false` を指定して軽量化する。

### 軽量メタデータ取得（esummary 相当）

抄録を含まない基本フィールド（タイトル・著者・ジャーナル・年・DOI・MeSH・出版タイプ）だけが必要な場合:

```
fetch_batch(
  pmids: ["37639719", "38012345"],
  include_abstract: false
)
```

または検索時に `output_mode: "compact"` を指定すると、検索結果に同等のメタデータが含まれる。

### タイトル検索（PMID不明時）

```
search(
  query: '"Title Phrase"[Title] AND Surname I[Author]',
  retmax: 5,
  sort: "relevance",
  output_mode: "compact"
)
```

`compact` には authors / journal / year / doi / pmcid が含まれるため、追加取得なしで照合できることが多い。抄録まで必要なら候補PMIDを `fetch_batch` に渡す。日付・言語・出版種別で絞り込む場合は `filters` 引数を併用する。

### DOI⇔PMID⇔PMCID 変換

```
convert_ids(
  from_type: "doi",
  to_type: "pmid",
  ids: ["10.1016/S0140-6736(24)00001-0"]
)
```

`from_type` / `to_type` は `pmid` / `pmcid` / `doi` から選択。最大200件。DOI→PMID解決、PMID→DOI/PMCID補完の双方に使える。

### 被引用数取得（iCite / elink）

```
get_citation_counts(
  pmids: ["37639719", "38012345"]
)
```

デフォルトは iCite（PubMed外の引用も含む件数のみ）。`citing_source: "pubmed"` かつ `include_citing_pmids: true` で引用元PMIDのリスト（後ろ向きスノーボーリング用）も取得できる。

### 類似論文・全文・一括処理（補助機能）

```
# 類似論文（elink 相当）
find_similar_articles(pmid: "37639719", retmax: 20)

# PMC全文（参考文献節のクロスチェック等に）
get_full_text(pmcIds: ["PMC1234567"], sections: ["references"])

# RIS出力（fixモードで参考文献を引用管理ソフト向けに生成）
export_to_ris(pmids: ["37639719", "38012345"])

# 同一PMID群に複数操作をまとめて適用
batch_process(
  pmids: ["37639719"],
  operations: ["abstract", "citations", "ris_export"]
)
```

### フォールバック（MCP不可時のみ）

PubMed MCP サーバーが利用できない環境では、従来どおり `WebFetch` で E-utilities を直接呼び出してよい。対応関係は以下:

- `fetch` / `fetch_batch` → `efetch.fcgi`（`rettype=abstract&retmode=xml`）
- `search` → `esearch.fcgi`、`count` → `esearch.fcgi`（`rettype=count`）
- `convert_ids` → `esearch.fcgi`（`term=...[doi]`）または ID Converter API
- `find_similar_articles` → `elink.fcgi`、`get_citation_counts` → `https://icite.od.nih.gov/api/pubs`

E-utilities 直接呼び出し時はレート制限（APIキーなし3req/秒）に注意し、呼び出し間に1秒以上の間隔を確保すること。
