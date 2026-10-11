---
name: pubmed-reference-verifier
description: >
  医学論文原稿（.md / .docx）の本文中引用と参考文献リストの整合性を検証し、PubMedで書誌情報
  （実在・著者・年・タイトル・雑誌・DOI）を照合して修正案を出すスキル。「引用をチェックして」
  「参考文献を検証」「Referencesの整合性」「引用番号がずれていないか」「PMIDを確認して」
  「reference check」など、原稿の引用・参考文献リストの確認や修正を求められたときに使う。
  Vancouver番号形式・Pandoc形式・PMID埋め込み形式に対応。文献を新たに探すだけなら pubmed-search を使う。
---

# Reference Verification Skill

医学論文の本文中引用（in-text citations）と参考文献リスト（References）の整合性を検証し、PubMed MCPを用いた書誌情報チェックと修正提案を行う。

## 引数

```
$ARGUMENTS = <mode> <file_path>
```

| モード | 説明 | PubMedアクセス |
|--------|------|----------------|
| `verify` | 完全検証（相互参照 + PubMed照合） | あり |
| `check` | 簡易検証（相互参照のみ、オフライン） | なし |
| `fix` | 完全検証 + 自動修正適用 | あり |

モード省略時は `verify` をデフォルトとする。ファイルパス省略時はカレントディレクトリの `.md` ファイルから原稿を探す。対象が `.docx` の場合は `pandoc -t markdown` でテキスト抽出してから検証する。

---

## PubMedアクセス方法 — MCP優先、E-utilitiesフォールバック

**重要: PubMed MCPサーバーのツール名プレフィックスは環境によって異なる**（例: プラグイン同梱なら `mcp__plugin_pubmed_pubmed__search`、ほか `mcp__PubMed__search`, `mcp__pubmed-remote__search`, `mcp__remote-devices__pubmed-mcp-server__search`）。特定のプレフィックスを決め打ちせず、**現在のセッションのツール一覧から `search` / `fetch` / `fetch_batch` / `count` / `convert_ids` / `export_to_ris` を持つPubMed系MCPサーバーを探して使う**。ツールが遅延ロード状態なら ToolSearch で「pubmed search fetch batch」等を1回検索してまとめて読み込む。

優先順位:

1. **第1優先: PubMed MCPツール** — 存在すれば必ずこちら。承認プロンプト不要で安定動作し、結果は構造化済み（XML/JSONの自前パース不要）。レート制限もサーバー側で管理される
2. **第2優先: NCBI E-utilities API（WebFetch直接呼び出し）** — PubMed MCPが未接続・エラーの場合のみ。WebFetchはURL承認が必要な環境があり、承認が得られない場合は失敗する。その場合はWebSearchによる補助確認も検討する

### 主要MCPツール（プレフィックスは環境のものに読み替える）

| 機能 | ツール | 主な引数 |
|------|--------|----------|
| 検索 | `search` | `query`（PubMed構文可）, `retmax`, `sort`, `output_mode`(minimal/compact/full) |
| 件数のみ | `count` | `query` |
| 単一PMID取得 | `fetch` | `id`（1件のみ） |
| バッチ取得 | `fetch_batch` | `pmids[]`, `include_abstract` |
| ID変換 (PMID⇔PMCID⇔DOI) | `convert_ids` | `from_type`, `to_type`, `ids[]` |
| RIS出力 | `export_to_ris` | `pmids[]` |

### 利用上の注意（実測に基づく）

- 5件以上のPMID照合は `fetch_batch` で一括取得する（個別 `fetch` を繰り返さない）。書誌照合だけなら `include_abstract: false` で軽量化
- **サーバー実装により `fetch` / `fetch_batch` が巻(号)・ページを返さないことがある**。その場合、巻号・ページはDOI・年・雑誌の一致から間接確認し、E-utilitiesの `esummary` が使えるなら補助併用する。どちらも不可ならレポートに「巻号・ページは未照合」と明記する（E003と誤判定しない）
- `search` のタイトル検索は**フレーズ全体を引用符付きで** `"..."[Title]` と指定する。引用符なしだと語ごとにAll Fields展開されて0件やノイズになる（例: `"automation bias"[Title] AND Goddard K[Author]`）。0件のときは語を減らす→引用符を外す→著者条件を外すの順で緩めて再検索する
- 著者指定は `Surname I[Author]` 形式（例: `Ayers JW[Author]`）
- **同梱MCP（pubmed_mcp_server2 v2.0.1以降）は著者31名以上の論文を「先頭10名 + `et al.`」に短縮して返す**。この場合は全著者数の比較（W003）を行わず、first author と先頭10名の一致のみ確認する（レポートに「著者リスト短縮のため著者数は未照合」と明記）

---

## 実行手順

### Step 0: 準備

1. `$ARGUMENTS` からモードとファイルパスを取得する
2. 対象ファイルを Read で読み込む（.docxはpandocでテキスト化）

### Step 1: 引用抽出

本文（References/参考文献セクションより前）から、以下のパターンの引用を行番号付きで全て抽出する。

1. **Pandoc形式**: `[@key]`, `[@key1; @key2]`, `[-@key]`
   - 正規表現: `\[(-?@[\w:.#$%&\-+?<>~/]+(?:\s*;\s*-?@[\w:.#$%&\-+?<>~/]+)*)\]`
2. **Vancouver番号形式**: `[1]`, `[1-3]`, `[1,2,5]` および上付き `1)`, `1,2)` 形式
   - 正規表現: `\[(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]`
   - 除外: `[95% CI]`, `[OR 2.3]`（統計表現）, `[Figure 1]`, `[Table 2]`（図表参照）, `[n = 50]`（サンプルサイズ）, 前後にp, =, %, CI等がある `[数値]`
3. **Bare PMID形式**: `{37639719}`（7-8桁の数字をブレースで囲む）
   - 正規表現: `\{(\d{7,8})\}`
4. **PMID prefix形式**: `{PMID:12345678}`
   - 正規表現: `\{PMID:(\d{7,8})\}`
5. **arXiv形式**: `{arXiv:2509.04664}`（PubMed未収載のプレプリント用）

各引用について行番号・引用テキスト・形式・キー/番号/PMIDを記録する。

### Step 2: 参考文献リスト解析

`References`, `参考文献`, `引用文献`, `Bibliography` セクション（見出しレベル・大文字小文字不問）を見つけ、各エントリから番号/キー・著者（全員）・タイトル・ジャーナル名・発行年・巻(号):ページ・DOI・PMIDをパースする。

- Vancouver形式: `1. Smith J, Doe A. Title. J Name. 2024;100(1):1-10. PMID: 12345678.` および `1) Smith J...` 形式
- Pandoc/BibTeX参照形式: `.bib` を YAMLフロントマター `bibliography:` → 同一ディレクトリ → Vault直下 `references.bib` の順で探索
- Bare PMID形式で参考文献リストがない場合は本文中のPMIDのみで検証を進める

### Step 3: 相互参照チェック

- 本文で引用されているが参考文献リストにない → **E001**
- 参考文献リストにあるが本文で未引用 → **E002**
- 番号不連続（Vancouver） → **W001**、出現順と番号順の不一致 → **W004**

### Step 4: PubMed検証（verify / fix モードのみ）

checkモードではスキップ。PubMed MCPツールで書誌情報を取得して照合する。

**PMID既知**: `fetch_batch(pmids: [...], include_abstract: false)` で一括取得。結論まで照合したい文献のみ `fetch(id)` で抄録込み取得。

**PMID不明**: `search(query: '"Title Phrase"[Title] AND Surname I[Author]', retmax: 5, output_mode: "compact")` で検索。compactにはauthors/journal/year/doiが含まれ多くはこれで照合できる。候補は **I001** で報告。DOIが分かる場合は `convert_ids(from_type: "doi", to_type: "pmid", ids: [...])` で解決する。

**PubMed未収載の文献**（arXiv等のプレプリント、書籍、Webページ）: タイトル・著者検索でヒットしないことを確認したら無理にPMIDを探さない。arXivは `{arXiv:XXXX.XXXXX}` 表記とし、必要ならWebSearchで原典の実在・著者を確認する。レポートには **W002** として理由付きで記載する。

**照合フィールド**:

| フィールド | 照合方法 | 不一致時 |
|-----------|---------|---------|
| 著者名 | 姓の一致（first author必須、全著者は個数も比較） | E003 / W003 |
| 発行年 | 完全一致 | E003 |
| タイトル | 正規化後の類似度（句読点・大小文字無視） | E003 |
| ジャーナル名 | 略称・フルネームどちらか一致 | W002 |
| 巻号 | 完全一致（MCPが返さない場合は間接確認、未照合なら明記） | E003 |
| ページ | 正規化後一致（`1209-19`→`1209-1219` 展開、e-page対応） | E003 |
| DOI | 完全一致（大小文字無視） | W002 |

**正規化**: タイトルは末尾ピリオド・HTMLタグ除去、著者名は姓のみ比較（アクセント記号正規化）、ジャーナル名はNLM略称とフルネーム両方許容。

### Step 5: レポート生成

```markdown
# Reference Verification Report
File: <path>  |  Mode: <mode>  |  Date: YYYY-MM-DD

## Summary
- 本文中引用数: N / 参考文献数: N
- 検出形式: Pandoc / Vancouver / BarePMID / Mixed
- PubMed照合: N/N件完了（アクセス手段: MCP / E-utilities）

## ERRORS (修正必須)
- **E001** 参照先なし引用 — Line <N>: `<citation>`
- **E002** 孤立参考文献 — Ref #<N>: <authors> (<year>)
- **E003** 書誌情報不一致 — Ref #<N>: <field> "<local>" vs PubMed "<pubmed>" → 修正案

## WARNINGS (確認推奨)
- **W001** 番号不連続 / **W002** PubMed照合不可（理由） / **W003** 著者数相違 / **W004** 出現順不一致

## INFO
- **I001** PMID候補 / **I002** DOI候補
```

ERRORSが0件なら「All references verified successfully.」と表示する。照合済み文献は1st author・雑誌名・発刊年をPubMedリンク付きで一覧化する。

### Step 6: 自動修正（fix モードのみ）

1. E003はPubMedの正確な値で修正案を生成
2. E001のPMID形式は `fetch_batch` から書誌情報を取得して参考文献エントリを生成（RIS出力が必要なら `export_to_ris`）
3. 全修正案をdiff形式で一覧表示し、ユーザー確認後に Edit で適用
4. 優先順位: ページ番号 → 著者名 → 発行年 → タイトル → ジャーナル名 → 新規エントリ追加

---

## エラーコード一覧

| コード | 重要度 | 説明 |
|--------|--------|------|
| E001 | ERROR | 参照先なし引用 |
| E002 | ERROR | 孤立参考文献 |
| E003 | ERROR | 書誌情報不一致 |
| W001 | WARNING | 番号不連続 |
| W002 | WARNING | PubMed照合不可（PMID不明・未収載） |
| W003 | WARNING | 著者数相違 |
| W004 | WARNING | 出現順と番号順の不一致 |
| I001 | INFO | PMID候補の提示 |
| I002 | INFO | DOI候補の提示 |

## Verification

- 全引用・全参考文献が抽出漏れなくリスト化されているか（引用数と置換/照合数の一致を確認）
- PubMed照合は全文献について実在・著者・年・雑誌の4点を最低限確認したか
- MCPが巻号・ページを返さなかった場合、未照合であることをレポートに明記したか