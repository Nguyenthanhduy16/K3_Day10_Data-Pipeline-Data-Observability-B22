from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


# Cot bat buoc phai co trong clean dataframe (theo contract voi Thanh vien 2).
REQUIRED_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "published",
    "age_days",
    "text_for_embedding",
]

# Ty le rong toi da chap nhan cho cac cot text truoc khi coi la fail.
MAX_EMPTY_RATIO = 0.2


def _empty_ratio(series: pd.Series) -> float:
    """Ty le gia tri null hoac chuoi rong trong mot cot."""
    if len(series) == 0:
        return 0.0
    normalized = series.fillna("").astype(str).str.strip()
    empty = (normalized == "").sum()
    return float(empty) / float(len(series))


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks tren clean dataframe va ghi ket qua ra data/quality/.

    Tra ve dict mo ta tung check (passed + chi tiet) va trang thai tong.
    """
    total_rows = int(len(df))
    checks: list[dict[str, Any]] = []

    # 1. Row count > 0.
    checks.append(
        {
            "name": "row_count_positive",
            "passed": total_rows > 0,
            "details": {"total_rows": total_rows},
        }
    )

    # 2. Cot bat buoc phai ton tai.
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    checks.append(
        {
            "name": "required_columns_present",
            "passed": not missing_columns,
            "details": {"missing_columns": missing_columns},
        }
    )

    # 3. paper_id khong null va unique.
    if "paper_id" in df.columns:
        null_ids = int(df["paper_id"].isna().sum())
        duplicate_ids = int(df["paper_id"].duplicated().sum())
        checks.append(
            {
                "name": "paper_id_not_null",
                "passed": null_ids == 0,
                "details": {"null_count": null_ids},
            }
        )
        checks.append(
            {
                "name": "paper_id_unique",
                "passed": duplicate_ids == 0,
                "details": {"duplicate_count": duplicate_ids},
            }
        )

    # 4. Cac cot text khong rong qua nhieu.
    for column in ["title", "summary", "text_for_embedding"]:
        if column in df.columns:
            ratio = _empty_ratio(df[column])
            checks.append(
                {
                    "name": f"{column}_not_mostly_empty",
                    "passed": ratio <= MAX_EMPTY_RATIO,
                    "details": {"empty_ratio": round(ratio, 4), "threshold": MAX_EMPTY_RATIO},
                }
            )

    # 5. Duplicate rows tren toan dataframe.
    # astype(str) de xu ly cot list (authors/categories) von khong hashable.
    duplicate_rows = int(df.astype(str).duplicated().sum())
    checks.append(
        {
            "name": "no_duplicate_rows",
            "passed": duplicate_rows == 0,
            "details": {"duplicate_rows": duplicate_rows},
        }
    )

    # 6. Freshness signal tu age_days.
    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages > settings.freshness_threshold_days).sum())
        checks.append(
            {
                "name": "freshness_within_threshold",
                "passed": stale_rows == 0,
                "details": {
                    "stale_rows": stale_rows,
                    "threshold_days": settings.freshness_threshold_days,
                },
            }
        )

    passed_checks = sum(1 for check in checks if check["passed"])
    report = {
        "report_name": report_name,
        "total_rows": total_rows,
        "checks_total": len(checks),
        "checks_passed": passed_checks,
        "checks_failed": len(checks) - passed_checks,
        "all_passed": passed_checks == len(checks),
        "checks": checks,
    }

    output_path = settings.paths.quality_dir / f"{safe_slug(report_name)}.json"
    write_json(output_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report tu cot published/age_days va ghi JSON."""
    total_rows = int(len(df))

    latest_published = None
    oldest_published = None
    if "published" in df.columns and total_rows > 0:
        published = df["published"].fillna("").astype(str).str.strip()
        published = published[published != ""]
        if not published.empty:
            latest_published = published.max()
            oldest_published = published.min()

    stale_rows = 0
    if "age_days" in df.columns and total_rows > 0:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages > settings.freshness_threshold_days).sum())

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": total_rows > 0 and stale_rows == 0,
    }

    write_json(report_path, report)
    return report
