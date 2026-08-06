from __future__ import annotations

from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into normalized paper records."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        title = _first_text(item.get("title"))
        summary = _clean_abstract(item.get("abstract") or item.get("description", ""))
        doi = normalize_whitespace(str(item.get("DOI", ""))).lower()
        url = normalize_whitespace(str(item.get("URL", "")))

        if not title or not summary:
            continue

        paper_id = doi or _fallback_id(title, url)
        if not paper_id or paper_id in seen_ids:
            continue

        authors = _parse_authors(item.get("author", []))
        categories = _parse_categories(item.get("subject", []))
        published = (
            _date_from_crossref(item.get("published-print"))
            or _date_from_crossref(item.get("published-online"))
            or _date_from_crossref(item.get("published"))
        )
        updated = _date_from_crossref(item.get("indexed")) or _date_from_crossref(item.get("created"))
        pdf_url = _extract_pdf_url(item.get("link", []))

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=pdf_url,
                comment=f"source=Crossref; doi={doi}" if doi else "source=Crossref",
            )
        )
        seen_ids.add(paper_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, save raw payload, and save parsed raw records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": ",".join(
            [
                "DOI",
                "URL",
                "title",
                "abstract",
                "author",
                "subject",
                "published",
                "published-print",
                "published-online",
                "indexed",
                "created",
                "link",
            ]
        ),
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)",
    }

    response = _get_with_retry(CROSSREF_API_URL, params=params, headers=headers)
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a raw records JSON snapshot into PaperRecord objects."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected raw records list at {path}, got {type(payload).__name__}.")

    records: list[PaperRecord] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        records.append(
            PaperRecord(
                paper_id=str(row.get("paper_id", "")),
                title=str(row.get("title", "")),
                summary=str(row.get("summary", "")),
                authors=list(row.get("authors") or []),
                categories=list(row.get("categories") or []),
                primary_category=str(row.get("primary_category", "")),
                published=str(row.get("published", "")),
                updated=str(row.get("updated", "")),
                abs_url=str(row.get("abs_url", "")),
                pdf_url=str(row.get("pdf_url", "")),
                comment=str(row.get("comment", "")),
            )
        )
    return records


def _get_with_retry(url: str, params: dict, headers: dict, max_attempts: int = 4) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        response: requests.Response | None = None
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
                return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == max_attempts - 1:
                raise
        else:
            if attempt == max_attempts - 1 and response is not None:
                response.raise_for_status()

        retry_after = _retry_after_seconds(response)
        delay = retry_after or 2**attempt
        time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("Crossref request failed without a response.")


def _retry_after_seconds(response: requests.Response | None) -> int:
    if response is None:
        return 0
    value = response.headers.get("Retry-After", "")
    try:
        return max(int(value), 0)
    except ValueError:
        return 0


def _first_text(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return normalize_whitespace(str(value or ""))


def _clean_abstract(value: str) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = normalize_whitespace(text)
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def _parse_authors(value) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = author.get("name") or " ".join(
            part for part in [author.get("given"), author.get("family")] if part
        )
        name = normalize_whitespace(str(name or ""))
        if name:
            authors.append(name)
    return authors


def _parse_categories(value) -> list[str]:
    if not isinstance(value, list):
        return []
    categories: list[str] = []
    seen: set[str] = set()
    for category in value:
        text = normalize_whitespace(str(category or ""))
        key = text.lower()
        if text and key not in seen:
            categories.append(text)
            seen.add(key)
    return categories


def _date_from_crossref(value) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if isinstance(date_parts, list) and date_parts:
        parts = date_parts[0]
        if isinstance(parts, list) and parts:
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
            except (TypeError, ValueError):
                return ""
            return f"{year:04d}-{month:02d}-{day:02d}"
    raw_date = value.get("date-time")
    if raw_date:
        return str(raw_date)[:10]
    return ""


def _extract_pdf_url(value) -> str:
    if not isinstance(value, list):
        return ""
    for link in value:
        if not isinstance(link, dict):
            continue
        url = normalize_whitespace(str(link.get("URL", "")))
        content_type = str(link.get("content-type", "")).lower()
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            return url
    return ""


def _fallback_id(title: str, url: str) -> str:
    source = url or title
    return safe_slug(source)[:96]
