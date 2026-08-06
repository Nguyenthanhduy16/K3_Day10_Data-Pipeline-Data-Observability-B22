# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                              |
| --------------- | ------------------------------------------------------------------------------------- |
| Họ và tên       | Thạch Minh Quân                                                                       |
| MSSV            | 2A202601585                                                                           |
| Khóa/Lớp        | K3                                                                                    |
| Tên nhóm        | B22                                                                                   |
| Vai trò chính   | Data Model & Eval Set Owner                                                           |
| Repository      | https://github.com/Nguyenthanhduy16/K3_Day10_Data-Pipeline-Data-Observability-B22.git |
| Ngày hoàn thành | 2026-08-06                                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable      | File/hàm phụ trách                                                                        | Input nhận vào                                                    | Output bàn giao                                              | Trạng thái  |
| ----------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------ | ----------- |
| Cleaning & clean schema | `src/ingestion/cleaning.py` — `build_clean_dataframe(records, run_date)`                  | `data/raw/crossref_records.json` (24 `PaperRecord`, từ Thành viên 1) | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 dòng × 16 cột) | Hoàn thành |
| Evaluation set          | `src/evaluation/testset.py` — `build_test_set(df, output_path)`                           | `data/clean/papers_clean.json`                                    | `data/eval/test_set.json` (24 sample / 8 paper)              | Hoàn thành |
| Helper cho downstream   | `cleaning.py` — `build_embedding_text`, `refresh_derived_fields`, `load_clean_dataframe` | Clean dataframe / artifact trên đĩa                               | 3 hàm public để Thành viên 3-4 tái dùng schema                | Hoàn thành |

Tôi không sở hữu và không sửa `src/ingestion/crossref.py`, `src/retrieval/`, `src/observability/`, `src/pipelines/`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ | Kết quả                                                                                                                                                                    |
| ------------------------------------------------------ | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kiểm tra điều kiện bàn giao mốc 1 trước khi nhận việc | Thành viên 1 / `crossref.py`  | Xác nhận đạt cả 6 điều kiện; phát hiện `categories` rỗng 24/24 và truy được nguyên nhân                                                                                     |
| Chẩn đoán nguyên nhân `categories` rỗng                | Thành viên 1 / `crossref.py`  | Chạy 4 phép thử API, chứng minh là giới hạn nguồn chứ không phải lỗi parse; đề xuất fallback `container-title` (đã xác nhận trường này có dữ liệu). Không tự sửa file người khác |
| Bọc rủi ro schema khi reload artifact                  | Thành viên 3-4                | Viết `load_clean_dataframe()` để chặn lỗi `NaN` mô tả ở mục 6                                                                                                              |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                        | File/hàm/artifact liên quan                                 | Kết quả bàn giao                                                                       | Cách xác minh                                                     |
| -------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Làm sạch 24 raw record thành clean dataset                      | `src/ingestion/cleaning.py`, `data/clean/papers_clean.*`     | 24/24 dòng giữ lại, 16 cột, `paper_id` unique                                          | Lệnh L1 mục 4                                                       |
| Strip thẻ XML/HTML khỏi title và summary                        | `_clean_text()`                                             | Title `Hi‐ <scp>RAG</scp> : A Hierarchical…` → `Hi-RAG: A Hierarchical…`               | So sánh `data/raw/crossref_records.json` với `papers_clean.json`     |
| Bỏ nhãn `Abstract`/`Background.` còn sót trong abstract        | `_strip_leading_label()`                                    | 9/24 summary có tiền tố, sau clean còn 0                                                | `first_sentence()` của mọi summary đều ≥ 100 ký tự, không nhãn      |
| Tính `published` chuẩn ISO và `age_days`                        | `_parse_date()`, `_age_days()`                              | `age_days` kiểu int, khoảng 5-175 ngày                                                  | Lệnh L4 mục 4                                                       |
| Tạo `text_for_embedding` theo format quy định                   | `build_embedding_text()`                                    | 24/24 khớp `Title: … \| Authors: … \| Summary: …`                                        | Lệnh L4 mục 4                                                       |
| Sinh evaluation set đóng băng                                   | `src/evaluation/testset.py`, `data/eval/test_set.json`      | 24 sample / 8 paper / 3 loại (summary 8, authors 8, date 8)                              | Lệnh L2, L3 mục 4                                                   |

Một output cụ thể phần việc của tôi tạo ra:

`data/eval/test_set.json` — bộ 24 câu hỏi đóng băng, mỗi câu có `ground_truth` trích trực tiếp từ đúng cột của clean data mà `retrieval/qa.py` đọc để trả lời. Đây là artifact mà cả ba trạng thái baseline, corrupted, repaired sẽ dùng chung, nên nếu nó sai lệch thì toàn bộ phép so sánh của bài lab mất ý nghĩa. Tôi đã xác minh 100% `ground_truth_doc_ids` tồn tại trong clean data và 100% title trong ngoặc đơn resolve được qua `index.lookup()`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi nằm giữa raw ingestion và vector index, giải quyết hai việc:

1. **Dữ liệu Crossref không dùng trực tiếp được.** Abstract chứa thẻ XML JATS và tiền tố `Abstract`/`Background.`, title còn sót `<scp>`, ngày tháng ở dạng `date-parts` lồng nhau, tác giả là list dict. Nếu đưa thẳng vào embedding thì rác đi vào vector và metadata.
2. **Cần một thước đo cố định.** Bài lab so sánh 3 trạng thái hệ thống, nên cần bộ câu hỏi + đáp án chuẩn không đổi giữa các lần chạy. Nếu test set sinh ngẫu nhiên hoặc đáp án không khớp cách agent trả lời, metric sẽ dao động vì lý do không liên quan đến chất lượng dữ liệu.

### Cách triển khai

**Cleaning** áp 6 quy tắc theo thứ tự: (1) loại record không có title hoặc summary dưới 100 ký tự, đồng thời loại record thiếu `paper_id` hoặc ngày không parse được vì cả bài lab khóa trên document identity và freshness; (2) strip thẻ `<[^>]+>` và HTML entity khỏi title lẫn summary, gỡ nhãn section; (3) chuẩn hóa `authors`/`categories` thành `list[str]` đã khử trùng lặp rồi nối bằng dấu phẩy; (4) đưa `published` về `YYYY-MM-DD` và tính `age_days` so với `run_date`; (5) ghép `text_for_embedding`; (6) khử trùng lặp theo `paper_id` **và** theo title rồi sort mới nhất trước để thứ tự luôn tất định.

Chi tiết đáng nói ở bước gỡ nhãn: tôi chỉ gỡ khi từ đó thực sự đóng vai trò nhãn — tức theo sau là dấu câu, hoặc từ kế tiếp viết hoa mở câu mới. Nhờ vậy `Background. Insurance penetration…` bị gỡ thành `Insurance penetration…`, nhưng một câu bắt đầu bằng `Methods for tuning retrievers…` thì giữ nguyên. Nếu gỡ vô điều kiện sẽ cắt mất nội dung thật.

**Test set** được thiết kế bám theo bảng định tuyến trong `retrieval/qa.py`. Hàm `_extract_answer` ở đó chọn trường trả lời bằng cách quét cụm từ trong câu hỏi: `who authored` → `authors_joined`, `when was` → `published`, `what categories` → `categories_joined`, còn lại → `first_sentence(summary)`. Vì vậy tôi lấy `ground_truth` từ đúng trường tương ứng, và thêm hàm `_assert_routing()` fail-fast: nếu ai sửa template làm câu hỏi định tuyến sai loại, hàm ném lỗi ngay thay vì để metric tụt một cách khó hiểu. Tôi cũng loại các paper có dấu nháy đơn trong title (sẽ phá regex `'<title>'`) hoặc title chứa chính các cụm định tuyến (sẽ cướp định tuyến của câu hỏi). Paper được chọn theo bước đều trên dataframe đã sort, hoàn toàn tất định.

Loại câu hỏi `categories` đã được cài sẵn nhưng sinh ra 0 sample, vì nguồn không có dữ liệu (xem mục 2 và 6). Code tự động sinh loại này ngay khi `categories` có nội dung.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `list[PaperRecord]` đọc từ `data/raw/crossref_records.json` + `run_date: datetime`                                                                                                                                    |
| Output                  | `pd.DataFrame` 16 cột: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `abs_url`, `pdf_url`, `comment`, `text_for_embedding`; và `list[dict]` test set 5 khóa |
| Module phụ thuộc        | `ingestion/crossref.py` (`PaperRecord`), `core/utils.py`, `core/config.py` (`settings.paths`)                                                                                                                          |
| Module sử dụng output   | `retrieval/index.py` (đọc 9 cột dựng metadata Chroma), `evaluation/metrics.py` (đọc test set), `observability/quality.py` (đọc `age_days`, `summary_chars`), `pipelines/phase1.py`, `pipelines/corruption_flow.py`     |
| Điều kiện lỗi cần xử lý | Abstract có thẻ XML; title có markup; `subject` rỗng nên `categories` là list rỗng; ngày thiếu hoặc sai format; `paper_id` trùng; title trùng khác DOI; chuỗi rỗng biến thành `NaN` khi round-trip qua CSV               |

### Cách xác minh

```bash
# L1 - clean dataset: so dong, paper_id unique, danh sach cot
python -c "import pandas as pd; df=pd.read_csv('data/clean/papers_clean.csv'); print(len(df), df['paper_id'].is_unique, df.columns.tolist()[:8])"

# L2 - test set: so sample, schema keys, phan bo loai cau hoi
python -c "import json;from collections import Counter;s=json.load(open('data/eval/test_set.json',encoding='utf-8'));print(len(s));print(sorted(s[0].keys()));print(dict(Counter(x['question_type'] for x in s)))"

# L3 - ground truth toan ven
python -c "import json,pandas as pd;s=json.load(open('data/eval/test_set.json',encoding='utf-8'));ids=set(pd.read_csv('data/clean/papers_clean.csv')['paper_id']);print(all(set(x['ground_truth_doc_ids'])<=ids for x in s), all(x['ground_truth'].strip() for x in s))"

# L4 - quy tac cleaning
python -c "import pandas as pd;df=pd.read_csv('data/clean/papers_clean.csv');print((df['summary'].str.len()>=100).all(), df['text_for_embedding'].str.match(r'^Title: .* \| Authors: .* \| Summary: ').all(), int(df['age_days'].min()), int(df['age_days'].max()))"
```

- **Kết quả mong đợi:** 24 dòng clean, `paper_id` unique; 24 sample đúng 5 khóa schema; mọi `ground_truth_doc_ids` tồn tại trong clean data; mọi summary ≥ 100 ký tự và `text_for_embedding` đúng format 3 phần.
- **Kết quả thực tế:** L1 → `24 True [...]`. L2 → `24`, keys `['ground_truth','ground_truth_doc_ids','id','question','question_type']`, `{'summary': 8, 'authors': 8, 'date': 8}`. L3 → `True True`. L4 → `True True 5 175`.
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`. Commit `66ac37e`, merge `a1bec9d` (PR #2).

Ngoài 4 lệnh trên, tôi còn dựng một index MiniLM + ChromaDB tạm **ngoài repo** (thư mục scratch, không ghi vào `data/chroma` vì đó là artifact mốc 5 của Thành viên 4) để chạy thử toàn bộ 24 câu hỏi qua `retrieval/qa.py`. Kết quả đo được ở mục 8.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `ground_truth` của mỗi câu hỏi lấy từ đâu? Đây là quyết định gốc rễ vì nó định nghĩa "đúng" nghĩa là gì cho cả ba trạng thái so sánh.
- **Các phương án đã cân nhắc:**
  1. Dùng LLM sinh câu hỏi và đáp án tự do từ abstract — tự nhiên, giống người dùng thật.
  2. Trích đáp án tất định từ đúng trường clean data mà `retrieval/qa.py` sẽ đọc để trả lời.
  3. Viết đáp án tay cho từng paper.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Phương án 1 đưa tính ngẫu nhiên của LLM vào chính cây thước đo — mỗi lần sinh lại được đáp án khác, và `token_f1` sẽ dao động vì cách diễn đạt chứ không phải vì chất lượng dữ liệu, làm hỏng mục tiêu so sánh baseline/corrupted/repaired. Nó cũng tốn API call và cần key ngay từ bước tạo test set. Phương án 3 không scale và không tái lập được. Phương án 2 cho thước đo tất định: khi retrieval đúng thì `token_f1` bằng đúng 1.0, nên mọi mức sụt sau này **chắc chắn** do dữ liệu hỏng chứ không do nhiễu đo. Chi phí là câu hỏi kém tự nhiên hơn, tôi chấp nhận đánh đổi đó vì bài lab đo tác động của data quality chứ không đo khả năng hội thoại.
- **Bằng chứng quyết định phù hợp:** Chạy 24 câu hỏi qua index thật với retrieval đúng: `mean_token_f1 = 1.0000` đều ở cả ba loại (summary 8, authors 8, date 8 câu). Nghĩa là sàn đo sạch, không có nhiễu nền.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Script kiểm tra của tôi báo `[FAIL] no NaN in index metadata columns - Chroma metadata rejects null values`. Clean dataframe trong bộ nhớ hoàn toàn sạch, nhưng sau khi ghi CSV rồi đọc lại thì cột `categories_joined` (rỗng ở cả 24 dòng) và `pdf_url` (rỗng ở 15 dòng) trở thành `NaN`.
- **Lệnh hoặc bước tái hiện:** `python -c "import pandas as pd; df=pd.read_csv('data/clean/papers_clean.csv'); print(df['categories_joined'].isna().sum())"` → trả về `24`.
- **Nguyên nhân gốc:** `pd.read_csv` mặc định coi ô rỗng là giá trị thiếu và chuyển thành `NaN`. Trong khi đó `LocalEmbeddingIndex._build_documents` ở `retrieval/index.py` đọc thẳng các cột này vào metadata của Chroma, và `qa.py::_extract_answer` trả về `metadata["categories_joined"]` cho câu hỏi loại categories. Hệ quả: agent sẽ trả lời chuỗi `nan`. Lỗi không lộ ra ở `phase1.py` vì pipeline đó dùng dataframe trong bộ nhớ, nhưng `corruption_flow.py` **load lại clean dataset từ đĩa** nên sẽ dính.
- **Cách xử lý:** Vì tôi sở hữu clean schema, tôi thêm `load_clean_dataframe(path)` vào `cleaning.py`: đọc CSV với `keep_default_na=False, na_values=[]`, khôi phục `authors`/`categories` từ dạng chuỗi về `list[str]`, ép các cột text về `str` và `age_days`/`summary_chars` về `int`. Hàm nhận cả `.csv` lẫn `.json`. Tôi đã báo Thành viên 3 và 4 dùng hàm này thay cho `pd.read_csv` trực tiếp.
- **Cách xác minh sau khi sửa:** Chạy lại bộ kiểm tra → `[PASS] no NaN in index metadata columns`, và toàn bộ 25 check chuyển sang `ALL CHECKS PASSED`. Sau đó dựng index thật và chạy 24 câu hỏi, không câu nào trả về `nan`.
- **Điều học được:** Một schema chỉ đúng khi nó đúng **qua vòng serialize**. Dataframe sạch trong bộ nhớ không đảm bảo artifact trên đĩa cũng sạch, và lỗi loại này chỉ lộ ra ở module của người khác, muộn hơn nhiều. Người sở hữu schema nên bàn giao kèm hàm đọc lại, chứ không chỉ bàn giao file.

**Blocker chưa xử lý xong:**

- **Phạm vi bị ảnh hưởng:** `categories`, `primary_category`, `categories_joined` rỗng ở cả 24 record, nên loại câu hỏi `categories` mà `Guide.md` Bước 5 yêu cầu sinh ra 0 sample. Test set còn 3 loại thay vì 4.
- **Những gì đã loại trừ:** (1) Không phải lỗi parse của Thành viên 1 — code map `item.get("subject", [])` là đúng. (2) Không phải do tham số `select` lược field: fetch lại **bỏ hẳn** `select` vẫn cho 0/24 item có key `subject`. (3) Không phải do filter ngày: query rộng hơn không filter vẫn cho 0/20 item có `subject` khác rỗng. (4) Gọi endpoint một work cụ thể thì `subject` **có tồn tại** nhưng giá trị là `[]`. Kết luận: Crossref thực sự không có dữ liệu subject cho nhóm work này.
- **Bước tiếp theo:** Sửa nằm trong `src/ingestion/crossref.py` thuộc Thành viên 1, tôi không tự sửa file người khác. Đề xuất: thêm `container-title` vào `select` và map thành `categories` — tôi đã xác nhận trường này **có** dữ liệu (ví dụ `['Innovative economy: information, analytics, forecasts']`). Khi raw records có `categories`, test set tự động sinh thêm loại thứ tư mà không cần sửa `testset.py`.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?** `fetch_source_records()` gọi Crossref REST API với `source_query` và `source_filter` (lọc bài trong 180 ngày và có abstract), lưu nguyên payload vào `data/raw/crossref_response.json` trước khi parse — đây là bản gốc để truy vết và để repair sau này. Payload được parse thành `PaperRecord` với `paper_id` lấy từ DOI, lưu tiếp vào `crossref_records.json`. `build_clean_dataframe()` của tôi biến list đó thành dataframe đã chuẩn hóa, trong đó `text_for_embedding` là chuỗi duy nhất sẽ được embed. `LocalEmbeddingIndex.build()` chạy `all-MiniLM-L6-v2` trên cột đó, đẩy vector vào collection ChromaDB với metadata gồm `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, URL. Mấu chốt xuyên suốt là `paper_id` giữ nguyên từ raw → clean → index → eval, nhờ đó mới đối chiếu được retrieval có trúng tài liệu hay không.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Đây là hai phép đo tách biệt trên cùng một câu hỏi. `ground_truth_doc_ids` đo **retrieval**: `evaluate_pipeline` lấy danh sách `paper_id` mà index trả về và kiểm tra có giao với tập ID đúng không — trúng thì tính 1, tạo ra `retrieval_hit_rate`. `ground_truth` đo **answer**: so chuỗi agent trả lời với đáp án chuẩn bằng `token_f1`, đồng thời gửi cho LLM judge chấm `score` 1-5 và `correct`, tạo ra `mean_token_f1`, `judge_accuracy`, `mean_judge_score`. Tách hai tầng như vậy cho phép phân biệt "tìm sai tài liệu" với "tìm đúng tài liệu nhưng trả lời sai".

**3. Quality checks khác freshness monitoring ở điểm nào?** Quality checks nhìn vào **tính toàn vẹn nội tại** của dataset tại một thời điểm: số dòng > 0, `paper_id` không null và unique, `title`/`summary`/`text_for_embedding` không rỗng quá nhiều, không có dòng trùng. Nó trả lời "dữ liệu có tự mâu thuẫn không". Freshness monitoring nhìn vào **quan hệ giữa dữ liệu và thời gian hiện tại**: dựa trên `age_days` so với `freshness_threshold_days` (180), đếm số dòng quá hạn, tìm ngày mới nhất/cũ nhất. Nó trả lời "dữ liệu có còn phản ánh thực tế không". Một dataset có thể pass toàn bộ quality checks mà vẫn stale — mọi trường đầy đủ, không trùng lặp, nhưng toàn bài cũ 2 năm. Đúng kịch bản corruption "làm stale publication date" nhắm vào: quality vẫn xanh, chỉ freshness đỏ.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì đây là thí nghiệm có đối chứng, chỉ được phép thay đổi **một** biến là chất lượng dữ liệu. Nếu mỗi trạng thái sinh test set riêng thì chênh lệch metric không quy được về nguyên nhân nào: có thể do dữ liệu hỏng, mà cũng có thể do bộ câu hỏi mới dễ hơn hoặc khó hơn. Ngoài ra corrupted dataset đã bị xóa bớt record, nên test set sinh từ nó sẽ không còn câu hỏi về những paper bị xóa — tức là tự che đi đúng thiệt hại cần đo. Vì vậy test set phải đóng băng từ baseline; `settings.refresh_test_set` mặc định tắt chính là để tránh sinh lại ngoài ý muốn. Cũng vì lý do đó, `top_k` phải giữ nguyên giữa ba lần chạy.

**5. Repair được xem là thành công dựa trên artifact và metric nào?** Không chỉ nhìn "chạy xong không lỗi". Cần đối chiếu ba nhóm bằng chứng trên cùng test set: (a) **agent metrics** trong `data/results/repaired_metrics.json` — `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` phải quay về xấp xỉ `baseline_metrics.json` chứ không chỉ nhích hơn `corrupted_metrics.json`; (b) **quality/freshness signals** trong `data/quality/` phải chuyển từ fail về pass, cụ thể là hết dòng trùng, hết summary rỗng, số dòng stale về 0; (c) **lineage** — dataset repaired phải được dựng lại từ `data/raw/crossref_records.json` và `corruption_log.json`, không phải sửa tay file corrupted, thể hiện qua số dòng khôi phục khớp với số record đã bị xóa trong log. Nếu metrics hồi phục mà quality vẫn fail, hoặc ngược lại, thì repair chưa thành công.

## 8. Phân tích kết quả

### Metrics chính

Tại thời điểm nộp báo cáo cá nhân này, **ba trạng thái chưa được chạy đầy đủ**, nên tôi không điền số cho corrupted và repaired. Kiểm chứng: `data/results/`, `data/embeddings/`, `data/reports/` đều còn rỗng, và `src/observability/quality.py`, `src/observability/reporting.py` vẫn còn `NotImplementedError` nên `phase1.py` chưa chạy hết được. Điền số vào đây lúc này sẽ là bịa.

| Metric/signal        |                                    Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                                                              |
| -------------------- | -------------------------------------------: | ---------: | --------: | ----------------------------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` | chưa có artifact chính thức (đo tại chỗ: 1.0000) | chưa chạy | chưa chạy | Sàn đo sạch. `qa.py` có bước lookup chính xác theo title nên baseline đạt trần; corruption cắt ngắn title và xóa record sẽ phá bước này |
| `mean_token_f1`      | chưa có artifact chính thức (đo tại chỗ: 1.0000) | chưa chạy | chưa chạy | Bằng đúng 1.0 nhờ `ground_truth` trích từ chính trường mà `qa.py` trả lời, nên mọi mức sụt sau này quy được về dữ liệu hỏng           |
| `judge_accuracy`     |                                    chưa chạy | chưa chạy | chưa chạy | Cần LLM provider; thuộc bước của Thành viên 4                                                                                        |
| `mean_judge_score`   |                                    chưa chạy | chưa chạy | chưa chạy | Như trên                                                                                                                             |
| Quality checks       |                                    chưa chạy | chưa chạy | chưa chạy | `quality.py` của Thành viên 3 chưa implement. Dữ liệu đầu vào của nó đã sẵn sàng: `paper_id` unique, không cột rỗng                   |
| Freshness status     |                                    chưa chạy | chưa chạy | chưa chạy | Clean data hiện có `age_days` từ 5 đến 175 ngày, đều dưới ngưỡng 180 nên baseline dự kiến `is_fresh = true`                           |

Số "đo tại chỗ" ở trên là kết quả tôi tự chạy trên index MiniLM + ChromaDB dựng tạm ngoài repo để kiểm tra bàn giao, **không phải** nội dung của `data/results/baseline_metrics.json`. Chi tiết:

| Phép đo tại chỗ (24 câu hỏi, `top_k=4`) | Kết quả |
| ---------------------------------------- | --------- |
| `retrieval_hit_rate` qua `qa.answer_question` | 1.0000 |
| `mean_token_f1` (summary / authors / date) | 1.0000 / 1.0000 / 1.0000 |
| Vector search thuần, độ chính xác top-1     | 0.8750 |
| Vector search thuần, tỉ lệ trúng trong top-4 | 1.0000 |

Hai dòng cuối là phép đo tôi thấy quan trọng nhất: chúng bỏ qua bước lookup chính xác theo title của `qa.py` để xem embedding tự nó mạnh đến đâu. Kết quả 0.8750 top-1 cho thấy corpus thực sự retrieve được bằng ngữ nghĩa, nên khi corruption phá title thì hệ thống sẽ suy giảm ở mức đo được chứ không sập thẳng về 0 — nghĩa là thí nghiệm sẽ cho tín hiệu có độ phân giải tốt.

### Kết luận từ số liệu

Hai chuỗi nguyên nhân–bằng chứng dưới đây tôi viết ở dạng **giả thuyết cần kiểm chứng**, vì chưa có số liệu corrupted/repaired:

1. [Xóa các record mới nhất + làm stale `published`] → [`stale_rows` tăng, `is_fresh` chuyển false; quality check phát hiện dòng trùng và summary rỗng] → [`retrieval_hit_rate` giảm vì tài liệu chứa đáp án không còn trong index; các câu hỏi loại `date` sai vì `_extract_answer` trả về `published` đã bị đẩy lùi].
2. [Repair dựng lại clean dataset từ `crossref_records.json` gốc] → [`stale_rows` về 0, quality checks pass trở lại] → [`retrieval_hit_rate` và `mean_token_f1` quay về mức baseline, vì repair tái tạo đúng schema và đúng `paper_id` mà test set đóng băng đang trỏ tới].

Corruption nào ảnh hưởng rõ nhất và vì sao?

Chưa có số để kết luận. Dựa trên cấu trúc dữ liệu tôi đã dựng, tôi **dự đoán** việc xóa các record mới nhất gây thiệt hại lớn nhất, vì đây là dạng hỏng duy nhất khiến tài liệu chứa đáp án biến mất hoàn toàn khỏi index — `retrieval_hit_rate` của những câu hỏi đó tụt thẳng về 0 và không cách nào bù lại. Các dạng còn lại chỉ làm nhiễu: blank summary vẫn giữ title và metadata nên lookup theo title còn hoạt động; truncate title phá lookup nhưng vector search vẫn có 0.8750 cơ hội cứu ở top-1. Cần đối chiếu `corruption_log.json` với `corrupted_answers.json` theo từng `paper_id` để xác nhận hoặc bác bỏ dự đoán này.

Kết quả nào khác với kỳ vọng ban đầu?

Tôi ban đầu nghĩ `categories` sẽ có dữ liệu vì cả `PaperRecord`, Contract Chung của nhóm lẫn `Guide.md` đều yêu cầu trường này, và Thành viên 1 cũng đã chủ động đưa `subject` vào tham số `select`. Thực tế 24/24 record rỗng. Giả thuyết đầu tiên của tôi là lỗi parse, nhưng đọc code thấy `item.get("subject", [])` là đúng. Tôi kiểm tra bằng bốn phép thử mô tả ở mục 6 và loại trừ được cả lỗi parse lẫn ảnh hưởng của `select` và của filter ngày. Bài học là không nên suy ra nguyên nhân từ triệu chứng: nếu tôi dừng ở giả thuyết đầu, tôi đã báo nhầm lỗi cho Thành viên 1.

Điều bất ngờ thứ hai là lỗi `NaN` ở mục 6 — nó không xuất hiện ở bất kỳ bước nào trong phần việc của tôi, chỉ lộ ra khi tôi cố tình kiểm tra artifact **sau khi đã ghi xuống đĩa** thay vì kiểm tra dataframe trong bộ nhớ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Ranh giới thật của một module không nằm ở chữ ký hàm mà nằm ở artifact nó ghi ra đĩa. Dataframe của tôi sạch tuyệt đối trong bộ nhớ nhưng vẫn sinh `NaN` sau khi qua CSV, và lỗi đó chỉ phát nổ trong module của người khác. Từ đó tôi hiểu vì sao lưu raw response **trước khi** parse lại quan trọng đến vậy: nó là điểm tựa duy nhất để repair và để phân biệt lỗi nguồn với lỗi xử lý — chính nhờ có `crossref_response.json` tôi mới chứng minh được `categories` rỗng là do nguồn.

2. **Về data quality/observability:** Quality và freshness đo hai thứ khác nhau và không thay thế nhau được. Một dataset toàn vẹn hoàn hảo vẫn có thể vô dụng vì đã cũ, và đó là loại lỗi nguy hiểm nhất vì mọi kiểm tra truyền thống đều báo xanh. Tôi cũng nhận ra observability phải bắt được lỗi **trước khi** người dùng nhận câu trả lời sai — nếu chỉ nhìn `judge_accuracy` thì lúc phát hiện đã muộn, còn `stale_rows` hay số dòng trùng cảnh báo được ngay ở tầng dữ liệu.

3. **Về ảnh hưởng của data đến RAG agent:** Chất lượng agent bị chặn trên bởi chất lượng corpus, và tôi thấy rõ điều này khi bỏ `Published`/`Categories` khỏi `text_for_embedding` theo đúng format quy định: độ chính xác top-1 của vector search tụt từ 0.9167 xuống 0.8750 mà không đổi một dòng code nào của retrieval hay agent. Chỉ thay đổi chuỗi được đem đi embed. Đó là bằng chứng cụ thể rằng quyết định ở tầng data modeling truyền thẳng xuống chất lượng câu trả lời.

### Nếu có thêm thời gian

Tôi sẽ bổ sung cho test set các câu hỏi **không nhúng title trong dấu nháy đơn**, ví dụ hỏi theo chủ đề như "Which paper applies retrieval-augmented generation to jawbone lesion diagnosis?". Lý do: hiện `qa.py` có bước lookup chính xác theo title nên baseline đạt trần 1.0000, khiến `retrieval_hit_rate` mất độ nhạy — không phân biệt được corpus retrieve tốt hay chỉ nhờ khớp chuỗi. Câu hỏi theo chủ đề buộc hệ thống dựa hoàn toàn vào embedding, nơi phép đo của tôi cho thấy còn dư địa thật (0.8750 top-1). Cách đo cải thiện: chạy cùng bộ corruption trên hai test set, so biên độ sụt của `retrieval_hit_rate`; test set không có title sẽ cho biên độ lớn hơn và phân giải rõ hơn giữa các loại corruption. Việc này cần thống nhất với nhóm vì đổi test set sau khi đã đóng băng sẽ phá tính so sánh được của các số đã chạy.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Thạch Minh Quân
**Ngày xác nhận:** 2026-08-06
