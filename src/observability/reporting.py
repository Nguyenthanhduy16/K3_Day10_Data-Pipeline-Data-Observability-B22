from __future__ import annotations

from typing import Any

from core.utils import write_text


# Cac metric trong tam hien thi trong moi report (khop voi evaluation/metrics.py).
METRIC_KEYS = [
    "samples",
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
]


def _fmt(value: Any) -> str:
    """Format gia tri metric gon gang cho markdown."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metrics_rows(metrics: dict[str, Any]) -> str:
    """Render metrics thanh cac dong bang markdown."""
    lines = []
    for key in METRIC_KEYS:
        if key in metrics:
            lines.append(f"| {key} | {_fmt(metrics[key])} |")
    return "\n".join(lines)


def _quality_lines(quality: dict[str, Any]) -> str:
    """Render tom tat quality checks."""
    lines = [
        f"- Total rows: {quality.get('total_rows', 'N/A')}",
        f"- Checks passed: {quality.get('checks_passed', 'N/A')}/{quality.get('checks_total', 'N/A')}",
        f"- All passed: {_fmt(quality.get('all_passed'))}",
    ]
    for check in quality.get("checks", []):
        status = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"  - [{status}] {check.get('name')}: {check.get('details')}")
    return "\n".join(lines)


def _freshness_lines(freshness: dict[str, Any]) -> str:
    """Render tom tat freshness report."""
    return "\n".join(
        [
            f"- Latest published: {freshness.get('latest_published', 'N/A')}",
            f"- Oldest published: {freshness.get('oldest_published', 'N/A')}",
            f"- Stale rows: {freshness.get('stale_rows', 'N/A')}/{freshness.get('total_rows', 'N/A')}",
            f"- Threshold days: {freshness.get('threshold_days', 'N/A')}",
            f"- Is fresh: {_fmt(freshness.get('is_fresh'))}",
        ]
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    sections = ["# Phase 1 Baseline Report", ""]

    # 1. Source summary.
    sections.append("## Source")
    if source_summary:
        for key, value in source_summary.items():
            sections.append(f"- {key}: {_fmt(value)}")
    else:
        sections.append("- No source summary provided.")
    sections.append("")

    # 2. Metrics retrieval/evaluation.
    sections.append("## Evaluation Metrics")
    sections.append("| Metric | Value |")
    sections.append("| --- | --- |")
    sections.append(_metrics_rows(metrics))
    sections.append("")

    # 3. Data quality.
    sections.append("## Data Quality")
    sections.append(_quality_lines(quality))
    sections.append("")

    # 4. Freshness.
    sections.append("## Freshness")
    sections.append(_freshness_lines(freshness))
    sections.append("")

    write_text(report_path, "\n".join(sections))


def _comparison_metrics_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
) -> list[str]:
    """Bang so sanh metrics giua ba trang thai."""
    lines = [
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
    ]
    for key in METRIC_KEYS:
        lines.append(
            f"| {key} | {_fmt(baseline_metrics.get(key))} "
            f"| {_fmt(corrupted_metrics.get(key))} "
            f"| {_fmt(repaired_metrics.get(key))} |"
        )
    return lines


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    sections = ["# Corruption Comparison Report", ""]

    # 1. Bang so sanh metrics ba trang thai.
    sections.append("## Metrics: Baseline vs Corrupted vs Repaired")
    sections.extend(
        _comparison_metrics_table(baseline_metrics, corrupted_metrics, repaired_metrics)
    )
    sections.append("")

    # 2. Quality corrupted vs repaired.
    sections.append("## Data Quality (Corrupted)")
    sections.append(_quality_lines(corrupted_quality))
    sections.append("")
    sections.append("## Data Quality (Repaired)")
    sections.append(_quality_lines(repaired_quality))
    sections.append("")

    # 3. Freshness corrupted vs repaired.
    sections.append("## Freshness (Corrupted)")
    sections.append(_freshness_lines(corrupted_freshness))
    sections.append("")
    sections.append("## Freshness (Repaired)")
    sections.append(_freshness_lines(repaired_freshness))
    sections.append("")

    write_text(report_path, "\n".join(sections))
