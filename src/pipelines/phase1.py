from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


# Columns the downstream index/agent really read. Keep in sync with the team data contract.
REQUIRED_CLEAN_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "published",
    "age_days",
    "text_for_embedding",
    "authors_joined",
    "categories_joined",
    "abs_url",
    "pdf_url",
)
REQUIRED_TESTSET_KEYS = ("id", "question", "ground_truth", "ground_truth_doc_ids", "question_type")
DEMO_QUESTION_COUNT = 2


def main() -> None:
    """Baseline pipeline: raw -> clean -> index -> evaluate -> observe -> report.

    Pseudo-code goc cua starter:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    settings = load_settings()
    run_date = now_utc()

    print("=" * 72)
    print("PHASE 1 - BASELINE PIPELINE")
    print(f"source      : {settings.source_api}")
    print(f"query       : {settings.source_query}")
    print(f"filter      : {settings.source_filter}")
    print(f"llm         : {settings.llm_provider} / {settings.model_name}")
    print(f"run date    : {run_date.isoformat()}")
    print("=" * 72)

    _step(1, "Load raw records")
    records = _load_or_fetch_raw_records(settings)
    print(f"    raw records: {len(records)}")

    _step(2, "Clean records")
    df = build_clean_dataframe(records, run_date)
    _validate_clean_dataframe(df)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, dataframe_records(df))
    print(f"    clean rows : {len(df)} -> {settings.paths.clean_csv.name}, {settings.paths.clean_json.name}")

    _step(3, "Build embedding index")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"    collection : {index.collection_name} ({len(index.documents)} documents)")

    _step(4, "Load or build evaluation set")
    test_set = _load_or_build_test_set(settings, df)
    print(f"    test cases : {len(test_set)}")

    _step(5, "Evaluate baseline")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"    metrics    : {settings.paths.baseline_metrics.name}, {settings.paths.baseline_answers.name}")

    _step(6, "Run data quality checks")
    quality = run_data_quality_checks(df, settings, "baseline")

    _step(7, "Build freshness report")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    _step(8, "Write markdown report")
    source_summary = build_source_summary(settings, records, df, index, len(test_set), run_date)
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"    report     : {settings.paths.baseline_report}")

    _step(9, "Agent demo (optional)")
    _run_agent_demo(settings, index, test_set)

    print("-" * 72)
    print_metrics("baseline", bundle.summary)
    print("Phase 1 finished. Next: uv run python script/run_corruption_flow.py")


def _load_or_fetch_raw_records(settings: Settings) -> list[PaperRecord]:
    snapshot = settings.paths.raw_records_json
    if settings.refresh_source or not snapshot.exists():
        reason = "REFRESH_SOURCE=1" if settings.refresh_source else "no raw snapshot found"
        print(f"    fetching from Crossref ({reason})")
        records = fetch_source_records(settings)
    else:
        print(f"    reusing snapshot {snapshot}")
        records = load_raw_records(snapshot)

    if not records:
        raise RuntimeError(
            f"No raw records available at {snapshot}. Run with REFRESH_SOURCE=1 to fetch from Crossref."
        )
    return records


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise RuntimeError("build_clean_dataframe() returned an empty dataframe.")

    missing = [column for column in REQUIRED_CLEAN_COLUMNS if column not in df.columns]
    if missing:
        raise RuntimeError(
            f"Clean dataframe is missing columns {missing}. "
            f"The index and agent need: {list(REQUIRED_CLEAN_COLUMNS)}."
        )
    if not df["paper_id"].is_unique:
        duplicates = df["paper_id"][df["paper_id"].duplicated()].tolist()
        raise RuntimeError(f"paper_id must be unique in the clean dataset. Duplicates: {duplicates[:5]}")

    empty_text = int((df["text_for_embedding"].astype(str).str.strip() == "").sum())
    if empty_text:
        print(f"    WARNING: {empty_text} rows have an empty text_for_embedding")


def _load_or_build_test_set(settings: Settings, df: pd.DataFrame) -> list[dict[str, Any]]:
    path = settings.paths.eval_testset
    if settings.refresh_test_set or not path.exists():
        reason = "REFRESH_TEST_SET=1" if settings.refresh_test_set else "no test set found"
        print(f"    building evaluation set ({reason})")
        test_set = build_test_set(df, path)
        if not path.exists():
            write_json(path, test_set)
    else:
        print(f"    reusing evaluation set {path}")
        test_set = read_json(path)

    _validate_test_set(test_set, df)
    return test_set


def _validate_test_set(test_set: Any, df: pd.DataFrame) -> None:
    if not isinstance(test_set, list) or not test_set:
        raise RuntimeError("The evaluation set must be a non-empty list of test cases.")

    known_ids = set(df["paper_id"].astype(str))
    unknown: set[str] = set()
    for item in test_set:
        missing = [key for key in REQUIRED_TESTSET_KEYS if key not in item]
        if missing:
            raise RuntimeError(f"Test case {item.get('id', '?')} is missing keys {missing}.")
        unknown.update(str(doc_id) for doc_id in item["ground_truth_doc_ids"] if str(doc_id) not in known_ids)

    if unknown:
        print(
            f"    WARNING: {len(unknown)} ground_truth_doc_ids are not in the clean dataset "
            f"(example: {sorted(unknown)[0]}). Retrieval hit rate will be capped."
        )


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> None:
    try:
        require_llm_credentials(settings)
    except RuntimeError as exc:
        print(f"    skipped: {exc}")
        return

    try:
        agent = build_agent(settings=settings, index=index)
        demo: list[dict[str, Any]] = []
        for item in test_set[:DEMO_QUESTION_COUNT]:
            answer = run_agent_question(agent, item["question"])
            demo.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "ground_truth": item["ground_truth"],
                    "agent_answer": answer,
                }
            )
        write_json(settings.paths.demo_answers, demo)
        print(f"    demo answers: {settings.paths.demo_answers.name} ({len(demo)} questions)")
    except Exception as exc:  # the demo is evidence, not a pipeline dependency
        print(f"    skipped: agent demo failed ({type(exc).__name__}: {exc})")


def build_source_summary(
    settings: Settings,
    records: list[PaperRecord],
    df: pd.DataFrame,
    index: LocalEmbeddingIndex,
    test_case_count: int,
    run_date,
) -> dict[str, Any]:
    """Context block handed to the markdown report (owned by member 3)."""
    return {
        "run_date": run_date.isoformat(),
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": len(records),
        "clean_rows": int(len(df)),
        "dropped_rows": len(records) - int(len(df)),
        "clean_columns": list(df.columns),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "indexed_documents": len(index.documents),
        "top_k": settings.top_k,
        "test_cases": test_case_count,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "artifacts": {
            "raw_response": str(settings.paths.raw_api_response),
            "raw_records": str(settings.paths.raw_records_json),
            "clean_csv": str(settings.paths.clean_csv),
            "clean_json": str(settings.paths.clean_json),
            "embeddings": str(settings.paths.embeddings_json),
            "test_set": str(settings.paths.eval_testset),
            "metrics": str(settings.paths.baseline_metrics),
            "answers": str(settings.paths.baseline_answers),
        },
    }


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """JSON-safe row dicts (handles NaN and timestamp columns)."""
    return json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))


def print_metrics(label: str, metrics: dict[str, Any]) -> None:
    keys = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    parts = []
    for key in keys:
        value = metrics.get(key)
        parts.append(f"{key}={value:.3f}" if isinstance(value, float) else f"{key}={value}")
    print(f"[{label}] " + "  ".join(parts))


def _step(number: int, title: str) -> None:
    print(f"[{number}] {title}")
