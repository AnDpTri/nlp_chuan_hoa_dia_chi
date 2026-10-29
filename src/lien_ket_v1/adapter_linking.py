"""Adapter thử nghiệm tích hợp điểm liên kết thực thể (Neural Linking Score)
vào lựa chọn giả thuyết chuẩn hóa và đánh giá độc lập / end-to-end.
Tách biệt hoàn toàn với chế độ mặc định (default).
"""

import time
import json
import torch
from pathlib import Path
from .du_lieu_linking import extract_geo_features


class NeuralLinkingAdapter:
    """Adapter đưa điểm từ Neural Linking Head vào quá trình xếp hạng giả thuyết."""

    def __init__(self, linking_head, cache_manager, danh_muc, weight_linking=0.4, device="cpu"):
        self.head = linking_head
        self.head.eval()
        self.cache = cache_manager
        self.dm = danh_muc
        self.weight = weight_linking
        self.device = torch.device(device)
        self.head.to(self.device)

    def score_single_candidate(self, mention_vec, cand_obj, span_text="", parent_support=False):
        """Chấm điểm 1 ứng viên cụ thể với mention vector."""
        cand_vec = self.cache.get_candidate_vector(cand_obj.cay, cand_obj.ma)
        if cand_vec is None:
            return 0.0

        dv = self.dm.don_vi.get((cand_obj.cay, cand_obj.ma))
        if not dv:
            return 0.0
        kieu_khop = getattr(cand_obj, "kieu_khop", "chinh_xac")
        co_tien_to = getattr(cand_obj, "co_tien_to", False)

        geo = extract_geo_features(
            span_text=span_text or dv.ten,
            cand_dv=dv,
            kieu_khop=kieu_khop,
            co_tien_to=co_tien_to,
            parent_support=parent_support
        )

        with torch.no_grad():
            m_t = mention_vec.unsqueeze(0).to(self.device)
            c_t = cand_vec.unsqueeze(0).to(self.device)
            g_t = torch.tensor([geo], dtype=torch.float32, device=self.device)
            score = self.head(m_t, c_t, g_t).item()

        return score

    def rerank_paths(self, ranked_items, mention_vec_by_role, tokens):
        """Xếp hạng lại các đường đi giả thuyết dựa trên điểm liên kết thực thể."""
        reranked = []
        for item in ranked_items:
            score, path, detail, spans, unknown, inferred = item
            linking_bonus = 0.0

            for u in path.ung_vien:
                m_vec = mention_vec_by_role.get(u.cap)
                if m_vec is not None:
                    span_text = " ".join(tokens[u.bat_dau:u.ket_thuc])
                    parent_support = any(
                        self.dm.tuong_thich(self.dm.lay(u.cay, u.ma), self.dm.lay(p.cay, p.ma))
                        for p in path.ung_vien if p.cap in ("huyen", "tinh") and p != u
                    )
                    c_score = self.score_single_candidate(m_vec, u, span_text, parent_support)
                    linking_bonus += c_score

            total_score = score + self.weight * linking_bonus
            reranked.append((total_score, path, detail, spans, unknown, inferred, linking_bonus))

        reranked.sort(key=lambda x: x[0], reverse=True)
        # Trả về format chuẩn tương thích pipeline cũ kèm linking bonus
        return [(x[0], x[1], x[2], x[3], x[4], x[5]) for x in reranked]

    def evaluate_linking_independent(self, test_instances):
        """Đo đạc độc lập chất lượng của Linking Head: Top-1, Recall@3, Recall@5, Coverage, Ambiguity."""
        total = len(test_instances)
        if total == 0:
            return {}

        top1_correct = 0
        top3_correct = 0
        top5_correct = 0
        coverage = 0
        ambiguous_cases = 0

        for inst in test_instances:
            m_vec = inst["mention_vec"]
            cands = inst["candidates"]
            span_text = inst.get("span_text", "")

            # Kiểm tra xem có positive trong candidates không
            pos_indices = [i for i, c in enumerate(cands) if c.get("is_positive")]
            if not pos_indices:
                continue
            coverage += 1
            pos_idx = pos_indices[0]

            scores = []
            for c in cands:
                dv = self.dm.lay(c["cay"], c["ma"])
                geo = c.get("geo_features") or extract_geo_features(span_text, dv)
                cand_vec = self.cache.get_candidate_vector(c["cay"], c["ma"])
                if cand_vec is None:
                    scores.append(-999.0)
                    continue
                with torch.no_grad():
                    m_t = m_vec.unsqueeze(0).to(self.device)
                    c_t = cand_vec.unsqueeze(0).to(self.device)
                    g_t = torch.tensor([geo], dtype=torch.float32, device=self.device)
                    sc = self.head(m_t, c_t, g_t).item()
                    scores.append(sc)

            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

            if ranked_indices[0] == pos_idx:
                top1_correct += 1
            if pos_idx in ranked_indices[:3]:
                top3_correct += 1
            if pos_idx in ranked_indices[:5]:
                top5_correct += 1

            if len(scores) >= 2:
                top1_sc = scores[ranked_indices[0]]
                top2_sc = scores[ranked_indices[1]]
                if abs(top1_sc - top2_sc) < 0.15: # Sai biệt sát nút
                    ambiguous_cases += 1

        return {
            "total_instances": total,
            "coverage_count": coverage,
            "coverage_pct": round(coverage / total * 100, 3),
            "top1_accuracy": round(top1_correct / max(1, coverage) * 100, 3),
            "recall_at_3": round(top3_correct / max(1, coverage) * 100, 3),
            "recall_at_5": round(top5_correct / max(1, coverage) * 100, 3),
            "ambiguity_count": ambiguous_cases,
            "ambiguity_pct": round(ambiguous_cases / total * 100, 3)
        }
