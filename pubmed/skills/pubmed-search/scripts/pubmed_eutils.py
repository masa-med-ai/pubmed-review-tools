#!/usr/bin/env python3
"""Direct PubMed/PMC client mirroring the common PubMed MCP operations."""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Iterable


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ICITE = "https://icite.od.nih.gov/api/pubs"
IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PMC_OA = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
SECTION_ORDER = (
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusions",
    "references",
)
LANG_MAP = {
    "eng": "english",
    "jpn": "japanese",
    "fre": "french",
    "ger": "german",
    "spa": "spanish",
    "ita": "italian",
    "chi": "chinese",
    "kor": "korean",
}


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def element_text(node: ET.Element | None) -> str:
    return clean_text("".join(node.itertext()) if node is not None else "")


def cap_authors(authors: list[str], max_authors: int = 30, keep: int = 10) -> list[str]:
    return authors if len(authors) <= max_authors else [*authors[:keep], "et al."]


def publication_year(pubdate: str) -> str:
    match = re.search(r"\b(18|19|20|21)\d{2}\b", pubdate or "")
    return match.group(0) if match else ""


def pubmed_date(value: str) -> str:
    """Normalize a user-supplied date to PubMed's YYYY/MM/DD form.

    Accepts YYYY, YYYY/MM, YYYY/MM/DD and the same with '-' or '.' separators,
    so both 2024/01/01 and 2024-01-01 work as filter values.
    """
    normalized = value.strip().replace("-", "/").replace(".", "/")
    match = re.fullmatch(r"(\d{4})(?:/(\d{1,2})(?:/(\d{1,2}))?)?", normalized)
    if not match:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}: use YYYY, YYYY/MM, or YYYY/MM/DD "
            "(hyphen or dot separators are also accepted)"
        )
    year, month, day = match.groups()
    parts = [year]
    if month:
        if not 1 <= int(month) <= 12:
            raise argparse.ArgumentTypeError(f"invalid month in date {value!r}")
        parts.append(f"{int(month):02d}")
    if day:
        if not 1 <= int(day) <= 31:
            raise argparse.ArgumentTypeError(f"invalid day in date {value!r}")
        parts.append(f"{int(day):02d}")
    return "/".join(parts)


class PubMedClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("NCBI_API_KEY", "").strip()
        self.email = os.getenv("NCBI_EMAIL", "").strip()
        self.tool = os.getenv("NCBI_TOOL", "chatgpt_pubmed_eutils_skill").strip()
        self.interval = 0.11 if self.api_key else 0.34
        self._last_request = 0.0
        self._rate_lock = threading.Lock()

    def _common(self) -> dict[str, str]:
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        post: bool = False,
        add_common: bool = True,
    ) -> bytes:
        payload = {key: str(value) for key, value in (params or {}).items() if value is not None}
        if add_common:
            payload.update(self._common())
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        target = url if post else f"{url}?{encoded.decode('ascii')}"
        data = encoded if post else None

        for attempt in range(4):
            with self._rate_lock:
                wait = self.interval - (time.monotonic() - self._last_request)
                if wait > 0:
                    time.sleep(wait)
                self._last_request = time.monotonic()
            request = urllib.request.Request(
                target,
                data=data,
                headers={"User-Agent": f"{self.tool}/1.0", "Accept": "application/json, application/xml, text/xml"},
                method="POST" if post else "GET",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlsplit(url).netloc}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError(f"Request failed for {urllib.parse.urlsplit(url).netloc}: {exc}") from exc
            time.sleep(2**attempt)
        raise RuntimeError("Request failed after retries")

    def get_json(self, url: str, params: dict[str, Any], *, post: bool = False, add_common: bool = True) -> Any:
        # A small number of legacy NCBI records contain literal control
        # characters inside JSON strings. strict=False preserves the record
        # instead of failing an otherwise valid batch.
        return json.loads(
            self.request(url, params, post=post, add_common=add_common).decode("utf-8"),
            strict=False,
        )

    def get_xml(self, url: str, params: dict[str, Any], *, post: bool = False, add_common: bool = True) -> ET.Element:
        return ET.fromstring(self.request(url, params, post=post, add_common=add_common))

    def build_filtered_query(self, query: str, args: argparse.Namespace) -> str:
        clauses = [f"({query})"]
        start = getattr(args, "start_date", None)
        end = getattr(args, "end_date", None)
        if start or end:
            clauses.append(f'(\"{start or "1800"}\"[dp] : \"{end or "3000"}\"[dp])')
        publication_types = getattr(args, "publication_type", None) or []
        if publication_types:
            clauses.append("(" + " OR ".join(f'\"{value}\"[pt]' for value in publication_types) + ")")
        languages = getattr(args, "language", None) or []
        if languages:
            terms = [LANG_MAP.get(value.lower(), value.lower()) for value in languages]
            clauses.append("(" + " OR ".join(f'\"{value}\"[la]' for value in terms) + ")")
        if getattr(args, "humans_only", False):
            clauses.append('\"humans\"[mh]')
        if getattr(args, "has_abstract", False):
            clauses.append('\"hasabstract\"')
        if getattr(args, "free_full_text", False):
            clauses.append('\"free full text\"[sb]')
        return " AND ".join(clauses)

    def count(self, query: str) -> dict[str, Any]:
        data = self.get_json(
            f"{EUTILS}/esearch.fcgi",
            {"db": "pubmed", "term": query, "retmode": "json", "retmax": 0},
        )
        result = data.get("esearchresult", {})
        warning_list = result.get("warninglist", {}) or {}
        warnings: list[str] = []
        for key in ("phraseignored", "quotedphrasefound", "outputmessages"):
            value = warning_list.get(key, [])
            warnings.extend(value if isinstance(value, list) else [value] if value else [])
        return {
            "query": query,
            "count": int(result.get("count", 0)),
            "query_translation": result.get("querytranslation", ""),
            "warnings": warnings,
        }

    def search(
        self,
        query: str,
        *,
        retmax: int = 50,
        retstart: int = 0,
        sort: str = "relevance",
        output_mode: str = "compact",
    ) -> dict[str, Any]:
        sort_value = {"pub_date": "pub date", "first_author": "first author"}.get(sort, sort)
        data = self.get_json(
            f"{EUTILS}/esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": retmax,
                "retstart": retstart,
                "sort": sort_value,
                "usehistory": "y",
            },
        )
        result = data.get("esearchresult", {})
        pmids = result.get("idlist", [])
        summaries = self.summaries(pmids)
        abstracts = {item["pmid"]: item for item in self.fetch_batch(pmids)} if output_mode == "full" else {}
        rows: list[dict[str, Any]] = []
        for pmid in pmids:
            item = summaries.get(pmid, self._empty_summary(pmid))
            base = {
                "id": pmid,
                "title": item["title"],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "full_text_available": bool(item["pmcid"]),
            }
            if output_mode == "minimal":
                rows.append(base)
                continue
            if output_mode == "compact":
                authors = item["authors"]
                rows.append(
                    {
                        **base,
                        "authors": [] if not authors else [authors[0]] if len(authors) == 1 else [f"{authors[0]} et al."],
                        "journal": item["journal"],
                        "year": item["year"],
                        "doi": item["doi"],
                        "pmcid": item["pmcid"],
                    }
                )
                continue
            abstract = abstracts.get(pmid, {})
            rows.append(
                {
                    **base,
                    "authors": cap_authors(abstract.get("authors") or item["authors"]),
                    "journal": item["journal"],
                    "year": item["year"],
                    "doi": item["doi"],
                    "pmcid": item["pmcid"],
                    "pub_date": item["pubdate"],
                    "abstract": abstract.get("abstract"),
                    "mesh_terms": abstract.get("mesh_terms", []),
                    "publication_types": abstract.get("publication_types", []),
                }
            )
        total = int(result.get("count", 0))
        showing = len(rows)
        return {
            "total": total,
            "showing": showing,
            "retstart": retstart,
            "next_start": retstart + showing if showing and retstart + showing < total else None,
            "query_translation": result.get("querytranslation", ""),
            "final_term": query,
            "sort": sort,
            "results": rows,
        }

    @staticmethod
    def _empty_summary(pmid: str) -> dict[str, Any]:
        return {
            "pmid": pmid,
            "pmcid": None,
            "title": "",
            "pubdate": "",
            "year": "",
            "journal": "",
            "authors": [],
            "doi": None,
        }

    def summaries(self, pmids: list[str]) -> dict[str, dict[str, Any]]:
        output: dict[str, dict[str, Any]] = {}
        for part in chunks(unique(pmids), 200):
            if not part:
                continue
            data = self.get_json(
                f"{EUTILS}/esummary.fcgi",
                {"db": "pubmed", "id": ",".join(part), "retmode": "json"},
            )
            result = data.get("result", {})
            for pmid in part:
                record = result.get(pmid)
                if not record:
                    continue
                pmcid = None
                doi = None
                for identifier in record.get("articleids", []) or []:
                    if identifier.get("idtype") == "pmc":
                        pmcid = identifier.get("value")
                    elif identifier.get("idtype") == "doi":
                        doi = identifier.get("value")
                pubdate = record.get("pubdate", "")
                output[pmid] = {
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "title": clean_text(record.get("title", "")),
                    "pubdate": pubdate,
                    "year": publication_year(pubdate),
                    "journal": clean_text(record.get("fulljournalname") or record.get("source") or ""),
                    "authors": [clean_text(author.get("name", "")) for author in record.get("authors", []) if author.get("name")],
                    "doi": doi,
                }
        return output

    def fetch_batch(self, pmids: list[str], include_abstract: bool = True) -> list[dict[str, Any]]:
        requested = unique(pmids)
        found: dict[str, dict[str, Any]] = {}
        for part in chunks(requested, 200):
            root = self.get_xml(
                f"{EUTILS}/efetch.fcgi",
                {"db": "pubmed", "id": ",".join(part), "retmode": "xml", "rettype": "abstract"},
                post=True,
            )
            for article in root.findall(".//PubmedArticle"):
                item = self._parse_pubmed_article(article)
                if item:
                    if not include_abstract:
                        item.pop("abstract", None)
                    found[item["pmid"]] = item
        return [found[pmid] for pmid in requested if pmid in found]

    def fetch(self, pmid: str) -> dict[str, Any]:
        items = self.fetch_batch([pmid])
        if not items:
            raise RuntimeError(f"No PubMed record found for PMID {pmid}")
        item = items[0]
        return {
            "id": pmid,
            "title": item["title"],
            "text": item["abstract"],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "metadata": {
                "journal": item["journal"],
                "year": item["year"],
                "authors": cap_authors(item["authors"]),
                "doi": item["doi"],
                "mesh_terms": item["mesh_terms"],
                "publication_types": item["publication_types"],
            },
        }

    def _parse_pubmed_article(self, node: ET.Element) -> dict[str, Any] | None:
        pmid = element_text(node.find("./MedlineCitation/PMID"))
        if not pmid:
            return None
        article = node.find("./MedlineCitation/Article")
        title = element_text(article.find("./ArticleTitle") if article is not None else None)
        abstract_parts: list[str] = []
        if article is not None:
            for part in article.findall("./Abstract/AbstractText"):
                text = element_text(part)
                if text:
                    label = part.attrib.get("Label") or part.attrib.get("NlmCategory")
                    abstract_parts.append(f"{label}: {text}" if label else text)
        authors: list[str] = []
        if article is not None:
            for author in article.findall("./AuthorList/Author"):
                collective = element_text(author.find("./CollectiveName"))
                if collective:
                    authors.append(collective)
                    continue
                last = element_text(author.find("./LastName"))
                initials = element_text(author.find("./Initials")) or element_text(author.find("./ForeName"))
                name = clean_text(f"{last} {initials}")
                if name:
                    authors.append(name)
        journal = element_text(article.find("./Journal/Title") if article is not None else None)
        pubdate_node = article.find("./Journal/JournalIssue/PubDate") if article is not None else None
        year = element_text(pubdate_node.find("./Year") if pubdate_node is not None else None)
        if not year and pubdate_node is not None:
            year = publication_year(element_text(pubdate_node.find("./MedlineDate")))
        if not year and article is not None:
            year = element_text(article.find("./ArticleDate/Year"))
        doi = None
        for identifier in node.findall("./PubmedData/ArticleIdList/ArticleId"):
            if identifier.attrib.get("IdType") == "doi":
                doi = element_text(identifier)
                break
        mesh_terms = [element_text(item) for item in node.findall("./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName")]
        pub_types = [element_text(item) for item in article.findall("./PublicationTypeList/PublicationType")] if article is not None else []
        return {
            "pmid": pmid,
            "title": title,
            "abstract": "\n".join(abstract_parts) if abstract_parts else "No abstract available",
            "journal": journal,
            "year": year or "Unknown",
            "authors": authors,
            "doi": doi,
            "mesh_terms": [term for term in mesh_terms if term],
            "publication_types": [value for value in pub_types if value],
        }

    def get_full_text(self, pmcids: list[str], sections: list[str]) -> list[dict[str, Any]]:
        wanted = set(SECTION_ORDER if "all" in sections else sections)
        return [self._get_full_text_one(pmcid, wanted) for pmcid in unique(pmcids)]

    def _get_full_text_one(self, raw_pmcid: str, wanted: set[str]) -> dict[str, Any]:
        numeric = re.sub(r"^PMC", "", raw_pmcid.strip(), flags=re.IGNORECASE)
        pmcid = f"PMC{numeric}"
        empty = {"pmcid": pmcid, "pmid": None, "title": "", "sections": [], "available_sections": []}
        if not numeric.isdigit():
            return {**empty, "error": "Invalid PMCID format"}
        try:
            root = self.get_xml(
                f"{EUTILS}/efetch.fcgi",
                {"db": "pmc", "id": pmcid, "retmode": "xml"},
                post=True,
            )
        except Exception as exc:
            return {**empty, "error": str(exc)}
        article = root.find(".//article")
        if article is None:
            return {**empty, "error": "Not found or not downloadable in PMC"}
        pmid = None
        for identifier in article.findall(".//article-id"):
            if identifier.attrib.get("pub-id-type") == "pmid":
                pmid = element_text(identifier)
                break
        title = element_text(article.find(".//article-title"))
        collected: dict[str, list[str]] = {}
        available: set[str] = set()
        abstract = article.find(".//front//abstract")
        if abstract is not None:
            available.add("abstract")
            text = self._paragraph_text(abstract)
            if "abstract" in wanted and text:
                collected.setdefault("abstract", []).append(text)
        body = article.find(".//body")
        if body is not None:
            for section in body.findall("./sec"):
                title_text = element_text(section.find("./title"))
                key = self._classify_section(section.attrib.get("sec-type", ""), title_text)
                if not key:
                    continue
                available.add(key)
                text = self._paragraph_text(section)
                if key in wanted and text:
                    collected.setdefault(key, []).append(text)
        references = article.find(".//ref-list")
        if references is not None:
            available.add("references")
            if "references" in wanted:
                refs = [element_text(ref) for ref in references.findall("./ref")]
                refs = [ref for ref in refs if ref]
                if refs:
                    collected["references"] = refs
        output_sections = [
            {"name": key, "text": "\n\n".join(collected[key])}
            for key in SECTION_ORDER
            if key in collected
        ]
        pdf_url = None
        try:
            oa_root = self.get_xml(PMC_OA, {"id": pmcid}, add_common=False)
            for link in oa_root.findall(".//link"):
                if link.attrib.get("format") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break
        except Exception:
            pass
        return {
            "pmcid": pmcid,
            "pmid": pmid,
            "title": title,
            "sections": output_sections,
            "available_sections": [key for key in SECTION_ORDER if key in available],
            "pdf_url": pdf_url,
        }

    @staticmethod
    def _paragraph_text(node: ET.Element) -> str:
        paragraphs = [element_text(part) for part in node.findall(".//p")]
        paragraphs = [part for part in paragraphs if part]
        return "\n\n".join(paragraphs) if paragraphs else element_text(node)

    @staticmethod
    def _classify_section(sec_type: str, title: str) -> str | None:
        value = f"{sec_type} {title}".lower()
        if "intro" in value or "background" in value:
            return "introduction"
        if "method" in value or "materials" in value or "study design" in value:
            return "methods"
        if "result" in value or "finding" in value:
            return "results"
        if "discussion" in value:
            return "discussion"
        if "conclusion" in value:
            return "conclusions"
        return None

    def find_similar(self, pmid: str, retmax: int = 20) -> dict[str, Any]:
        data = self.get_json(
            f"{EUTILS}/elink.fcgi",
            {"dbfrom": "pubmed", "db": "pubmed", "linkname": "pubmed_pubmed", "id": pmid, "retmode": "json"},
        )
        linked: list[str] = []
        for linkset in data.get("linksets", []) or []:
            for database in linkset.get("linksetdbs", []) or []:
                if database.get("linkname") == "pubmed_pubmed":
                    linked.extend(str(value) for value in database.get("links", []) if str(value) != pmid)
        linked = unique(linked)[:retmax]
        summaries = self.summaries(linked)
        articles = []
        for linked_pmid in linked:
            item = summaries.get(linked_pmid)
            if not item:
                continue
            articles.append(
                {
                    "pmid": linked_pmid,
                    "pmcid": item["pmcid"],
                    "title": item["title"],
                    "authors": cap_authors(item["authors"]),
                    "journal": item["journal"],
                    "pubdate": item["pubdate"],
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{linked_pmid}/",
                    "full_text_available": bool(item["pmcid"]),
                }
            )
        return {"reference_pmid": pmid, "similar_articles": articles, "count": len(articles), "error": None}

    def citation_counts(self, pmids: list[str], source: str, include_citing: bool) -> list[dict[str, Any]]:
        requested = unique(pmids)
        if source == "pubmed":
            return [self._pubmed_citations(pmid, include_citing) for pmid in requested]
        data = self.get_json(ICITE, {"pmids": ",".join(requested), "format": "json"}, add_common=False)
        by_pmid = {str(item.get("pmid")): item for item in data.get("data", []) or []}
        return [
            {
                "pmid": pmid,
                "citation_count": by_pmid.get(pmid, {}).get("citation_count"),
                "source": "icite",
                **({"note": "Citation data not available"} if pmid not in by_pmid else {}),
            }
            for pmid in requested
        ]

    def _pubmed_citations(self, pmid: str, include: bool) -> dict[str, Any]:
        data = self.get_json(
            f"{EUTILS}/elink.fcgi",
            {"dbfrom": "pubmed", "db": "pubmed", "linkname": "pubmed_pubmed_citedin", "id": pmid, "retmode": "json"},
        )
        citing: list[str] = []
        for linkset in data.get("linksets", []) or []:
            for database in linkset.get("linksetdbs", []) or []:
                if database.get("linkname") == "pubmed_pubmed_citedin":
                    citing.extend(str(value) for value in database.get("links", []))
        result: dict[str, Any] = {"pmid": pmid, "citation_count": len(citing), "source": "pubmed"}
        if include:
            result["citing_pmids"] = citing
        return result

    def convert_ids(self, ids: list[str], from_type: str, to_type: str) -> dict[str, Any]:
        requested = unique(ids)
        patterns = {
            "pmid": re.compile(r"^\d+$"),
            "pmcid": re.compile(r"^PMC\d+$", re.IGNORECASE),
            "doi": re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE),
        }
        valid = [value for value in requested if patterns[from_type].match(value)]
        data = (
            self.get_json(
                IDCONV,
                {"ids": ",".join(valid), "idtype": from_type, "format": "json"},
            )
            if valid
            else {"records": []}
        )
        conversions: list[dict[str, Any]] = []
        failed: list[str] = []
        records = data.get("records", []) or []
        by_input: dict[str, dict[str, Any]] = {}
        for index, record in enumerate(records):
            key = str(
                record.get("requested-id")
                or record.get("requestedid")
                or (valid[index] if index < len(valid) else "")
            )
            if key:
                by_input[key] = record
        valid_index = {value: index for index, value in enumerate(valid)}
        for input_id in requested:
            if input_id not in valid_index:
                conversions.append({"input": input_id, "error": f"Invalid {from_type} format"})
                failed.append(input_id)
                continue
            index = valid_index[input_id]
            record = by_input.get(input_id, records[index] if index < len(records) else {})
            item = {
                "input": input_id,
                "pmid": str(record["pmid"]) if record.get("pmid") is not None else None,
                "pmcid": record.get("pmcid"),
                "doi": record.get("doi"),
            }
            if record.get("errmsg") or not item.get(to_type):
                item["error"] = record.get("errmsg") or f"No {to_type} mapping available"
                failed.append(input_id)
            conversions.append(item)
        return {
            "requested": len(requested),
            "converted": len(requested) - len(failed),
            "failed": len(failed),
            "conversions": conversions,
            "failedIds": failed,
        }

    def ris(self, pmids: list[str]) -> str:
        records = self.fetch_batch(pmids)
        blocks = []
        for item in records:
            lines = ["TY  - JOUR"]
            if item["authors"]:
                lines.append(f"AU  - {item['authors'][0]}")
            if item["title"]:
                lines.append(f"TI  - {item['title']}")
            if item["journal"]:
                lines.append(f"JO  - {item['journal']}")
            if item["year"] and item["year"] != "Unknown":
                lines.append(f"PY  - {item['year']}///")
            if item["doi"]:
                lines.append(f"DO  - {item['doi']}")
            lines.extend([f"AN  - {item['pmid']}", "DB  - PubMed", "ER  - "])
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks) + ("\n" if blocks else "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct NCBI PubMed/PMC API client")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_filter_arguments(target: argparse.ArgumentParser) -> None:
        # count and search must accept identical filters so that the count
        # used to calibrate a query reflects the exact final search.
        target.add_argument("--start-date", type=pubmed_date)
        target.add_argument("--end-date", type=pubmed_date)
        target.add_argument("--publication-type", action="append")
        target.add_argument("--language", action="append")
        target.add_argument("--humans-only", action="store_true")
        target.add_argument("--has-abstract", action="store_true")
        target.add_argument("--free-full-text", action="store_true")

    count = sub.add_parser("count", help="Count PubMed matches and show query translation")
    count.add_argument("query")
    add_filter_arguments(count)

    search = sub.add_parser("search", help="Search PubMed")
    search.add_argument("query")
    search.add_argument("--retmax", type=int, default=50, choices=range(1, 501), metavar="1-500")
    search.add_argument("--retstart", type=int, default=0)
    search.add_argument("--sort", choices=["relevance", "pub_date", "first_author"], default="relevance")
    search.add_argument("--output-mode", choices=["minimal", "compact", "full"], default="compact")
    add_filter_arguments(search)

    fetch = sub.add_parser("fetch", help="Fetch one PMID abstract")
    fetch.add_argument("pmid")

    fetch_batch = sub.add_parser("fetch-batch", help="Fetch multiple PMID abstracts")
    fetch_batch.add_argument("pmids", nargs="+")
    fetch_batch.add_argument("--no-abstract", action="store_true")

    full_text = sub.add_parser("get-full-text", help="Fetch PMC full text")
    full_text.add_argument("pmcids", nargs="+")
    full_text.add_argument("--sections", nargs="+", choices=[*SECTION_ORDER, "all"], default=["all"])

    similar = sub.add_parser("find-similar-articles", help="Find related PubMed articles")
    similar.add_argument("pmid")
    similar.add_argument("--retmax", type=int, default=20, choices=range(1, 101), metavar="1-100")

    ris = sub.add_parser("export-to-ris", help="Export compact RIS")
    ris.add_argument("pmids", nargs="+")
    ris.add_argument("--output")

    citations = sub.add_parser("get-citation-counts", help="Get iCite or PubMed citation counts")
    citations.add_argument("pmids", nargs="+")
    citations.add_argument("--source", choices=["icite", "pubmed"], default="icite")
    citations.add_argument("--include-citing-pmids", action="store_true")

    convert = sub.add_parser("convert-ids", help="Convert PMID, PMCID, and DOI")
    convert.add_argument("ids", nargs="+")
    convert.add_argument("--from-type", choices=["pmid", "pmcid", "doi"], required=True)
    convert.add_argument("--to-type", choices=["pmid", "pmcid", "doi"], required=True)

    batch = sub.add_parser("batch-process", help="Run multiple MCP-like operations")
    batch.add_argument("pmids", nargs="+")
    batch.add_argument(
        "--operations",
        nargs="+",
        choices=["abstract", "citations", "similar", "ris_export", "full_text"],
        required=True,
    )
    batch.add_argument("--max-concurrency", type=int, default=3, choices=range(1, 6), metavar="1-5")
    return parser


def run_batch(client: PubMedClient, pmids: list[str], operations: list[str], max_workers: int) -> dict[str, Any]:
    requested = unique(pmids)

    def execute(operation: str) -> tuple[str, Any]:
        if operation == "abstract":
            return operation, {"items": client.fetch_batch(requested)}
        if operation == "citations":
            return operation, {"items": client.citation_counts(requested, "icite", False)}
        if operation == "similar":
            return operation, {"items": {pmid: client.find_similar(pmid, 10) for pmid in requested}}
        if operation == "ris_export":
            return operation, {"ris": client.ris(requested)}
        converted = client.convert_ids(requested, "pmid", "pmcid")
        pmcids = [item["pmcid"] for item in converted["conversions"] if item.get("pmcid")]
        return operation, {"items": client.get_full_text(pmcids, ["all"])}

    results: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(operations))) as pool:
        futures = {pool.submit(execute, operation): operation for operation in unique(operations)}
        for future in concurrent.futures.as_completed(futures):
            operation = futures[future]
            try:
                name, value = future.result()
                results[name] = value
            except Exception as exc:
                results[operation] = {"error": str(exc)}
    return {"pmids": requested, "results": results}


def main() -> int:
    args = build_parser().parse_args()
    client = PubMedClient()
    try:
        if args.command == "count":
            output: Any = client.count(client.build_filtered_query(args.query, args))
        elif args.command == "search":
            query = client.build_filtered_query(args.query, args)
            output = client.search(
                query,
                retmax=args.retmax,
                retstart=args.retstart,
                sort=args.sort,
                output_mode=args.output_mode,
            )
        elif args.command == "fetch":
            if not args.pmid.isdigit():
                raise ValueError("PMID must be numeric")
            output = client.fetch(args.pmid)
        elif args.command == "fetch-batch":
            output = {"items": client.fetch_batch(args.pmids, not args.no_abstract)}
        elif args.command == "get-full-text":
            if len(args.pmcids) > 20:
                raise ValueError("get-full-text accepts at most 20 PMCIDs")
            output = {"items": client.get_full_text(args.pmcids, args.sections)}
        elif args.command == "find-similar-articles":
            if not args.pmid.isdigit():
                raise ValueError("PMID must be numeric")
            output = client.find_similar(args.pmid, args.retmax)
        elif args.command == "export-to-ris":
            ris_text = client.ris(args.pmids)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as handle:
                    handle.write(ris_text)
                output = {"count": len(unique(args.pmids)), "output": os.path.abspath(args.output)}
            else:
                output = {"count": len(unique(args.pmids)), "ris": ris_text}
        elif args.command == "get-citation-counts":
            if len(args.pmids) > 1000:
                raise ValueError("get-citation-counts accepts at most 1000 PMIDs")
            output = {"items": client.citation_counts(args.pmids, args.source, args.include_citing_pmids)}
        elif args.command == "convert-ids":
            if len(args.ids) > 200:
                raise ValueError("convert-ids accepts at most 200 identifiers")
            output = client.convert_ids(args.ids, args.from_type, args.to_type)
        else:
            if len(args.pmids) > 50:
                raise ValueError("batch-process accepts at most 50 PMIDs")
            output = run_batch(client, args.pmids, args.operations, args.max_concurrency)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
