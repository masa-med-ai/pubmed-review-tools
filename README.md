# pubmed-review-tools

**English** | [日本語](README.ja.md)

A Claude Code plugin marketplace that distributes **`pubmed`**: a PubMed search toolkit for Claude.
It bundles a local PubMed MCP server with skills for searching PubMed with hyperlinked citations,
checking a manuscript's references, and collecting numbers from many papers into tables
(a PubMed-only, systematic-review-style workflow).

- The MCP server runs **on your computer** and talks to NCBI directly. Its requests don't pass through any server run by the plugin author.
- No manual server installation: Claude Code starts it with `npx` when the plugin is enabled.

> This is a research-support tool. Always check important numbers and citations against the original papers.
> It is not a substitute for a full systematic review or for clinical judgement.

---

## Contents

- [What's included](#whats-included)
- [Requirements](#requirements)
- [Installation](#installation)
- [NCBI API key (optional, recommended)](#ncbi-api-key-optional-recommended)
- [Usage](#usage)
  - [pubmed-search: everyday searching](#pubmed-search-everyday-searching)
  - [pubmed-reference-verifier: checking a manuscript's references](#pubmed-reference-verifier-checking-a-manuscripts-references)
  - [pubmed-literature-review: tables of numbers from many papers](#pubmed-literature-review-tables-of-numbers-from-many-papers)
  - [literature-scout agent](#literature-scout-agent)
  - [The 10 MCP tools](#the-10-mcp-tools)
- [Citation format](#citation-format)
- [Privacy and data flow](#privacy-and-data-flow)
- [Limitations](#limitations)
- [Updating, uninstalling, and upgrading from 0.1.x](#updating-uninstalling-and-upgrading-from-01x)
- [Troubleshooting](#troubleshooting)
- [Other ways to use the MCP server](#other-ways-to-use-the-mcp-server)
- [License](#license)

---

## What's included

| Component | Name | What it does |
|---|---|---|
| MCP server | `pubmed` | [`pubmed_mcp_server2`](https://github.com/masa-med-ai/pubmed_mcp_server2) v2.0.4, launched with `npx -y pubmed_mcp_server2@2.0.4`. Provides 10 tools for PubMed, PubMed Central (PMC), and iCite. |
| Skill | `pubmed-search` | Everyday PubMed searching: builds MeSH + free-text queries, checks hit counts, reads abstracts, and answers with hyperlinked citations. |
| Skill | `pubmed-reference-verifier` | Checks that in-text citations match the reference list, and verifies each reference against PubMed (existence, authors, year, title, journal, DOI). |
| Skill | `pubmed-literature-review` | Searches PubMed systematically, screens records, and extracts numbers (N, outcomes, effect sizes, 95% CI, P values) from abstracts or PMC full text into Excel, CSV, or slides. Can also collect meta-analysis input data. |
| Agent | `literature-scout` | Does a quick literature scan in a separate context and returns a summary with a citation list. |

Skills are used automatically when your request matches them. You can also call them explicitly, for example `/pubmed:pubmed-search`.

## Requirements

- **Claude Code** (the one-line install command below needs 2.1.275 or later)
- **Node.js 18 or later** — used by `npx` to start the MCP server. Check with `node -v`. Install from <https://nodejs.org/> if needed.
- Internet access to `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov`, and `icite.od.nih.gov`
- *(Optional)* An NCBI API key — raises NCBI's rate limit from 3 to 10 requests per second
- *(Optional, for `.docx` manuscripts)* [pandoc](https://pandoc.org/) — `pubmed-reference-verifier` uses it to read Word files

## Installation

In Claude Code:

```
/plugin marketplace add masa-med-ai/pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

On Claude Code 2.1.275 or later you can do both in one step:

```
/plugin install pubmed --marketplace masa-med-ai/pubmed-review-tools
```

Then restart Claude Code and check the server:

```
/mcp
```

Installation is complete when `pubmed` shows as **connected**.
The first start can take 10–20 seconds while `npx` downloads the server; later starts use the cache.

## NCBI API key (optional, recommended)

Without a key the plugin works, but NCBI allows only 3 requests per second. With a free key you get 10 per second, which helps with large searches and batch fetching.

1. Sign in to NCBI: <https://account.ncbi.nlm.nih.gov/>
2. Open **Account settings**, scroll to **API Key Management**, and click **Create an API Key**.
3. Put the key in the `NCBI_API_KEY` environment variable, then restart Claude Code.

macOS / Linux (zsh):

```bash
echo 'export NCBI_API_KEY="your-key"' >> ~/.zshrc
source ~/.zshrc
```

(For bash, use `~/.bashrc` instead.)

Windows (PowerShell):

```powershell
setx NCBI_API_KEY "your-key"
```

Open a new terminal before starting Claude Code.

The plugin reads the key from the environment (`"NCBI_API_KEY": "${NCBI_API_KEY:-}"` in `.mcp.json`). The key is never stored in the plugin. Don't commit it to git or share it.

## Usage

Just ask Claude in plain language. The matching skill is picked up automatically.

### pubmed-search: everyday searching

Examples:

- "Search PubMed for evidence on SGLT2 inhibitors and hospitalization for heart failure."
- "Find recent RCTs of computer-aided detection in colonoscopy."
- "What does PubMed have on the long-term safety of GLP-1 receptor agonists? Give me the key papers."

What happens:

1. Claude breaks the question into concepts (PICO for clinical questions).
2. It builds a query that combines MeSH terms and free-text (`[tiab]`) terms.
3. It checks the hit count and PubMed's query translation with `count`, and adjusts the query.
4. It searches, reads the relevant abstracts, and answers with [hyperlinked citations](#citation-format).

Tips:

- Ask for "more", "newer", or "only RCTs" to refine the search.
- Ask for "papers similar to PMID 12345678" or "papers citing this one" to expand from a good paper.
- Ask for an RIS file to import results into EndNote, Zotero, or Mendeley.

### pubmed-reference-verifier: checking a manuscript's references

Examples:

- "Check the references in `draft.md`."
- "Verify the citations in `~/papers/manuscript.docx` against PubMed."
- "Fix the reference list in `draft.md`." (shows the proposed changes before applying them)

Modes:

| Mode | What it does | Uses PubMed |
|---|---|---|
| `verify` (default) | Cross-checks in-text citations and the reference list, and verifies each reference in PubMed | Yes |
| `check` | Cross-check only (offline) | No |
| `fix` | `verify`, then proposes corrections and applies them after you confirm | Yes |

It supports Vancouver numbering (`[1]`, `[1-3]`), Pandoc citations (`[@key]`), and PMIDs embedded in the text (`{12345678}`, `{PMID:12345678}`).
The report lists errors (for example, a citation with no reference entry, or a reference whose year or authors differ from PubMed), warnings, and suggested PMIDs and DOIs.

Note: PubMed records returned by the server don't include volume, issue, or pages. When those can't be confirmed, the report says so instead of guessing.

### pubmed-literature-review: tables of numbers from many papers

Examples:

- "Collect RCTs of CADe in colonoscopy from PubMed and put the primary outcomes in an Excel table."
- "Make an evidence table of [topic] with N, outcomes, effect sizes, and P values."
- "Collect 2x2 data for a meta-analysis of [intervention] vs [control] on [outcome]."

How it works:

1. **Settings.** Claude first asks two questions:
   - Is this a summary table only, or do you also need meta-analysis input data (2x2 tables, mean/SD/N, effect sizes with 95% CI)?
   - Should it use abstracts only, or full text as well? Full text is used for PMC articles and for PDFs you provide.
2. **Protocol.** It writes the question (PICO), the inclusion and exclusion criteria, and the outcomes to `protocol.md`, and asks you to confirm.
3. **Search.** It builds and calibrates the query, then fetches all PMIDs. It reads every page twice and checks that the set of PMIDs is the same both times, so nothing is missed.
4. **Screening.** It screens each record on title and abstract (include / exclude / uncertain, with a reason for each exclusion). Retracted papers are excluded, and reports of the same study are linked together. In full-text mode it then judges eligibility on the full text.
5. **Extraction.** It reads the included papers 5–6 at a time. For each number it records where it came from and a short quote from the original. Anything not reported is written as `NR`, never guessed.
6. **Checks.** It verifies that every included paper and every pre-specified outcome is in the data, then runs a self-check (N analyzed vs enrolled, primary vs secondary, group direction, P value vs significance).
7. **Output.** It produces Excel, CSV, or slides, together with PRISMA 2020 counts and the search record.

Everything for one review is saved in a folder named `review-YYYYMMDD/`:

| File | Contents |
|---|---|
| `protocol.md` | Question, criteria, settings, and the search record (database, date, exact query, PubMed's query translation, hit count) |
| `search_pages.csv` | Raw PMID lists returned by each search page |
| `ledger.csv` | One row per PMID: screening decision, eligibility, reasons, flags, study ID, extraction status |
| `data.csv` | Extracted data, one row per paper × outcome × time point × analysis population |
| Outputs | Excel / CSV / PowerPoint, plus meta-analysis sheets if requested |

The ledger makes long reviews resumable: if a session is interrupted, Claude reads `ledger.csv` and continues where it stopped.

This skill searches **PubMed only**. A full systematic review needs several databases (for example Embase and CENTRAL) and trial registries. Describe results from this skill as a PubMed-based rapid review, an evidence map, or the data-collection step of a review, and state the single-database limitation. The skill reminds you of this in its outputs. It collects meta-analysis input data, but doesn't compute pooled estimates, I², or forest plots; use R (`meta`, `metafor`), RevMan, or similar for those.

### literature-scout agent

Use it when you want a quick overview without filling your main conversation with search results:

- "Use the literature-scout agent to scan the literature on [topic]."

It returns the search query and hit count, a short list of key papers (citation, design, N, one-line summary), an overview of the evidence, and gaps or caveats.

### The 10 MCP tools

You rarely need to call these directly. The skills use them for you.

| Tool | Purpose |
|---|---|
| `search` | PubMed search with MeSH, filters (dates, publication types, languages, humans only, has abstract, free full text), sorting, and paging |
| `count` | Hit count and PubMed's query translation only (fast) |
| `fetch` | Abstract and bibliographic data for one PMID |
| `fetch_batch` | Abstracts, MeSH terms, and publication types for several PMIDs |
| `get_full_text` | Section-aware full text from PubMed Central (PMC articles only) |
| `find_similar_articles` | Related articles for a PMID |
| `get_citation_counts` | Citation counts (iCite), or citing PMIDs from PubMed |
| `convert_ids` | Convert between PMID, PMCID, and DOI |
| `export_to_ris` | RIS file for reference managers |
| `batch_process` | Run several of the above on one set of PMIDs |

## Citation format

When Claude uses a paper in an answer, it cites it as first author, journal, and year, linked to PubMed:

```
[*Yamada T, N Engl J Med, 2025*](https://pubmed.ncbi.nlm.nih.gov/12345678/)
```

Authors, journal, year, and PMID always come from the tool results, never from memory. If you prefer a different format, just say so.

## Privacy and data flow

- The MCP server runs locally over stdio. Its API requests go **directly from your computer** to NCBI E-utilities, PubMed Central, and iCite (NIH). They are not sent to the plugin author or to any other service.
- This covers the MCP server only. Your conversation with Claude, including the search results Claude reads, is processed by Claude as usual under Anthropic's terms ([data usage](https://code.claude.com/docs/en/data-usage)). The `literature-scout` agent may also use Claude's web search.
- Your `NCBI_API_KEY` stays in your environment. It is sent only to NCBI.
- NCBI's [usage policies](https://www.ncbi.nlm.nih.gov/home/about/policies/) apply.

## Limitations

- **PubMed only.** Embase, CENTRAL, Web of Science, Scopus, and trial registries are not searched.
- **Full text** is available only for articles in PubMed Central. For other articles, use abstracts or provide PDFs yourself.
- **Abstracts can disagree with full texts.** Check important numbers against the full paper.
- **Long author lists** (more than 30 authors) are returned as the first 10 names plus "et al." by `fetch`, `fetch_batch`, `search` in full mode, and `batch_process`. Search results in the default compact mode show the first author plus "et al.".
- **Publication-type tags** in PubMed depend on indexing and can be missing for recent papers. The skills combine them with free-text terms.
- **No search snapshot (WebEnv).** Very large result sets can shift while being paged. The literature-review skill reads every page twice to detect this, but can't guarantee completeness.
- **AI double-checking is not independent human review.** The literature-review skill can re-check suspicious numbers with a second agent. That is not equivalent to two independent reviewers.

## Updating, uninstalling, and upgrading from 0.1.x

Update to the latest version:

```
/plugin marketplace update pubmed-review-tools
```

Then update the installed plugin, either from the **Installed** tab of `/plugin` ("Update now"), or from your terminal:

```bash
claude plugin update pubmed@pubmed-review-tools
```

Restart Claude Code afterwards.

Uninstall:

```
/plugin uninstall pubmed@pubmed-review-tools
```

**Upgrading from 0.1.x.** Version 0.1.x had one plugin named `pubmed-systematic-review`. It was renamed to `pubmed` in 0.2.0, so you need to reinstall:

```
/plugin marketplace update pubmed-review-tools
/plugin uninstall pubmed-systematic-review@pubmed-review-tools
/plugin install pubmed@pubmed-review-tools
```

If you also have older copies of these skills elsewhere (personal skills, or skills uploaded to claude.ai), remove them so they don't trigger alongside the plugin.

## Troubleshooting

| Symptom | What to try |
|---|---|
| `/mcp` shows `pubmed` as failed | Run `node -v` (needs 18 or later). If you use nvm, make sure Node.js is available in the environment Claude Code starts from. Restart Claude Code. |
| It fails only on the first start | `npx` may still be downloading the server. Restart Claude Code. Behind a corporate proxy, set npm's proxy settings. |
| "429 Too Many Requests" or slow batches | Set an [NCBI API key](#ncbi-api-key-optional-recommended). |
| The PubMed tools don't appear | Check that the plugin is enabled (`/plugin`), then restart Claude Code. |
| A skill isn't used automatically | Call it explicitly, for example `/pubmed:pubmed-search`, or mention PubMed in your request. |
| Two similar skills respond | Remove older copies of the skills (see [Upgrading from 0.1.x](#updating-uninstalling-and-upgrading-from-01x)). |
| `.docx` files can't be read by the verifier | Install [pandoc](https://pandoc.org/), or save the manuscript as Markdown. |

## Other ways to use the MCP server

The server is also available on its own, without the skills:

- **Claude Desktop:** install the `.mcpb` bundle from the [pubmed_mcp_server2 releases](https://github.com/masa-med-ai/pubmed_mcp_server2/releases). No Node.js setup needed.
- **Any MCP client:** run `npx -y pubmed_mcp_server2` (on [npm](https://www.npmjs.com/package/pubmed_mcp_server2)).

See the [pubmed_mcp_server2 README](https://github.com/masa-med-ai/pubmed_mcp_server2) for details.

## License

MIT © Masashi Misawa
