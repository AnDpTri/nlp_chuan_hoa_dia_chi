"""Report generator from measured tooling artifacts only; no model or API calls."""
import json,hashlib
from collections import Counter
from pathlib import Path
from gold_common import GOLD,sha256

def run():
    stats=json.loads((GOLD/"thong_ke_chon_mau.json").read_text(encoding="utf8"))
    dev=json.loads((GOLD/"thong_ke_quy_uoc_dev.json").read_text(encoding="utf8"))
    leak=json.loads((GOLD/"BAO_CAO_RO_RI_DOC_LAP.json").read_text(encoding="utf8"))
    demo=json.loads((GOLD/"thu_nghiem/KIEM_CONG_CU_KHONG_PHAI_GOLD_KET_QUA.json").read_text(encoding="utf8"))
    h=sha256(GOLD/"mau_ung_vien.csv")
    if stats["sample_csv_sha256"]!=h or leak["status"]!="PASS":
        raise RuntimeError("Invalid or nonreproducible measured artifacts")
    province=Counter()
    for x in stats["distribution"]:province[x["nhom_tinh"]]+=x["selected"]
    feature=stats["sample_feature_counts"]
    mode=stats["sample_input_modes"]
    n=stats["requested"]
    lines=[
    "# BÁO CÁO DỰNG CÔNG CỤ NHÃN ỨNG VIÊN — 30/10/2026",
    "",
    "**TRẠNG THÁI: CHƯA CÓ GOLD.** Chưa có hai bộ AI độc lập gán nhãn thật, chưa có phán quyết con người, chưa kiểm sai số thật. Mọi tệp ở đây chỉ là ứng viên, quy ước nháp hoặc dữ liệu kiểm công cụ.",
    "",
    "## 1. Phạm vi và chứng cứ",
    "",
    "- Worktree ghi duy nhất: `D:\\nlp_gold`, nhánh `data/gold-20261030`. Repo refactor và các nguồn tham chiếu chỉ đọc.",
    "- Test 400 **chỉ đọc cột** `id,dau_vao,nguon` để loại trừ; không đọc nhãn, trạng thái duyệt, thống kê điểm hay kết quả inference test.",
    "- OSM source: `D:\\nlp_chuan_hoa_dia_chi\\data\\test\\goc\\osm_public_candidates.jsonl`; dữ liệu `input_mode=structured_tags_joined` có cấu trúc thẻ nhưng thẻ không được gửi cho AI trong prompt.",
    "- Hàm fingerprint `normalize, masked_family, osm_identity` nạp **read-only** từ `D:\\nlp_chuan_hoa_dia_chi\\data\\audit\\audit_du_lieu.py`; matcher hành chính `src.danh_muc.DanhMuc` cũng chỉ đọc.",
    "",
    "## 2. Chọn 800 mẫu ứng viên mới — số liệu đã đo",
    "",
    f"- Tổng bản ghi nguồn OSM đã quét: **{stats['osm_rows_scanned']:,}**.",
    f"- Loại do nguồn/chuỗi thiếu: **{stats['excluded_counts'].get('invalid_source_or_text',0):,}**.",
    f"- Loại vì đụng ít nhất một khóa nguồn đã dùng: **{stats['excluded_counts']['excluded_any_cross_source']:,}**.",
    f"- Loại trùng khóa với ứng viên khác bên trong pool: **{stats['internal_pool_duplicate_records']:,}** bản ghi.",
    f"- Đủ điều kiện sau loại trừ và loại trùng nội bộ: **{stats['eligible_after_all_gates']:,}**.",
    f"- Lấy mẫu ngẫu nhiên seed **{stats['seed']}** bằng phân bổ tỷ lệ Hamilton theo tầng `(nhom_tinh, nhom_dac_diem, input_mode)`: **{n}** dòng.",
    f"- Số tầng có pool: **{len(stats['distribution'])}**.",
    f"- SHA-256 `mau_ung_vien.csv`: **`{h}`** (UTF-8 BOM, CRLF, ID `UNGVIEN_####`).",
    "",
    "### Số lượt dính theo từng khóa (không cộng trực tiếp)",
    "",
    f"- Chuỗi chuẩn hóa: **{stats['excluded_counts'].get('independent_text',0):,}**.",
    f"- Cùng OSM identity: **{stats['excluded_counts'].get('independent_osm',0):,}**.",
    f"- Cùng khóa họ che số nhà: **{stats['excluded_counts'].get('independent_masked',0):,}**.",
    "- Một ứng viên có thể trùng nhiều khóa/nhiều nguồn; tổng theo khóa hoặc theo nguồn không bằng số bản ghi bị loại.",
    "",
    "| Nhóm dữ liệu loại trừ | Dòng địa chỉ đã đọc | Trùng text | Trùng OSM ID | Trùng họ che số nhà |",
    "|---|---:|---:|---:|---:|"
    ]
    for name,meta in stats["exclusion_sources"].items():
        c=stats["excluded_by_source_and_key"][name]
        lines.append(f"| {name} | {meta['source_rows_with_address']} | {c.get('text',0)} | {c.get('osm',0)} | {c.get('masked',0)} |")
    lines.extend([
        "",
        "### Kiểm tra rò rỉ độc lập",
        "",
        f"- `kiem_ro_ri_doc_lap.py`: **{leak['status']}**, đã quét lại toàn bộ thư mục con (rglob) của v1/v2, không chỉ file cấp đầu. "
        "Mỗi tập đối chiếu ba khóa riêng; cả ba giao đều **0 trên 800 mẫu cuối**.",
        "- Test trong verifier cũng chỉ dùng ba cột được phép; file báo cáo `BAO_CAO_RO_RI_DOC_LAP.json` ghi số dòng đọc thực tế theo từng nguồn.",
        "",
        "### Phân bố mẫu theo chiều tầng",
        "",
        "| Kiểu đầu vào (ưu tiên phân loại) | Số mẫu | Tỷ lệ |",
        "|---|---:|---:|"
    ])
    for name,count in sorted(feature.items(),key=lambda x:(-x[1],x[0])):
        lines.append(f"| {name} | {count} | {100*count/n:.3f}% |")
    lines.extend(["","| input_mode OSM | Số mẫu | Tỷ lệ |","|---|---:|---:|"])
    for name,count in sorted(mode.items(),key=lambda x:(-x[1],x[0])):
        lines.append(f"| {name} | {count} | {100*count/n:.3f}% |")
    lines.extend(["","| Nhóm địa danh tỉnh **suy từ thẻ nguồn (chỉ dùng phân tầng)** | Số mẫu | Tỷ lệ |",
                  "|---|---:|---:|"])
    for name,count in province.most_common():
        lines.append(f"| {name} | {count} | {100*count/n:.3f}% |")
    lines.extend(["",
       "**Giới hạn tầng:** nhãn nhóm tỉnh được suy từ các thẻ OSM `addr:province/state/city`, **không được xác thực là tỉnh hành chính**; có thể là tên thành phố cấp dưới, biến thể viết tắt hoặc thiếu thẻ. "
       "Quy tắc loại input ưu tiên không dấu → viết tắt → thiếu thành phần → còn lại; đây là **một phân lớp ưu tiên, không phải các cờ độc lập**. "
       "Mẫu đang rất lệch về `structured_tags_joined`; không đại diện cho phân bố địa chỉ người dùng gõ tự do. Cần người quyết cơ cấu và lấy mẫu mới nếu cần phân tầng cân bằng.",
       "",
       f"### Bảng đầy đủ {len(stats['distribution'])} tầng (đếm pool/số chọn/tỷ trọng trên 800)",
       "",
       "| Nhóm tỉnh nguồn | Nhóm đặc điểm | input_mode | Pool | Chọn | Tỷ lệ % |",
       "|---|---|---|---:|---:|---:|"])
    for x in stats["distribution"]:
        lines.append(f"| {x['nhom_tinh']} | {x['nhom_dac_diem']} | {x['input_mode']} | {x['pool']} | {x['selected']} | {x['sample_pct']:.3f} |")
    lines.extend(["",
    "## 3. Bằng chứng bất nhất của nhãn máy trên dev",
    "",
    f"Đọc `data/train_dev/dev.csv`: **{dev['rows']}** dòng; phép đếm regex, không kiểm toán ngữ nghĩa; nhóm chồng nhau.",
    "",
    "| Dấu hiệu | Số dòng dev | ID ví dụ đầu tiên |",
    "|---|---:|---|"])
    for name,x in dev["cases"].items():
        eg=x["examples"][0]["id"] if x["examples"] else "—"
        lines.append(f"| {name} | {x['count']} | {eg} |")
    lines.extend(["",
    "- Trường hợp `VNDEV_00012`: “Số 16 ngõ 12 Trần Quý Kiên ...” có `ngo_ngach_hem=Ngõ 12` đồng thời `duong=Đường Ngõ 12 Trần Quý Kiên`. "
    "Trường hợp `VNDEV_00028`: “Số 3 ngõ 55 Đỗ Quang ...” tách `Ngõ 55` và `Đỗ Quang`. "
    "Tài liệu nháp `QUY_UOC_NHAN.md` nêu các phương án rõ và điểm cần người duyệt.",
    "",
    "## 4. Công cụ đã xây và mẻ kiểm công cụ 60 địa chỉ",
    "",
    "- `SCHEMA_NHAN.json`, `kiem_nhan.py`: schema strict, offset bằng lát cắt, chống chồng span, từ chối khóa mã do AI gửi.",
    "- `tao_goi_gan_nhan.py`: **16 gói × 50 địa chỉ** trong `goi_gan_nhan/`, mỗi gói prompt độc lập và CSV đầu vào; **không gọi API/mô hình**.",
    "- `anh_xa_hanh_chinh.py`: tra mã từ danh mục, mã xã bị chia/tên trùng hoặc không phân giải được -> để trống và abstain.",
    "- `dong_thuan.py`: tất cả bộ gán phải có đủ cùng ID và input, đồng thuận riêng từng trường; Fleiss kappa, queue CSV.",
    "- `lay_mau_kiem.py`: mặc định chọn ngẫu nhiên **150 mục đồng thuận đủ trường** với seed, xuất phiếu chưa đánh dấu cho người.",
    "- `uoc_luong_sai_so.py`: cận trên một phía 95% Clopper–Pearson từ **phiếu đã được người thực sự kiểm đủ các trường**, thiếu nhãn thì fail.",
    f"- Mẻ `thu_nghiem/` dùng 60 địa chỉ **chỉ kiểm công cụ**: {demo['dummy_consensus_count']}/60 đồng thuận giả lập, {demo['dummy_queue_rows']} dòng queue; "
    f"phiếu giả lập {demo['dummy_check_rows']} dòng kiểm trường (30 địa chỉ × 7), "
    "**0 bộ AI độc lập thật, 0 người duyệt**. Nhãn do một người viết bằng rule đơn giản và bản sao cơ học, **không phải gold**.",
    "- Test Clopper–Pearson: 0 lỗi/150 -> cận trên ~**1,977%**; 3 lỗi/150 -> cận trên xấp xỉ **5,1%**. "
    "Các ví dụ này là toán kiểm phần mềm, không phải ước lượng dữ liệu thật.",
    "",
    "## 5. QUYẾT ĐỊNH CẦN NGƯỜI DUYỆT",
    "",
    "Chốt **từng điểm** trong `QUY_UOC_NHAN.md`: ngõ/hẻm tách khỏi đường; cách hiểu `37-39` và `12/5` (mâu thuẫn §4.6); tiền tố tự sinh; tổ/khu phố/ấp/thôn; CMT8/QL; mã bưu chính; tòa nhà/phòng/tầng; tiếng Anh; xã cũ bị chia; trùng tên/thiếu tỉnh; điều kiện công nhận ứng viên thành bộ đánh giá vàng.",
    "",
    "## 6. Chưa làm và giới hạn bắt buộc",
    "",
    "1. **Chưa gán nhãn thật bằng hai hoặc nhiều họ AI khác nhau**; prompt chỉ là file để đưa ra ngoài dự án. Không gọi API/LLM, không cài thư viện.",
    "2. **Chưa có người kiểm 150 địa chỉ**, nên **chưa đo được sai số thực hoặc cận tin cậy thực**. Mọi ước lượng giả lập nằm trong thư mục KIEM_CONG_CU_KHONG_PHAI_GOLD.",
    "3. Cơ cấu OSM bias về địa chỉ từ structured tags, đô thị có dữ liệu và tỉnh ghi trong tags. Tỷ lệ các loại địa chỉ khó còn thấp; cần chốt quota nếu mong đánh giá theo độ khó, không dùng trọng số mẫu hiện tại như phân bố quốc gia.",
    "4. Bộ ánh xạ hành chính luôn conservative: tên trùng/xã bị chia không có căn cứ -> mã xã rỗng; thiếu địa giới chi tiết thì không được tự đoán. Không dùng tọa độ để gắn gold.",
    "5. Khóa họ che số nhà là heuristic của audit; PASS không loại trừ được mọi trùng lặp ngữ nghĩa/diễn đạt khác.",
    "6. Phần lớn dev và test cũ có nhãn máy; ví dụ dev chỉ chứng minh sự thiếu nhất quán, **không xác nhận đáp án**.",
    "",
    "## 7. Chạy lại kiểm chứng offline",
    "",
    "```powershell",
    "cd D:\\nlp_gold",
    "& D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe -X utf8 -B -m unittest tests.test_gold_tooling",
    "& D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe -X utf8 -B data/gold/chon_mau.py --verify",
    "```",
    "",
    "Không chạy `chon_mau.py` không có `--verify` khi file mẫu đã tồn tại: script sẽ từ chối ghi đè để bảo vệ hồ sơ.",
    ""
    ])
    path=GOLD/"BAO_CAO.md"
    if path.exists():raise FileExistsError(path)
    path.write_text("\n".join(lines),encoding="utf8")
    print("REPORT_CREATED",len(lines),"lines","SAMPLE_HASH",h)
if __name__=="__main__":run()
