"""Adapter span/emission -> lưới token; không chạy mạng và không chọn mã đích."""
import math
import unicodedata
from .crf_chi_tiet import NguCanhCRF
from .tach_phan_con import FIELDS
from .tien_xu_ly import Token, token_co_vi_tri
from .nhan import TAGS, TAG_ID, tag_spans

class NguCanhChar(NguCanhCRF):
    def __init__(self, raw, normalized, offsets, tags, log_probs):
        spans = []
        for role, a, b in tag_spans(tags):
            while a < b and not normalized[a].isalnum():
                a += 1
            while a < b and not normalized[b-1].isalnum():
                b -= 1
            if a < b:
                spans.append((role, offsets[a][0], offsets[b-1][1]))
        boundaries = {p for _, a, b in spans for p in (a, b)}
        records = []
        for tok in token_co_vi_tri(raw):
            if tok.chu.isalpha():
                cuts = [tok.bat_dau, tok.ket_thuc]
            else:
                cuts = sorted({tok.bat_dau, tok.ket_thuc} | {b for b in boundaries if tok.bat_dau < b < tok.ket_thuc})
            for a, b in zip(cuts, cuts[1:]):
                records.append(Token(unicodedata.normalize('NFC', raw[a:b]), a, b))
        labels, p_o, probabilities = [], [], []
        for t in records:
            chars = [j for j, (a, b) in enumerate(offsets) if t.bat_dau <= a and b <= t.ket_thuc]
            lp = log_probs[chars].mean(0).tolist() if chars else [math.log(1 / len(TAGS))] * len(TAGS)
            role = next((r for r, a, b in spans if a <= t.bat_dau and t.ket_thuc <= b), None)
            begins = any(r == role and a == t.bat_dau for r, a, _ in spans)
            labels.append(('B-' if begins else 'I-') + role if role in FIELDS else 'O')
            p_o.append(math.exp(lp[0]))
            probabilities.append(lp)
        super().__init__([t.chu for t in records], labels, p_o)
        self.records, self.char_spans, self.role_log_probs = records, spans, probabilities
        self.loi_bio = 0  # Viterbi không cho I thiếu B/I cùng vai trò phía trước.

    def diem_ung_vien(self, u):
        ids = [TAG_ID['B-' + u.cap], TAG_ID['I-' + u.cap]]
        return sum(max(self.role_log_probs[i][j] for j in ids) for i in range(u.bat_dau, u.ket_thuc)) / max(1, u.ket_thuc - u.bat_dau)

    def diem_hanh_chinh(self, occupied):
        # Điểm tương thích vùng hành chính: O/xa/huyen/tinh, loại các vai trò chi tiết.
        ids = [0] + [TAG_ID[p + r] for r in ('xa', 'huyen', 'tinh') for p in ('B-', 'I-')]
        return sum(max(self.role_log_probs[i][j] for j in ids) for i in occupied)
