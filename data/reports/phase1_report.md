# Phase 1 Baseline Report

## Source
- run_date: 2026-08-06T05:21:09.104667+00:00
- source_api: Crossref REST API
- source_query: agentic retrieval augmented generation large language model
- source_filter: from-pub-date:2026-02-07,has-abstract:true
- max_results: 24
- raw_records: 24
- clean_rows: 24
- dropped_rows: 0
- clean_columns: ['paper_id', 'title', 'summary', 'authors', 'categories', 'primary_category', 'published', 'updated', 'age_days', 'authors_joined', 'categories_joined', 'summary_chars', 'abs_url', 'pdf_url', 'comment', 'text_for_embedding']
- embedding_model: sentence-transformers/all-MiniLM-L6-v2
- collection_name: papers-baseline
- indexed_documents: 24
- top_k: 4
- test_cases: 24
- llm_provider: openrouter
- llm_model: openai/gpt-4o-mini
- freshness_threshold_days: 180
- artifacts: {'raw_response': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\raw\\crossref_response.json', 'raw_records': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\raw\\crossref_records.json', 'clean_csv': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\clean\\papers_clean.csv', 'clean_json': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\clean\\papers_clean.json', 'embeddings': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\embeddings\\papers_embeddings.json', 'test_set': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\eval\\test_set.json', 'metrics': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\results\\baseline_metrics.json', 'answers': 'D:\\projects\\vinai\\day10\\K3_Day10_Data-Pipeline-Data-Observability-B22\\data\\results\\baseline_answers.json'}

## Evaluation Metrics
| Metric | Value |
| --- | --- |
| samples | 24 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

## Data Quality
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

## Freshness
- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0/24
- Threshold days: 180
- Is fresh: yes
