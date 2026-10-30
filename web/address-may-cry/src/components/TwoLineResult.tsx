import React from 'react';
import type { KetQuaHaiDong } from '../shared/contracts';
import { CopyButton } from './CopyButton';
import './components.css';

/** Hai dòng kết quả nổi bật: có đối chiếu (xã/phường + tỉnh mới) và thiếu dữ liệu đối chiếu (chi tiết nhà/đường). */
export function TwoLineResult({ data }: { data: KetQuaHaiDong }) {
  const co = data.co_doi_chieu;
  const thieu = data.thieu_du_lieu_doi_chieu;
  return (
    <div className="two-lines">
      <section className="line-card line-ok" aria-labelledby="line-co-title">
        <div className="line-head">
          <h3 id="line-co-title" className="line-title">
            <span className="line-dot" aria-hidden="true" />Có đối chiếu
          </h3>
          <span className="line-sub">Xã/phường và tỉnh/thành mới, mốc 01/07/2025</span>
        </div>
        <div className="line-body">
          <p className={`line-value ${co.chuoi ? '' : 'is-empty'}`}>
            {co.chuoi || 'Chưa xác định được xã/phường và tỉnh/thành mới.'}
          </p>
          {co.chuoi && <CopyButton text={co.chuoi} what="dòng có đối chiếu" />}
        </div>
        {(co.ma_xa || co.ma_tinh) && (
          <dl className="line-codes">
            {co.ma_xa && <div><dt>Mã xã/phường</dt><dd className="mono">{co.ma_xa}</dd></div>}
            {co.ma_tinh && <div><dt>Mã tỉnh/thành</dt><dd className="mono">{co.ma_tinh}</dd></div>}
          </dl>
        )}
      </section>

      <section className="line-card line-lack" aria-labelledby="line-thieu-title">
        <div className="line-head">
          <h3 id="line-thieu-title" className="line-title">
            <span className="line-dot" aria-hidden="true" />Thiếu dữ liệu đối chiếu
          </h3>
          <span className="line-sub">Số nhà, ngõ, thôn, đường</span>
        </div>
        <div className="line-body">
          <p className={`line-value ${thieu.chuoi ? '' : 'is-empty'}`}>
            {thieu.chuoi || 'Địa chỉ không có số nhà, ngõ, thôn hay đường.'}
          </p>
          {thieu.chuoi && <CopyButton text={thieu.chuoi} what="dòng thiếu dữ liệu đối chiếu" />}
        </div>
        <p className="line-note">
          {thieu.ghi_chu || 'Chỉ chuẩn hóa cách viết, không có dữ liệu để kiểm đúng sai.'}
        </p>
      </section>
    </div>
  );
}
