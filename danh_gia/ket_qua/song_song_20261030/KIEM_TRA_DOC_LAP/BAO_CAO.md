# Tổng hợp kiểm tra ba nhiệm vụ A/B/C — 30/10/2026

Đã đọc báo cáo và script, kiểm lại JSON, xác nhận cả ba hội thoại IDLE. 37 file baseline chung còn nguyên hash. Không chạy lại test, không train và không sửa lõi. Các kết quả sau là kiểm tra mã/số liệu đã bàn giao, không phải benchmark toàn tập mới.

## Phần có thể tận dụng

- A: replay adapter và lưu per-case, coverage hành chính tách non-empty, cấu trúc đo gần đúng nhiệm vụ hơn trước. Runtime LightGBM916/1136 và330/464. Chưa nghiệm thu oracle và so sánh heuristic vì parity không đạt.
- B: exact span microF1CNNv2 trên phần có annotation:98,58% gốc1026 và98,76% khó464. Đây là reference-span match, không phải semanticgold hoặc E2E. Đáng giữ CNNv2 làm bộ trích xuất mặc định của thí nghiệm, chưa đủ căn cứ thay extractor bằng mô hình mới. Thôn/xóm support18 ca gốc rất ít, F1 81,08%, nên không suy từ microF1 rằng mọi role đều tốt.
- C: prototype trả nhiều phương án có provenance, giữsurface, giới hạn8candidates. Có ích làm nguồn sinh phương án cho bộ chọn tiếp theo. Độ trễ riêng generator tự đo mean0,88/0,85ms; chưa phải E2E/SLA. Chưa ghép lõi.

## A: Oracle vẫn chưa được nghiệm thu

thong_ke.json.parity_check:1117/1136 và456/464, tức lệch19/8 ca so với runtime thật. Báo cáo final không làm rõ điều này dù chính script có ghi. Replay chỉ trả singleton và bỏ ranker; runtime dùng tập các giả thuyết có điểm gần nhau để quyết định giữ trống xã/tỉnh. Vì vậy singleton làm thay đổi chính sách mơ hồ. Thêm nữa smoke_test_adapter.py kiểm một đường khác (toàn ranked, vẫn ranker) còn main dùng singleton khôngranker; smoke không xác nhận đúng adapter oracle được dùng.

Các số trần980/1136=86,27%,345/464=74,35%, rankingheadroom64/15 và heuristic914/332 chỉ là kết quả của adapter chưa khớp semantics. Không dùng làm trần chuẩn hoặc chứng minh so sánh bộ chọn. Main cũng tự gán oracletrue cho top1đúng thay vì replay xác nhận, che độ lệch. Hành chínhcoveragecao trênnon-empty vẫn là bằng chứng hỗ trợ rằng rawadmin không thiếu nhiều trong tập này; không chứng minh exactabstention hoặc mọi trường hợp ngoài tập.

## B: Không chấp nhận phép oracle từ điển117/152

Trong compute_independent_oracles, vòng oracle_dictionary dùng inp[s:e] từ biến inp còn sót ở vòng oracle_span cuối, thay vì c['input'] của từng bản ghi. Cả gold/pred bị cắt trên sai chuỗi, nên con số117/152 không hợp lệ.

Ngay cả sửa biến, điều kiện rawspan trùng và lookup không có candidate chỉ chứng minh lookupmiss, không chứng minh sửa riêng từ điển cứu cả6trường; code không thayduong rồi kiểm5trườngcònlại hay chạy lại oracle tương ứng. Cần tách missingcanonicalentry, querymiss, cóentrynhưng saioutput. Phân nhóm58OOV cũng dựa querymiss, chưa bảođảm canonicalref thật sự vắng danh mục. Cócandidate không tự chứng minh19ca là rankingcanonicalsai. Các nhãnnghivấn vẫn được gắn bằngheuristic thô.

OracleSpan16/152 thay cả emissions thành0, đổi bao_ve_chi_tiet=True và weakadmin tags cùng detail; catchException rồi bỏqua. Không phải ablation chỉ thay span4roles giữ nguyên mọi phầncòn lại. Không dùng để tuyên bố extractor tuyệt đối không phải bottleneck. RawF1cao là dữkiện riêng cógiátrị, nhưng110cagốc khôngcóannotation vẫn chưa đượckiểmspans.

## C: Coverage tăng, bộ chọn chưa cải thiện

Số đếm từ JSON (chỉ riêng trườngduong):

| Tập | Baseline một đầu ra | Prototype top1 | Có đáp án trong<=8phươngán |
|---|---:|---:|---:|
| Dev gốc1136 |999|989|1014|
| Dev khó464 |345|346|355|

+15/+10 là thêm ca mà danh sách chứa ref, không phải đầu ra cuối hay E2E. Top1thực theo thứ tự tier còn giảm10ca gốc và tăng1cakhó. Không được nói +15/-0hồi quy của finalselector. Danh sáchchứa nhiềuđápán không đồngnghĩa inputthựcsựmơhồ.

Evaluator có context_admin.ma_tinh=mt or ref_ma_tinh: dùng tỉnhthamchiếu khimtthiếu, vi phạm inference-only. Chưa đo số ca bịảnhhưởng; cần bỏfallback vàđolại trước nghiệmthucoverage. Không đọctest.

Coverage dictionary26,04%khó dùng so khớp fullcanonical exact của ref, có thể khác marker/dấu/chuẩn biểu diễn, không đồngnghĩa73,96% thực thể đường thật sự vắng. Chính cùngreport cho thấy244caOOV vẫn cósurfacekhớp. Bởi vậy không có trầnchấtlượngbằngdictionarycoverage và chưa đủ căn cứ tuyênbố chỉbổsunggazetteer mớiđạt.

Giátrị giữ lại: prototype tách candidate generation khỏi selection, cósurface vàcanonical choices; chưa nên thayoutputđangchạy hoặc mặc địnhưu tiêndictionaryweak hơninput.

## Hướng tiếp theo đã chốt

1. Giữ CNNv2 hiện tại và baseline toànbộ, chưatrain/extractor/Transformerthêm.
2. Dùng prototypeC làm nhánh sinhcandidate độc lập, bỏreffallback; giữ baselineoutput trongcandidates đểcófallback; lưu charoffsets/provenance và khôngclaimcertified cho nguồnweak.
3. Xây bộ chọn có thể giữoutputcũ khi chưađủbằngchứng; điểm xử lý dấu/prefix/địa bàn và biên phải đoablation, không tune theo từngdevcase. Đo top1final và joint6fields với baseline cùngconfig, gained/lost, latency. Coverage tăng chỉ là dưđịa, chưa là gainthực.
4. Tập trungcanonical/linking: xác địnhquerymiss vs missingentry vs selectorwrong. Chỉ train đầuchấmcanonical khi candidateđúngcó nhưng selector hiện hành vẫn sai đángkể. Đây là nhiệm vụ khác với chỉrerank adminbeam.
5. Sửa oracle adapter theo chính sách mơ hồ hiện hành để làm công cụ đo; đừng tiếp tục dùng con số64/15 như đã xác nhận. Đo oracleSpan đúng cần giữemissions/model/admincontext khác khôngđổi.

Không mở vòng yêu cầu agy sửa báo cáo tiếp trong lần kiểm tra này. Các script/đầu ra giữ nguyên để đối chiếu, nhận xét độc lập tại file này và KIEM_CHUNG.json.
