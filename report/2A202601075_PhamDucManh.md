# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Điền họ tên]           |
| MSSV               | [Điền MSSV]                |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | Nhóm 4                    |
| Vai trò chính    | Observability & Reporting owner (Thành viên 3) |
| Repository         | K3_Day10_Data-Pipeline-Data-Observability-B22 |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Data quality checks | `src/observability/quality.py` → `run_data_quality_checks` | Clean/corrupted/repaired DataFrame, `settings`, `report_name` | `data/quality/{baseline,corrupted,repaired}.json` | Hoàn thành |
| Freshness report | `src/observability/quality.py` → `build_freshness_report` | DataFrame, `settings`, `report_path` | `data/quality/freshness_report*.json` | Hoàn thành |
| Baseline markdown report | `src/observability/reporting.py` → `generate_phase1_report` | source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Comparison report | `src/observability/reporting.py` → `generate_corruption_report` | metrics + quality + freshness của 3 trạng thái | `data/reports/corruption_report.md` | Hoàn thành |

Chỉ nhận ownership cho hai file `src/observability/quality.py` và `src/observability/reporting.py`. Các hàm này được Thành viên 4 gọi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Chạy tích hợp end-to-end và duyệt cuối | Toàn nhóm | Chạy `run_phase1.py` + `run_corruption_flow.py`, sinh đủ artifact, đối chiếu report với JSON |
| Xác minh tính nhất quán report ↔ artifact | Thành viên 4 (pipeline) | Xác nhận mọi con số trong `corruption_report.md` khớp `data/results/*_metrics.json` và `data/quality/*.json` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Bộ 9 quality checks | `run_data_quality_checks` → `data/quality/baseline.json` | 9/9 pass trên baseline; 6/9 trên corrupted | Đọc file JSON và đối chiếu |
| Freshness signal theo `age_days` | `build_freshness_report` → `data/quality/freshness_report.json` | baseline `is_fresh=true`; corrupted `is_fresh=false`, 5 stale rows | Đọc file JSON |
| Baseline report | `generate_phase1_report` → `data/reports/phase1_report.md` | Markdown gom source + metrics + quality + freshness | Mở file, đối chiếu metrics |
| Comparison report | `generate_corruption_report` → `data/reports/corruption_report.md` | Bảng so sánh baseline/corrupted/repaired | Đối chiếu với `*_metrics.json` |

Output cụ thể do phần việc của tôi tạo ra: `data/reports/corruption_report.md` — báo cáo so sánh chứng minh corruption làm giảm cả bốn agent metric và repair khôi phục về đúng baseline, kèm chi tiết từng quality check pass/fail cho corrupted và repaired.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một lớp observability để phát hiện dữ liệu lỗi **trước khi** người dùng nhận câu trả lời sai, và một lớp reporting để biến metrics + quality signals thành báo cáo con người đọc được. Phần của tôi trả lời câu hỏi: "làm sao biết dataset đang tốt hay đã hỏng, và trình bày bằng chứng đó ra sao".

### Cách triển khai

`run_data_quality_checks` chạy 9 kiểm tra độc lập, mỗi kiểm tra trả về `{name, passed, details}`: row count > 0; đủ cột bắt buộc theo clean schema; `paper_id` không null; `paper_id` unique; tỷ lệ rỗng của `title`/`summary`/`text_for_embedding` dưới ngưỡng 20%; không có duplicate row (dùng `astype(str)` để so trùng vì cột `authors`/`categories` là list không hashable); và freshness theo `age_days` so với `settings.freshness_threshold_days`. Kết quả ghi JSON vào `data/quality/` theo `report_name`.

`build_freshness_report` tính `latest_published`, `oldest_published`, đếm `stale_rows` (số dòng `age_days > threshold`), và cờ `is_fresh`.

Hai hàm report gom dữ liệu thành Markdown; `generate_corruption_report` dựng bảng so sánh ba trạng thái trên cùng bộ metric keys.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Clean/corrupted/repaired DataFrame (schema: `paper_id, title, summary, authors, categories, published, age_days, text_for_embedding`), `settings`, đường dẫn output |
| Output | dict quality/freshness + file JSON; hai file Markdown report |
| Module phụ thuộc | `core.config.Settings`, `core.utils` (`write_json`, `write_text`, `safe_slug`); DataFrame từ `ingestion.cleaning` (Thành viên 2) |
| Module sử dụng output | `pipelines.phase1` và `pipelines.corruption_flow` (Thành viên 4) |
| Điều kiện lỗi cần xử lý | Cột list không hashable khi `duplicated()`; cột `published`/`age_days` rỗng hoặc không numeric |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** baseline quality 9/9 pass và fresh; corrupted quality fail ở các check bị corruption tác động; report khớp metrics.
- **Kết quả thực tế:** baseline 9/9 pass, `is_fresh=true`; corrupted 6/9 (fail `paper_id_unique`, `no_duplicate_rows`, `freshness_within_threshold`), `is_fresh=false`; repaired trở lại 9/9. Mọi con số trong report khớp file JSON.
- **Artifact/log:** `data/quality/baseline.json`, `data/quality/corrupted.json`, `data/quality/repaired.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đặt ngưỡng cho check "cột text rỗng".
- **Các phương án đã cân nhắc:** (1) fail ngay khi có 1 dòng rỗng; (2) chỉ fail khi tỷ lệ rỗng vượt một ngưỡng.
- **Phương án đã chọn:** ngưỡng tỷ lệ rỗng 20% (`MAX_EMPTY_RATIO = 0.2`).
- **Lý do:** dữ liệu thật từ Crossref có thể thiếu lác đác vài abstract mà vẫn dùng được; fail-on-any quá nhạy sẽ báo động giả. Ngưỡng tỷ lệ phân biệt được "vài dòng thiếu" với "corruption blank hàng loạt".
- **Bằng chứng quyết định phù hợp:** corrupted data có `blank_summary` 3 dòng nhưng `summary_not_mostly_empty` vẫn PASS ở mức `empty_ratio=0.1304` (dưới 0.2), trong khi các check thật sự vỡ (`paper_id_unique`, duplicate, freshness) đều FAIL đúng — cho thấy ngưỡng phân biệt được nhiễu nhỏ với hỏng thật.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: unhashable type: 'list'` tại `df.duplicated()`.
- **Lệnh hoặc bước tái hiện:** gọi `run_data_quality_checks` trên DataFrame in-memory có cột `authors`/`categories` là list.
- **Nguyên nhân gốc:** `DataFrame.duplicated()` cần hash từng cột; cột kiểu list không hashable.
- **Cách xử lý:** đổi thành `df.astype(str).duplicated()` để so trùng trên biểu diễn chuỗi.
- **Cách xác minh sau khi sửa:** chạy lại với data thật → check `no_duplicate_rows` chạy được, phát hiện đúng 2 duplicate row trong corrupted data.
- **Điều học được:** DataFrame đọc từ CSV (list thành string) khác DataFrame in-memory (list thật); phải test với đúng dạng mà pipeline truyền vào, không chỉ với CSV.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Crossref API → `fetch_source_records` lưu raw response/records → `build_clean_dataframe` chuẩn hóa và tạo `text_for_embedding` → `LocalEmbeddingIndex.build` nhúng bằng all-MiniLM-L6-v2 và nạp vào ChromaDB.
2. Mỗi test case có `question`, `ground_truth`, `ground_truth_doc_ids`. Retrieval hit = có doc_id retrieve trùng ground_truth_doc_ids; token_f1 so answer với ground_truth; LLM judge chấm điểm 1-5 + correct.
3. Quality checks kiểm tra tính đúng đắn cấu trúc dữ liệu (null, unique, rỗng, duplicate) tại một thời điểm; freshness monitoring theo dõi độ mới theo `age_days` so với ngưỡng — một cái về "đúng", một cái về "mới".
4. Cùng test set để phép so sánh có nghĩa: nếu đổi câu hỏi giữa các trạng thái thì không tách bạch được thay đổi metric là do corruption hay do câu hỏi khác.
5. Repair thành công khi: paper_id set trùng baseline (`matches_baseline_ids`), duplicate về 0, và metrics phục hồi về mức baseline — ở lần chạy này cả 4 metric repaired trùng baseline (delta +0.000).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.750 | 1.000 | Corruption làm mất/nhiễu doc khiến retrieval trượt 25% |
| `mean_token_f1` | 1.000 | 0.709 | 1.000 | Summary blank/nhiễu làm câu trả lời lệch ground truth |
| `judge_accuracy` | 1.000 | 0.667 | 1.000 | LLM judge (OpenRouter) xác nhận chất lượng giảm |
| `mean_judge_score` | 5.000 | 3.833 | 5.000 | Điểm judge giảm hơn 1 điểm khi corrupted |
| Quality checks | 9/9 | 6/9 | 9/9 | Bắt đúng duplicate + stale |
| Freshness status | fresh | stale (5 rows) | fresh | `stale_published_date` đẩy 5 dòng vượt ngưỡng 180 ngày |

### Kết luận từ số liệu

1. Corruption (drop latest + blank/noisy summary + stale date + duplicate) → quality xuống 6/9 và freshness thành stale → `retrieval_hit_rate` giảm 0.25, `mean_token_f1` giảm 0.29, `judge_accuracy` giảm 0.33.
2. Repair từ raw snapshot → quality trở lại 9/9 và fresh → cả 4 metric phục hồi đúng baseline (delta +0.000).

Corruption ảnh hưởng rõ nhất: nhóm summary (blank + noisy) và drop_latest, vì `text_for_embedding` dựa nhiều vào summary — hỏng summary trực tiếp kéo cả retrieval lẫn token_f1.

Kết quả khác kỳ vọng: **baseline đạt 1.000 tuyệt đối cho mọi metric**. Đây không phải agent hoàn hảo mà là đặc tính của evaluation set: ground_truth lấy từ abstract của paper và retrieval trả về đúng đoạn abstract đó, nên token_f1 = 1.0 tất yếu. Kiểm tra bằng cách đọc `baseline_answers.json`: 24/24 answer trùng khít ground_truth. Vì vậy giá trị của bài nằm ở **delta** giữa các trạng thái, không phải con số tuyệt đối.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline phải giữ raw snapshot bất biến — repair chỉ đáng tin khi rebuild từ nguồn, không vá tay dữ liệu hỏng.
2. Quality checks cần ngưỡng hợp lý (tỷ lệ, không tuyệt đối) để phân biệt nhiễu nhỏ với hỏng thật, tránh báo động giả.
3. Chất lượng dữ liệu ảnh hưởng trực tiếp và đo được lên RAG: cùng agent, cùng câu hỏi, chỉ đổi dữ liệu → metric thay đổi rõ rệt.

### Nếu có thêm thời gian

Làm evaluation set khó hơn (câu hỏi suy luận thay vì trích abstract) để baseline không bão hòa ở 1.0, giúp thấy tác động corruption ở dải rộng hơn; đo cải thiện bằng việc baseline token_f1 tụt khỏi 1.0 và khoảng cách corrupted-baseline giãn ra.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Điền họ tên]
**Ngày xác nhận:** 2026-08-06
