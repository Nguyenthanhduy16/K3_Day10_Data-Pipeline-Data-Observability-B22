# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | Nhóm 4 (B22)              |
| Repository         | https://github.com/Nguyenthanhduy16/K3_Day10_Data-Pipeline-Data-Observability-B22 |
| Ngày hoàn thành | 2026-08-06                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Thành Duy | 2A202601599 | Source Owner | `src/ingestion/crossref.py` |
| 2 | Thạch Minh Quân | 2A202601585 | Data Model & Evaluation-Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Phạm Đức Mạnh | 2A202601075 | Observability & Reporting Owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Nguyễn Minh Phúc | 01161 | Corruption & Integration Owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ pipeline end-to-end cho hệ thống RAG trên dữ liệu bài báo Crossref, qua cả hai pha. Pha 1 (baseline) lấy 24 record từ Crossref, làm sạch thành 24 dòng clean, nhúng bằng all-MiniLM-L6-v2 vào ChromaDB, xây evaluation set 24 câu hỏi và đánh giá; sinh đầy đủ artifact raw/clean/embeddings/eval/metrics/quality/report. Pha 2 tạo dữ liệu lỗi có chủ đích, đánh giá lại, repair từ raw snapshot rồi so sánh ba trạng thái trên cùng test set.

Corruption tác động rõ nhất là nhóm làm hỏng summary (blank + noisy) và drop_latest, vì `text_for_embedding` phụ thuộc chủ yếu vào summary; kèm theo stale date đẩy dữ liệu quá ngưỡng freshness và duplicate rows. Kết quả: quality checks giảm từ 9/9 xuống 6/9, freshness chuyển từ fresh sang stale (5 dòng), và cả bốn agent metric giảm — retrieval_hit_rate 1.000→0.750, mean_token_f1 1.000→0.709, judge_accuracy 1.000→0.667, mean_judge_score 5.000→3.833.

Repair rebuild dữ liệu từ raw snapshot (không vá tay), khôi phục quality về 9/9, freshness về fresh, và cả bốn metric trở về đúng mức baseline (delta +0.000). Giới hạn còn lại: baseline metrics bão hòa ở 1.000 do evaluation set lấy ground_truth từ abstract nên retrieval trả về đúng đoạn đó; giá trị phân tích nằm ở delta giữa các trạng thái, không phải con số tuyệt đối.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API | Fetch, retry (429/5xx), parse payload thành `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Nguyễn Thành Duy |
| Cleaning          | 24 raw records | Normalize field, tạo `text_for_embedding`, `age_days`, dedupe theo `paper_id` | `data/clean/papers_clean.{csv,json}` | Thạch Minh Quân |
| Embedding/index   | Clean dataframe | all-MiniLM-L6-v2 → ChromaDB collection | `data/embeddings/papers_embeddings.json` | (starter) + TV4 tích hợp |
| Evaluation        | Clean dataset | Test set 24 câu, token_f1 + retrieval hit + LLM judge | `data/eval/test_set.json`, `data/results/baseline_metrics.json` | Thạch Minh Quân + TV4 |
| Observability     | Clean/corrupted/repaired df | 9 quality checks + freshness theo `age_days` | `data/quality/*.json`, `data/reports/*.md` | Phạm Đức Mạnh |
| Corruption/repair | Clean df, raw snapshot | 6 corruption scenario + repair từ raw | `data/results/corruption_log.json`, corrupted/repaired artifacts | Nguyễn Minh Phúc |
| Orchestration     | Tất cả module trên | Ghép flow phase1 + corruption_flow | `phase1_report.md`, `corruption_report.md`, metrics | Nguyễn Minh Phúc |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | openrouter          |
| `LLM_MODEL`                | openai/gpt-4o-mini  |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval `top_k`          | 4                   |
| Freshness threshold          | 180 ngày           |
| Random seed                  | Không dùng seed cố định (Crossref là nguồn sống) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ------------ | ----------------------------- | ------------ |
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API                     |
| Query/filter                | query="agentic retrieval augmented generation large language model"; filter=`from-pub-date:<180 ngày>,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 (snapshot lưu tại `data/raw/`) |
| Số record nhận được    | 24                                    |
| Cơ chế retry/backoff      | Retry cho `429`, `500`, `502`, `503`, `504` |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str | Có | Document ID ổn định (ưu tiên DOI) | Fallback ID từ title/source nếu thiếu DOI |
| `title` | str | Có | Tiêu đề bài báo | Loại record nếu rỗng |
| `summary` | str | Có | Abstract dùng cho embedding | Chuẩn hóa, strip HTML |
| `authors` | list[str] | Không | Danh sách tác giả | List rỗng nếu thiếu |
| `categories` | list[str] | Không | Chủ đề | List rỗng nếu thiếu |
| `published` | str (date) | Có | Ngày xuất bản | Dùng để tính `age_days` |
| `age_days` | int | Có | Tuổi bài báo (ngày) | Tính từ `published` và run_date |
| `text_for_embedding` | str | Có | Text nhúng vào ChromaDB | Ghép title + summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record thiếu title/summary | Completeness | 0 (24→24) | `data/quality/baseline.json` |
| Deduplicate theo `paper_id` | Uniqueness | 0 duplicate còn lại | `paper_id` unique = true |
| Chuẩn hóa text, tạo `text_for_embedding` | Validity | 24 | Cột không rỗng |

`text_for_embedding` ghép title + summary đã chuẩn hóa; document ID là `paper_id` (ưu tiên DOI, giữ ổn định raw→clean→index→eval); `age_days` = số ngày giữa `published` và run_date.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24 (từ 8 paper)              |
| Các `question_type`                    | Theo `test_set.json` (factual về nội dung paper) |
| Ground-truth document ID                 | `ground_truth_doc_ids` = `paper_id` của paper nguồn |
| Embedding model                          | all-MiniLM-L6-v2              |
| Vector store/collection                  | ChromaDB, collection `papers-baseline` |
| Retrieval `top_k`                       | 4                             |
| LLM provider/model                       | openrouter / openai/gpt-4o-mini |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (24/24 ground_truth_doc_ids tồn tại trong clean data) |

Test set được giữ nguyên khi đánh giá baseline, corrupted và repaired để phép so sánh có nghĩa: nếu đổi câu hỏi giữa các trạng thái thì không tách bạch được thay đổi metric là do corruption hay do câu hỏi khác. Giữ cố định test set cô lập biến độc lập là chất lượng dữ liệu.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng × 16 cột |
| Embedding manifest/index | `data/embeddings/`                   | Có | collection papers-baseline |
| Evaluation set           | `data/eval/`                         | Có | 24 câu hỏi |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness        | `data/quality/`                      | Có | baseline 9/9 pass |
| Baseline report          | `data/reports/phase1_report.md`      | Có | |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.000 | Mọi câu hỏi retrieve đúng paper nguồn |
| `mean_token_f1`      | 1.000 | Answer trùng khít ground_truth (abstract) |
| `judge_accuracy`     | 1.000 | LLM judge (gpt-4o-mini) đánh giá correct |
| `mean_judge_score`   | 5.000 | Điểm judge tối đa |
| Ragas                | N/A | Không chạy (đặt `RUN_RAGAS=1` để bật) |

Lưu ý: baseline 1.000 tuyệt đối phản ánh đặc tính của evaluation set (ground_truth = abstract, retrieval trả đúng đoạn đó), không phải agent hoàn hảo. Xác minh: `baseline_answers.json` cho thấy 24/24 answer trùng ground_truth.

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| row_count_positive | Completeness | > 0 | PASS (24) | `data/quality/baseline.json` |
| required_columns_present | Validity | đủ cột schema | PASS | `baseline.json` |
| paper_id_not_null | Completeness | 0 null | PASS | `baseline.json` |
| paper_id_unique | Uniqueness | 0 duplicate | PASS | `baseline.json` |
| title/summary/text không rỗng | Completeness | empty_ratio ≤ 0.2 | PASS | `baseline.json` |
| no_duplicate_rows | Uniqueness | 0 duplicate row | PASS | `baseline.json` |
| freshness_within_threshold | Timeliness | 0 stale | PASS | `baseline.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (`age_days`)          |
| Timestamp mới nhất       | 2026-08-01                          |
| Ngưỡng freshness         | 180 ngày                           |
| Trạng thái baseline      | Fresh                               |
| Lý do                     | 0/24 dòng vượt ngưỡng 180 ngày (`is_fresh=true`) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | Xóa 3 paper mới nhất | 3 | Row count giảm | 24→23 dòng | Rebuild từ raw |
| blank_summary | Xóa nội dung summary | 3 | Empty ratio tăng | text_for_embedding yếu | Rebuild từ raw |
| noisy_summary | Chèn nhiễu vào summary | 3 | Validity giảm | Retrieval lệch | Rebuild từ raw |
| truncated_title | Cắt ngắn title | 3 | Validity giảm | Context yếu | Rebuild từ raw |
| stale_published_date | Đẩy date về quá khứ | 4 | Freshness fail | 5 stale rows, is_fresh=false | Rebuild từ raw |
| duplicate_rows | Nhân bản dòng | 2 | Uniqueness fail | 2 duplicate | Rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 scenario, 17 affected paper_ids, và `repair_verification` xác nhận 3/3 dòng mất được khôi phục, duplicate 2→0, `matches_baseline_ids=true`.

Repair rebuild lại toàn bộ clean dataset từ raw snapshot (`load_raw_records` → `build_clean_dataframe`) thay vì vá tay dữ liệu hỏng. Cách này đảm bảo phục hồi từ nguồn đáng tin cậy: `repair_verification` cho `matches_baseline_ids=true` chứng minh tập paper_id repaired trùng khớp baseline, không phải chỉ che kết quả lỗi.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.000 | 0.750 | 1.000 | −0.250 | +0.250 (đầy đủ) | Mất/nhiễu doc làm retrieval trượt |
| `mean_token_f1`        | 1.000 | 0.709 | 1.000 | −0.291 | +0.291 (đầy đủ) | Summary hỏng làm answer lệch |
| `judge_accuracy`       | 1.000 | 0.667 | 1.000 | −0.333 | +0.333 (đầy đủ) | LLM judge xác nhận chất lượng giảm |
| `mean_judge_score`     | 5.000 | 3.833 | 5.000 | −1.167 | +1.167 (đầy đủ) | Điểm judge giảm hơn 1 điểm |
| Quality checks pass/fail | 9/9 | 6/9 | 9/9 | −3 checks | phục hồi đủ | Bắt duplicate + stale |
| Freshness status         | fresh | stale (5) | fresh | fresh→stale | phục hồi đủ | stale_date đẩy 5 dòng quá ngưỡng |

Hai kết luận nhân quả được artifact hỗ trợ:

1. Corruption (drop_latest + blank/noisy summary + stale date + duplicate) → quality xuống 6/9 và freshness thành stale (`data/quality/corrupted.json`, `freshness_report_corrupted.json`) → cả bốn agent metric giảm (`corrupted_metrics.json`).
2. Repair từ raw snapshot → quality trở lại 9/9 và fresh (`repaired.json`), `matches_baseline_ids=true` (`corruption_log.json`) → cả bốn metric phục hồi đúng baseline, delta +0.000 (`repaired_metrics.json`).

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `TypeError: unhashable type: 'list'` khi chạy quality checks trên DataFrame in-memory từ pipeline.
- **Nguyên nhân:** `DataFrame.duplicated()` cần hash từng cột, nhưng `authors`/`categories` là kiểu list không hashable. Lỗi không xuất hiện khi test bằng CSV (list bị đọc thành string) nhưng xuất hiện khi pipeline truyền DataFrame in-memory.
- **Cách xử lý:** đổi thành `df.astype(str).duplicated()` trong `run_data_quality_checks`.
- **Cách xác minh:** chạy lại `run_phase1.py` + `run_corruption_flow.py` trên data thật; check `no_duplicate_rows` chạy đúng và phát hiện 2 duplicate trong corrupted data.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Baseline metrics bão hòa ở 1.000 | Khó thấy tác động corruption ở dải rộng | Làm eval set khó hơn (câu hỏi suy luận, không trích abstract); đo bằng việc baseline token_f1 tụt khỏi 1.0 |
| Judge phụ thuộc quota LLM | Free tier cạn dễ rơi về fallback heuristic | Cache verdict theo (question, answer); dùng provider trả phí ổn định |
| Corpus nhỏ (24 record) | Retrieval ít cạnh tranh | Tăng `max_results` để test độ nhiễu ở corpus lớn hơn |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
