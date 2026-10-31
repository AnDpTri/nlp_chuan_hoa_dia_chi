/**
 * Bộ kiểm thử đơn vị độc lập cho các tiện ích Batch Workspace (Phần B)
 * Chạy bằng: node --experimental-strip-types docs/ui-address-may-cry/B_batch/test_batch_unit.ts
 */

import { parseCSV, parsePastedLines, detectDelimiter, detectAddressColumn, CSV_LIMITS } from '../../../web/address-may-cry/src/features/batch/csvParser.ts';
import { sanitizeForCsvFormula, escapeCsvField } from '../../../web/address-may-cry/src/features/batch/exportUtils.ts';
import { SAMPLE_ADDRESSES, getSampleCsvContent } from '../../../web/address-may-cry/src/features/batch/sampleData.ts';

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`[FAIL] ${message}`);
    process.exit(1);
  }
  console.log(`[PASS] ${message}`);
}

console.log('=== 1. KIỂM THỬ CSV PARSER ===');

// 1.1 Kiểm thử UTF-8 BOM
const bomCsv = '\uFEFFstt,dia_chi\r\n1,"Số 10, Đường Lê Lợi, Cần Thơ"\r\n2,"45B Hoàng Văn Thụ"';
const parsedBom = parseCSV(bomCsv);
assert(parsedBom.headers.length === 2, 'Parse CSV có BOM nhận diện đúng 2 headers');
assert(parsedBom.headers[0] === 'stt', 'Header 0 không bị dính ký tự BOM');
assert(parsedBom.rows.length === 2, 'Parse đúng 2 dòng dữ liệu');
assert(parsedBom.rows[0]['dia_chi'] === 'Số 10, Đường Lê Lợi, Cần Thơ', 'Ô có dấu phẩy trong ngoặc kép được giữ nguyên vẹn');

// 1.2 Kiểm thử dấu xuống dòng bên trong ngoặc kép (Newline inside quotes)
const newlineCsv = 'id,dia_chi\r\n1,"Dòng 1\nDòng 2\r\nDòng 3"\r\n2,"Địa chỉ thường"';
const parsedNewline = parseCSV(newlineCsv);
assert(parsedNewline.rows.length === 2, 'Parse đúng 2 dòng mặc dù dòng 1 có newline bên trong');
assert(parsedNewline.rows[0]['dia_chi'].includes('Dòng 1\nDòng 2\r\nDòng 3'), 'Nội dung xuống dòng bên trong ô được bảo toàn');

// 1.3 Kiểm thử Escaped Quotes ("")
const escapedCsv = 'id,dia_chi\r\n1,"Số 10 ""A"", Lê Lợi"';
const parsedEscaped = parseCSV(escapedCsv);
assert(parsedEscaped.rows[0]['dia_chi'] === 'Số 10 "A", Lê Lợi', 'Dấu ngoặc kép kép ("") được chuyển thành dấu ngoặc đơn (")');

// 1.4 Kiểm thử các loại Delimiter (, ; \t)
const semicolonCsv = 'id;dia_chi;ghi_chu\r\n1;Hà Nội;Khách VIP\r\n2;Đà Nẵng;Giao gấp';
assert(detectDelimiter(semicolonCsv) === ';', 'Tự động phát hiện dấu chấm phẩy (;)');
const parsedSemi = parseCSV(semicolonCsv);
assert(parsedSemi.rows[1]['dia_chi'] === 'Đà Nẵng', 'Parse đúng với dấu chấm phẩy');

const tabCsv = 'id\tdia_chi\n1\tCần Thơ\n2\tTP.HCM';
assert(detectDelimiter(tabCsv) === '\t', 'Tự động phát hiện dấu Tab (\\t)');
const parsedTab = parseCSV(tabCsv);
assert(parsedTab.rows[0]['dia_chi'] === 'Cần Thơ', 'Parse đúng với dấu Tab');

// 1.5 Kiểm thử phát hiện cột địa chỉ
assert(detectAddressColumn(['stt', 'ten', 'dia_chi'], []) === 'dia_chi', 'Nhận diện đúng cột dia_chi');
assert(detectAddressColumn(['id', 'customer_address', 'phone'], []) === 'customer_address', 'Nhận diện đúng cột customer_address');

// 1.6 Kiểm thử parse danh sách dán nhiều dòng (parsePastedLines)
const pastedText = `
268/10 NGUYỄN VĂN LINH, CẦN THƠ
45 XÔ VIẾT NGHỆ TĨNH, CẦN THƠ

Số 16 ngõ 12 Trần Quý Kiên, Cầu Giấy, Hà Nội
`;
const lines = parsePastedLines(pastedText);
assert(lines.length === 3, 'Parse pasted lines lọc dòng trắng thừa, giữ đúng 3 địa chỉ');
assert(lines[0] === '268/10 NGUYỄN VĂN LINH, CẦN THƠ', 'Dòng 1 nguyên vẹn');

// 1.7 Kiểm thử giới hạn độ dài ô
let caughtLengthErr = false;
try {
  const giantAddress = 'A'.repeat(2049);
  parseCSV(`id,dia_chi\n1,"${giantAddress}"`);
} catch (e: any) {
  caughtLengthErr = true;
  assert(e.message.includes('2.048 ký tự'), 'Bắt chính xác lỗi vượt quá 2048 ký tự');
}
assert(caughtLengthErr, 'Ném ngoại lệ khi ô vượt quá 2048 ký tự');

console.log('\n=== 2. KIỂM THỬ XUẤT DỮ LIỆU & BẢO VỆ CSV FORMULA INJECTION ===');

// 2.1 Kiểm thử chống chèn công thức Excel (=, +, -, @)
assert(sanitizeForCsvFormula('=1+1') === "'=1+1", 'Chặn công thức bắt đầu bằng =');
assert(sanitizeForCsvFormula('+cmd|') === "'+cmd|", 'Chặn công thức bắt đầu bằng +');
assert(sanitizeForCsvFormula('-123') === "'-123", 'Chặn công thức bắt đầu bằng -');
assert(sanitizeForCsvFormula('@SUM(A1:A10)') === "'@SUM(A1:A10)", 'Chặn công thức bắt đầu bằng @');
assert(sanitizeForCsvFormula('Số 45 Lê Lợi') === 'Số 45 Lê Lợi', 'Địa chỉ bình thường không bị thay đổi');

// 2.2 Kiểm thử escapeCsvField
assert(escapeCsvField('Hà Nội, Việt Nam') === '"Hà Nội, Việt Nam"', 'Bọc ngoặc kép khi chuỗi có dấu phẩy');
assert(escapeCsvField('Tên "Đặc Biệt"') === '"Tên ""Đặc Biệt"""', 'Escape dấu ngoặc kép bên trong');
assert(escapeCsvField('=SUM(A1)') === '"\'=SUM(A1)"', 'Thoát an toàn cho chuỗi có công thức độc hại');

console.log('\n=== 3. KIỂM THỬ DỮ LIỆU MẪU ===');
assert(SAMPLE_ADDRESSES.length >= 8, 'Có ít nhất 8 địa chỉ mẫu phong phú');
const sampleCsv = getSampleCsvContent();
assert(sampleCsv.charCodeAt(0) === 0xfeff, 'File CSV mẫu bắt đầu bằng UTF-8 BOM');
const parsedSample = parseCSV(sampleCsv);
assert(parsedSample.rows.length === 8, 'File CSV mẫu parse thành công 8 dòng dữ liệu');

console.log('\n>>> TẤT CẢ CÁC BÀI KIỂM THỬ ĐƠN VỊ ĐÃ CHẠY THÀNH CÔNG VỚI ĐỘ CHÍNH XÁC CAO! <<<');
