# Phân Công Nhóm 4 - Day 10 Data Pipeline & Observability

Mục tiêu của file này là chia việc để 4 người làm song song, hạn chế sửa trùng file, ai cũng có phần code/report để commit và vẫn ghép được end-to-end.

## Contract Chung Cần Chốt Trước Khi Code

| Contract | Quy ước |
| --- | --- |
| Raw record | Dùng `PaperRecord` trong `src/ingestion/crossref.py`, `paper_id` ổn định theo DOI nếu có |
| Clean schema | Tối thiểu có `paper_id`, `title`, `summary`, `authors`, `categories`, `published`, `age_days`, `text_for_embedding` |
| Document ID | `paper_id` phải giữ nguyên từ raw -> clean -> index -> eval |
| Artifact paths | Dùng `settings.paths` trong `src/core/config.py`, không hard-code path rời |
| Evaluation | `question`, `ground_truth`, `ground_truth_doc_ids`, `question_type` |
| Comparison | So sánh `baseline`, `corrupted`, `repaired` trên cùng test set và cùng `top_k` |

## Bảng Phân Công Chính

| Thành viên | Vai trò | File sở hữu chính | Output phải commit |
| --- | --- | --- | --- |
| Thành viên 1 | Source owner | `src/ingestion/crossref.py` | Raw Crossref response, raw records, schema raw rõ ràng |
| Thành viên 2 | Data model & evaluation-set owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | Cleaned dataset, `text_for_embedding`, evaluation set |
| Thành viên 3 | Observability & reporting owner | `src/observability/quality.py`, `src/observability/reporting.py` | Quality checks, freshness report, markdown reports |
| Thành viên 4 | Corruption & integration owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/` | Baseline flow, corruption/repair flow, metrics comparison |


## Flow Làm Việc Liền Mạch

Flow này dùng để biết ở từng thời điểm ai đang làm gì, ai cần chờ output của ai, và khi nào được chuyển sang bước tiếp theo.

```text
0. Chốt contract chung
   -> 1. Raw ingestion
   -> 2. Cleaning + clean schema
   -> 3. Test set + observability code
   -> 4. Baseline pipeline end-to-end
   -> 5. Corruption flow
   -> 6. Repair + comparison report
   -> 7. Review, commit cuối, chuẩn bị nộp
```

| Mốc | Người làm chính | Người làm song song | Cần có trước khi bắt đầu | Output bàn giao | Commit gợi ý khi xong mốc |
| --- | --- | --- | --- | --- | --- |
| 0. Chốt contract | Cả nhóm | Cả nhóm | Đọc `README.md`, `Guide.md`, `Rubric.md` | Thống nhất raw schema, clean schema, `paper_id`, paths, branch | `docs: agree team workflow and data contracts` |
| 1. Raw ingestion | Thành viên 1 | Thành viên 2 đọc schema dự kiến, Thành viên 3 chuẩn bị quality checklist, Thành viên 4 đọc pipeline | Contract mốc 0 | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, hàm load raw | `member1: fetch crossref source and save raw records` |
| 2. Cleaning | Thành viên 2 | Thành viên 3 cập nhật quality theo clean schema, Thành viên 4 chuẩn bị khung `phase1.py` | Raw records từ Thành viên 1 | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | `member2: generate clean paper artifacts` |
| 3. Evaluation set | Thành viên 2 | Thành viên 3 hoàn thiện quality/freshness, Thành viên 4 kiểm tra index input | Clean dataset ổn định | `data/eval/test_set.json` | `member2: build evaluation set from clean papers` |
| 4. Observability/report code | Thành viên 3 | Thành viên 4 ghép baseline flow | Clean dataset và test set | Quality/freshness functions, report functions | `member3: implement data quality freshness and reports` |
| 5. Baseline end-to-end | Thành viên 4 | Thành viên 1 kiểm tra raw lineage, Thành viên 2 kiểm tra clean/test set, Thành viên 3 kiểm tra report | Mốc 1-4 hoàn tất | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md` | `member4: wire baseline pipeline end to end` |
| 6. Corruption scenarios | Thành viên 4 | Thành viên 2 kiểm tra corrupted schema, Thành viên 3 kiểm tra quality signal | Baseline đã chạy thành công | `papers_clean_corrupted.*`, `corruption_log.json` | `member4: implement corruption scenarios and log` |
| 7. Evaluate corrupted | Thành viên 4 | Thành viên 3 đối chiếu quality/freshness | Corrupted dataset và test set cũ | `corrupted_metrics.json`, `corrupted_answers.json` | `member4: generate corrupted evaluation artifacts` |
| 8. Repair từ raw | Thành viên 4 | Thành viên 1 xác minh raw source, Thành viên 2 xác minh repaired clean schema | Raw records còn nguyên, corruption log có đủ ID | `papers_clean_repaired.*`, repaired index | `member4: repair corrupted data from raw records` |
| 9. Evaluate repaired + comparison | Thành viên 4 + Thành viên 3 | Cả nhóm review số liệu | Baseline, corrupted, repaired metrics | `repaired_metrics.json`, `corruption_report.md` | `member3: finalize corruption comparison report` |
| 10. Review cuối | Cả nhóm | Cả nhóm | Tất cả artifact có thật | Checklist nộp bài, individual reports | `docs: finalize team submission evidence` |

## Handoff Giữa Các Thành Viên

| Handoff | Khi nào bàn giao | Người nhận cần kiểm tra gì | Nếu lỗi thì quay lại ai |
| --- | --- | --- | --- |
| Thành viên 1 -> Thành viên 2 | Sau mốc 1 | Raw JSON đọc được, `paper_id`, `title`, `summary`, `published` có dữ liệu | Thành viên 1 |
| Thành viên 2 -> Thành viên 3 | Sau mốc 2 | Clean schema có đủ cột để check quality/freshness | Thành viên 2 |
| Thành viên 2 -> Thành viên 4 | Sau mốc 3 | Test set dùng `ground_truth_doc_ids` tồn tại trong clean data | Thành viên 2 |
| Thành viên 3 -> Thành viên 4 | Sau mốc 4 | Hàm quality/report nhận đúng dataframe, settings và output path | Thành viên 3 |
| Thành viên 4 -> Cả nhóm | Sau mốc 5 | Baseline artifacts đủ và report khớp metrics | Người sở hữu module gây lỗi |
| Thành viên 4 + Thành viên 3 -> Cả nhóm | Sau mốc 9 | Comparison có đủ baseline/corrupted/repaired và kết luận dựa trên số liệu | Thành viên 3 hoặc 4 |

## Quy Tắc Chạy Song Song

- Thành viên 1 phải ưu tiên xong raw ingestion trước, vì Thành viên 2 phụ thuộc trực tiếp vào raw records.
- Thành viên 2 có thể viết khung cleaning trước, nhưng chỉ commit clean artifacts sau khi dùng raw records thật.
- Thành viên 3 có thể viết quality/reporting sớm theo contract, nhưng phải chạy lại sau khi có clean data thật.
- Thành viên 4 có thể dựng khung pipeline sớm, nhưng chỉ merge flow hoàn chỉnh sau khi các hàm của Thành viên 1-3 đã merge.
- Corruption chỉ bắt đầu sau khi baseline đã có `data/results/baseline_metrics.json` và `data/eval/test_set.json`.
- Repair phải chạy từ raw records hoặc source đáng tin, không sửa tay corrupted dataset hoặc metrics.
## Thành Viên 1 - Source Owner

Branch: `feature/member-1-source`

Phạm vi chính:

- Hoàn thiện `parse_crossref_payload(payload)` trong `src/ingestion/crossref.py`.
- Hoàn thiện `fetch_source_records(settings)` để gọi Crossref API, retry khi gặp `429` hoặc `503`, lưu raw response và raw records.
- Hoàn thiện `load_raw_records(path)` để đọc lại snapshot JSON thành `PaperRecord`.

Không nên sửa:

- `src/ingestion/cleaning.py`, trừ khi cần phối hợp sửa schema đã thống nhất.
- `src/pipelines/phase1.py`, chỉ báo cho Thành viên 4 cách gọi hàm.

Output kiểm tra:

- `data/raw/crossref_response.json`
- `data/raw/crossref_records.json`
- Có thể giải thích query/filter đang dùng trong `settings.source_query` và `settings.source_filter`.

Lệnh kiểm tra gợi ý:

```powershell
uv run python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); print(len(fetch_source_records(s)))"
```

Commit theo từng task:

| Task | File nên add | Commit message gợi ý |
| --- | --- | --- |
| Parse payload Crossref thành `PaperRecord` | `src/ingestion/crossref.py` | `member1: parse crossref payload into paper records` |
| Gọi API, retry và lưu raw response | `src/ingestion/crossref.py`, `data/raw/crossref_response.json` | `member1: fetch crossref source and save raw response` |
| Lưu raw records đã parse | `src/ingestion/crossref.py`, `data/raw/crossref_records.json` | `member1: save parsed raw paper records` |
| Đọc lại raw snapshot | `src/ingestion/crossref.py` | `member1: load raw records from snapshot` |
| Ghi chú schema raw cho nhóm nếu cần | `PHAN_CONG_NHOM_4.md` hoặc report cá nhân | `member1: document raw ingestion schema` |


## Kế Hoạch Thực Hiện Riêng - Thành Viên 1

Mục tiêu của Thành viên 1 là hoàn thiện toàn bộ phần lấy dữ liệu Crossref và bàn giao raw records ổn định cho Thành viên 2. Không bắt đầu sửa cleaning hoặc pipeline nếu chưa có thống nhất với nhóm.

### Thứ Tự Công Việc

| Bước | Việc cần làm | File xử lý | Đầu vào cần có | Đầu ra bàn giao | Commit gợi ý |
| --- | --- | --- | --- | --- | --- |
| 1 | Đọc contract và cấu hình source | `src/core/config.py`, `src/ingestion/crossref.py` | `Settings`, `PaperRecord`, `source_query`, `source_filter`, `max_results` | Hiểu API query và schema raw cần trả về | Không cần commit nếu chỉ đọc |
| 2 | Implement parse Crossref payload | `src/ingestion/crossref.py` | Payload mẫu từ Crossref hoặc raw response | `list[PaperRecord]` có `paper_id`, `title`, `summary`, `authors`, `categories`, `published`, URLs | `member1: parse crossref payload into paper records` |
| 3 | Xử lý dữ liệu thiếu và chuẩn hóa nhẹ | `src/ingestion/crossref.py` | Crossref items có thể thiếu DOI, abstract, authors, date | Bỏ record không hợp lệ, normalize text cơ bản, ID ổn định | `member1: handle missing crossref fields` |
| 4 | Implement fetch source records | `src/ingestion/crossref.py` | `settings.source_query`, `settings.source_filter`, `settings.max_results` | Gọi API, retry `429/503`, lưu raw response | `member1: fetch crossref source with retry` |
| 5 | Lưu raw records sau parse | `src/ingestion/crossref.py`, `data/raw/crossref_records.json` | List `PaperRecord` từ parser | JSON raw records đọc lại được | `member1: save parsed raw paper records` |
| 6 | Implement load raw records | `src/ingestion/crossref.py` | `data/raw/crossref_records.json` | Đọc snapshot thành `list[PaperRecord]` | `member1: load raw records from snapshot` |
| 7 | Smoke test riêng module ingestion | `src/ingestion/crossref.py`, `data/raw/` | `.env` nếu cần, internet, dependency đã cài | In được số lượng records > 0, raw files tồn tại | `member1: verify crossref ingestion outputs` nếu có sửa nhỏ |
| 8 | Bàn giao cho Thành viên 2 | Report cá nhân hoặc ghi chú nhóm | Raw records đã đọc được | Thành viên 2 xác nhận dùng được cho cleaning | `member1: document raw ingestion handoff` nếu có ghi docs |

### Checklist Khi Code

- [ ] Không hard-code absolute path, dùng `settings.paths.raw_api_response` và `settings.paths.raw_records_json`.
- [ ] `paper_id` ổn định. Ưu tiên DOI; nếu DOI thiếu thì dùng cách tạo ID nhất quán từ title/source.
- [ ] `title` và `summary` không để kiểu list/object thô từ API lọt sang cleaning.
- [ ] `authors` luôn là `list[str]`, kể cả khi API thiếu author.
- [ ] `categories` luôn là `list[str]`.
- [ ] `published` và `updated` dùng chuỗi date dễ parse lại ở bước cleaning.
- [ ] Raw API response được lưu trước khi parse để truy vết lỗi.
- [ ] Raw records JSON không chứa dataclass object chưa serialize được.

### Lệnh Kiểm Tra Riêng

Chạy fetch thật và in số record:

```powershell
uv run python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); records=fetch_source_records(s); print(len(records)); print(records[0])"
```

Kiểm tra load lại snapshot:

```powershell
uv run python -c "from core.config import load_settings; from ingestion.crossref import load_raw_records; s=load_settings(); records=load_raw_records(s.paths.raw_records_json); print(len(records)); print(records[0].paper_id)"
```

Kiểm tra file output:

```powershell
Get-ChildItem data\raw
```

### Điều Kiện Bàn Giao Cho Thành Viên 2

Chỉ bàn giao khi đủ các điều kiện sau:

- `data/raw/crossref_response.json` tồn tại.
- `data/raw/crossref_records.json` tồn tại.
- `load_raw_records(settings.paths.raw_records_json)` chạy được.
- Có ít nhất một record hợp lệ.
- Mỗi record hợp lệ có `paper_id`, `title`, `summary`, `published`.
- Thành viên 2 có thể gọi `build_clean_dataframe(records, run_date)` mà không cần biết chi tiết payload Crossref gốc.

### Khi Gặp Lỗi

| Lỗi | Cách xử lý |
| --- | --- |
| Crossref trả `429` | Retry có delay/backoff, không spam API liên tục |
| Crossref trả `503` | Retry vài lần rồi báo blocker kèm status code |
| Item thiếu DOI | Dùng fallback ID ổn định hoặc bỏ record nếu không đủ title/URL |
| Abstract có HTML/XML tag | Strip tag hoặc normalize trước khi đưa vào `summary` |
| Date thiếu hoặc format lạ | Ghi chuỗi rỗng hoặc fallback an toàn để Thành viên 2 xử lý tiếp |
| JSON không serialize được | Convert dataclass sang dict trước khi ghi file |
## Thành Viên 2 - Data Model & Evaluation-Set Owner

Branch: `feature/member-2-clean-eval`

Phạm vi chính:

- Hoàn thiện `build_clean_dataframe(records, run_date)` trong `src/ingestion/cleaning.py`.
- Chuẩn hóa title, summary, authors, categories.
- Tạo `text_for_embedding`.
- Tính `published`, `age_days`.
- Loại record không hợp lệ và deduplicate theo `paper_id`.
- Hoàn thiện `build_test_set(df, output_path)` trong `src/evaluation/testset.py`.

Không nên sửa:

- `src/ingestion/crossref.py`, chỉ dùng `PaperRecord` Thành viên 1 bàn giao.
- `src/retrieval/` vì phần index/agent đã có starter tham khảo.
- `src/pipelines/`, chỉ báo input/output cho Thành viên 4.

Output kiểm tra:

- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`
- `data/eval/test_set.json`
- `paper_id` unique, `text_for_embedding` không rỗng.

Lệnh kiểm tra gợi ý:

```powershell
uv run python -c "import pandas as pd; df=pd.read_csv('data/clean/papers_clean.csv'); print(df.columns.tolist()); print(df['paper_id'].is_unique)"
```

Commit theo từng task:

| Task | File nên add | Commit message gợi ý |
| --- | --- | --- |
| Chuẩn hóa field text, authors, categories | `src/ingestion/cleaning.py` | `member2: normalize paper fields for clean dataset` |
| Tạo `text_for_embedding` và `age_days` | `src/ingestion/cleaning.py` | `member2: add embedding text and freshness fields` |
| Filter record lỗi và deduplicate | `src/ingestion/cleaning.py` | `member2: filter invalid records and deduplicate papers` |
| Sinh clean artifacts | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | `member2: generate clean paper artifacts` |
| Tạo evaluation set từ clean data | `src/evaluation/testset.py`, `data/eval/test_set.json` | `member2: build evaluation set from clean papers` |

## Thành Viên 3 - Observability & Reporting Owner

Branch: `feature/member-3-observability`

Phạm vi chính:

- Hoàn thiện `run_data_quality_checks(df, settings, report_name)` trong `src/observability/quality.py`.
- Hoàn thiện `build_freshness_report(df, settings, report_path)` trong `src/observability/quality.py`.
- Hoàn thiện `generate_phase1_report(...)` trong `src/observability/reporting.py`.
- Hoàn thiện `generate_corruption_report(...)` trong `src/observability/reporting.py`.

Quality checks tối thiểu:

- Row count > 0.
- `paper_id` không null và unique.
- `title`, `summary`, `text_for_embedding` không rỗng quá nhiều.
- Duplicate rows/documents.
- Freshness dựa trên `age_days` và `settings.freshness_threshold_days`.

Không nên sửa:

- `src/evaluation/metrics.py`, trừ khi cả nhóm thống nhất metric contract mới.
- `src/pipelines/`, chỉ cung cấp hàm report cho Thành viên 4 gọi.

Output kiểm tra:

- File JSON quality trong `data/quality/`.
- `data/quality/freshness_report.json`.
- `data/reports/phase1_report.md`.
- `data/reports/corruption_report.md`.

Lệnh kiểm tra gợi ý:

```powershell
Get-ChildItem data\quality, data\reports -Recurse
```

Commit theo từng task:

| Task | File nên add | Commit message gợi ý |
| --- | --- | --- |
| Implement quality checks cơ bản | `src/observability/quality.py` | `member3: implement core data quality checks` |
| Implement freshness report | `src/observability/quality.py` | `member3: add freshness reporting` |
| Sinh quality/freshness artifacts | `data/quality/` theo file thực tế | `member3: generate quality and freshness artifacts` |
| Viết phase 1 markdown report | `src/observability/reporting.py`, `data/reports/phase1_report.md` | `member3: generate baseline markdown report` |
| Viết comparison report | `src/observability/reporting.py`, `data/reports/corruption_report.md` | `member3: generate corruption comparison report` |

## Thành Viên 4 - Corruption & Integration Owner

Branch: `feature/member-4-integration`

Phạm vi chính:

- Hoàn thiện `corrupt_clean_dataframe(df, output_log_path)` trong `src/ingestion/corruption.py`.
- Hoàn thiện baseline orchestration trong `src/pipelines/phase1.py`.
- Hoàn thiện corruption -> evaluate -> repair -> compare trong `src/pipelines/corruption_flow.py`.
- Đảm bảo `script/run_phase1.py` và `script/run_corruption_flow.py` chạy đúng entrypoint.

Corruption cần có:

- Xóa một số latest records.
- Blank summary.
- Add noise vào summary.
- Truncate title.
- Làm stale publication date hoặc tăng `age_days`.
- Add duplicate rows.
- Ghi `data/results/corruption_log.json` nêu rõ record nào bị tác động.

Không nên sửa:

- Logic ingestion/cleaning/observability của người khác nếu chưa trao đổi.
- File data baseline khi chạy corrupted/repaired. Phải dùng path riêng trong `settings.paths`.

Output kiểm tra:

- `data/results/baseline_metrics.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/results/corruption_log.json`
- `data/reports/corruption_report.md`

Lệnh kiểm tra gợi ý:

```powershell
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Commit theo từng task:

| Task | File nên add | Commit message gợi ý |
| --- | --- | --- |
| Ghép baseline flow | `src/pipelines/phase1.py` | `member4: wire baseline pipeline flow` |
| Chạy và lưu baseline metrics | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | `member4: generate baseline evaluation artifacts` |
| Implement corruption scenarios và log | `src/ingestion/corruption.py`, `data/results/corruption_log.json` | `member4: implement corruption scenarios and log` |
| Ghép corruption/re-evaluate/repair flow | `src/pipelines/corruption_flow.py` | `member4: wire corruption repair comparison flow` |
| Lưu corrupted/repaired metrics | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json` | `member4: generate corrupted and repaired metrics` |
| Kiểm tra script entrypoint | `script/run_phase1.py`, `script/run_corruption_flow.py` nếu có sửa | `member4: verify pipeline entrypoints` |

## Thứ Tự Merge Để Ít Conflict

1. Thành viên 1 merge trước khi có raw ingestion chạy được.
2. Thành viên 2 merge sau khi đọc được raw records và tạo clean/test set.
3. Thành viên 3 merge observability/reporting, vì chủ yếu được pipeline gọi sau.
4. Thành viên 4 merge cuối để ghép end-to-end và sửa integration nhỏ nếu cần.

Nếu Thành viên 4 cần merge sớm để dựng khung pipeline, chỉ commit khung gọi hàm, không sửa sâu vào file của Thành viên 1-3.

## Checklist Trước Khi Nộp

- [ ] `rg -n "TODO\(student\)|NotImplementedError" src` không còn task bắt buộc chưa làm.
- [ ] `uv run python script/run_phase1.py` chạy được.
- [ ] `uv run python script/run_corruption_flow.py` chạy được sau baseline.
- [ ] Có đủ artifact trong `data/raw/`, `data/clean/`, `data/eval/`, `data/results/`, `data/quality/`, `data/reports/`.
- [ ] Report so sánh có đủ baseline, corrupted, repaired.
- [ ] Không có `.env`, API key hoặc secret trong Git.
- [ ] Mỗi thành viên có nội dung riêng để ghi vào `report/individual_report.md` hoặc bản sao `<MSSV>_HoTen.md`.

## Mẫu Nội Dung Báo Cáo Cá Nhân

Mỗi người có thể copy khung này vào file báo cáo cá nhân riêng:

~~~~markdown
## Vai trò

Tôi phụ trách: ...

## File đã trực tiếp sửa

- ...

## Output đã tạo

- ...

## Lệnh đã chạy để kiểm tra

```text
...
```

## Kết quả và bằng chứng

- ...

## Blocker hoặc giới hạn còn lại

- ...
~~~~
