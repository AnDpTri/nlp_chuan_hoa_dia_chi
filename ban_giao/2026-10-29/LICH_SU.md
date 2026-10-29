# Lịch sử công việc và các lần thử

Đây là lịch sử kỹ thuật tổng hợp từ tài liệu đối chiếu session, code,
checkpoint, predictions và audit đã lưu. Không phải toàn bộ raw chat, không
tự thêm timestamp cho thao tác không có log. Các mốc sau chủ yếu diễn ra
trong ngày29/10/2026; thiết kế ban đầu từ25–26/10. Thứ tự theo chuỗi công việc.

## 1. Thiết kế ban đầu và dữ liệu nền

Trong session Claude25–26/10, hướng đã bàn là trie+cây hành chính, sinh
ứng viên rồi tìm cách hiểu cả địa chỉ, dùng quận/huyện cũ làm bằng chứng,
chuyển về tỉnh/xã mới. CRF cho chi tiết và logistic regression/LightGBM
cho điểm là đề xuất ban đầu. Chưa có căn cứ nói tất cả đã triển khai.

Nguồn đối chiếu: `bao_cao/2026-10-29/pipeline_claude_doi_chieu.md` và
`ban_giao_du_an.md`. Hai bản session Claude có nội dung trùng, đã loại khi
tổng hợp. Bản đầu từng có mô tả chọn một cây cho toàn chuỗi; yêu cầu thực
tế sau đó chốt cho phép **trộn thành phần cũ–mới trong cùng input**.

Các commit đã có khi tiếp quản: `d30b19c` khởi tạo đặc tả/dữ liệu/khung;
`de2d41c` thêm400 địa chỉ OSM với nhãn sơ bộ. Không coi commit này như toàn
bộ hiện trạng local sau hàng loạt thử nghiệm chưa commit.

## 2. Tiếp quản và kiểm tra khung

Đọc đặc tả, tài liệu, lịch sử Claude/Codex và dữ liệu trên máy. Ghi nhận
15hàm/phương thức còn NotImplementedError, chưa có train/checkpoint trong
khung lúc đó. Danh mục gồm hai mốc và mapping nhiều đích;440xã cũ chia đích.
Tập400 ban đầu có168 tự động khớp/232 cần duyệt, không có nhãn human gold.

Đã phân biệt chạy validator cấu trúc với chứng thực ngữ nghĩa, dữ liệu OSM
thật với biến thể tổng hợp, và thiết kế dự kiến với code đã thực thi.

## 3. Bản thử luật đầu tiên

Triển khai pipeline chạy được bằng Unicode/token, trie, beam, tách chi tiết,
chuyển đổi và cảnh báo. Đầu tiên đo mức khớp đầu ra theo nhãn dev, sau đó
bổ sung output từng câu, không chỉ số tổng. Bản luật không có model đã train.

Bằng chứng: `bao_cao/2026-10-29/ban_thu_pipeline_v1/` và các bản sửa nền.
Các số trong báo cáo tuần3 hoặc tài liệu cũ phản ánh thời điểm đó, không
được dùng thay điểm mốc mới nhất.

## 4. Sửa nền v2/v3 và chẩn đoán hướng đi

Đã sửa theo các nhóm lỗi quan sát được:

- Xét từng thành phần theo mốc, giữ quan hệ cha-con nguồn.
- Giữ dấu đã nhập làm bằng chứng thay vì bỏ dấu cho mọi bước.
- Tên đầy đủ có số không bị nhánh tên ngắn cạnh tranh như đủ thông tin.
- Dấu nháy trong D'Ran/M'Đrắk và vị trí Unicode.
- Giữ số nhà ghép/dấu phân cách, tránh cắt154-156 hoặc24B-24.
- Hạn chế suy mọi phần sau số nhà thành đường, giữ phần chưa phân loại.
- Ghi rõ nhãn mơ hồ và phần mapping không cho phép chọn một xã mới.

Đồng thời phát hiện một số nhãn máy bỏ bằng chứng hành chính, lấy số trong
tên đường làm số nhà hoặc gán đường/thôn không nhất quán. Không tự sửa dev
để tăng điểm. Số cảnh báo/không cảnh báo không được xem là xác suất đúng.

Bằng chứng: `docs/SUA_LOI_PIPELINE_V3.md`,
`docs/DANH_GIA_HUONG_DI_PIPELINE.md`, các gói `chan_doan_huong_di_v2` và
`sua_loi_pipeline_v3`. Luật v3 được giữ làm default để không tự nâng backend
chỉ theo mức khớp nhãn máy.

## 5. Chuẩn bị, sửa và audit dữ liệu qua nhiều lượt

Hai nhánh riêng làm tập400 và train/dev bổ sung. Đã kiểm độc lập nhiều lần,
không coi lời bàn giao PASS100% là đủ:

- Train/dev từng có2.037/464; lỗi tên đích/offset/provenance và giao họ
  sau che số nhà được phát hiện, giao sửa theo từng nhóm.
- Có nhãn ghi Phương Liệt thay vì Phường Phương Liệt; có gói tái sinh không
  giữ đúng những gì bảng đối ứng tuyên bố là kế thừa.
- Test từng ghi đè chỉnh sửa hiện hành; evidence kiểm nhãn đầu vào khác
  nhãn thực xuất ra; đường không có trong input vẫn được cấp đủ căn cứ.
- Fixture số81 bên trong181, vai trò quận/phường trùng chữ, `KP1` bị coi
  như Thôn199999 và các ca Unicode đã bắt lỗ hổng dù unit test gói PASS.
- Audit4 ghi train2.169/dev500, có56ca lệch tokenizer được cách ly;
  provenance còn54đối ứng đổi tên đường nhưng khai kế thừa. Test289AI/
  111cần duyệt,36xã chia. Hồ sơ nghị quyết có URL/mốc/diễn giải cần sửa.

Đã giao sửa, lưu hash/snapshot/fixture và lịch sử đính chính. Các audit
khác ngày/phiên bản không thay thế nhau. Báo cáo AI không phải nhãn human gold.

Bằng chứng: `bao_cao/2026-10-29/kiem_tra_agy*`,
`docs/antigravity_rpc/KIEM_TRA_HAI_TASK_AGY_LAN_*.md`.

## 6. CRF CPU: kiểm tra model nhận diện nhẹ

Huấn luyện CRF trên train gốc sau lọc3.973mẫu và train kết hợp5.966mẫu.
Fit khoảng9,77s/13,91s CPU; checkpoint khoảng249/282KiB.

End-to-end mốc CRF kết hợp:895/1.136=78,785% gốc,274/464=59,052% khó;
luật870/1.136=76,585% và228/464=49,138% ở cùng phép đo đối chứng sau này.

Span token lịch sử trên dev khó chỉ có452câu. F1kết hợp99,282% ở subset đó
không đồng nghĩa accuracy end-to-end99% và không được so thẳng với F1raw
char464câu của model sau. Default không tự đổi sang CRF.

Bằng chứng: `docs/THU_NGHIEM_CRF_V1.md`,
`danh_gia/ket_qua/crf_v1_01/`.

## 7. Char-CNN + CRF và LightGBM

Xây model ký tự7vai trò, giải mã BIO có ràng buộc, map NFC về raw input.
Đã giữ ranh giới cắt giữa token; không ép chỉnh tokenizer theo nhãn từng ca.

Đóng băng train/dev/danh mục. Chia theo họ/cha để CNN và ranker học phần
train riêng:4.841CNN/1.169ranker. CNN351.246tham số,12epoch263,27sCPU;
ranker1.129nhóm/27.730giả thuyết,19,18s gồm đặc trưng.

End-to-end đầu: CNN điểm tay886/1.136 và281/464; CNNranker893/1.136 và
280/464. F1raw span98,132%/98,761%. Không có căn cứ nói ranker cải thiện
đồng đều hoặc model này giải được tên chuẩn/mơ hồ. Đã báo được/mất từng câu.

Bằng chứng: `danh_gia/ket_qua/char_v1_01_cuoi/` và checkpoint `char_v1_01`.

## 8. Lưu trữ báo cáo vào dự án

Đã đưa194file gốc của các gói trước vào `bao_cao/2026-10-29/`,
46.394.613byte ở lần chụp lưu trữ đó, kiểm SHA256. Đây không phải số file/
kích thước toàn repo hiện tại. Tạo `docs/MUC_LUC_BAO_CAO.md` làm chỉ mục.

## 9. ViDeBERTa thực nghiệm trên Colab

Dùng checkpoint pretrained `Fsoft-AIC/videberta-xsmall`, thêm đầu ký tự
và CRF. Chuẩn bị notebook/ZIP, chạy GPU T4, export model/report để chạy CPU.

Gói v1 gặp lỗi key manifest Windows khi sang Linux. Một lượt chỉnh trực
tiếp notebook gây lỗi cú pháp/nuốt lỗi verify. Đã chụp bản trước sửa, sửa
reader pathportable, gói v2 bất biến, log stdout/stderr và kiểm verify/test.
Đổi sang luồng Drive để đọc ZIP và lưu checkpoint/kết quả không cần widget.

ViDeBERTa70.753.742tham số đã train5epoch/4.841mẫu. Tổng vòng train412,37s
T4; peak allocated khoảng1.374MiB, không đồng nghĩa toànVRAM. Dev không
dùng chọn checkpoint. Nhập49file xuất, kiểm hash/dữ liệu/code, tính lại điểm.

Kết quả đầu, trên pipeline cũ:

| Model | Dev gốc | Dev khó |
|---|---:|---:|
| ViDeBERTa điểm tay |878/1.136=77,289%|284/464=61,207%|
| ViDeBERTa ranker |879/1.136=77,377%|282/464=60,776%|

Trên CPU Colab khoảng92–95ms/địa chỉ bản ranker, chậm hơn CRF cùng máy
khoảng7lần. Không so trực tiếp thời gian này với CNN trên laptop.
Model mới chưa thắng CRF/CNN đồng đều. Báo cáo không dùng tên model để
biện minh cho điểm thấp hoặc hứa95%.

Bằng chứng: `danh_gia/ket_qua/videberta_v1_01_colab/`, `colab/kiem_tra/`.

## 10. Sửa sau model, giữ CNN/ranker

Thử tra tên theo tỉnh từ train (1.018cặp tên/tỉnh) và bảo vệ span đường khỏi
ứng viên hành chính không tiền tố nằm trọn bên trong. Từ điển train chưa
được coi là danh mục chứng thực. Giữ dấu đã nhập, không chọn theo tần suất
khi trùng khóa; ghi provenance.

| Cấu hình CNN | Gốc | Khó |
|---|---:|---:|
| Mốc trước |893|280|
| Chỉ tra tên |941|295|
| Chỉ bảo vệ đường |893|281|
| Cả hai |941|296|

Không mất câu vốn đúng trên hai tập ở lượt này. Hai ca đường Điện Biên Phủ/
Đại lộ Bình Dương bỏ được suy tỉnh từ chữ trong đường nhưng nhãn vẫn yêu
cầu tỉnh: phải ghi khác biệt ngữ nghĩa, không chỉ chạy theo điểm.

Bằng chứng: `danh_gia/ket_qua/sua_pipeline_cnn_v1_01/`.

## 11. Đo ma trận12cấu hình trên cùng CPU/pipeline

Đã chốt cần đối chứng đầy đủ thay vì chỉ chạy CNN sau sửa. Luật/CRF dùng
điểm tay; CNN/ViDeBERTa có điểm tay/ranker; mỗi bản chạy cũ và đã sửa.
Mỗi encoder chạy một lần/câu, các nhánh dùng lại context riêng; thời gian là
tổng thành phần, không giả gọi đó là12lượt full inference độc lập.

| Sau cùng hai sửa ở mốc ma trận | Gốc% | Khó% |
|---|---:|---:|
| Luật |80,810|51,940|
| CRF |83,011|62,284|
| CNN điểm tay |82,218|63,793|
| CNN ranker |82,835|63,793|
| ViDeBERTa điểm tay |81,514|64,440|
| ViDeBERTa ranker |81,602|64,009|

Không có backend thắng mọi phía. Rawspan tốt chưa đưa được giá trị chuẩn
đúng vào beam. Ranker chưa giúp đồng đều. Bản ranker CNN/ViDeBERTa sai chung
180câu gốc/163câu khó ở mốc này. Không tự coi số chung sai là lỗi model.

Bằng chứng: `danh_gia/ket_qua/ma_tran_v1_01/`.

## 12. Phân loại beam và sửa định dạng tiền tố

Chẩn đoán riêng các câu sai dev khó: CNN thiếu đáp án trong155beam;
ViDeBERTa thiếu152. Trong đó144câu của mỗi backend vẫn có span chi tiết
khớp nhãn. Phân loại có nhóm thiếu dấu, thừa tiền tố lỗi, nhãn canonical
trống và lỗi hành chính. Không coi phân loại cơ học là xác minh toàn bộ.

Sửa formatter đầu span cho một số kiểu gõ Telex và tiền tố lồng loại tuyến
số, giữ số nhà/tên riêng. Ví dụ `dduowngf Hùng Vương` không được xuất thành
`Đường Dduowngf Hùng Vương`; `d. ql8a` có thể định dạng theo loại tuyến.

CNN296→333/464=71,767%; ViDeBERTa299→336/464=72,414%; mỗi model thêm37,
mất0câu vốn đúng ở lượt đo. Điểm gốc không đổi.73unit tests qua.
Đã ghi nguy cơ bám template dev; chưa coi điểm tăng là tổng quát hóa.

Bằng chứng: `chan_doan_beam_v1_01/`, `sua_dinh_dang_v1_01/`.

## 13. Chế độ hợp đồng/giải thích: kết quả giảm điểm

Thêm chế độ giữ tên từ train ở gợi ý, không tự thay canonical; bỏ lọc cứng
ứng viên theo span model, xuất nguồn và các giả thuyết. Kiểm thử cơ chế
qua nhưng chưa phải bộ giải mã tốt hơn. Đã đo ngay sau triển khai:

| Model | Gốc trước→sau% | Khó trước→sau% |
|---|---:|---:|
| CNNranker |82,835→78,609|71,767→68,319|
| ViDeBERTa điểm tay |81,514→77,289|72,414→69,181|

Mỗi model mất48câu gốc/15câu khó vì chỉ giữ tên đúng trong gợi ý; CNN mất
thêm1ca hành chính khi bỏ lọc. Không có câu mới đúng thêm. Giữ thử nghiệm,
không thay default hoặc che điểm giảm bằng lý do có giải thích.

Qua đọc metadata,18ca canonical đường trống được xác nhận là cố ý mơ hồ
(ví dụ NTT có nhiều tên), không mặc định là nhãn thiếu. Chúng chỉ thuộc3họ
sau che số nhà. Đã đính chính cách diễn đạt trong phân tích sau.

Bằng chứng: `do_hop_dong_v1_01/`, `docs/PHAN_TICH_DIEM_NGHEN_SAU_DO.md`.

## 14. Dữ liệu bổ sung v2 và danh mục đường: audit mới

Gói train3.000/650họ và danh mục1.461confirmed/1.007tên được bàn giao.
Hai validator và11+16unit tests của gói PASS, nhưng kiểm độc lập tìm:

- Nguồn đường .txt được tạo lại từ hằng Python, không phải raw tải độc lập;
 8/10URL là trang gốc. URL ghiQĐ1454 thực ra làQĐ89/QĐ-TCTĐB.
-654nhãn ngõ và79nhãn thôn có span null;433/66tương ứng vẫn cho fit canonical.
  Ví dụ input không có Khu phố3 nhưng nhãn còn giữ từ cha.

Đã giao sửa nguồn/nhãn và tách dữ liệu từ snapshot để không chờ cả gói:
1.183qua cổng lọc,927/301cha bổ sung CNN,256giữ theo họ;1.817không dùng
theo lý do chồng lấn. Tạo tập CNN5.768, chưa dùng để tạo điểm đang báo.

File danh mục live sau sửa khai53confirmed/1.484pending và có raw nguồn;
chưa có audit độc lập mới trong mốc này. Các tuyên bố cải thiện vẫn cần
kiểm lại, không sửa nội dung audit cũ.

Bằng chứng: `audit_agy_duong_train_v2_01/`, `data/train_dev/duyet_v2_01/`.

## 15. Sửa thiếu ứng viên hành chính và ranh giới model

Trong17ca CNN chỉ lệch hành chính, beam giữ ứng viên có13đích tham chiếu,
4ca không có. Một ca Tam Dan có cả Tam Đàn/Tam Dân, nên không ép một nhãn.

Phát hiện tiền tố `phuowngf1` không nhận dạng khiến1bị bỏ qua như số rời.
Thêm mã hóa Telex từ từ vựng loại chuẩn thay vì ngoại lệ theo địa danh.
CNN sửa được4ca, ViDeBERTa chưa tăng. Kiểm trực tiếp thấy model cắt
`phuowngf` thành `phuown`+`gf`, làm parser mất tiền tố.

Giữ thêm nhánh token lexical gốc, chiếu ứng viên sang lưới model theo offset,
gộp không nhân điểm. Không thêm threshold/weight theo IDdev. Cả hai thêm4ca,
mất0ca; Tam Dan vẫn mơ hồ.87tests qua. Đây là mốc số đo mới nhất:
CNN941/1.136 và337/464; ViDeBERTa926/1.136 và340/464.

Bằng chứng: `sua_tien_to_hanh_chinh_v1_01/` và `v2_01/`.

## 16. Tách module và đo tiền xử lý riêng

Đã chuyển NFC/offset sang `tien_xu_ly`, nhãn sang `nhan`, adapter neural sang
`ngu_canh_neural`, formatter sang `dinh_dang`; giữ tương thích import cũ.
92tests qua, mỗi backend kiểm parity8raw-span/4end-to-end giữ nguyên.

Đo riêng1.600câu: invariants Unicode/offset/giữ ký tự đạt100% trong tập;
biên lexical khớp100%span gốc và97,414%span khó. Đính chính rõ: không có
accuracy token ngữ nghĩa độc lập, không được gọi tiền xử lý chính xác100%.
Tính lại F1model từ predictions đầy đủ, không chạy lại full chỉ vì refactor.

Cho formatter span tham chiếu để tách tác động model: khớp giá trị gốc94,742%,
khó88,242%; sau bỏ dấu99,375%/96,264%. Không quy mọi lệch tên chuẩn choformatter.

Bằng chứng: `docs/MODULE_VA_SO_DO.md`, `tung_module_v1_01/`.

## 17. Những bài học phải giữ khi tiếp nhận

1. Không nhầm F1span với chuẩn hóa giá trị/mã hoặc end-to-end.
2. Không nhầm invariant tiền xử lý, unit test hay hashPASS với đúng ngữ nghĩa.
3. Không coi bỏ dấu/đổi số nhà là tạo nhiều bằng chứng độc lập.
4. Giữ cả kết quả giảm điểm và hồi quy; không chọn báo cáo có lợi nhất.
5. Các sửa theo lỗi đã xem có nguy cơ quá khớp; cần đánh giá độc lập thật.
6. Có input không chứa đủ thông tin để có một đích duy nhất. Đây là thuộc
   tính bài toán, không phải mọi trường trống đều là lỗi cần ép model điền.
7. Giữ không gian thay phương pháp. Những gì đã thử là baseline/chứng cứ,
   không phải kiến trúc bắt buộc cho người tiếp nhận.
