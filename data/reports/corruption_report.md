# Corruption Comparison Report

## Metrics: Baseline vs Corrupted vs Repaired
| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| samples | 24 | 24 | 24 |
| retrieval_hit_rate | 1.0000 | 0.7500 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.7088 | 1.0000 |
| judge_accuracy | 1.0000 | 0.6667 | 1.0000 |
| mean_judge_score | 5 | 3.8333 | 5 |

## Data Quality (Corrupted)
- Total rows: 23
- Checks passed: 6/9
- All passed: no
  - [PASS] row_count_positive: {'total_rows': 23}
  - [PASS] required_columns_present: {'missing_columns': []}
  - [PASS] paper_id_not_null: {'null_count': 0}
  - [FAIL] paper_id_unique: {'duplicate_count': 2}
  - [PASS] title_not_mostly_empty: {'empty_ratio': 0.0, 'threshold': 0.2}
  - [PASS] summary_not_mostly_empty: {'empty_ratio': 0.1304, 'threshold': 0.2}
  - [PASS] text_for_embedding_not_mostly_empty: {'empty_ratio': 0.0, 'threshold': 0.2}
  - [FAIL] no_duplicate_rows: {'duplicate_rows': 2}
  - [FAIL] freshness_within_threshold: {'stale_rows': 5, 'threshold_days': 180}

## Data Quality (Repaired)
- Total rows: 24
- Checks passed: 9/9
- All passed: yes
  - [PASS] row_count_positive: {'total_rows': 24}
  - [PASS] required_columns_present: {'missing_columns': []}
  - [PASS] paper_id_not_null: {'null_count': 0}
  - [PASS] paper_id_unique: {'duplicate_count': 0}
  - [PASS] title_not_mostly_empty: {'empty_ratio': 0.0, 'threshold': 0.2}
  - [PASS] summary_not_mostly_empty: {'empty_ratio': 0.0, 'threshold': 0.2}
  - [PASS] text_for_embedding_not_mostly_empty: {'empty_ratio': 0.0, 'threshold': 0.2}
  - [PASS] no_duplicate_rows: {'duplicate_rows': 0}
  - [PASS] freshness_within_threshold: {'stale_rows': 0, 'threshold_days': 180}

## Freshness (Corrupted)
- Latest published: 2026-07-10
- Oldest published: 2023-01-24
- Stale rows: 5/23
- Threshold days: 180
- Is fresh: no

## Freshness (Repaired)
- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0/24
- Threshold days: 180
- Is fresh: yes
