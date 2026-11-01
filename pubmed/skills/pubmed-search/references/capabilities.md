# API capability map

| Skill command | Primary endpoint | Returned data | Important limitation |
|---|---|---|---|
| `count`, `search` | NCBI ESearch + ESummary | Count, PMID, translated query, title, authors, journal, DOI, PMCID | Search relevance still requires screening |
| `fetch`, `fetch-batch` | NCBI PubMed EFetch | Abstract, authors, MeSH, publication types, DOI | Usually not the article full text |
| `get-full-text` | NCBI PMC EFetch | JATS full text and selected sections | Only PMC-downloadable content |
| `find-similar-articles` | NCBI ELink `pubmed_pubmed` | NCBI-computed related PMIDs and summaries | Similarity is discovery support, not an inclusion criterion |
| `get-citation-counts --source icite` | NIH iCite | Citation count, RCR, percentile, citations per year, clinical and research flags; references with `--include-references` | Coverage and update timing differ from other indexes; RCR is missing or provisional for recent papers |
| `impact-candidates` | NCBI ESearch + NIH iCite + PubMed EFetch | Full candidate CSV and a shortlist with publication types | Metrics rank attention, not quality or fit to the question |
| `chain-candidates` | NIH iCite + PubMed EFetch | Papers shared by the references or citers of seed PMIDs | Limited to what iCite links; seeds must be screened first |
| `get-citation-counts --source pubmed` | NCBI ELink `pubmed_pubmed_citedin` | PubMed citing PMIDs and count | Counts only PubMed-linked citing records |
| `convert-ids` | NCBI PMC ID Converter | PMID, PMCID, DOI mappings | A DOI does not guarantee a PMCID or open full text |
| `export-to-ris` | PubMed EFetch | Compact RIS | Verify metadata after reference-manager import |
| `batch-process` | Combination of the above | Operations grouped by PMID set | Full text is returned only when PMID maps to PMCID |

## Search construction

Use PubMed syntax directly. A sensitive clinical query usually combines:

```text
("Concept A"[MeSH Terms] OR synonym-a[Title/Abstract] OR synonym-b[Title/Abstract])
AND
("Concept B"[MeSH Terms] OR synonym-c[Title/Abstract])
```

Add design filters only when they match the question:

```text
AND (randomized controlled trial[Publication Type] OR random*[Title/Abstract])
```

Do not rely on a single acronym unless it is highly specific. Check `query_translation` because PubMed automatic term mapping can broaden or reinterpret untagged phrases.

## Pagination and batching

- `search` supports `--retstart`; continue from `next_start` until the desired page or all records are obtained.
- Maximum `--retmax` is 500. Prefer smaller pages for model screening.
- `fetch-batch` chunks requests internally. For close manual extraction, process only 5–10 abstracts at a time to avoid output truncation.
- `get-full-text` accepts no more than 20 PMCIDs per command.
- `get-citation-counts` accepts no more than 1,000 PMIDs; `convert-ids` accepts no more than 200.

## Date interpretation

ESummary may expose a journal issue date later than the electronic publication date. When recency matters, inspect the fetched record and describe which date is being used. Do not label an article as newly published solely from a future issue date.

