/**
 * Script tự động hóa chụp ảnh kiểm chứng thực tế toàn bộ các trạng thái giao diện Batch Workspace
 * Sử dụng zero-dependency cdp.mjs từ taste-skill.
 */

import { Browser } from 'file:///C:/Users/andan/.gemini/antigravity/brain/388e264d-6447-42fb-b64f-559ba8e2e86d/taste-skill/skills/taste-skill/scripts/lib/cdp.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const OUT_DIR = 'docs/ui-address-may-cry/B_batch/screenshots';
mkdirSync(OUT_DIR, { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function main() {
  console.log('=== KHỞI CHẠY TỰ ĐỘNG HÓA CHỤP ẢNH GIAO DIỆN BATCH WORKSPACE ===');
  const browser = await Browser.launch({ width: 1440, height: 900 });

  try {
    const page = await browser.newPage({ width: 1440, height: 900 });
    const url = 'http://localhost:5173/src/features/batch/harness.html';
    console.log(`Đang truy cập: ${url}...`);
    await page.goto(url, { settleMs: 1500 });

    // 1. Chụp trạng thái ban đầu (Empty / Paste tab)
    console.log('1. Chụp trạng thái ban đầu (1440px)...');
    const sc1 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '01_initial_state_1440.png'), Buffer.from(sc1, 'base64'));

    // 2. Chuyển sang Tab CSV
    console.log('2. Chuyển sang Tab CSV và chụp dropzone...');
    await page.eval(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const csvBtn = btns.find(b => b.textContent?.includes('Kéo / Chọn tệp CSV'));
      if (csvBtn) csvBtn.click();
    });
    await sleep(600);
    const sc2 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '02_csv_dropzone_1440.png'), Buffer.from(sc2, 'base64'));

    // 3. Chuyển lại Tab Dán và bấm "Nạp tất cả 8 mẫu"
    console.log('3. Nạp 8 địa chỉ thực tế và bấm chuẩn hóa...');
    await page.eval(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const pasteBtn = btns.find(b => b.textContent?.includes('Dán danh sách'));
      if (pasteBtn) pasteBtn.click();
    });
    await sleep(400);

    await page.eval(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const sampleBtn = btns.find(b => b.textContent?.includes('Nạp tất cả 8 mẫu'));
      if (sampleBtn) sampleBtn.click();
    });
    await sleep(400);

    // Bấm nút "Bắt đầu chuẩn hóa danh sách"
    await page.eval(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const startBtn = btns.find(b => b.textContent?.includes('Bắt đầu chuẩn hóa danh sách'));
      if (startBtn) startBtn.click();
    });

    // Chờ quá trình xử lý qua API hoàn thành (tối đa 15s)
    console.log('Đang chờ API xử lý chuẩn hóa 8 mẫu qua chunk 20...');
    let done = false;
    for (let i = 0; i < 30; i++) {
      await sleep(500);
      done = await page.eval(() => {
        const rows = document.querySelectorAll('table tbody tr');
        return rows.length >= 8 && !document.querySelector('button')?.textContent?.includes('Hủy dừng tiến trình');
      });
      if (done) break;
    }
    console.log(`Đã xử lý xong (done=${done})`);
    await sleep(800);

    // Chụp trạng thái sau khi đã xử lý thành công
    console.log('4. Chụp bảng kết quả đã xử lý kèm KPIs (1440px)...');
    const sc3 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '03_processed_results_1440.png'), Buffer.from(sc3, 'base64'));

    // 5. Bấm vào dòng đầu tiên để mở ngăn xem chi tiết (Drawer Inspector)
    console.log('5. Mở Drawer Inspector xem chi tiết 6 trường hành chính...');
    await page.eval(() => {
      const firstRow = document.querySelector('table tbody tr');
      if (firstRow) firstRow.click();
    });
    await sleep(600);
    const sc4 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '04_drawer_inspector_1440.png'), Buffer.from(sc4, 'base64'));

    // Đóng drawer
    await page.eval(() => {
      const closeBtn = document.querySelector('aside button[title*="Đóng"]');
      if (closeBtn) closeBtn.click();
    });
    await sleep(400);

    // 6. Lọc trạng thái: Bấm tab "Cần kiểm tra"
    console.log('6. Lọc trạng thái "Cần kiểm tra"...');
    await page.eval(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const filterBtn = btns.find(b => b.textContent?.includes('Cần kiểm tra'));
      if (filterBtn) filterBtn.click();
    });
    await sleep(400);
    const sc5 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '05_filter_needs_review_1440.png'), Buffer.from(sc5, 'base64'));

    // 7. Chuyển sang kích thước Tablet (768px)
    console.log('7. Chuyển sang Tablet viewport (768px)...');
    await page.setViewport({ width: 768, height: 1024 });
    await sleep(600);
    const sc6 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '06_tablet_view_768.png'), Buffer.from(sc6, 'base64'));

    // 8. Chuyển sang kích thước Mobile (390px)
    console.log('8. Chuyển sang Mobile viewport (390px, card view)...');
    await page.setViewport({ width: 390, height: 844, mobile: true });
    await sleep(600);
    const sc7 = await page.screenshot({ format: 'png' });
    writeFileSync(join(OUT_DIR, '07_mobile_cards_390.png'), Buffer.from(sc7, 'base64'));

    console.log('=== HOÀN TẤT CHỤP ẢNH TOÀN BỘ 7 TRẠNG THÁI GIAO DIỆN THỰC TẾ! ===');
  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error('Lỗi khi chụp ảnh:', err);
  process.exit(1);
});
