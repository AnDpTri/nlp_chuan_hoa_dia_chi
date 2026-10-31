# Thiết kế lại giao diện Address May Cry (31/10/2026)

## Mục tiêu
Giao diện rõ, chuyên nghiệp, đọc được kết quả trong vài giây: hai dòng kết quả nổi bật, rồi mới đến chi tiết.

## Hệ thiết kế
- Biến màu, chữ, khoảng cách ở `:root` trong `src/index.css`; dark mode theo `prefers-color-scheme`. Chữ Be Vietnam Pro (có đủ dấu tiếng Việt), số và mã dùng JetBrains Mono.
- Màu theo loại thành phần (số nhà, ngõ, thôn, đường, xã, huyện, tỉnh, bỏ qua) là biến `--k-*`, cặp nền/chữ đạt tương phản AA ở cả sáng và tối. Màu không đứng một mình: mỗi chip luôn có nhãn chữ.
- CSS tách theo vùng: `components/components.css`, `components/header.css`, `features/single/single.css`, `features/batch/batch.module.css`, `app.css`. Không còn inline style (trừ độ rộng thanh tiến độ, giá trị động).

## Bố cục
- Màn một địa chỉ: ≥1024px chia hai cột (ô nhập và ví dụ bên trái, kết quả bên phải); dưới 1024px xếp một cột và tự cuộn tới kết quả sau khi xử lý.
- Thứ tự kết quả: trạng thái và nút “Báo kết quả sai”, hai dòng (Có đối chiếu / Thiếu dữ liệu đối chiếu, mỗi dòng có nút chép), địa chỉ ghép đầy đủ, chuỗi nhập tô màu và chú thích, bảng từng thành phần, cảnh báo, phần chưa phân loại, xã/phường ứng viên, các trường tách riêng, dấu vết kỹ thuật (thu gọn).
- Bảng từng thành phần dưới 720px chuyển thành danh sách thẻ (mỗi ô có nhãn), không cuộn ngang.

## Nội dung
- Cảnh báo dịch từ mã sang câu tiếng Việt trong `src/lib/warnings.ts`; mã lạ hiện “Cảnh báo khác (mã)”.
- Nhãn loại thành phần ở `src/lib/kinds.ts`; không hiện tên biến cho người dùng.
- Không hiện độ tin cậy; `needs_review` hiện “Cần xem lại”, `processed` chỉ là “Đã xử lý”.

## Component dùng chung (cả màn đơn và hàng loạt)
`CopyButton`, `StatusBadge`, `TwoLineResult`, `WarningList` / `CandidateList`, `ComponentBreakdown`, `TechTrace`, `ReportWrong`.

## Quy tắc Web Interface Guidelines đã áp dụng
Skip link và `<main>`; tiêu đề phân cấp; nhãn cho mọi ô nhập; `aria-live` cho trạng thái chép, kiểm tra máy chủ, lỗi; `:focus-visible` rõ; vùng chạm ≥44px; `prefers-reduced-motion`; không `transition: all`; chỉ animate transform/opacity (spin, shimmer); `…` thay `...`; dấu ngoặc kép cong; khoảng trắng không ngắt (`&nbsp;`); `tabular-nums`; `text-wrap: balance/pretty`; `overflow-wrap` cho nội dung dài; `color-scheme`, `theme-color` hai chế độ; `translate="no"` cho tên thương hiệu; điều hướng bằng liên kết `#mot-dia-chi` / `#hang-loat`; ngăn chi tiết có `aria-modal`, đóng bằng Esc, trả focus; `overscroll-behavior`; `safe-area-inset`; `Intl.DateTimeFormat` cho giờ lịch sử; `autocomplete="off"`, `spellCheck={false}` cho ô địa chỉ.
