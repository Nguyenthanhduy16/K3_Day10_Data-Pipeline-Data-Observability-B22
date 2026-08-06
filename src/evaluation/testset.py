from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


MIN_DOCUMENTS = 3
DEFAULT_MAX_PAPERS = 8

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
)

QUESTION_ORDER = ("summary", "authors", "date", "categories")

QUESTION_TEMPLATES = {
    "summary": "What is the main focus of the paper '{title}'?",
    "authors": "Who authored '{title}'?",
    "date": "When was '{title}' published?",
    "categories": "What categories are assigned to '{title}'?",
}

# `retrieval.qa._extract_answer` picks the answer field by scanning the question
# for these phrases, in this order. The test set mirrors that routing table so a
# generated question always resolves to the field its ground truth came from.
ROUTING_PHRASES = (
    ("who authored", "authors"),
    ("list the authors", "authors"),
    ("when was", "date"),
    ("publication date", "date"),
    ("published on", "date"),
    ("what categories", "categories"),
)


def build_test_set(
    df: pd.DataFrame,
    output_path,
    max_papers: int = DEFAULT_MAX_PAPERS,
) -> list[dict[str, Any]]:
    """Build the evaluation set used for baseline, corrupted and repaired runs.

    Each sample carries ``id``, ``question_type``, ``question``,
    ``ground_truth`` and ``ground_truth_doc_ids``. Ground truths are read from
    the exact clean columns that ``retrieval.qa`` answers from, so a correct
    retrieval yields a high token F1 and a wrong retrieval is visibly penalised.

    Selection is deterministic: papers are picked at even strides over the
    newest-first clean dataframe, so re-running against the same corpus
    reproduces the same set and the three pipeline states stay comparable.
    """
    _validate_dataframe(df)

    subjects = _select_subject_papers(df, max_papers)
    samples: list[dict[str, Any]] = []

    for _, row in subjects.iterrows():
        title = normalize_whitespace(str(row["title"]))
        paper_id = str(row["paper_id"])
        for question_type in QUESTION_ORDER:
            ground_truth = _ground_truth(row, question_type)
            if not ground_truth:
                continue
            question = QUESTION_TEMPLATES[question_type].format(title=title)
            _assert_routing(question, question_type)
            samples.append(
                {
                    "id": f"q{len(samples) + 1}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not samples:
        raise ValueError("No evaluation samples could be generated from the clean dataframe.")

    write_json(Path(output_path), samples)
    return samples


def _validate_dataframe(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("Cannot build a test set from an empty clean dataframe.")
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns: {missing}")
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(
            f"Need at least {MIN_DOCUMENTS} clean documents to build a test set, got {len(df)}."
        )


def _select_subject_papers(df: pd.DataFrame, max_papers: int) -> pd.DataFrame:
    usable = df[df.apply(_is_usable_subject, axis=1)]
    if usable.empty:
        raise ValueError("No clean paper is usable as a question subject.")

    limit = max(1, min(int(max_papers), len(usable)))
    return usable.iloc[_even_positions(len(usable), limit)]


def _is_usable_subject(row: pd.Series) -> bool:
    title = normalize_whitespace(str(row.get("title") or ""))
    if not title or "'" in title:
        # A straight apostrophe would break the `'<title>'` lookup in qa.py.
        return False
    lowered = title.lower()
    if any(phrase in lowered for phrase, _ in ROUTING_PHRASES):
        return False
    if not normalize_whitespace(str(row.get("summary") or "")):
        return False
    return bool(normalize_whitespace(str(row.get("paper_id") or "")))


def _even_positions(total: int, count: int) -> list[int]:
    if count >= total:
        return list(range(total))
    if count == 1:
        return [0]
    step = (total - 1) / (count - 1)
    positions = sorted({round(index * step) for index in range(count)})
    return positions


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(str(row.get("summary") or ""))
    if question_type == "authors":
        return normalize_whitespace(str(row.get("authors_joined") or ""))
    if question_type == "date":
        return normalize_whitespace(str(row.get("published") or ""))
    if question_type == "categories":
        return normalize_whitespace(str(row.get("categories_joined") or ""))
    raise ValueError(f"Unsupported question type: {question_type}")


def _routed_question_type(question: str) -> str:
    lowered = question.lower()
    for phrase, routed_type in ROUTING_PHRASES:
        if phrase in lowered:
            return routed_type
    return "summary"


def _assert_routing(question: str, question_type: str) -> None:
    routed = _routed_question_type(question)
    if routed != question_type:
        raise ValueError(
            f"Question for type '{question_type}' would be answered as '{routed}' "
            f"by retrieval.qa: {question!r}"
        )
