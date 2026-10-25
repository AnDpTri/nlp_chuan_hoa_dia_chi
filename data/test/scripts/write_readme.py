"""Render corpus documentation from measured statistics, never from assumed quotas."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    stats = json.loads((ROOT/'statistics.json').read_text(encoding='utf-8'))
    selection = json.loads((ROOT/'selection.json').read_text(encoding='utf-8'))
    download = json.loads((ROOT/'goc/download.json').read_text(encoding='utf-8'))
    validation = json.loads((ROOT/'validation.json').read_text(encoding='utf-8'))
    asof = json.loads((ROOT/'asof2025_manifest.json').read_text(encoding='utf-8'))
    table = '\n'.join(f'| {name} | {count} |' for name,count in stats['new_provinces'].items())
    eras = '\n'.join(f'- `{key}`: {value} dòng.' for key,value in stats['eras'].items())
    text = f'''# Tập kiểm tra địa chỉ thật — nhãn sơ bộ

**Nhãn là sơ bộ, do máy gán. Nhóm phải duyệt tay trước khi dùng để chấm điểm. Không có dòng nào được ghi `da_duyet`.**

Tập này dành riêng cho đánh giá cuối. Không dùng đầu vào, nhãn, prompt hay kết quả kiểm tra trên tập này để huấn luyện, chọn luật, điều chỉnh mô hình, chọn ngưỡng hoặc chỉnh hệ thống. Bộ tra cứu ở `scripts/admin_lookup.py` độc lập với `src/`; không chạy pipeline đang được đánh giá để tạo đáp án. Việc kiểm tra dưới đây chỉ kiểm tra chất lượng tập dữ liệu, không phải kết quả đánh giá hệ thống NLP.

## Nguồn và giấy phép

- © OpenStreetMap contributors; dữ liệu theo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), xem [OSM copyright](https://www.openstreetmap.org/copyright). Phần trích dữ liệu OSM và bảng có nguồn gốc OSM trong thư mục này được chia sẻ theo ODbL 1.0; không mặc định áp dụng giấy phép phần mềm của repo cho dữ liệu này.
- Bản trích Việt Nam do [Geofabrik](https://download.geofabrik.de/asia/vietnam.html) cung cấp: [{download['url'].rsplit('/',1)[-1]}]({download['url']}). Bản ngày 24/10/2026 được ghim cố định để tái lập; ngày tải UTC: `{download['retrieved_utc']}`.
- Kích thước {download['bytes']:,} byte; MD5 `{download['md5']}`, đã so với checksum Geofabrik. Chi tiết tại `goc/download.json`.
- Mỗi dòng CSV có `nguon` là URL node/way/relation OSM. `goc/selected_sources.jsonl` giữ tên địa điểm công khai, các thẻ địa chỉ gốc, phiên bản và thời điểm sửa đối tượng OSM. Đây là bằng chứng nguồn đã đóng băng, vì trang OSM trực tuyến có thể thay đổi.
- Chỉ lấy đối tượng có tên và thẻ tổ chức/địa điểm công khai (`amenity`, `shop`, `office`, `tourism`, `craft`, `healthcare`, `leisure`); bỏ `access=private`. Không chọn nhà dân chỉ có thẻ địa chỉ. Nhóm vẫn cần kiểm tra thủ công tên, tính công khai và địa chỉ nguồn; thẻ OSM có thể sai hoặc cũ.

## Đầu vào nguyên văn và cách trích

- `{stats['input_modes'].get('addr:full',0)}` dòng lấy **nguyên văn toàn bộ** thẻ `addr:full`.
- `{stats['input_modes'].get('structured_tags_joined',0)}` dòng không có `addr:full`: ghép các **giá trị thẻ có thật** theo thứ tự trong `collect_osm.ADDRESS_ORDER`, phân cách bằng `, `. Giữ nguyên từng giá trị; bỏ giá trị giống hệt đã xuất hiện để tránh lặp. Đây là đầu vào ghép từ các thẻ cấu trúc, **không phải chuỗi người dùng đã gõ nguyên văn cả địa chỉ**. Phân biệt rõ bằng `input_mode` trong bản nguồn và `nguon_dau_vao` trong `ghi_chu`.
- Không thêm lỗi gõ, bỏ dấu, mở rộng viết tắt hoặc tự bịa địa chỉ để đạt hạn ngạch. Không dùng tên cơ sở hay tọa độ để bổ sung thành phần thiếu trong chuỗi đầu vào.

## Chọn mẫu

Quét PBF theo luồng, lọc {selection['eligible_unique_pool']:,} chuỗi địa chỉ công khai khác nhau sau khi loại trùng theo chuỗi chuẩn hóa. Chọn xác định bằng SHA-256 của URL nguồn, phân tầng theo tỉnh cũ nhận diện được, ưu tiên `addr:full` và các mẫu có thông tin cấp xã. Tầng địa lý chỉ hỗ trợ lấy mẫu, không phải đáp án; các ứng viên xã khi chọn mẫu có thể trùng tên hoặc nhầm mốc.

Chọn dư mẫu có dấu hiệu thuộc xã cũ bị chia, rồi kiểm tra lại bằng nhãn văn bản và quan hệ mã. Kết quả thực tế: **{stats['confirmed_old_split_rows']} địa chỉ thuộc {stats['unique_old_split_codes']} xã cũ có nhiều xã mới đích**. Không dựa vào tên đường trùng tên xã để tính chỉ tiêu này. Không giải quyết các xã bị chia bằng tọa độ.

Không mặc định đại diện phân bố dân cư toàn quốc: mẫu công khai có thiên lệch cơ sở kinh doanh, trung tâm đô thị và địa phương có nhiều người đóng góp OSM. Không cam kết có đủ 34 tỉnh hoặc tỷ lệ đô thị/nông thôn cân bằng; xem thống kê thực tế bên dưới. Các trường hợp xã nông thôn vẫn có trong mẫu, nhưng không tự gắn nhãn đô thị/nông thôn cho từng địa điểm khi thiếu căn cứ.

## Quy trình nhãn và mã

**Sai khác mốc trong dữ liệu đầu vào:** `data/clean/moi_tinh.csv` hiện ghi Bắc Ninh (`24`), Quảng Ninh (`22`) và Đồng Nai (`75`) là `Thành phố`, trái với loại `Tỉnh` ở bảng chuyển đổi mốc 01/07/2025. Nhiệm vụ này không được sửa `data/clean`, nên script `asof_2025.py` tạo lớp tra cứu đích chỉ đọc: giữ mã, quan hệ và tên đã làm sạch, lấy **loại đơn vị** từ `data/raw/goc/conversion-table.xlsx`, sheet `Tổng hợp_không merge `, cột A/B/C. Bảng nguồn có đủ 34 mã tỉnh và 3.321 mã xã, kiểm tra quan hệ cha con trước khi áp dụng. Nguồn XLSX là bản sao trong repo cộng đồng nêu trên, không coi là chứng thực độc lập của cơ quan nhà nước.

`asof2025_overrides.csv` ghi đúng **{asof['type_overrides']}** sai khác và ô nguồn; `asof2025_manifest.json` ghim SHA-256 của workbook. Kết quả đích có **6 thành phố** tại mốc 01/07/2025. Các biến thể loại trong nguồn được nhận diện để tra mã nhưng chỉ xuất loại đúng mốc; nếu loại nguồn không phù hợp cả mốc cũ và mốc đích thì thêm `loai_nguon_khac_moc_2025`. Không thay đổi các bảng sạch hoặc suy diễn thêm thay đổi ranh giới. Mốc 2026 trong tên loại tỉnh của đầu vào sạch vẫn là vấn đề để nhóm xử lý riêng ở nhiệm vụ khác.

1. `agy` dùng duy nhất `gemini-3.8-flash-high`, chạy **tuần tự một job**, lô tối đa 35 địa chỉ. Gọi qua Git Bash với `-p="$NLP_LABEL_PROMPT"`; không cấp công cụ. Model tách số nhà, ngõ/hẻm, thôn/xóm, đường và tên xã/huyện/tỉnh; không sinh mã, không chuyển địa giới. Prompt được lưu ở `agy/prompt_*.txt`; phản hồi JSON hợp lệ ở `agy/labels_*.json`. Log lỗi/thử lại không commit.
2. Code kiểm tra đoạn nhãn có trong chuỗi nguồn. Nhãn tự sinh thêm bị bỏ và đưa `can_duyet`; phần chuỗi chưa được phân loại được ghi trong `ghi_chu` với cờ `phan_chua_phan_loai`. Mã được tra chính xác sau chuẩn hóa dấu/chữ viết và tiền tố, dùng quan hệ tỉnh–huyện–xã. Không dùng fuzzy match để chốt mã vàng.
3. Tra danh mục cũ trước; đổi qua `data/clean/doi_chieu_xa_cu_moi.csv`. Nếu không có ứng viên cũ, thử danh mục mới. Nếu tên dùng được ở hai mốc và dẫn tới đáp án khác nhau, gắn cờ `mo_ho_moc_cu_moi`, không tự chốt xã. Nếu hai mốc cho cùng kết quả mới, không khẳng định mã xã cũ khi thiếu bằng chứng mốc cũ.
4. Thiếu thành phần thì để trống. Tỉnh có thể suy ra từ xã/huyện đã được nhận diện duy nhất theo quan hệ cha con; vẫn ghi `thieu_tinh_dau_vao` khi chuỗi không ghi tỉnh. Không dùng thẻ ngoài chuỗi để điền phần thiếu.
5. Xã cũ nhiều đích: để trống `ma_xa`, `xa_phuong`, thêm `xa_bi_chia` và danh sách ứng viên trong `ghi_chu`. Giữ cả trường hợp nguồn nói toàn bộ dân số về một đích để nhóm duyệt; không tự biến nhận định đó thành nhãn đã xác minh.
6. `tu_dong_khop`: tra mã duy nhất, không có cảnh báo hoặc ghi chú nghi vấn từ model. `can_duyet`: thiếu, nhập nhằng, không khớp, mâu thuẫn, phần đường/thôn còn không dấu, số nhà có dấu `/` hoặc model đề nghị kiểm tra. **Cả hai trạng thái đều chưa được người duyệt.** Số nhà có `/` được giữ nguyên và gắn cờ vì chưa xác minh cách diễn giải số nhà/ngõ. Các tiền tố loại thành phần được viết thống nhất (ví dụ `ng.` → `Ngõ`, `kp` → `Khu phố`), nhưng không tự thêm dấu cho tên đường/thôn thiếu dấu.
7. Nếu `addr:full` và thẻ `addr:housenumber`/`addr:street` trên cùng đối tượng khác nhau, vẫn dùng `addr:full` và thêm `mau_thuan_the_osm`; không lấy thẻ cấu trúc ghi đè chuỗi nguồn.

Mã là chuỗi, giữ số 0 đầu. Khi mở Excel phải nhập các cột mã dưới dạng **Text**. `canh_bao` là JSON array trong một ô CSV; ứng viên xã mới là JSON trong `ghi_chu`. Đáp án mới được đưa về mốc 01/07/2025 bằng lớp tra cứu bảng gốc nêu trên, không lấy loại tỉnh năm 2026 trong danh mục sạch làm loại đích. `catalogue_manifest.json` ghim SHA-256 của sáu bảng đầu vào; bước sinh và kiểm tra sẽ dừng nếu chúng thay đổi, để tránh âm thầm đổi đáp án của phiên bản tập test này.

## Thống kê thực tế

- Tổng: **{stats['rows']} địa chỉ**, {validation['new_provinces_represented']} tỉnh/thành mới đã xác định được.
- `tu_dong_khop`: **{stats['status'].get('tu_dong_khop',0)}**; `can_duyet`: **{stats['status'].get('can_duyet',0)}**; `da_duyet`: **0**.
- Có ký tự tiếng Việt mang dấu: **{stats['has_diacritics']}**; không có: **{stats['no_diacritics']}**. Đây là thống kê ký tự, không đồng nghĩa tất cả địa danh không dấu đều viết đúng.
- Có viết tắt theo regex đã công bố trong `build_labels.py`: **{stats['abbreviations']}**. Các lỗi gõ tự nhiên không có gold riêng; chưa công bố số lượng lỗi gõ khi chưa duyệt tay.
- Xã cũ bị chia: **{stats['confirmed_old_split_rows']}** dòng, **{stats['unique_old_split_codes']}** mã xã khác nhau.
- Có thành phần thôn/xóm/ấp/bản/khu phố/tổ dân phố: **{stats['with_hamlet_component']}** dòng. Phân bố loại đơn vị cũ đã xác định: `{json.dumps(stats['old_ward_types'],ensure_ascii=False)}`; đây là loại hành chính, không phải nhãn đô thị/nông thôn của địa điểm.

Phân loại mốc sơ bộ (không suy từ ngày sửa đối tượng OSM):

{eras}

Số dòng theo tỉnh/thành mới trong nhãn:

| Tỉnh/thành | Số dòng |
|---|---:|
{table}

## Tái lập trên máy

Python 3.12 và `osmium==4.3.2` cho bước trích; các bước còn lại dùng thư viện chuẩn. `agy` đã đăng nhập và Git Bash cần cho bước nhãn. Không chạy nhiều job CPU/agy cùng lúc.

```powershell
py -3.12 -m pip install osmium==4.3.2
py -3.12 data/test/scripts/pin_catalogues.py
py -3.12 data/test/scripts/asof_2025.py
py -3.12 data/test/scripts/collect_osm.py
py -3.12 data/test/scripts/select_sample.py
py -3.12 data/test/scripts/label_agy.py
py -3.12 data/test/scripts/build_labels.py
py -3.12 data/test/scripts/validate_dataset.py
py -3.12 data/test/scripts/write_readme.py
```

PBF (~332 MB) và danh sách ứng viên toàn bộ không commit, đã có `.gitignore`; chạy lại bước trích để tái tạo. Chỉ commit trích nguồn 400 mẫu. Tái lập CSV/kiểm tra từ các phản hồi model **đã lưu** không cần gọi lại agy hoặc tải PBF: chạy ba script cuối. Gọi lại model có thể cho nhãn khác; cache từng lô giúp giữ nguyên tập sơ bộ đã công bố. Không thay đổi cách chia lô khi tái sử dụng cache.

`validation.json` kiểm tra schema, nguồn nguyên văn, khóa/mã/quan hệ cha con, số mẫu, ít nhất 20 mẫu xã bị chia, phân bố địa lý, cờ và trạng thái duyệt. Trạng thái **{validation['status']}** chỉ là kiểm tra cấu trúc và bảo toàn nguồn, không chứng minh nhãn ngữ nghĩa đúng. Nhóm cần duyệt từng mẫu, sửa nhãn và ghi người/ngày duyệt trước khi đóng băng gold test.

## Những việc chưa làm và giới hạn

- Chưa có người duyệt đáp án; chưa được dùng làm điểm đánh giá cuối.
- Chưa có dữ liệu địa phương chi tiết để gỡ mọi xã bị chia; ứng viên được giữ để duyệt.
- Không tạo đủ hạn ngạch lỗi gõ, thiếu dấu hoặc nông thôn bằng cách sửa chuỗi nguồn. Các nhóm này phụ thuộc dữ liệu tự nhiên.
- Địa chỉ thật trên nguồn có thể lỗi, cũ hoặc xung đột giữa `addr:full` và thẻ cấu trúc. Bản `addr:full` luôn được ưu tiên làm đầu vào và không tự sửa. Cần nhóm so nguồn khi duyệt.
- Các vấn đề còn trong danh mục sạch không được âm thầm sửa ở nhiệm vụ này. Bộ dữ liệu không sửa `data/raw`, `data/clean`, `src/` hoặc `bai_toan.md`.
'''
    (ROOT/'README.md').write_text(text,encoding='utf-8',newline='\n')
    print('README updated from actual statistics')

if __name__ == '__main__': main()
