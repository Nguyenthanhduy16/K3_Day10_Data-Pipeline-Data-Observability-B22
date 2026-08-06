from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, now_utc, write_json


CORRUPTION_SEED = 20251010

# Scenario volumes scale with the corpus size so the flow behaves the same on a 12-row
# smoke fixture and on the real ~24-row Crossref pull. Together the in-place scenarios
# touch about 65% of the surviving rows, which leaves clean rows to compare against.
DROP_LATEST_FRACTION = 0.12
BLANK_SUMMARY_FRACTION = 0.15
NOISE_SUMMARY_FRACTION = 0.15
TRUNCATE_TITLE_FRACTION = 0.15
STALE_DATE_FRACTION = 0.20
DUPLICATE_FRACTION = 0.10
MAX_DROP_LATEST = 3

TRUNCATE_TITLE_CHARS = 12
STALE_SHIFT_DAYS = 1200

NOISE_BLOCK = (
    "%%% RAW-SCRAPE-ARTIFACT %%% ]]> lorem ipsum dolor sit amet 0x3f2a1b "
    "&amp;nbsp; <p>&lt;div&gt;</p> ZZZZ QQQQ XXXX 99999 ##### undefined null NaN "
    "aGVsbG8gd29ybGQgbm9pc2UgcGF5bG9hZA== %%% END-ARTIFACT %%%"
)

REQUIRED_COLUMNS = ("paper_id", "title", "summary", "published", "text_for_embedding")


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate realistic data-quality incidents on top of a clean dataframe.

    Scenarios applied (deterministic for a fixed input order thanks to ``CORRUPTION_SEED``):

    1. Drop the most recent records (failed incremental load).
    2. Blank out summaries (upstream field went missing).
    3. Inject scraper/OCR noise into summaries.
    4. Truncate titles (column width / bad export).
    5. Push publication dates into the past (stale partition replayed).
    6. Duplicate rows (pipeline retried without idempotency).

    ``text_for_embedding`` is patched in place so the corrupted content really reaches the
    vector index, and every affected ``paper_id`` is written to ``output_log_path`` so the
    repair step can be verified instead of trusted.

    Pseudo-code goc cua starter:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    if df is None or len(df) == 0:
        raise ValueError("corrupt_clean_dataframe() needs a non-empty clean dataframe.")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Clean dataframe is missing required columns {missing}. "
            "Expected the agreed clean schema (paper_id, title, summary, published, text_for_embedding)."
        )

    rng = random.Random(CORRUPTION_SEED)
    working = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(working)
    scenarios: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    working, event = _drop_latest_records(working)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working, event = _blank_summaries(working, rng, used_ids)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working, event = _inject_summary_noise(working, rng, used_ids)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working, event = _truncate_titles(working, rng, used_ids)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working, event = _make_dates_stale(working, rng, used_ids)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working, event = _add_duplicate_rows(working, rng)
    scenarios.append(event)
    used_ids.update(event["paper_ids"])

    working = working.reset_index(drop=True)

    log = {
        "generated_at": now_utc().isoformat(),
        "seed": CORRUPTION_SEED,
        "input_rows": input_rows,
        "output_rows": int(len(working)),
        "removed_rows": input_rows - int(working["paper_id"].nunique()),
        "affected_paper_ids": sorted(used_ids),
        "scenarios": scenarios,
        "expected_signals": [
            "row count drops below the baseline",
            "paper_id is no longer unique because of duplicated rows",
            "empty/short summaries appear in the corpus",
            "age_days grows past the freshness threshold",
            "retrieval and answer metrics degrade on the same test set",
        ],
    }
    write_json(Path(output_log_path), log)
    return working


def _drop_latest_records(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    count = min(MAX_DROP_LATEST, _scaled_count(len(df), DROP_LATEST_FRACTION))
    ordered = df.assign(_published_dt=df["published"].map(_parse_date))
    ordered = ordered.sort_values(by="_published_dt", ascending=False, na_position="last")
    dropped_ids = [str(value) for value in ordered.head(count)["paper_id"].tolist()]
    remaining = df[~df["paper_id"].astype(str).isin(dropped_ids)].copy()
    event = {
        "name": "drop_latest_records",
        "description": "Removed the most recently published papers to simulate a failed incremental load.",
        "affected_rows": len(dropped_ids),
        "paper_ids": dropped_ids,
        "details": {"strategy": "sort by published desc", "count": count},
    }
    return remaining.reset_index(drop=True), event


def _blank_summaries(df: pd.DataFrame, rng: random.Random, used_ids: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    positions = _pick_positions(df, rng, used_ids, _scaled_count(len(df), BLANK_SUMMARY_FRACTION))
    for position in positions:
        _set_field(df, position, "summary", "")
    event = {
        "name": "blank_summary",
        "description": "Blanked the summary field so those documents lose their embedding content.",
        "affected_rows": len(positions),
        "paper_ids": _paper_ids_at(df, positions),
        "details": {"new_value": ""},
    }
    return df, event


def _inject_summary_noise(df: pd.DataFrame, rng: random.Random, used_ids: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    positions = _pick_positions(df, rng, used_ids, _scaled_count(len(df), NOISE_SUMMARY_FRACTION))
    for position in positions:
        original = str(df.at[position, "summary"] or "")
        _set_field(df, position, "summary", normalize_whitespace(f"{NOISE_BLOCK} {original} {NOISE_BLOCK}"))
    event = {
        "name": "noisy_summary",
        "description": "Wrapped summaries in scraper/OCR junk so the embedded text stops matching the question wording.",
        "affected_rows": len(positions),
        "paper_ids": _paper_ids_at(df, positions),
        "details": {"noise_chars": len(NOISE_BLOCK) * 2},
    }
    return df, event


def _truncate_titles(df: pd.DataFrame, rng: random.Random, used_ids: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    positions = _pick_positions(df, rng, used_ids, _scaled_count(len(df), TRUNCATE_TITLE_FRACTION))
    for position in positions:
        original = str(df.at[position, "title"] or "")
        _set_field(df, position, "title", original[:TRUNCATE_TITLE_CHARS].strip())
    event = {
        "name": "truncated_title",
        "description": "Truncated titles so exact-title lookup in the agent no longer resolves the document.",
        "affected_rows": len(positions),
        "paper_ids": _paper_ids_at(df, positions),
        "details": {"kept_chars": TRUNCATE_TITLE_CHARS},
    }
    return df, event


def _make_dates_stale(df: pd.DataFrame, rng: random.Random, used_ids: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    positions = _pick_positions(df, rng, used_ids, _scaled_count(len(df), STALE_DATE_FRACTION))
    for position in positions:
        original = _parse_date(df.at[position, "published"])
        if original is None:
            stale_value = ""
        else:
            stale_value = (original - timedelta(days=STALE_SHIFT_DAYS)).date().isoformat()
        _set_field(df, position, "published", stale_value)
        if "age_days" in df.columns:
            current_age = pd.to_numeric(df.at[position, "age_days"], errors="coerce")
            base_age = 0 if pd.isna(current_age) else int(current_age)
            df.at[position, "age_days"] = base_age + STALE_SHIFT_DAYS
    event = {
        "name": "stale_published_date",
        "description": "Pushed publication dates far into the past so the freshness monitor must flag the corpus.",
        "affected_rows": len(positions),
        "paper_ids": _paper_ids_at(df, positions),
        "details": {"shift_days": STALE_SHIFT_DAYS},
    }
    return df, event


def _add_duplicate_rows(df: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df.empty:
        return df, {
            "name": "duplicate_rows",
            "description": "Skipped because the dataframe is empty.",
            "affected_rows": 0,
            "paper_ids": [],
            "details": {},
        }

    count = min(_scaled_count(len(df), DUPLICATE_FRACTION), len(df))
    positions = sorted(rng.sample(range(len(df)), count))
    duplicated_ids = _paper_ids_at(df, positions)
    duplicated = df.iloc[positions].copy()
    combined = pd.concat([df, duplicated], ignore_index=True)
    event = {
        "name": "duplicate_rows",
        "description": "Appended duplicate rows to simulate a non-idempotent pipeline retry.",
        "affected_rows": len(positions),
        "paper_ids": duplicated_ids,
        "details": {"duplicated_copies": 1},
    }
    return combined, event


def _set_field(df: pd.DataFrame, position: int, column: str, new_value: str) -> None:
    """Write a corrupted value and keep the derived columns in sync.

    ``text_for_embedding`` is patched by replacing the old field value inside the existing
    string. That keeps whatever layout the cleaning step chose instead of re-inventing it here.
    """
    old_value = str(df.at[position, column] or "")
    df.at[position, column] = new_value

    if column == "summary" and "summary_chars" in df.columns:
        df.at[position, "summary_chars"] = len(new_value)

    text = str(df.at[position, "text_for_embedding"] or "")
    if old_value and old_value in text:
        df.at[position, "text_for_embedding"] = normalize_whitespace(text.replace(old_value, new_value))
    else:
        df.at[position, "text_for_embedding"] = _compose_embedding_text(df.loc[position])


def _compose_embedding_text(row: pd.Series) -> str:
    """Fallback embedding text used only when the original value cannot be patched in place."""
    authors = row.get("authors_joined") or _join_list(row.get("authors"))
    categories = row.get("categories_joined") or _join_list(row.get("categories"))
    parts = [
        str(row.get("title") or ""),
        str(row.get("summary") or ""),
        f"Authors: {authors}" if authors else "",
        f"Categories: {categories}" if categories else "",
        f"Published: {row.get('published') or ''}",
    ]
    return normalize_whitespace(compact_join(parts, sep=" "))


def _join_list(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if str(item).strip())
    return str(value or "")


def _scaled_count(rows: int, fraction: float) -> int:
    """At least one row, otherwise a fraction of the corpus so small corpora stay usable."""
    return max(1, round(rows * fraction))


def _pick_positions(df: pd.DataFrame, rng: random.Random, used_ids: set[str], count: int) -> list[int]:
    """Pick row positions that no earlier scenario already touched, so the log stays attributable."""
    candidates = [
        position
        for position in range(len(df))
        if str(df.at[position, "paper_id"]) not in used_ids
    ]
    if not candidates:
        return []
    return sorted(rng.sample(candidates, min(count, len(candidates))))


def _paper_ids_at(df: pd.DataFrame, positions: list[int]) -> list[str]:
    return [str(df.at[position, "paper_id"]) for position in positions]


def _parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime().replace(tzinfo=None)
