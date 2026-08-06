from __future__ import annotations

import ast
from datetime import date, datetime
from html import unescape
import json
from pathlib import Path
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


MIN_SUMMARY_CHARS = 100

CLEAN_COLUMNS: list[str] = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
]

_MARKUP_TAG = re.compile(r"<[^>]+>")
_ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff\u00ad]")
_HYPHEN_VARIANTS = re.compile(r"[\u2010\u2011]")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?])")
_SPLIT_HYPHEN = re.compile(r"(?<=\w)-\s+(?=\w)")
_ABSTRACT_LABEL = re.compile(
    r"^(abstract|summary)\b(\s*[.:;\u2013\u2014-]+\s*|\s+)",
    re.IGNORECASE,
)
_SECTION_LABEL = re.compile(
    r"^(background|introduction|objectives?|purpose|aims?|"
    r"materials and methods|methods?|results?|conclusions?|"
    r"motivation|context|significance)\b(\s*[.:;\u2013\u2014-]+\s*|\s+)",
    re.IGNORECASE,
)
_LABEL_PUNCTUATION = re.compile(r"[.:;\u2013\u2014-]")
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw Crossref records into an embedding-ready dataframe.

    Cleaning rules applied here:
    1. Drop junk records: no title, or a summary shorter than
       ``MIN_SUMMARY_CHARS`` (100) characters. Records without a stable
       ``paper_id`` or a parsable publication date are dropped too, because the
       whole lab keys on document identity and freshness.
    2. Strip XML/HTML tags (``<jats:p>``, ``<b>``, ``<scp>``, ...) and HTML
       entities out of title and summary, and drop the ``Abstract``/
       ``Background.`` section labels Crossref keeps in abstracts.
    3. Normalize ``authors``/``categories`` into deduplicated ``list[str]`` and
       join them with commas into ``authors_joined``/``categories_joined``.
    4. Keep ``published``/``updated`` as ISO ``YYYY-MM-DD`` strings and derive
       ``age_days`` against ``run_date``.
    5. Build ``text_for_embedding`` as
       ``Title: ... | Authors: ... | Summary: ...``.
    6. Deduplicate on ``paper_id`` and on title, then sort newest first so
       downstream steps have a deterministic order.
    """
    run_day = _as_date(run_date)
    rows: list[dict] = []

    for record in records:
        paper_id = normalize_whitespace(str(getattr(record, "paper_id", ""))).lower()
        title = _clean_title(getattr(record, "title", ""))
        summary = _clean_summary(getattr(record, "summary", ""))
        published_day = _parse_date(getattr(record, "published", ""))

        if not paper_id or published_day is None:
            continue
        if not title or len(summary) < MIN_SUMMARY_CHARS:
            continue

        authors = _clean_list(getattr(record, "authors", []))
        categories = _clean_list(getattr(record, "categories", []))
        published = published_day.isoformat()
        updated_day = _parse_date(getattr(record, "updated", ""))

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0] if categories else "",
                "published": published,
                "updated": updated_day.isoformat() if updated_day else published,
                "age_days": _age_days(published_day, run_day),
                "authors_joined": compact_join(authors),
                "categories_joined": compact_join(categories),
                "summary_chars": len(summary),
                "abs_url": _clean_text(getattr(record, "abs_url", "")),
                "pdf_url": _clean_text(getattr(record, "pdf_url", "")),
                "comment": _clean_text(getattr(record, "comment", "")),
                "text_for_embedding": build_embedding_text(
                    title=title,
                    authors_joined=compact_join(authors),
                    summary=summary,
                ),
            }
        )

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if df.empty:
        return df

    df = df.sort_values(["published", "paper_id"], ascending=[False, True])
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.loc[~df["title"].str.lower().duplicated(keep="first")]

    df["age_days"] = df["age_days"].astype(int)
    df["summary_chars"] = df["summary_chars"].astype(int)
    return df.reset_index(drop=True)


def build_embedding_text(title: str, authors_joined: str, summary: str) -> str:
    """Render the single string that gets embedded for one paper."""
    return f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"


def refresh_derived_fields(df: pd.DataFrame, run_date: datetime | None = None) -> pd.DataFrame:
    """Recompute derived columns after a dataframe has been mutated.

    Downstream steps that rewrite ``title``, ``summary``, ``authors`` or
    ``published`` (for example the corruption flow) should call this so
    ``authors_joined``, ``categories_joined``, ``summary_chars``,
    ``text_for_embedding`` and optionally ``age_days`` stay consistent with the
    columns they were derived from.
    """
    updated = df.copy()
    if updated.empty:
        return updated

    updated["authors"] = updated["authors"].apply(_as_list)
    updated["categories"] = updated["categories"].apply(_as_list)
    updated["primary_category"] = updated["categories"].apply(lambda items: items[0] if items else "")
    updated["authors_joined"] = updated["authors"].apply(compact_join)
    updated["categories_joined"] = updated["categories"].apply(compact_join)
    updated["title"] = updated["title"].fillna("").astype(str)
    updated["summary"] = updated["summary"].fillna("").astype(str)
    updated["published"] = updated["published"].fillna("").astype(str)
    updated["summary_chars"] = updated["summary"].str.len().astype(int)

    if run_date is not None:
        run_day = _as_date(run_date)
        updated["age_days"] = updated["published"].apply(
            lambda value: _age_days(_parse_date(value), run_day)
        )

    updated["text_for_embedding"] = [
        build_embedding_text(
            title=row["title"],
            authors_joined=row["authors_joined"],
            summary=row["summary"],
        )
        for _, row in updated.iterrows()
    ]
    return updated


def load_clean_dataframe(path) -> pd.DataFrame:
    """Read a clean CSV/JSON artifact back with the schema intact.

    A bare ``pd.read_csv`` breaks two parts of the contract: empty strings come
    back as ``NaN`` (which then leak into the Chroma metadata built by
    ``retrieval.index``) and the list columns come back as their ``repr``. Any
    step that reloads the clean dataset from disk - the corruption flow in
    particular - should go through this helper.
    """
    source = Path(path)
    if source.suffix.lower() == ".json":
        df = pd.DataFrame(json.loads(source.read_text(encoding="utf-8")))
    else:
        df = pd.read_csv(source, keep_default_na=False, na_values=[])

    if df.empty:
        return df

    for column in ("authors", "categories"):
        if column in df.columns:
            df[column] = df[column].apply(_as_list)
    for column in (
        "paper_id",
        "title",
        "summary",
        "primary_category",
        "published",
        "updated",
        "authors_joined",
        "categories_joined",
        "abs_url",
        "pdf_url",
        "comment",
        "text_for_embedding",
    ):
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    for column in ("age_days", "summary_chars"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    return df


def _clean_text(value) -> str:
    text = unescape(str(value or ""))
    text = _MARKUP_TAG.sub(" ", text)
    text = _ZERO_WIDTH.sub("", text)
    text = _HYPHEN_VARIANTS.sub("-", text)
    text = normalize_whitespace(text)
    text = _SPLIT_HYPHEN.sub("-", text)
    return _SPACE_BEFORE_PUNCT.sub(r"\1", text)


def _clean_title(value) -> str:
    return _clean_text(value)


def _clean_summary(value) -> str:
    text = _clean_text(value)
    text = _strip_leading_label(text, _ABSTRACT_LABEL)
    text = _strip_leading_label(text, _SECTION_LABEL)
    return text.strip()


def _strip_leading_label(text: str, pattern: re.Pattern[str]) -> str:
    """Drop a leading structural label such as ``Abstract`` or ``BACKGROUND``.

    The label is only removed when it really reads as a label: either it is
    followed by punctuation, or the next word starts a fresh sentence with a
    capital letter. That keeps genuine content such as ``Methods for tuning
    retrievers ...`` untouched.
    """
    match = pattern.match(text)
    if not match:
        return text
    remainder = text[match.end() :]
    if not remainder:
        return text
    separator_is_punctuated = bool(_LABEL_PUNCTUATION.search(match.group(2)))
    if separator_is_punctuated or remainder[:1].isupper():
        return remainder
    return text


def _clean_list(value) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in _as_list(value):
        text = _clean_text(item)
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _as_list(value) -> list[str]:
    """Coerce a cell into ``list[str]``, tolerating CSV round-tripped values."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, (list, tuple)):
            return [str(item) for item in parsed]
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_date(value) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = _ISO_DATE.match(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = _parse_date(value)
    if parsed is None:
        raise ValueError(f"Cannot interpret {value!r} as a run date.")
    return parsed


def _age_days(published_day: date | None, run_day: date) -> int:
    if published_day is None:
        return 0
    return max(0, (run_day - published_day).days)
