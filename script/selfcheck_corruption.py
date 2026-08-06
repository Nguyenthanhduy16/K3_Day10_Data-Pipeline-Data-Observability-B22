"""Offline self-check for the member 4 deliverables.

Runs the corruption scenarios against a synthetic clean dataframe that follows the agreed
team schema, so corruption logic can be verified before the cleaning/observability modules
are finished. It never touches the real artifacts under data/.

Usage:
    uv run python script/selfcheck_corruption.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import json
import tempfile

import pandas as pd

from ingestion.corruption import corrupt_clean_dataframe


ROW_COUNT = 12


def build_fake_clean_dataframe() -> pd.DataFrame:
    today = datetime.now(UTC).date()
    rows = []
    for index in range(ROW_COUNT):
        age_days = index * 7
        published = (today - timedelta(days=age_days)).isoformat()
        title = f"Paper {index:02d} on agentic retrieval augmented generation"
        summary = (
            f"This study {index:02d} evaluates retrieval augmented generation pipelines "
            "and reports measurable gains on scholarly question answering."
        )
        authors = [f"Author {index:02d}A", f"Author {index:02d}B"]
        categories = ["Artificial Intelligence", "Information Retrieval"]
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        rows.append(
            {
                "paper_id": f"10.1234/fake.{index:04d}",
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0],
                "published": published,
                "updated": published,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "abs_url": f"https://doi.org/10.1234/fake.{index:04d}",
                "pdf_url": "",
                "text_for_embedding": (
                    f"{title} {summary} Authors: {authors_joined} "
                    f"Categories: {categories_joined} Published: {published}"
                ),
            }
        )
    return pd.DataFrame(rows)


def check(condition: bool, label: str) -> bool:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
    return condition


def main() -> None:
    baseline = build_fake_clean_dataframe()
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "corruption_log.json"
        corrupted = corrupt_clean_dataframe(baseline, log_path)
        log = json.loads(log_path.read_text(encoding="utf-8"))
        rerun = corrupt_clean_dataframe(baseline, Path(tmp) / "corruption_log_rerun.json")

    scenarios = {item["name"]: item for item in log["scenarios"]}
    baseline_ids = set(baseline["paper_id"])
    corrupted_ids = set(corrupted["paper_id"])

    print("corruption self-check")
    results = [
        check(log_path.name == "corruption_log.json" and bool(log), "corruption log written"),
        check(len(scenarios) == 6, f"6 scenarios logged (got {len(scenarios)})"),
        check(
            all(scenario["affected_rows"] >= 1 for scenario in scenarios.values()),
            "every scenario touched at least one row",
        ),
        check(
            len(baseline_ids - corrupted_ids) == scenarios["drop_latest_records"]["affected_rows"],
            "latest records dropped as logged",
        ),
        check(
            (corrupted["summary"].astype(str).str.strip() == "").sum()
            >= scenarios["blank_summary"]["affected_rows"],
            "blank summaries present",
        ),
        check(
            corrupted["text_for_embedding"].astype(str).str.contains("RAW-SCRAPE-ARTIFACT").sum()
            >= scenarios["noisy_summary"]["affected_rows"],
            "noise reached text_for_embedding",
        ),
        check(
            (corrupted["title"].astype(str).str.len() <= 12).sum()
            >= scenarios["truncated_title"]["affected_rows"],
            "titles truncated",
        ),
        check(int(corrupted["age_days"].max()) > 1000, "stale rows push age_days past the threshold"),
        check(
            len(corrupted) - corrupted["paper_id"].nunique()
            == scenarios["duplicate_rows"]["affected_rows"],
            "duplicate rows added",
        ),
        check(
            all(str(value).strip() != "" for value in baseline["text_for_embedding"]),
            "baseline fixture itself is valid",
        ),
        check(rerun.equals(corrupted), "corruption is deterministic across reruns"),
        check(
            len(baseline) == ROW_COUNT and baseline["summary_chars"].min() > 0,
            "input dataframe was not mutated in place",
        ),
    ]

    print(f"\nrows {log['input_rows']} -> {log['output_rows']}, affected ids: {len(log['affected_paper_ids'])}")
    for name, scenario in scenarios.items():
        print(f"  {name:<24} rows={scenario['affected_rows']}")

    if all(results):
        print("\nAll member 4 corruption checks passed.")
    else:
        raise SystemExit("Some member 4 corruption checks failed.")


if __name__ == "__main__":
    main()
