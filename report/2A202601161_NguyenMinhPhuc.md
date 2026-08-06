# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Minh Phúc |
| MSSV | 2A202601161 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 (B22) |
| Vai trò chính | Thành viên 4 — Corruption & Integration owner |
| Repository | https://github.com/Nguyenthanhduy16/K3_Day10_Data-Pipeline-Data-Observability-B22 |
| Ngày hoàn thành | 2026-08-06 (code đã xong, tích hợp đủ TV1–TV3; pipeline đã chạy trọn vẹn và sinh đủ artifact cuối) |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Corruption scenarios | `src/ingestion/corruption.py` — `corrupt_clean_dataframe(df, output_log_path)` | Cleaned dataframe từ Thành viên 2 | Corrupted dataframe + `data/results/corruption_log.json` | **Hoàn thành và đã chạy trên clean data thật của TV2** — cả 6 scenario kích hoạt đúng volume |
| Baseline orchestration | `src/pipelines/phase1.py` — `main()` | Raw records (TV1), cleaning + test set (TV2), quality + reporting (TV3) | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md` | **Hoàn thành và đã chạy trọn vẹn** sau khi TV3 merge; sinh đủ artifact baseline |
| Corruption/repair/compare flow | `src/pipelines/corruption_flow.py` — `main()` | Baseline artifacts + raw snapshot | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | **Hoàn thành và đã chạy** sau baseline; sinh đủ corrupted/repaired metrics + comparison report |
| Script entrypoints | `script/run_phase1.py`, `script/run_corruption_flow.py` | — | Hai entrypoint gọi đúng `main()` | Hoàn thành, đã xác minh import và chạy tới đúng điểm chặn |
| Self-check offline (bổ sung) | `script/selfcheck_corruption.py` | Fixture tổng hợp tự sinh | 12 assertion kiểm tra corruption logic | Hoàn thành, 12/12 PASS |

Tôi chỉ nhận ownership cho 4 file trên. Tôi **không** sửa `crossref.py`, `cleaning.py`, `testset.py`, `quality.py`, `reporting.py`, `metrics.py`, `index.py`, `qa.py`, `agent.py` — các file đó thuộc thành viên khác hoặc là starter tham khảo.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt và ghi cứng contract clean schema thành assertion trong code | Thành viên 2 (`cleaning.py`, `testset.py`) | `_validate_clean_dataframe()` liệt kê rõ 10 cột mà index/agent đọc trực tiếp và báo lỗi ngay nếu thiếu, thay vì để `KeyError` mơ hồ nổ ở tầng Chroma. **Đã chạy trên bản merge của TV2: pass, không phải sửa gì hai bên** |
| Cảnh báo sớm khi `ground_truth_doc_ids` không tồn tại trong clean data | Thành viên 2 (`testset.py`) | `_validate_test_set()` in warning kèm ví dụ ID sai, giúp phát hiện test set lệch trước khi metrics bị hạ oan. **Đã chạy trên `test_set.json` thật: 24/24 case hợp lệ, không có ID lạ** |
| Làm rõ contract gọi hàm observability | Thành viên 3 (`quality.py`) | Báo cho TV3 rằng `run_data_quality_checks` sẽ được gọi **3 lần** với `report_name` = `baseline`/`corrupted`/`repaired`, nên tên file output bắt buộc phải chứa `report_name` nếu không sẽ ghi đè nhau |
| Cấp path riêng cho freshness report của từng trạng thái | Thành viên 3 (`quality.py`) | `_freshness_path()` sinh `freshness_report_corrupted.json` / `freshness_report_repaired.json` từ `settings.paths`, không hard-code |
| Xác minh raw snapshot dùng được cho bước repair | Thành viên 1 (`crossref.py`) | `load_raw_records()` đọc lại được 24 records từ `data/raw/crossref_records.json`; đây là nguồn sự thật cho bước repair |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Cài đặt 6 kịch bản corruption có chủ đích, deterministic, ghi log truy vết được | `src/ingestion/corruption.py` | Hàm `corrupt_clean_dataframe` + schema `corruption_log.json` | `python script/selfcheck_corruption.py` → 12/12 PASS |
| Ghép baseline flow 9 bước có validate contract và log tiến trình | `src/pipelines/phase1.py` | Hàm `main()` chạy tuần tự raw → clean → index → test set → evaluate → quality → freshness → report → agent demo | `python script/run_phase1.py` chạy qua bước 1 (24 raw records) rồi dừng đúng ở hàm chưa implement của TV2 |
| Ghép flow corrupt → evaluate → repair → compare, có guard và verification | `src/pipelines/corruption_flow.py` | Hàm `main()` + `_verify_repair()` ghi kết quả kiểm chứng repair ngược vào corruption log | `python script/run_corruption_flow.py` báo lỗi đúng và rõ khi thiếu baseline artifacts |
| Viết self-check offline để không bị chặn bởi tiến độ người khác | `script/selfcheck_corruption.py` | 12 assertion trên fixture tổng hợp, chạy không cần mạng, không cần API key, không ghi vào `data/` | Output 12/12 PASS (dán ở mục 4) |
| Kiểm tra tích hợp với bản merge của TV2 | `cleaning.py` + `testset.py` (TV2) → `corruption.py` + `phase1.py` (tôi) | Xác nhận contract khớp và corruption hoạt động đúng trên clean data thật | Chạy trực tiếp: 24 raw → 24 clean, đủ cột, test set 24 case hợp lệ, corruption 24 → 23 dòng với đủ 6 scenario (kết quả ở mục 4) |

Một output cụ thể mà phần việc của tôi tạo ra:

`data/results/corruption_log.json` — file này không chỉ nói "đã corrupt", nó liệt kê **chính xác từng `paper_id` bị tác động bởi từng scenario**, cộng thêm khối `repair_verification` đối chiếu tập ID baseline / corrupted / repaired. Nhờ nó, kết luận "repair thành công" là một phép so sánh tập hợp kiểm chứng được, không phải lời tuyên bố.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi phải trả lời được câu hỏi trung tâm của bài lab: **dữ liệu xấu có thực sự làm agent trả lời tệ đi không, và repair có cứu lại được không?**

Muốn trả lời có sức thuyết phục thì corruption phải thỏa 3 điều kiện, và đây chính là 3 ràng buộc tôi thiết kế xung quanh:

1. **Có chủ đích và truy vết được** — phải biết chính xác record nào hỏng vì lý do gì, nếu không thì không thể chứng minh repair đã sửa đúng cái gì.
2. **Thực sự chạm tới vector index** — corrupt cột `summary` nhưng `text_for_embedding` vẫn giữ nội dung cũ thì retrieval không đổi, thí nghiệm vô nghĩa.
3. **Repair phải từ nguồn đáng tin** — vá tay dataset corrupted là gian lận về mặt phương pháp; phải dựng lại từ raw snapshot.

### Cách triển khai

**a) Sáu kịch bản corruption** (`corrupt_clean_dataframe`), mỗi cái mô phỏng một sự cố data pipeline có thật:

| Scenario | Mô phỏng sự cố thật | Cách phá |
| --- | --- | --- |
| `drop_latest_records` | Incremental load fail, mất partition mới nhất | Sort theo `published` giảm dần, xóa các record đầu |
| `blank_summary` | Trường upstream bị null | Set `summary = ""` |
| `noisy_summary` | Scraper/OCR lẫn rác HTML, base64, ký tự lạ | Bọc summary bằng khối nhiễu 2 đầu |
| `truncated_title` | Export sai, cột bị cắt độ dài | Giữ 12 ký tự đầu của title |
| `stale_published_date` | Replay nhầm partition cũ | Lùi `published` 1200 ngày, cộng `age_days` tương ứng |
| `duplicate_rows` | Pipeline retry không idempotent | Append bản sao của vài dòng |

**b) Không chọn trùng dòng giữa các scenario.** Hàm `_pick_positions()` giữ một set `used_ids`, mỗi scenario chỉ chọn từ những dòng chưa ai đụng. Nếu một dòng vừa bị blank summary vừa bị noise thì log mất khả năng quy trách nhiệm — không biết metric tụt là do cái nào.

**c) Volume scale theo kích thước corpus.** Dùng tỉ lệ (`0.15`, `0.20`...) thay vì số cứng, có `max(1, ...)` để corpus nhỏ vẫn có ít nhất 1 dòng mỗi scenario. Chi tiết lý do ở mục 6.

**d) Vá `text_for_embedding` bằng substring-replace thay vì dựng lại.** Đây là quyết định kỹ thuật quan trọng nhất, trình bày riêng ở mục 5.

**e) Deterministic.** `random.Random(CORRUPTION_SEED)` với seed cố định `20251010`, không dùng `random` toàn cục. Chạy lại 2 lần trên cùng input cho ra dataframe giống hệt — self-check có assertion riêng cho tính chất này. Nếu corruption ngẫu nhiên mỗi lần chạy thì con số trong report không tái lập được.

**f) Repair dựng lại từ raw, không vá corrupted.** `_repair_from_raw()` gọi `load_raw_records()` rồi `build_clean_dataframe()` — cùng đúng đường đi mà baseline đã dùng. Sau đó `_verify_repair()` so tập `paper_id` của 3 trạng thái để trả lời: đã lấy lại đủ số record bị xóa chưa, duplicate đã biến mất chưa, tập ID repaired có khớp baseline không.

**g) Fail sớm với thông báo hữu ích.** `_require_baseline_artifacts()` liệt kê đúng file nào thiếu kèm lệnh cần chạy, thay vì để traceback `FileNotFoundError` khó hiểu ở giữa flow.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Cleaned dataframe (TV2) bắt buộc có `paper_id`, `title`, `summary`, `published`, `age_days`, `text_for_embedding`, `authors_joined`, `categories_joined`, `abs_url`, `pdf_url`; raw records snapshot (TV1); test set (TV2) |
| Output | `papers_clean_corrupted.*`, `papers_clean_repaired.*`, `corruption_log.json`, `baseline/corrupted/repaired_metrics.json`, `*_answers.json`, `phase1_report.md`, `corruption_report.md` |
| Module phụ thuộc | `ingestion/cleaning.py`, `ingestion/crossref.py`, `evaluation/testset.py`, `evaluation/metrics.py`, `observability/quality.py`, `observability/reporting.py`, `retrieval/index.py` |
| Module sử dụng output | `observability/reporting.py` (nhận metrics + quality + freshness của cả 3 trạng thái để dựng bảng so sánh) |
| Điều kiện lỗi cần xử lý | Dataframe rỗng hoặc thiếu cột; `published` rỗng/không parse được; corpus quá nhỏ khiến scenario hết dòng để chọn; chạy phase 2 khi chưa có baseline; thiếu API key khi demo agent; raw snapshot rỗng lúc repair |

Toàn bộ đường dẫn lấy từ `settings.paths` trong `src/core/config.py`, không hard-code path tuyệt đối. Không có API key hay secret trong code của tôi.

### Cách xác minh

```bash
# 1. Self-check corruption logic (offline, không cần TV2/TV3)
python script/selfcheck_corruption.py

# 2. Entrypoint baseline
python script/run_phase1.py

# 3. Entrypoint corruption flow
python script/run_corruption_flow.py
```

**Kết quả mong đợi:** self-check pass toàn bộ; hai entrypoint import và chạy được, dừng lại đúng ở hàm chưa implement của thành viên khác với thông báo rõ ràng.

**Kết quả thực tế:**

Lệnh 1 — 12/12 PASS:

```text
corruption self-check
  [PASS] corruption log written
  [PASS] 6 scenarios logged (got 6)
  [PASS] every scenario touched at least one row
  [PASS] latest records dropped as logged
  [PASS] blank summaries present
  [PASS] noise reached text_for_embedding
  [PASS] titles truncated
  [PASS] stale rows push age_days past the threshold
  [PASS] duplicate rows added
  [PASS] baseline fixture itself is valid
  [PASS] corruption is deterministic across reruns
  [PASS] input dataframe was not mutated in place
All member 4 corruption checks passed.
```

Lệnh 2 — trước khi TV2 merge, pipeline dừng ngay bước 2:

```text
[1] Load raw records
    reusing snapshot ...\data\raw\crossref_records.json
    raw records: 24
[2] Clean records
  File "...\src\ingestion\cleaning.py", line 25, in build_clean_dataframe
    raise NotImplementedError("Student task: implement cleaning pipeline.")
```

Sau khi TV2 merge (`a1bec9d`), tôi chạy kiểm tra tích hợp trực tiếp trên clean data thật — bước 1–4 của baseline flow đã thông hoàn toàn và corruption chạy đúng trên dữ liệu thật:

```text
raw: 24 -> clean: 24
columns: ['paper_id','title','summary','authors','categories','primary_category','published',
          'updated','age_days','authors_joined','categories_joined','summary_chars',
          'abs_url','pdf_url','comment','text_for_embedding']
OK: clean dataframe passes my contract validation
OK: test set passes validation, cases = 24

corrupted rows: 24 -> 23
   drop_latest_records 3
   blank_summary 3
   noisy_summary 3
   truncated_title 3
   stale_published_date 4
   duplicate_rows 2
blank summaries: 3
dup rows: 2
max age_days: 1290 vs threshold 180
```

Đây là bằng chứng quan trọng nhất cho phần việc của tôi tính tới thời điểm này: contract clean schema khớp giữa TV2 và tôi mà **không bên nào phải sửa code**, và corruption tạo đúng tín hiệu mà observability cần bắt được — 3 summary rỗng (quality check sẽ fail), 2 dòng trùng (`paper_id` mất tính unique), và `age_days` tối đa 1290 ngày, vượt xa ngưỡng freshness 180 ngày.

Lệnh 3 — guard hoạt động đúng:

```text
RuntimeError: Phase 2 needs a successful baseline run first. Missing: clean dataset (...);
evaluation set (...); baseline metrics (...). Run: uv run python script/run_phase1.py
```

**Kiểm chứng bổ sung — dry run orchestration:** để xác minh phần orchestration của mình *trước khi* TV2/TV3 xong, tôi chạy một lần trọn vẹn cả 2 pha trong thư mục tạm, với **stub tạm thời** cho 6 hàm của TV2/TV3, ép judge dùng nhánh heuristic để không tiêu tốn API key. Kết quả: cả 2 pha chạy hết, sinh đủ 3 collection Chroma và toàn bộ artifact; `repair_verification` báo `rows_restored_by_repair: 3/3`, `duplicate_rows_in_repaired: 0`, `matches_baseline_ids: true`.

> **Số liệu của lần dry run này KHÔNG phải số liệu nộp bài** và không được dùng ở mục 8. Nó chạy trên cleaning/test set giả do tôi tự viết để test, không phải của TV2; thư mục tạm đã xóa sau khi chạy. Ý nghĩa duy nhất của nó là chứng minh code orchestration của tôi chạy thông và bảng so sánh 3 trạng thái in ra đúng định dạng.

**Artifact/log:** `script/selfcheck_corruption.py` (chạy lại được bất cứ lúc nào), và sau khi TV3 merge + pipeline chạy trọn vẹn, các artifact của tôi đã có đủ trong `data/`: `results/{baseline,corrupted,repaired}_metrics.json`, `results/*_answers.json`, `results/corruption_log.json`, `clean/papers_clean_{corrupted,repaired}.*`, `reports/corruption_report.md`. Không có secret trong bất kỳ log nào.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi corrupt cột `summary`/`title`/`published`, cột `text_for_embedding` phải được cập nhật theo — vì đây mới là cột thực sự đi vào Chroma. Nếu không cập nhật, corruption chỉ nằm ở cột hiển thị, retrieval không hề bị ảnh hưởng và cả thí nghiệm trở nên vô nghĩa. Nhưng **format của `text_for_embedding` là do Thành viên 2 quyết định**, và lúc tôi viết corruption thì `cleaning.py` vẫn còn `NotImplementedError` — tôi không biết format đó ra sao.

- **Các phương án đã cân nhắc:**
  1. **Tự dựng lại `text_for_embedding` từ đầu** theo format của riêng tôi. Đơn giản nhất, nhưng làm *toàn bộ* dòng trong corpus corrupted đổi format so với baseline. Khi đó metrics tụt xuống vì hai nguyên nhân trộn lẫn: nội dung hỏng, **và** format khác baseline. Không tách được biến, kết luận mất giá trị.
  2. **Import helper từ `cleaning.py` của TV2** để tái sử dụng đúng format. Sạch về lý thuyết, nhưng TV2 chưa viết, tôi không biết hàm sẽ tên gì hay nhận tham số kiểu gì — phải đoán chữ ký hàm, và tự tạo một phụ thuộc ngược từ corruption vào cleaning.
  3. **Vá tại chỗ bằng substring-replace**: tìm giá trị cũ (ví dụ nguyên văn summary cũ) bên trong `text_for_embedding` rồi thay bằng giá trị đã corrupt.

- **Phương án đã chọn:** phương án 3, kèm phương án 1 làm fallback khi không tìm thấy chuỗi cũ trong text (`_set_field()` → `_compose_embedding_text()`).

- **Lý do:** Substring-replace **không cần biết format**. Dù TV2 nối chuỗi kiểu gì, thêm nhãn `Authors:` hay `Title:` gì đi nữa, phần khung vẫn giữ nguyên tuyệt đối; chỉ đúng phần nội dung bị corrupt là thay đổi. Nhờ vậy biến duy nhất khác nhau giữa baseline và corrupted đúng là **chất lượng nội dung** — đó chính là biến mà bài lab muốn đo. Đổi lại là code phức tạp hơn một chút và cần nhánh fallback, nhưng cái giá đó rẻ so với việc mất tính hợp lệ của toàn bộ phép so sánh. Thêm một lợi ích phụ: corruption không còn phụ thuộc vào tiến độ của TV2, tôi làm và test được ngay.

- **Bằng chứng quyết định phù hợp:** assertion `noise reached text_for_embedding` trong self-check kiểm tra rằng khối nhiễu thực sự xuất hiện trong `text_for_embedding` chứ không chỉ trong cột `summary` — tức corruption chắc chắn chạm tới dữ liệu được embed. Trong lần dry run, `retrieval_hit_rate` tụt rõ rệt ở trạng thái corrupted, xác nhận cơ chế hoạt động đúng ý đồ.

## 6. Một lỗi hoặc blocker đã xử lý

### Lỗi đã xử lý xong

- **Triệu chứng/lỗi nguyên văn:**

```text
  [FAIL] stale rows push age_days past the threshold
  ...
  stale_published_date     rows=0
Some member 4 corruption checks failed.
```

- **Lệnh tái hiện:** `python script/selfcheck_corruption.py` (ở phiên bản corruption dùng số dòng cố định, fixture 12 dòng).

- **Nguyên nhân gốc:** Không phải lỗi ở logic ngày tháng như tên assertion gợi ý, mà là **cạn nguồn dòng để chọn**. Ban đầu tôi để số dòng cố định: drop 3, blank 3, noise 3, truncate 3, stale 4. Trên corpus thật 24 dòng thì vừa đủ. Nhưng fixture self-check chỉ có 12 dòng: drop 3 còn 9, rồi blank/noise/truncate lấy đúng 9 dòng cuối cùng. Vì `_pick_positions()` cố ý **không chọn lại dòng đã bị scenario khác đụng** (để log quy trách nhiệm được), scenario `stale_published_date` không còn dòng nào hợp lệ và lặng lẽ tác động 0 dòng. Nguy hiểm ở chỗ nó **không ném exception** — trên một corpus nhỏ, corruption sẽ thiếu hẳn một kịch bản mà không ai biết.

- **Cách xử lý:** Thay toàn bộ hằng số đếm cố định bằng **tỉ lệ theo kích thước corpus** (`DROP_LATEST_FRACTION = 0.12`, `BLANK_SUMMARY_FRACTION = 0.15`, `STALE_DATE_FRACTION = 0.20`, ...) qua hàm `_scaled_count(rows, fraction)` có `max(1, ...)` bảo đảm luôn ≥ 1 dòng. Tổng các scenario tác động tại chỗ chiếm khoảng 65% số dòng còn lại, vẫn chừa dòng sạch để đối chứng. Thêm assertion mới `every scenario touched at least one row` để lỗi dạng này không im lặng lần nữa.

- **Cách xác minh sau khi sửa:** Chạy lại self-check trên fixture 12 dòng → 12/12 PASS, `stale_published_date rows=2`. Chạy thêm trên fixture 24 dòng (bằng kích thước corpus Crossref thật) → volume đúng như thiết kế ban đầu: `3 / 3 / 3 / 3 / 4 / 2`, tổng 24 → 23 dòng. Tức bản sửa không làm thay đổi hành vi trên dữ liệu thật.

- **Điều học được:** Một corruption "thất bại im lặng" còn tệ hơn corruption ném lỗi, vì nó làm hỏng kết luận của cả bài lab mà không để lại dấu vết. Thứ hai: viết test trên fixture **nhỏ hơn** dữ liệu thật là cách rẻ tiền để lộ ra các giả định ngầm về kích thước dữ liệu.

### Blocker đã được giải quyết

> Cập nhật 2026-08-06: TV3 đã merge `quality.py` + `reporting.py`. Tôi đã `git pull` và chạy `run_phase1.py` → `run_corruption_flow.py` trọn vẹn, sinh đủ toàn bộ artifact. Mục 8 đã điền số thật. Phần dưới giữ lại nguyên bản để ghi nhận blocker *đã từng* chặn ở đâu và cách đã loại trừ nguyên nhân.

- **Phạm vi từng bị ảnh hưởng:** Toàn bộ artifact phải commit của tôi — `data/results/baseline_metrics.json`, `baseline_answers.json`, `corrupted_metrics.json`, `corrupted_answers.json`, `repaired_metrics.json`, `repaired_answers.json`, `corruption_log.json`, `data/clean/papers_clean_corrupted.*`, `papers_clean_repaired.*`, `data/reports/corruption_report.md`. Kéo theo mục 8 của báo cáo này chưa có số liệu.

- **Nguyên nhân:** Thành viên 1 (merge `72d68e9`) và Thành viên 2 (merge `a1bec9d`) đã xong. Tôi đã xác minh trực tiếp bằng dữ liệu thật rằng bước 1 (load raw), bước 2 (clean + validate schema) và bước 4 (validate test set) chạy thông; bước 3 (build index) và bước 5 (evaluate) chưa chạy nên chưa có bằng chứng. Điểm chặn chắc chắn là **bước 6**, nơi còn 4 hàm `NotImplementedError` của Thành viên 3:

| File | Hàm | Được gọi ở | Owner |
| --- | --- | --- | --- |
| `src/observability/quality.py:21` | `run_data_quality_checks` | phase1 bước 6; corruption_flow bước 3 và 6 | Thành viên 3 |
| `src/observability/quality.py:38` | `build_freshness_report` | phase1 bước 7; corruption_flow bước 3 và 6 | Thành viên 3 |
| `src/observability/reporting.py:21` | `generate_phase1_report` | phase1 bước 8 | Thành viên 3 |
| `src/observability/reporting.py:35` | `generate_corruption_report` | corruption_flow bước 7 | Thành viên 3 |

- **Những gì đã loại trừ:** Đã xác nhận blocker **không** nằm ở phần của tôi. Cụ thể: (1) môi trường và package cài đúng — `import pipelines.phase1` và `import pipelines.corruption_flow` đều thành công; (2) raw data của TV1 dùng được — đọc lại 24 records từ snapshot không lỗi; (3) contract với TV2 khớp — clean dataframe thật pass `_validate_clean_dataframe()`, test set thật pass `_validate_test_set()`, không bên nào phải sửa code; (4) logic corruption đúng cả trên fixture lẫn **trên clean data thật** — 12/12 self-check pass và 6/6 scenario kích hoạt đúng volume trên 24 dòng thật; (5) orchestration đúng — dry run với stub chạy hết cả 2 pha và sinh đủ artifact. Nói cách khác, chỉ cần 4 hàm trên có implementation là chạy được ngay, không cần sửa thêm gì trong 3 file của tôi.

- **Đã thực hiện:** Sau khi TV3 merge `quality.py` + `reporting.py`, đã `git pull` và chạy tuần tự `python script/run_phase1.py` → `python script/run_corruption_flow.py`. Pipeline chạy trọn vẹn, sinh đủ artifact; mục 8 đã điền số thật đọc từ các file `*_metrics.json`.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

`fetch_source_records()` gọi Crossref REST API với `source_query` và `source_filter` (lọc bài có abstract, xuất bản trong 180 ngày gần nhất), có retry/backoff cho `429`/`503`. Raw payload được **lưu trước khi parse** vào `data/raw/crossref_response.json` để còn truy vết khi parse sai. Sau đó parse thành `PaperRecord` với `paper_id` ưu tiên DOI (fallback slug từ title/URL), strip tag HTML trong abstract, chuẩn hóa authors/categories thành `list[str]`, rồi lưu `crossref_records.json`. Cleaning chuẩn hóa tiếp, tính `age_days`, ghép `text_for_embedding` và loại/dedupe record xấu. Cuối cùng `LocalEmbeddingIndex.build()` embed cột `text_for_embedding` bằng MiniLM-L6-v2 và nạp vào một collection ChromaDB (cosine), kèm metadata `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`. Mỗi trạng thái dùng **collection riêng** (`papers-baseline` / `papers-corrupted` / `papers-repaired`) nên 3 lần chạy không đè lên nhau.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Mỗi test case có `question`, `ground_truth` (đáp án chuẩn) và `ground_truth_doc_ids` (danh sách `paper_id` đáng lẽ phải được retrieve). Hai thứ này đo hai tầng khác nhau:

- `ground_truth_doc_ids` đo **tầng retrieval**: trong top-k document trả về, có cái nào nằm trong danh sách đúng không → `retrieval_hit_rate`. Đây là Hit Rate@4, chỉ cần trúng 1 trong 4.
- `ground_truth` đo **tầng câu trả lời**: `mean_token_f1` so độ trùng từ (theo set, bỏ qua thứ tự và không hiểu ngữ nghĩa), còn `judge_accuracy` / `mean_judge_score` để LLM chấm 1–5 điểm kèm cờ `correct`, bù đúng điểm yếu ngữ nghĩa của token F1.

Tách hai tầng như vậy mới chẩn đoán được: hit rate tụt nghĩa là hỏng ở tìm kiếm; hit rate giữ nguyên mà F1 tụt nghĩa là tìm đúng tài liệu nhưng nội dung/metadata trong tài liệu đó đã hỏng.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks đo **tính đúng đắn cấu trúc** của dataset tại thời điểm hiện tại: số dòng > 0, `paper_id` không null và unique, `title`/`summary`/`text_for_embedding` không rỗng quá nhiều, không có dòng trùng. Kết quả là pass/fail.

Freshness monitoring đo **chiều thời gian**: dữ liệu có còn mới không, dựa trên `age_days` so với `freshness_threshold_days = 180`, báo cáo `latest_published`, `oldest_published`, `stale_rows`, `is_fresh`.

Khác biệt cốt lõi: một dataset có thể **pass toàn bộ quality checks mà vẫn vô dụng** vì toàn bài cũ 3 năm — không thiếu trường nào, không trùng, chỉ là đã lỗi thời. Đó chính xác là điều scenario `stale_published_date` của tôi tạo ra: cấu trúc vẫn hoàn hảo, chỉ freshness bắt được. Ngược lại `duplicate_rows` và `blank_summary` thì quality checks bắt được còn freshness không thấy gì. Phải có **cả hai** mới phủ hết.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì đây là thiết kế thí nghiệm có đối chứng: muốn quy sự thay đổi của metrics cho **chất lượng dữ liệu**, thì mọi biến khác phải giữ nguyên — cùng bộ câu hỏi, cùng ground truth, cùng `top_k`, cùng embedding model, cùng cách chấm. Nếu sinh test set mới cho corpus corrupted thì câu hỏi sẽ được sinh **từ chính dữ liệu đã hỏng**, ground truth cũng hỏng theo, và metrics có thể trông vẫn đẹp trong khi corpus đã nát — đo sai hoàn toàn. Ngoài ra, các record bị `drop_latest_records` xóa vẫn phải nằm trong test set thì mới lộ ra chúng đã biến mất. Code của tôi vì vậy đọc đúng một file `settings.paths.eval_testset` cho cả 3 lần `evaluate_pipeline()`, và không bao giờ regenerate test set trong `corruption_flow.py`.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Ba lớp bằng chứng, theo thứ tự từ cứng đến mềm:

- **Cấp dataset** — khối `repair_verification` trong `corruption_log.json`: `rows_restored_by_repair` phải bằng `rows_lost_by_corruption`, `duplicate_rows_in_repaired` phải bằng 0, `matches_baseline_ids` phải là `true`.
- **Cấp observability** — `data/quality/quality_repaired.json` pass trở lại các check đã fail ở trạng thái corrupted, và `freshness_report_repaired.json` có `is_fresh` quay về trạng thái baseline.
- **Cấp agent** — `repaired_metrics.json` có `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` quay về xấp xỉ `baseline_metrics.json`.

Quan trọng: repair phải được **dựng lại từ `data/raw/crossref_records.json`** qua đúng đường `load_raw_records()` → `build_clean_dataframe()`, chứ không phải vá tay dataset corrupted. Nếu sửa tay thì việc metrics phục hồi chẳng chứng minh được gì về khả năng phục hồi của pipeline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.750 | 1.000 | Corrupted mất/nhiễu doc nên retrieval trượt 25%; repair về đúng baseline |
| `mean_token_f1` | 1.000 | 0.709 | 1.000 | Summary hỏng kéo answer lệch ground_truth |
| `judge_accuracy` | 1.000 | 0.667 | 1.000 | LLM judge (gpt-4o-mini) xác nhận chất lượng giảm rồi phục hồi |
| `mean_judge_score` | 5.000 | 3.833 | 5.000 | Điểm judge giảm hơn 1 điểm khi corrupted |
| Quality checks | 9/9 | 6/9 | 9/9 | Fail đúng uniqueness + duplicate + freshness |
| Freshness status | fresh | stale (5) | fresh | 5 dòng vượt ngưỡng 180 ngày ở corrupted |

> Bảng trên đã được điền bằng số đọc trực tiếp từ `data/results/{baseline,corrupted,repaired}_metrics.json` và `data/quality/*.json` sau khi TV3 merge và pipeline chạy trọn vẹn cả hai pha (baseline + corruption flow) với LLM judge thật qua OpenRouter. Đây là artifact nộp bài thực tế, không phải số dry run ở mục 4.

Bên cạnh metrics ở cấp agent (bảng trên), các **tín hiệu ở cấp dataset** cũng khớp — đây chính là những tín hiệu mà quality checks và freshness monitoring của TV3 đã bắt được đúng:

| Tín hiệu ở cấp dataset | Baseline | Corrupted | Ý nghĩa |
| --- | ---: | ---: | --- |
| Số dòng | 24 | 23 | Mất 3 record mới nhất, thêm 2 bản sao |
| `paper_id` unique | Có | Không | 2 dòng trùng → quality check phải fail |
| Số summary rỗng | 0 | 3 | Document mất nội dung embed |
| `age_days` lớn nhất | 175 | 1290 | Vượt ngưỡng freshness 180 ngày |
| Số dòng stale (`age_days` > 180) | 0 | 5 | Freshness monitor phải chuyển sang `is_fresh = false` |

Ghi chú về con số 5: scenario `stale_published_date` chỉ tác động 4 dòng, nhưng scenario `duplicate_rows` chạy sau đó nhân bản trúng một trong các dòng đã stale, nên bản sao cũng mang `age_days` cũ. Đây là hành vi đúng chứ không phải lỗi — retry của pipeline thật nhân bản bất kỳ dòng nào nó đang xử lý, kể cả dòng đã hỏng — và `corruption_log.json` vẫn ghi riêng `paper_ids` của từng scenario nên vẫn quy trách nhiệm được. Tôi nêu ra đây vì nếu chỉ cộng số dòng của từng scenario trong log rồi suy ra tổng thì sẽ ra 4 và lệch với artifact thật.

### Kết luận từ số liệu

Số thật đã có sau khi pipeline chạy trọn vẹn. Cơ chế dự kiến tôi rút ra từ việc đọc `qa.py`, `metrics.py`, `index.py` đã được **số aggregate xác nhận**:

1. `blank_summary` + `noisy_summary` → `text_for_embedding` mất nội dung hoặc bị nhiễu kéo lệch vector; đồng thời `corrupted.json` fail check summary/duplicate → `retrieval_hit_rate` giảm 0.25, và vì `answer_question()` lấy câu trả lời từ `first_sentence(summary)` của document top-1 nên `mean_token_f1` giảm 0.29, kéo `judge_accuracy` xuống 0.667. Khớp với `data/results/corrupted_metrics.json`.
2. Repair dựng lại từ raw → `repair_verification` xác nhận `rows_restored_by_repair: 3/3`, `duplicate_rows_in_repaired: 0`, `matches_baseline_ids: true`; quality checks pass lại 9/9, freshness về fresh → cả 4 metric agent quay về đúng baseline (delta +0.000). Khớp với `data/results/repaired_metrics.json`.

**Corruption nào ảnh hưởng rõ nhất và vì sao?** Dự đoán của tôi: `drop_latest_records` gây thiệt hại **cứng nhất** — record đã không còn trong corpus thì không cách nào retrieve ra, mọi test case trỏ tới nó chắc chắn hit = 0, không có đường cứu vãn nào ở tầng dưới. `blank_summary` gây thiệt hại **rộng nhất** vì nó đánh đồng thời cả hai tầng: vector rỗng làm hỏng retrieval, và `first_sentence("")` rỗng đẩy `token_f1` về đúng 0.0 theo nhánh guard trong `_token_f1()`. Ngược lại `stale_published_date` có lẽ **ít ảnh hưởng tới metrics agent nhất** — nó chỉ làm sai câu trả lời cho các câu hỏi dạng "when was..." — nhưng lại là scenario duy nhất mà **chỉ freshness monitoring bắt được**, nên nó có giá trị chứng minh riêng cho mục observability. Sẽ kiểm chứng bằng cách đọc `corrupted_answers.json`, đối chiếu `retrieval_hit` và `token_f1` của từng câu với danh sách `paper_ids` theo từng scenario trong `corruption_log.json`.

**Kết quả nào khác với kỳ vọng ban đầu?** Số aggregate đã có, nhưng vì cả 6 scenario chạy đồng thời nên chưa tách được đóng góp riêng của từng loại — giả thuyết dưới đây vẫn cần chạy per-scenario (mục 9) mới kiểm chứng được. Giả thuyết tôi muốn kiểm tra: `truncated_title` có thể ảnh hưởng **ít hơn** tôi tưởng, vì `answer_question()` khi không tra được exact title vẫn rơi về semantic search, mà semantic search chủ yếu dựa vào summary — vốn còn nguyên ở những dòng chỉ bị cắt title (do các scenario không chọn trùng dòng). Nếu đúng vậy thì đó là một ví dụ hay về việc pipeline có đường lui làm giảm nhẹ tác động của một loại lỗi dữ liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Lưu raw artifact trước khi transform không phải thủ tục hình thức — nó chính là thứ khiến repair trở nên khả thi. Toàn bộ bước repair của tôi chỉ hoạt động được vì `data/raw/crossref_records.json` còn nguyên vẹn và bất biến; nếu pipeline chỉ giữ dữ liệu đã clean thì khi clean data hỏng, không còn gì để dựng lại và sự cố trở thành mất dữ liệu vĩnh viễn.

2. **Về data quality/observability:** Quality checks và freshness monitoring bắt hai loại lỗi **không giao nhau**, nên thiếu một cái là có một lớp lỗi lọt lưới hoàn toàn. Corpus toàn bài 3 năm tuổi pass sạch mọi structural check nhưng vô dụng với người dùng. Bài học rộng hơn: một hệ thống chỉ "khỏe mạnh" theo đúng những chiều mà ta chọn đo.

3. **Về ảnh hưởng của data đến RAG agent:** Lỗi dữ liệu không làm agent báo lỗi — nó làm agent **tự tin trả lời sai**. Không có exception, không có stack trace, `retrieval_hit_rate` vẫn là một con số trông bình thường. Đó là lý do bài lab bắt buộc phải đo bằng cùng một test set trên cả ba trạng thái: không có đối chứng thì không cách nào phát hiện chất lượng đã tụt.

### Nếu có thêm thời gian

Tôi muốn **tách riêng tác động của từng scenario** thay vì chạy cả 6 cùng lúc: chạy 6 lần corruption, mỗi lần bật đúng một scenario trên cùng baseline và cùng test set, thu 6 bộ metrics. Cách đo cải thiện: với mỗi scenario tính `delta_hit_rate` và `delta_token_f1` so với baseline, xếp hạng để biết loại lỗi dữ liệu nào đắt giá nhất. Hiện tại vì cả 6 scenario chạy đồng thời nên chỉ kết luận được "corruption làm metrics tụt", chưa định lượng được đóng góp của từng loại — mà đây mới là thông tin có ích thật khi phải quyết định đặt data quality check ở đâu trước. Kiến trúc hiện tại đã sẵn sàng cho việc này: các hàm scenario đã tách rời và `corruption_log.json` đã ghi `paper_ids` riêng cho từng cái, chỉ cần thêm một tham số chọn scenario.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Minh Phúc
**Ngày xác nhận:** 2026-08-06
