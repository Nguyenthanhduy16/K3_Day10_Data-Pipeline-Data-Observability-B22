from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import dataframe_records, print_metrics
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Phase 2: corrupt -> evaluate -> repair from raw -> evaluate -> compare.

    Pseudo-code goc cua starter:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    settings = load_settings()
    run_date = now_utc()

    print("=" * 72)
    print("PHASE 2 - CORRUPTION, REPAIR AND COMPARISON")
    print(f"run date    : {run_date.isoformat()}")
    print("=" * 72)

    _require_baseline_artifacts(settings)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = _load_clean_dataframe(settings)
    print(f"[0] Baseline loaded: {len(baseline_df)} rows, {baseline_metrics.get('samples')} test cases")

    _step(1, "Corrupt the clean dataset")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, dataframe_records(corrupted_df))
    corruption_log = read_json(settings.paths.corruption_log)
    _print_corruption_log(corruption_log)

    _step(2, "Rebuild index and evaluate the corrupted corpus")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    _step(3, "Observe the corrupted corpus")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, _freshness_path(settings, "corrupted")
    )

    _step(4, "Repair from the raw Crossref snapshot")
    repaired_df = _repair_from_raw(settings, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, dataframe_records(repaired_df))
    repair_verification = _verify_repair(baseline_df, corrupted_df, repaired_df, corruption_log)
    _print_repair_verification(repair_verification)

    _step(5, "Rebuild index and evaluate the repaired corpus")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    _step(6, "Observe the repaired corpus")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, _freshness_path(settings, "repaired")
    )

    _step(7, "Write the comparison report")
    corruption_log["repair_verification"] = repair_verification
    write_json(settings.paths.corruption_log, corruption_log)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"    report     : {settings.paths.comparison_report}")

    print("-" * 72)
    print_metrics("baseline ", baseline_metrics)
    print_metrics("corrupted", corrupted_bundle.summary)
    print_metrics("repaired ", repaired_bundle.summary)
    _print_deltas(baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary)
    print("Phase 2 finished.")


def _require_baseline_artifacts(settings: Settings) -> None:
    required = {
        "clean dataset": settings.paths.clean_json,
        "evaluation set": settings.paths.eval_testset,
        "baseline metrics": settings.paths.baseline_metrics,
    }
    missing = [
        f"{label} ({path})"
        for label, path in required.items()
        if not path.exists() and not (label == "clean dataset" and settings.paths.clean_csv.exists())
    ]
    if missing:
        raise RuntimeError(
            "Phase 2 needs a successful baseline run first. Missing: "
            + "; ".join(missing)
            + ". Run: uv run python script/run_phase1.py"
        )


def _load_clean_dataframe(settings: Settings) -> pd.DataFrame:
    """Prefer the JSON snapshot because it keeps list columns as lists."""
    if settings.paths.clean_json.exists():
        return pd.DataFrame(read_json(settings.paths.clean_json))
    return pd.read_csv(settings.paths.clean_csv)


def _repair_from_raw(settings: Settings, run_date) -> pd.DataFrame:
    """Rebuild the clean dataset from the raw snapshot instead of patching corrupted rows."""
    records = load_raw_records(settings.paths.raw_records_json)
    if not records:
        raise RuntimeError(
            f"Cannot repair: no raw records at {settings.paths.raw_records_json}. "
            "The raw snapshot is the source of truth for the repair step."
        )
    print(f"    raw records: {len(records)} from {settings.paths.raw_records_json.name}")
    return build_clean_dataframe(records, run_date)


def _verify_repair(
    baseline_df: pd.DataFrame,
    corrupted_df: pd.DataFrame,
    repaired_df: pd.DataFrame,
    corruption_log: dict[str, Any],
) -> dict[str, Any]:
    baseline_ids = set(baseline_df["paper_id"].astype(str))
    corrupted_ids = set(corrupted_df["paper_id"].astype(str))
    repaired_ids = set(repaired_df["paper_id"].astype(str))
    affected_ids = {str(value) for value in corruption_log.get("affected_paper_ids", [])}

    return {
        "baseline_rows": int(len(baseline_df)),
        "corrupted_rows": int(len(corrupted_df)),
        "repaired_rows": int(len(repaired_df)),
        "rows_lost_by_corruption": int(len(baseline_ids - corrupted_ids)),
        "rows_restored_by_repair": int(len((baseline_ids - corrupted_ids) & repaired_ids)),
        "duplicate_rows_in_corrupted": int(len(corrupted_df) - corrupted_df["paper_id"].nunique()),
        "duplicate_rows_in_repaired": int(len(repaired_df) - repaired_df["paper_id"].nunique()),
        "affected_ids_present_after_repair": int(len(affected_ids & repaired_ids)),
        "affected_ids_total": len(affected_ids),
        "matches_baseline_ids": baseline_ids == repaired_ids,
        "missing_after_repair": sorted(baseline_ids - repaired_ids)[:10],
    }


def _freshness_path(settings: Settings, label: str) -> Path:
    base = settings.paths.freshness_report
    return base.with_name(f"{base.stem}_{label}{base.suffix}")


def _print_corruption_log(log: dict[str, Any]) -> None:
    print(f"    rows       : {log.get('input_rows')} -> {log.get('output_rows')}")
    for scenario in log.get("scenarios", []):
        print(f"    - {scenario['name']:<24} rows={scenario['affected_rows']}")
    print(f"    log        : {len(log.get('affected_paper_ids', []))} affected paper_ids")


def _print_repair_verification(verification: dict[str, Any]) -> None:
    print(
        f"    restored   : {verification['rows_restored_by_repair']}/{verification['rows_lost_by_corruption']} "
        f"dropped rows, duplicates {verification['duplicate_rows_in_corrupted']} -> "
        f"{verification['duplicate_rows_in_repaired']}"
    )
    if not verification["matches_baseline_ids"]:
        print(f"    WARNING: repaired paper_id set differs from baseline: {verification['missing_after_repair']}")


def _print_deltas(baseline: dict[str, Any], corrupted: dict[str, Any], repaired: dict[str, Any]) -> None:
    print(f"{'metric':<22}{'baseline':>10}{'corrupted':>11}{'repaired':>10}{'corr delta':>12}{'repair delta':>14}")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        base_value = baseline.get(key)
        corrupted_value = corrupted.get(key)
        repaired_value = repaired.get(key)
        if not all(isinstance(value, (int, float)) for value in (base_value, corrupted_value, repaired_value)):
            continue
        print(
            f"{key:<22}{base_value:>10.3f}{corrupted_value:>11.3f}{repaired_value:>10.3f}"
            f"{corrupted_value - base_value:>+12.3f}{repaired_value - base_value:>+14.3f}"
        )


def _step(number: int, title: str) -> None:
    print(f"[{number}] {title}")
