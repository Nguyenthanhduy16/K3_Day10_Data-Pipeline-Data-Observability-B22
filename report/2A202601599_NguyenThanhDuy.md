# Báo cáo cá nhân - Thành viên 1

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thành Duy |
| MSSV | 2A202601599|
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm B22 |
| Vai trò chính | Thành viên 1 - Source Owner |
| Repository | K3_Day10_Data-Pipeline-Data-Observability-B22 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách phần lấy dữ liệu nguồn từ Crossref, chuẩn hóa payload thô thành schema `PaperRecord`, lưu snapshot raw để các bước cleaning, evaluation và pipeline phía sau có dữ liệu ổn định để sử dụng lại.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Parse Crossref payload | `src/ingestion/crossref.py::parse_crossref_payload` | Payload JSON từ Crossref REST API | `list[PaperRecord]` đã chuẩn hóa | Hoàn thành |
| Fetch dữ liệu nguồn | `src/ingestion/crossref.py::fetch_source_records` | `settings.source_query`, `settings.source_filter`, `settings.max_results` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Load snapshot raw | `src/ingestion/crossref.py::load_raw_records` | `data/raw/crossref_records.json` | `list[PaperRecord]` đọc lại được | Hoàn thành |
| Retry API | `src/ingestion/crossref.py::_get_with_retry` | Crossref endpoint, params, headers | Request có retry cho `429`, `500`, `502`, `503`, `504` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất raw schema và `paper_id` | Thành viên 2 - cleaning/evaluation | Cleaning có thể dùng trực tiếp `PaperRecord` và giữ nguyên document ID |
| Bàn giao raw artifacts | Thành viên 2, 4 | Pipeline sau có thể chạy lại từ snapshot, không phụ thuộc luôn vào API sống |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa title, abstract, DOI, author, subject, date từ Crossref | `src/ingestion/crossref.py` | Record có `paper_id`, `title`, `summary`, `authors`, `categories`, `published`, `updated`, URL | Đọc `data/raw/crossref_records.json` |
| Lưu raw response đầy đủ để truy vết | `data/raw/crossref_response.json` | Snapshot response gốc từ Crossref | Kiểm tra file trong `data/raw/` |
| Lưu raw records đã parse | `data/raw/crossref_records.json` | 24 records raw đã chuẩn hóa | `load_raw_records(settings.paths.raw_records_json)` |
| Xử lý dữ liệu thiếu và trùng | `parse_crossref_payload` | Bỏ record thiếu `title`/`summary`, chống trùng `paper_id` | Kiểm tra logic `seen_ids` và dữ liệu output |

Artifact cụ thể đã tạo:

- `data/raw/crossref_response.json`
- `data/raw/crossref_records.json`

Tại thời điểm kiểm tra, `data/raw/crossref_records.json` có 24 records.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả về payload JSON có cấu trúc không đồng nhất: `title` thường là list, `abstract` có thể chứa tag XML/HTML, DOI có thể thiếu, author/date/subject có thể không đầy đủ. Nếu chuyển thẳng payload này sang bước cleaning thì các module sau sẽ phải xử lý quá nhiều trường hợp đặc biệt.

### Cách triển khai

Tôi tạo lớp schema trung gian `PaperRecord` để gom các field cần thiết cho pipeline. Hàm `parse_crossref_payload` duyệt từng item trong `message.items`, chuẩn hóa text, làm sạch abstract, parse author/category/date, tạo `paper_id` ổn định từ DOI hoặc fallback từ title/URL, sau đó bỏ record không đủ `title` hoặc `summary`.

Hàm `fetch_source_records` gọi Crossref REST API bằng query/filter trong `Settings`, lưu response gốc trước, parse thành `PaperRecord`, rồi lưu danh sách record đã serialize sang JSON. Hàm `_get_with_retry` retry các lỗi tạm thời như rate limit hoặc server error để giảm khả năng fail do API không ổn định.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref payload từ `https://api.crossref.org/works` |
| Output | `list[PaperRecord]`, `crossref_response.json`, `crossref_records.json` |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py` |
| Module sử dụng output | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | API trả `429/503`, item thiếu DOI, abstract có tag, date thiếu hoặc format lạ, JSON không serialize được |

### Cách xác minh

```powershell
uv run python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); records=fetch_source_records(s); print(len(records)); print(records[0])"
```

```powershell
uv run python -c "from core.config import load_settings; from ingestion.crossref import load_raw_records; s=load_settings(); records=load_raw_records(s.paths.raw_records_json); print(len(records)); print(records[0].paper_id)"
```

```powershell
Get-ChildItem data\raw
```

- Kết quả mong đợi: có raw response, raw records, đọc lại được ít nhất một `PaperRecord`.
- Kết quả thực tế đã kiểm tra: `data/raw/crossref_records.json` có 24 records; `data/raw/crossref_response.json` và `data/raw/crossref_records.json` đều tồn tại.
- Artifact/log: `data/raw/`.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: Crossref DOI có thể thiếu trong một số item, nhưng pipeline cần `paper_id` ổn định để nối raw, clean, index và evaluation.
- Các phương án đã cân nhắc: bỏ toàn bộ record thiếu DOI; hoặc tạo fallback ID từ URL/title.
- Phương án đã chọn: ưu tiên DOI, nếu DOI thiếu thì dùng `safe_slug(url or title)` làm fallback ID.
- Lý do: giữ được nhiều dữ liệu hợp lệ hơn nhưng vẫn đảm bảo document ID nhất quán và có thể deduplicate.
- Bằng chứng quyết định phù hợp: `parse_crossref_payload` có logic `paper_id = doi or _fallback_id(title, url)` và kiểm tra `seen_ids` để tránh trùng.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi: Abstract từ Crossref có thể chứa tag như `<jats:p>` hoặc ký tự HTML entity.
- Lệnh hoặc bước tái hiện: đọc trực tiếp field `abstract` trong raw response Crossref.
- Nguyên nhân gốc: Crossref lưu abstract theo định dạng metadata, không phải plain text sạch.
- Cách xử lý: dùng `html.unescape`, regex loại tag, sau đó normalize whitespace trong `_clean_abstract`.
- Cách xác minh sau khi sửa: kiểm tra `summary` trong `data/raw/crossref_records.json` là text phẳng, không còn tag HTML/XML.
- Điều học được: dữ liệu nguồn cần được snapshot và chuẩn hóa nhẹ ngay tại ingestion để giảm lỗi lan sang cleaning và indexing.

## 7. Hiểu biết về luồng end-to-end

Dữ liệu đi từ Crossref vào `crossref_response.json`, sau đó được parse thành `PaperRecord` trong `crossref_records.json`. Thành viên 2 dùng raw records này để tạo clean dataset, bổ sung `text_for_embedding`, tính `age_days` và tạo evaluation set. Clean dataset được index thành vector store để agent truy xuất tài liệu theo câu hỏi. Metrics baseline đo trên cùng test set sẽ được so sánh với metrics sau corruption và repaired.

Evaluation set dùng `ground_truth_doc_ids` để kiểm tra retrieval có tìm đúng tài liệu hay không. Quality checks kiểm tra tính đầy đủ, unique, duplicate và các lỗi schema; freshness monitoring tập trung vào độ mới của dữ liệu dựa trên `age_days`. Phải dùng cùng test set cho baseline, corrupted và repaired để so sánh công bằng. Repair được xem là thành công khi dữ liệu repaired khôi phục được quality/freshness signal và metrics tiến gần hoặc tốt hơn trạng thái corrupted.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | Source quality ảnh hưởng trực tiếp đến khả năng retrieval |
| `mean_token_f1` | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | Summary sạch giúp câu trả lời bám sát ground truth hơn |
| `judge_accuracy` | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | Cần đối chiếu với artifact answers |
| `mean_judge_score` | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | [Điền sau khi Thành viên 4 chạy] | Cần đọc report cuối |
| Quality checks | Raw records đọc được, ID ổn định | [Điền sau corruption] | [Điền sau repair] | Ingestion cần giữ schema sạch để quality pass |
| Freshness status | Có `published` để tính freshness | [Điền sau corruption] | [Điền sau repair] | Date chuẩn hóa là input cho freshness |

### Kết luận từ số liệu

Phần ingestion của tôi tạo đầu vào ổn định cho chuỗi nguyên nhân sau: dữ liệu nguồn có `paper_id`, `summary`, `published` rõ ràng -> cleaning tạo được `text_for_embedding` và `age_days` -> index/evaluation có thể đo retrieval và answer quality.

Khi có số liệu cuối cùng, cần điền thêm hai chuỗi phân tích:

1. Corruption làm thay đổi field nào -> quality/freshness signal thay đổi ra sao -> agent metric thay đổi thế nào.
2. Repair từ raw records -> signal nào phục hồi -> metric nào phục hồi hoặc chưa phục hồi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Snapshot raw response là cần thiết để pipeline có thể tái hiện và repair khi clean data bị corruption.
2. `paper_id` phải ổn định từ đầu, vì nó là khóa nối giữa raw, clean, index và evaluation.
3. Data observability không chỉ kiểm tra pipeline có chạy hay không, mà còn kiểm tra dữ liệu có đủ sạch để agent trả lời đúng hay không.

### Nếu có thêm thời gian

Tôi sẽ bổ sung unit test riêng cho `parse_crossref_payload`, gồm các case thiếu DOI, abstract có tag, author thiếu field, date thiếu tháng/ngày và duplicate DOI. Việc này giúp ingestion ít phụ thuộc vào việc test thủ công bằng API sống.

## 10. Cam kết của thành viên

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thành Duy  
**Ngày xác nhận:** 2026-08-06
