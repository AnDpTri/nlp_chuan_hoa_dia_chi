"""Khôi phục tên đường bằng từ điển và span chi tiết."""


def thu_ung_vien_duong(tu_dien_duong, cand: str, ma_tinh: str, tien_to_mac_dinh: bool = True, tien_to_duong: bool | None = None):
    cand_matches = tu_dien_duong.ung_vien(cand, ma_tinh)
    if len(cand_matches) == 1 and cand_matches[0]['tuong_thich_dau']:
        cand_new, cand_ev = tu_dien_duong.chuan_hoa(
            cand, ma_tinh,
            tien_to_mac_dinh=tien_to_mac_dinh,
            tien_to_duong=tien_to_duong
        )
        return cand_new, (cand_ev or cand_matches[0])
    return None, None


def loc_tien_to_phong_tang(detail):
    if detail.get('duong') and detail['duong'].casefold().replace('đường ', '').replace('phố ', '').startswith(('phòng ', 'tầng ', 'căn hộ ', 'tòa nhà ', 'kios ', 'gian hàng ')):
        detail = dict(detail)
        detail['duong'] = ''
    return detail


def mo_rong_duong_tu_unknown(curr_duong, current_new_duong, duong_spans, tokens, unknown, ma_tinh,
                             tu_dien_duong, tien_to_mac_dinh=True, tien_to_duong=None):
    new_duong = current_new_duong
    name_evidence = None
    end_idx = duong_spans[-1]['ket_thuc']
    cand = curr_duong
    while end_idx < len(tokens) and end_idx in unknown and tokens[end_idx] not in {',', ';', '.', '-'}:
        cand = cand + ' ' + tokens[end_idx]
        cand_new, cand_ev = thu_ung_vien_duong(
            tu_dien_duong, cand, ma_tinh,
            tien_to_mac_dinh=tien_to_mac_dinh,
            tien_to_duong=tien_to_duong
        )
        if cand_new is not None:
            new_duong = cand_new
            name_evidence = cand_ev
            unknown = [u for u in unknown if u != end_idx]
            break
        end_idx += 1
    if not name_evidence:
        start_idx = duong_spans[0]['bat_dau']
        cand = curr_duong
        while start_idx - 1 >= 0 and (start_idx - 1) in unknown and tokens[start_idx - 1] not in {',', ';', '.', '-'}:
            cand = tokens[start_idx - 1] + ' ' + cand
            cand_new, cand_ev = thu_ung_vien_duong(
                tu_dien_duong, cand, ma_tinh,
                tien_to_mac_dinh=tien_to_mac_dinh,
                tien_to_duong=tien_to_duong
            )
            if cand_new is not None:
                new_duong = cand_new
                name_evidence = cand_ev
                unknown = [u for u in unknown if u != start_idx - 1]
                break
            start_idx -= 1
    return new_duong, name_evidence, unknown


def khoi_phuc_tu_so_nha(duong_spans, spans, tokens, detail, ma_tinh, tu_dien_duong,
                        tien_to_mac_dinh=True, tien_to_duong=None, tien_to_so_nha=None):
    so_nha_spans = [s for s in spans if s.get('truong') == 'so_nha']
    if not (duong_spans and so_nha_spans):
        return None, None
    d_start = duong_spans[0]['bat_dau']
    d_end = duong_spans[-1]['ket_thuc']
    sns = so_nha_spans[-1]
    if sns['ket_thuc'] == d_start and tokens[d_start - 1].isdigit():
        cand = ' '.join(tokens[d_start - 1 : d_end])
        cand_new, cand_ev = thu_ung_vien_duong(
            tu_dien_duong, cand, ma_tinh,
            tien_to_mac_dinh=tien_to_mac_dinh,
            tien_to_duong=tien_to_duong
        )
        if cand_new is not None:
            sns['ket_thuc'] -= 1
            if sns['ket_thuc'] <= sns['bat_dau']:
                detail['so_nha'] = ''
            else:
                from .crf_chi_tiet import dinh_dang_span
                detail['so_nha'], _ = dinh_dang_span(
                    tokens[sns['bat_dau']:sns['ket_thuc']], 'so_nha',
                    tien_to_mac_dinh=tien_to_mac_dinh,
                    tien_to_so_nha=tien_to_so_nha
                )
            return cand_new, cand_ev
    return None, None


def dung_lai_tu_span_cnn(duong_spans, tokens, ma_tinh, tu_dien_duong, tien_to_mac_dinh=True, tien_to_duong=None):
    if not (ma_tinh and duong_spans):
        return None, None
    cand = ' '.join(tokens[duong_spans[0]['bat_dau']:duong_spans[-1]['ket_thuc']])
    return thu_ung_vien_duong(tu_dien_duong, cand, ma_tinh, tien_to_mac_dinh=tien_to_mac_dinh, tien_to_duong=tien_to_duong)


def khoi_phuc_tu_spans(curr_duong, new_duong, duong_spans, spans, tokens, unknown, detail, ma_tinh,
                       tu_dien_duong, tien_to_mac_dinh=True, tien_to_duong=None, tien_to_so_nha=None):
    new_duong, name_evidence, unknown = mo_rong_duong_tu_unknown(
        curr_duong, new_duong, duong_spans, tokens, unknown, ma_tinh, tu_dien_duong,
        tien_to_mac_dinh, tien_to_duong
    )
    verified = bool(name_evidence)
    if not verified and curr_duong and ma_tinh:
        ung = tu_dien_duong.ung_vien(curr_duong, ma_tinh)
        if len(ung) == 1 and ung[0]['tuong_thich_dau']:
            verified = True
    if not verified and ma_tinh:
        cand_new, cand_ev = khoi_phuc_tu_so_nha(
            duong_spans, spans, tokens, detail, ma_tinh, tu_dien_duong,
            tien_to_mac_dinh, tien_to_duong, tien_to_so_nha
        )
        if cand_new is not None:
            new_duong = cand_new
            name_evidence = cand_ev
            verified = True
    if not verified and ma_tinh:
        cand_new, cand_ev = dung_lai_tu_span_cnn(
            duong_spans, tokens, ma_tinh, tu_dien_duong,
            tien_to_mac_dinh, tien_to_duong
        )
        if cand_new is not None:
            new_duong = cand_new
            name_evidence = cand_ev
            verified = True
    return new_duong, name_evidence, unknown


def quet_token_chua_phan_loai(tokens, unknown, ma_tinh, tu_dien_duong, tien_to_mac_dinh=True, tien_to_duong=None):
    if not (ma_tinh and unknown):
        return None, None, unknown
    u_sorted = sorted(unknown)
    groups = []
    curr_g = [u_sorted[0]]
    for idx in u_sorted[1:]:
        if idx == curr_g[-1] + 1 and tokens[idx] not in {',', ';', '.', '-'}:
            curr_g.append(idx)
        else:
            groups.append(curr_g)
            curr_g = [idx]
    groups.append(curr_g)

    # Giữ nguyên ngữ nghĩa bản gốc: KHÔNG dừng sau nhóm đầu tiên. Nhóm sau khớp thì ghi đè
    # kết quả và loại thêm token khỏi unknown; sau mỗi nhóm, vòng start dừng khi đã có tên.
    new_duong, name_evidence = None, None
    for g in groups:
        for start in range(len(g)):
            for end in range(start + 1, min(start + 7, len(g) + 1)):
                sub_phrase = ' '.join(tokens[g[k]] for k in range(start, end))
                cand_new, cand_ev = thu_ung_vien_duong(
                    tu_dien_duong, sub_phrase, ma_tinh,
                    tien_to_mac_dinh=tien_to_mac_dinh,
                    tien_to_duong=tien_to_duong
                )
                if cand_new is not None:
                    new_duong = cand_new
                    name_evidence = cand_ev
                    unknown = [u for u in unknown if u not in g[start:end]]
                    break
            if new_duong:
                break
    return new_duong, name_evidence, unknown


def phuc_hoi_ten_duong(detail, spans, unknown, tokens, ma_tinh, tu_dien_duong, hop_dong,
                       tien_to_mac_dinh=True, tien_to_duong=None, tien_to_so_nha=None):
    name_evidence = None
    detail = loc_tien_to_phong_tang(detail)
    if tu_dien_duong is None or hop_dong:
        return detail, spans, unknown, name_evidence

    detail = dict(detail)
    curr_duong = detail['duong']
    new_duong, name_evidence = tu_dien_duong.chuan_hoa(
        curr_duong, ma_tinh,
        tien_to_mac_dinh=tien_to_mac_dinh,
        tien_to_duong=tien_to_duong
    )
    if not name_evidence and curr_duong and ma_tinh:
        duong_spans = [s for s in spans if s.get('truong') == 'duong']
        if duong_spans:
            new_duong, name_evidence, unknown = khoi_phuc_tu_spans(
                curr_duong, new_duong, duong_spans, spans, tokens, unknown, detail,
                ma_tinh, tu_dien_duong, tien_to_mac_dinh, tien_to_duong, tien_to_so_nha
            )

    if not new_duong and ma_tinh and unknown:
        cand_new, cand_ev, unknown = quet_token_chua_phan_loai(
            tokens, unknown, ma_tinh, tu_dien_duong,
            tien_to_mac_dinh=tien_to_mac_dinh,
            tien_to_duong=tien_to_duong
        )
        if cand_new is not None:
            new_duong = cand_new
            name_evidence = cand_ev

    detail['duong'] = new_duong
    return detail, spans, unknown, name_evidence
