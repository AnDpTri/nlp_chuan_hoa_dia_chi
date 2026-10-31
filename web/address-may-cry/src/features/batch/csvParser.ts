/**
 * Bộ phân tích cú pháp CSV tuân thủ chuẩn RFC 4180 viết bằng TypeScript thuần.
 * Hỗ trợ:
 * - UTF-8 có hoặc không có BOM (\uFEFF)
 * - CRLF (\r\n), LF (\n), CR (\r)
 * - Trường nằm trong dấu ngoặc kép có chứa dấu phẩy, dấu chấm phẩy, tab, hoặc xuống dòng
 * - Dấu ngoặc kép được escape bằng cặp ngoặc kép liên tiếp ("")
 * - Tự động nhận diện dấu phân cách (phẩy, chấm phẩy, tab)
 * - Giới hạn kích thước file 5MB, tối đa 1.000 dòng, tối đa 2.048 ký tự mỗi ô
 */

export interface ParsedCSV {
  headers: string[];
  rows: Record<string, string>[];
  totalRows: number;
  delimiter: string;
  detectedAddressColumn: string;
}

export interface ParseOptions {
  maxRows?: number;
  maxCharsPerCell?: number;
}

export const CSV_LIMITS = {
  MAX_FILE_BYTES: 5 * 1024 * 1024, // 5MB
  MAX_ROWS: 1000,
  MAX_CHARS_PER_ADDRESS: 2048,
};

/**
 * Tự động phát hiện dấu phân cách thích hợp nhất (, hoặc ; hoặc \t)
 */
export function detectDelimiter(sampleText: string): string {
  // Lấy tối đa 5 dòng đầu
  const lines = sampleText.split(/\r\n|\n|\r/).filter(l => l.trim().length > 0).slice(0, 5);
  if (lines.length === 0) return ',';

  const delimiters = [',', ';', '\t'];
  const counts: Record<string, number[]> = { ',': [], ';': [], '\t': [] };

  for (const line of lines) {
    let inQuotes = false;
    const lineCounts = { ',': 0, ';': 0, '\t': 0 };
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (!inQuotes && (char === ',' || char === ';' || char === '\t')) {
        lineCounts[char]++;
      }
    }
    for (const d of delimiters) {
      counts[d].push(lineCounts[d as keyof typeof lineCounts]);
    }
  }

  // Chọn delimiter có số lần xuất hiện > 0 và nhất quán giữa các dòng
  let bestDelimiter = ',';
  let bestScore = -1;

  for (const d of delimiters) {
    const list = counts[d];
    const total = list.reduce((a, b) => a + b, 0);
    if (total === 0) continue;
    // Kiểm tra tính nhất quán (độ lệch giữa các dòng)
    const first = list[0];
    const consistent = list.every(c => c === first && c > 0);
    const score = total + (consistent ? 100 : 0);
    if (score > bestScore) {
      bestScore = score;
      bestDelimiter = d;
    }
  }

  return bestDelimiter;
}

/**
 * Phân tích chuỗi CSV theo chuẩn RFC 4180
 */
export function parseCSV(content: string, options: ParseOptions = {}): ParsedCSV {
  const maxRows = options.maxRows ?? CSV_LIMITS.MAX_ROWS;
  const maxChars = options.maxCharsPerCell ?? CSV_LIMITS.MAX_CHARS_PER_ADDRESS;

  // 1. Tách và loại bỏ BOM nếu có
  let text = content;
  if (text.charCodeAt(0) === 0xfeff) {
    text = text.slice(1);
  }

  if (!text.trim()) {
    throw new Error('Tệp CSV rỗng hoặc chỉ chứa khoảng trắng.');
  }

  // 2. Nhận diện dấu phân cách
  const delimiter = detectDelimiter(text);

  // 3. Phân tách tokens theo trạng thái máy (State Machine RFC 4180)
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = '';
  let inQuotes = false;
  let i = 0;
  const len = text.length;

  while (i < len) {
    const char = text[i];

    if (inQuotes) {
      if (char === '"') {
        // Kiểm tra xem có phải escaped quote ("") không
        if (i + 1 < len && text[i + 1] === '"') {
          currentCell += '"';
          i += 2;
          continue;
        } else {
          // Kết thúc quote
          inQuotes = false;
          i++;
          continue;
        }
      } else {
        currentCell += char;
        i++;
        continue;
      }
    } else {
      // Khi không nằm trong quotes
      if (char === '"') {
        inQuotes = true;
        i++;
        continue;
      } else if (char === delimiter) {
        currentRow.push(currentCell.trim());
        currentCell = '';
        i++;
        continue;
      } else if (char === '\r') {
        // CRLF hoặc CR
        if (i + 1 < len && text[i + 1] === '\n') {
          i += 2;
        } else {
          i++;
        }
        currentRow.push(currentCell.trim());
        currentCell = '';
        if (currentRow.some(c => c.length > 0)) {
          rows.push(currentRow);
        }
        currentRow = [];
        continue;
      } else if (char === '\n') {
        // LF
        i++;
        currentRow.push(currentCell.trim());
        currentCell = '';
        if (currentRow.some(c => c.length > 0)) {
          rows.push(currentRow);
        }
        currentRow = [];
        continue;
      } else {
        currentCell += char;
        i++;
        continue;
      }
    }
  }

  // Đẩy ô và dòng cuối cùng nếu còn
  if (currentCell.length > 0 || currentRow.length > 0) {
    currentRow.push(currentCell.trim());
    if (currentRow.some(c => c.length > 0)) {
      rows.push(currentRow);
    }
  }

  if (rows.length === 0) {
    throw new Error('Không tìm thấy dòng dữ liệu nào trong tệp CSV.');
  }

  // 4. Lấy headers từ dòng đầu tiên
  const rawHeaders = rows[0];
  const headers = rawHeaders.map((h, idx) => (h.trim() ? h.trim() : `Cột_${idx + 1}`));

  const dataRows = rows.slice(1);

  if (dataRows.length === 0) {
    throw new Error('Tệp CSV chỉ có dòng tiêu đề, không có dòng dữ liệu nào.');
  }

  if (dataRows.length > maxRows) {
    throw new Error(
      `Tệp CSV chứa ${dataRows.length.toLocaleString('vi-VN')} dòng dữ liệu, vượt quá giới hạn cho phép (${maxRows.toLocaleString('vi-VN')} dòng/phiên). Vui lòng chia nhỏ tệp.`
    );
  }

  // 5. Chuyển thành danh sách Record và kiểm tra độ dài ô
  const formattedRows: Record<string, string>[] = [];

  for (let rIdx = 0; rIdx < dataRows.length; rIdx++) {
    const row = dataRows[rIdx];
    const record: Record<string, string> = {
      _row_index: String(rIdx + 1),
    };

    for (let cIdx = 0; cIdx < headers.length; cIdx++) {
      const headerName = headers[cIdx];
      const cellValue = row[cIdx] ?? '';

      if (cellValue.length > maxChars) {
        throw new Error(
          `Dòng ${rIdx + 2}, cột "${headerName}" có độ dài ${cellValue.length.toLocaleString('vi-VN')} ký tự, vượt quá giới hạn tối đa ${maxChars.toLocaleString('vi-VN')} ký tự.`
        );
      }

      record[headerName] = cellValue;
    }
    formattedRows.push(record);
  }

  // 6. Gợi ý cột địa chỉ phù hợp
  const detectedCol = detectAddressColumn(headers, formattedRows);

  return {
    headers,
    rows: formattedRows,
    totalRows: formattedRows.length,
    delimiter,
    detectedAddressColumn: detectedCol,
  };
}

/**
 * Gợi ý cột chứa địa chỉ dựa trên tên cột và nội dung dữ liệu
 */
export function detectAddressColumn(headers: string[], sampleRows: Record<string, string>[]): string {
  const keywords = [
    'địa chỉ',
    'dia_chi',
    'diachi',
    'address',
    'addr',
    'dau_vao',
    'input',
    'nơi ở',
    'địa chỉ cư trú',
    'dia chi',
  ];

  // 1. Kiểm tra theo tên header
  for (const h of headers) {
    const lower = h.toLowerCase().trim();
    if (keywords.some(k => lower.includes(k))) {
      return h;
    }
  }

  // 2. Kiểm tra theo nội dung ô nếu header không rõ ràng
  if (sampleRows.length > 0) {
    const addressClues = ['đường', 'phố', 'phường', 'quận', 'thành phố', 'huyện', 'tỉnh', 'xã', 'thị trấn', 'số'];
    let bestHeader = headers[0];
    let maxClueMatches = -1;

    for (const h of headers) {
      let matches = 0;
      for (const row of sampleRows.slice(0, 5)) {
        const val = (row[h] || '').toLowerCase();
        for (const clue of addressClues) {
          if (val.includes(clue)) matches++;
        }
      }
      if (matches > maxClueMatches) {
        maxClueMatches = matches;
        bestHeader = h;
      }
    }

    if (maxClueMatches > 0) {
      return bestHeader;
    }
  }

  return headers[0] || 'Cột_1';
}

/**
 * Phân tích danh sách địa chỉ dán trực tiếp (mỗi dòng một địa chỉ)
 */
export function parsePastedLines(text: string, maxRows = CSV_LIMITS.MAX_ROWS, maxChars = CSV_LIMITS.MAX_CHARS_PER_ADDRESS): string[] {
  if (!text || !text.trim()) {
    return [];
  }

  const rawLines = text.split(/\r\n|\n|\r/);
  // Loại bỏ các dòng hoàn toàn rỗng ở đầu và cuối, nhưng giữ nguyên các dòng giữa để giữ chỉ số
  const lines = rawLines.map(l => l.trim()).filter(l => l.length > 0);

  if (lines.length > maxRows) {
    throw new Error(
      `Danh sách dán có ${lines.length.toLocaleString('vi-VN')} dòng, vượt quá giới hạn tối đa ${maxRows.toLocaleString('vi-VN')} dòng/phiên.`
    );
  }

  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length > maxChars) {
      throw new Error(
        `Dòng ${i + 1} có độ dài ${lines[i].length.toLocaleString('vi-VN')} ký tự, vượt quá giới hạn ${maxChars.toLocaleString('vi-VN')} ký tự.`
      );
    }
  }

  return lines;
}
