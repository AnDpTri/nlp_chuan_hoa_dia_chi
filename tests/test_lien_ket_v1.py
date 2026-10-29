"""Bộ kiểm thử độc lập cho module liên kết thực thể (Neural Entity Linking).
Kiểm tra:
1. Frozen encoder: weights không đổi, chỉ head có gradient.
2. Candidate cache: xác thực hash chặt chẽ, từ chối nạp khi lệch hash.
3. Hard negatives & bảo vệ false negative.
4. Xử lý ca mơ hồ và phân biệt mốc nguồn / đích.
5. Zero family leakage giữa Train và Validation nội bộ.
6. Checkpoint roundtrip (save/load).
7. Tiny smoke training trên CPU thật: loss finite, optimizer cập nhật đúng.
8. Adapter reranking flow.
"""

import unittest
import tempfile
import json
import torch
import torch.nn as nn
from pathlib import Path

from src.lien_ket_v1.mo_hinh_linking import NeuralLinkingHead, ViDeBERTaLinkingModel
from src.lien_ket_v1.cache_ung_vien import CandidateCacheManager, compute_cache_validation_hash
from src.lien_ket_v1.du_lieu_linking import (
    extract_geo_features,
    compute_string_similarity,
    split_dataset_by_family,
    LinkingSampleBuilder
)
from src.lien_ket_v1.adapter_linking import NeuralLinkingAdapter
from src.danh_muc import DanhMuc


class MockTinyEncoder(nn.Module):
    """Encoder giả lập kích thước nhỏ để chạy test trên CPU nhẹ nhàng và nhanh chóng."""
    def __init__(self, hidden_size=384):
        super().__init__()
        self.hidden_size = hidden_size
        self.embedding = nn.Embedding(100, hidden_size)
        self.linear = nn.Linear(hidden_size, hidden_size)

    def forward(self, input_ids, attention_mask=None):
        x = self.embedding(input_ids)
        x = self.linear(x)
        class Output:
            pass
        out = Output()
        out.last_hidden_state = x
        return out


class TestLienKetV1(unittest.TestCase):

    def setUp(self):
        torch.manual_seed(42)
        self.dm = DanhMuc()

    def test_encoder_freeze_and_head_gradients(self):
        """1. Kiểm tra Encoder ViDeBERTa đóng băng 100%, chỉ Linking Head nhận gradient và đổi weights."""
        encoder = MockTinyEncoder(hidden_size=384)
        model = ViDeBERTaLinkingModel(encoder=encoder, enc_dim=384, proj_dim=64, geo_dim=12, hidden_dim=64)

        # Kiểm tra encoder đóng băng
        for p in model.encoder.parameters():
            self.assertFalse(p.requires_grad, "Encoder parameter vẫn có requires_grad=True")

        # Kiểm tra head sẵn sàng học
        for p in model.head.parameters():
            self.assertTrue(p.requires_grad, "Head parameter phải có requires_grad=True")

        # Lưu weights ban đầu
        old_enc_weight = model.encoder.linear.weight.clone()
        old_head_weight = model.head.mlp[0].weight.clone()

        # Giả lập 1 bước forward + backward
        opt = torch.optim.Adam(model.head.parameters(), lr=1e-3)
        mention_vecs = torch.randn(4, 384)
        cand_vecs = torch.randn(4, 384)
        geo_feats = torch.randn(4, 12)
        targets = torch.tensor([1.0, 0.0, 0.0, 0.0])

        scores = model.head(mention_vecs, cand_vecs, geo_feats)
        loss = nn.functional.binary_cross_entropy_with_logits(scores, targets)
        loss.backward()

        # Kiểm tra gradient
        for p in model.encoder.parameters():
            self.assertIsNone(p.grad, "Encoder không được nhận bất kỳ gradient nào")

        has_head_grad = any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.head.parameters())
        self.assertTrue(has_head_grad, "Head bắt buộc phải có gradient")

        opt.step()

        # Kiểm tra weights sau cập nhật
        self.assertTrue(torch.equal(old_enc_weight, model.encoder.linear.weight), "Encoder weights bị thay đổi!")
        self.assertFalse(torch.equal(old_head_weight, model.head.mlp[0].weight), "Head weights chưa được cập nhật!")

    def test_candidate_cache_hash_integrity_and_mismatch_rejection(self):
        """2. Kiểm tra xác thực hash của Candidate Cache; từ chối nạp khi lệch hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            cache_file = tmp_p / "candidate_cache.pt"
            meta_file = tmp_p / "candidate_cache_meta.json"

            dummy_embeds = torch.randn(5, 384)
            key_to_idx = {f"moi_xa_{i}": i for i in range(5)}
            torch.save({"embeddings": dummy_embeds, "key_to_idx": key_to_idx}, cache_file)

            valid_hash = "abcdef1234567890"
            meta_file.write_text(json.dumps({
                "format": "candidate_cache_v1",
                "validation_hash": valid_hash,
                "metadata_map": {}
            }), encoding="utf-8")

            mgr = CandidateCacheManager()

            # Nạp đúng hash -> Thành công
            meta = mgr.load_cache(cache_file, meta_file, expected_hash=valid_hash)
            self.assertEqual(meta["validation_hash"], valid_hash)
            self.assertEqual(mgr.embeddings.size(0), 5)

            # Nạp sai hash -> Bắt buộc ném ValueError
            with self.assertRaises(ValueError) as ctx:
                mgr.load_cache(cache_file, meta_file, expected_hash="wrong_hash_9999")
            self.assertIn("Cache hash mismatch", str(ctx.exception))

    def test_hard_negatives_and_no_false_negatives(self):
        """3. Kiểm tra sinh Hard Negatives cùng tên khác địa bàn và không gán nhãn âm cho đơn vị tương đương mốc 2025."""
        # Lấy cặp thật từ danh mục
        sample_old = next((dv for dv in self.dm.don_vi.values() if dv.cay == "cu" and dv.cap == "xa"), None)
        sample_new = next((dv for dv in self.dm.don_vi.values() if dv.cay == "moi" and dv.cap == "xa"), None)
        doi_chieu_mock = [{"ma_xa_cu": sample_old.ma, "ma_xa_moi": sample_new.ma}] if sample_old and sample_new else []
        builder = LinkingSampleBuilder(self.dm, doi_chieu_mock)

        if sample_old and sample_new:
            is_equiv = builder.is_equivalent_target(sample_old, sample_new)
            self.assertTrue(is_equiv, "Đơn vị cũ và mới tương ứng qua đổi chiếu phải được coi là tương đương")

        # Test khai thác negative
        sample_dv = next(iter(self.dm.don_vi.values()))
        negs = builder.mine_negatives(sample_dv, sample_dv.ten, num_hard=2, num_random=2)
        self.assertGreater(len(negs), 0)
        for neg in negs:
            self.assertFalse(builder.is_equivalent_target(sample_dv, neg), "Negative không được tương đương với Positive!")

    def test_ambiguity_and_split_ward_policy(self):
        """4. Kiểm tra ca mơ hồ (xã bị chia, viết tắt đa nghĩa) không bị ép gán 1 mã đích đơn nhất."""
        split_ward_code = "00019" # Phường Điện Biên cũ (chia làm nhiều phường mới)
        doi_chieu_split = [
            {"ma_xa_cu": split_ward_code, "ma_xa_moi": "00004"},
            {"ma_xa_cu": split_ward_code, "ma_xa_moi": "00006"},
            {"ma_xa_cu": split_ward_code, "ma_xa_moi": "00007"}
        ]
        builder = LinkingSampleBuilder(self.dm, doi_chieu_split)
        valid_targets = builder.old_to_new_targets.get(split_ward_code, set())
        self.assertGreater(len(valid_targets), 1, "Xã bị chia phải có nhiều đích đến hợp lệ")
        self.assertIn("00004", valid_targets)
        self.assertIn("00006", valid_targets)

    def test_no_family_leakage_between_train_and_val(self):
        """5. Kiểm tra phân chia Train và Validation nội bộ theo họ nguồn cha (Zero Family Leakage)."""
        mock_rows = []
        for fid_idx in range(50):
            fid = f"FAM_MOCK_{fid_idx:03d}"
            for v in range(4):
                mock_rows.append({"id": f"ID_{fid_idx}_{v}", "training_group": fid, "text": f"Mẫu {v} của họ {fid}"})

        split_res = split_dataset_by_family(mock_rows, val_ratio=0.2, seed=123)
        train_rows = split_res["train_rows"]
        val_rows = split_res["val_rows"]

        train_fams = set(split_res["train_families"])
        val_fams = set(split_res["val_families"])

        self.assertGreater(len(train_rows), 0)
        self.assertGreater(len(val_rows), 0)
        self.assertEqual(len(train_fams & val_fams), 0, "Rò rỉ họ nguồn cha giữa Train và Val!")

        train_row_fams = {r["training_group"] for r in train_rows}
        val_row_fams = {r["training_group"] for r in val_rows}
        self.assertEqual(len(train_row_fams & val_row_fams), 0, "Rò rỉ họ trong các dòng train/val!")

    def test_head_checkpoint_roundtrip(self):
        """6. Kiểm tra lưu và nạp checkpoint Linking Head (Roundtrip consistency)."""
        head = NeuralLinkingHead(enc_dim=384, proj_dim=64, geo_dim=12, hidden_dim=64)
        head.eval()
        m_vec = torch.randn(2, 384)
        c_vec = torch.randn(2, 384)
        g_feat = torch.randn(2, 12)

        with torch.no_grad():
            score_before = head(m_vec, c_vec, g_feat)

        with tempfile.TemporaryDirectory() as tmpdir:
            model = ViDeBERTaLinkingModel(encoder=None, enc_dim=384, proj_dim=64, geo_dim=12, hidden_dim=64)
            model.head = head
            model.save_head(tmpdir, extra_meta={"test": "ok"})

            model_new = ViDeBERTaLinkingModel(encoder=None, enc_dim=384, proj_dim=64, geo_dim=12, hidden_dim=64)
            model_new.load_head(tmpdir)
            model_new.head.eval()

            with torch.no_grad():
                score_after = model_new.head(m_vec, c_vec, g_feat)

            self.assertTrue(torch.allclose(score_before, score_after, atol=1e-6), "Điểm số sau load checkpoint không khớp!")

    def test_tiny_cpu_smoke_training(self):
        """7. Tiny CPU smoke training: Kiểm tra chạy 3 bước optimizer thật trên CPU (loss hữu hạn và giảm dần)."""
        head = NeuralLinkingHead(enc_dim=64, proj_dim=32, geo_dim=12, hidden_dim=32)
        opt = torch.optim.Adam(head.parameters(), lr=0.01)

        losses = []
        # Tạo batch cố định
        m_batch = torch.randn(8, 64)
        c_batch = torch.randn(8, 64)
        g_batch = torch.randn(8, 12)
        labels = torch.tensor([1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])

        for step in range(5):
            opt.zero_grad()
            scores = head(m_batch, c_batch, g_batch)
            loss = nn.functional.binary_cross_entropy_with_logits(scores, labels)
            self.assertTrue(torch.isfinite(loss), f"Loss bị NaN hoặc Inf tại step {step}")
            loss.backward()
            opt.step()
            losses.append(loss.item())

        self.assertLess(losses[-1], losses[0], "Loss không giảm sau các bước gradient descent!")

    def test_adapter_reranking_flow(self):
        """8. Kiểm tra luồng tính điểm và rerank của NeuralLinkingAdapter."""
        head = NeuralLinkingHead(enc_dim=384, proj_dim=64, geo_dim=12, hidden_dim=64)
        sample_dv = next(iter(self.dm.don_vi.values()))
        cache_mgr = CandidateCacheManager()
        # Tạo cache giả lập
        cache_mgr.embeddings = torch.randn(10, 384)
        cache_mgr.key_to_idx = {f"{sample_dv.cay}_{sample_dv.ma}": 0}

        adapter = NeuralLinkingAdapter(head, cache_mgr, self.dm, weight_linking=0.5)

        class MockUngVien:
            def __init__(self, cay, ma, cap, bat_dau, ket_thuc):
                self.cay = cay
                self.ma = ma
                self.cap = cap
                self.bat_dau = bat_dau
                self.ket_thuc = ket_thuc
                self.kieu_khop = "chinh_xac"
                self.co_tien_to = True

        class MockPath:
            def __init__(self, ung_vien):
                self.ung_vien = ung_vien

        u1 = MockUngVien(sample_dv.cay, sample_dv.ma, sample_dv.cap, 2, 4)
        path1 = MockPath([u1])
        item1 = (10.0, path1, {}, [], [], False)

        m_vec = torch.randn(384)
        mention_vecs = {sample_dv.cap: m_vec}
        tokens = ["Số", "12", "Lê", "Lợi", "Hà", "Nội"]

        reranked = adapter.rerank_paths([item1], mention_vecs, tokens)
        self.assertEqual(len(reranked), 1)
        # Score mới phải khác điểm gốc vì được cộng thêm linking bonus
        self.assertNotEqual(reranked[0][0], 10.0)

    def test_checkpoint_resume_consistency(self):
        """9. Kiểm tra Resume Checkpoint: Tiếp tục huấn luyện từ checkpoint cho kết quả hội tụ nhất quán."""
        head = NeuralLinkingHead(enc_dim=32, proj_dim=16, geo_dim=12, hidden_dim=16, dropout=0.0)
        opt = torch.optim.Adam(head.parameters(), lr=0.01)

        m_b = torch.randn(4, 32)
        c_b = torch.randn(4, 32)
        g_b = torch.randn(4, 12)
        y_b = torch.tensor([1.0, 0.0, 1.0, 0.0])

        # Step 1
        opt.zero_grad()
        loss1 = nn.functional.binary_cross_entropy_with_logits(head(m_b, c_b, g_b), y_b)
        loss1.backward()
        opt.step()

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "ckpt_epoch_1.pt"
            torch.save({
                "epoch": 1,
                "head_state_dict": head.state_dict(),
                "optimizer_state_dict": opt.state_dict(),
                "loss": loss1.item()
            }, ckpt_path)

            # Khởi tạo head2 và resume
            head2 = NeuralLinkingHead(enc_dim=32, proj_dim=16, geo_dim=12, hidden_dim=16, dropout=0.0)
            opt2 = torch.optim.Adam(head2.parameters(), lr=0.01)
            ckpt = torch.load(ckpt_path)
            head2.load_state_dict(ckpt["head_state_dict"])
            opt2.load_state_dict(ckpt["optimizer_state_dict"])

            # Step 2 tiếp tục trên cả 2
            opt.zero_grad()
            l2_a = nn.functional.binary_cross_entropy_with_logits(head(m_b, c_b, g_b), y_b)
            l2_a.backward()
            opt.step()

            opt2.zero_grad()
            l2_b = nn.functional.binary_cross_entropy_with_logits(head2(m_b, c_b, g_b), y_b)
            l2_b.backward()
            opt2.step()

            self.assertAlmostEqual(l2_a.item(), l2_b.item(), places=5, msg="Resume checkpoint cho loss không nhất quán")

    def test_independent_linking_metrics_calculation(self):
        """10. Kiểm tra hàm đo đạc linking độc lập: Top-1, Recall@K, Ambiguity margin."""
        head = NeuralLinkingHead(enc_dim=32, proj_dim=16, geo_dim=12, hidden_dim=16)
        head.eval()
        sample_dv = next(iter(self.dm.don_vi.values()))

        cache_mgr = CandidateCacheManager()
        cache_mgr.embeddings = torch.randn(5, 32)
        cache_mgr.key_to_idx = {f"{sample_dv.cay}_{sample_dv.ma}": 0}

        adapter = NeuralLinkingAdapter(head, cache_mgr, self.dm, weight_linking=0.5)

        test_instances = [{
            "mention_vec": torch.randn(32),
            "candidates": [
                {"cay": sample_dv.cay, "ma": sample_dv.ma, "is_positive": True},
                {"cay": sample_dv.cay, "ma": sample_dv.ma, "is_positive": False}
            ]
        }]

        metrics = adapter.evaluate_linking_independent(test_instances)
        self.assertIn("top1_accuracy", metrics)
        self.assertIn("recall_at_3", metrics)
        self.assertIn("coverage_pct", metrics)
        self.assertEqual(metrics["coverage_count"], 1)


if __name__ == "__main__":
    unittest.main()
