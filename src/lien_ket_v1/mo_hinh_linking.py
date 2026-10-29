"""Mô hình đầu liên kết thực thể địa chỉ (Neural Entity Linking Head).
Sử dụng ViDeBERTa-xsmall làm shared encoder đóng băng (frozen),
chỉ đầu neural chấm ứng viên (linking head) được huấn luyện.
"""

import json
import torch
import torch.nn as nn
from pathlib import Path


class NeuralLinkingHead(nn.Module):
    """Đầu neural nhỏ học chấm điểm tương thích giữa span ngữ cảnh và ứng viên."""

    def __init__(self, enc_dim=384, proj_dim=128, geo_dim=12, hidden_dim=128, dropout=0.1):
        super().__init__()
        self.enc_dim = enc_dim
        self.proj_dim = proj_dim
        self.geo_dim = geo_dim

        # Chiếu giảm chiều mention và candidate
        self.proj_mention = nn.Linear(enc_dim, proj_dim)
        self.proj_cand = nn.Linear(enc_dim, proj_dim)

        # Vector kết hợp: [u_p, v_p, |u_p - v_p|, u_p * v_p, u_p . v_p (1d), geo (geo_dim)]
        combined_dim = proj_dim * 4 + 1 + geo_dim

        self.mlp = nn.Sequential(
            nn.Linear(combined_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, mention_vecs, cand_vecs, geo_features):
        """
        mention_vecs: [B, enc_dim]
        cand_vecs: [B, enc_dim]
        geo_features: [B, geo_dim]
        return: scores [B]
        """
        u = torch.relu(self.proj_mention(mention_vecs))
        v = torch.relu(self.proj_cand(cand_vecs))

        diff = torch.abs(u - v)
        prod = u * v
        dot = (u * v).sum(dim=-1, keepdim=True)

        combined = torch.cat([u, v, diff, prod, dot, geo_features], dim=-1)
        score = self.mlp(combined).squeeze(-1)
        return score


class ViDeBERTaLinkingModel(nn.Module):
    """Mô hình liên kết thực thể tích hợp Encoder ViDeBERTa đóng băng và Linking Head."""

    def __init__(self, encoder, enc_dim=384, proj_dim=128, geo_dim=12, hidden_dim=128, dropout=0.1):
        super().__init__()
        self.encoder = encoder
        self.head = NeuralLinkingHead(
            enc_dim=enc_dim,
            proj_dim=proj_dim,
            geo_dim=geo_dim,
            hidden_dim=hidden_dim,
            dropout=dropout
        )
        self.freeze_encoder()

    def freeze_encoder(self):
        """Đóng băng 100% tham số của ViDeBERTa encoder."""
        if self.encoder is not None:
            for p in self.encoder.parameters():
                p.requires_grad = False
            assert all(not p.requires_grad for p in self.encoder.parameters()), "Encoder chưa được đóng băng hoàn toàn"

    def unfreeze_encoder_for_debug(self):
        """Chỉ dùng kiểm tra tests so sánh freeze."""
        if self.encoder is not None:
            for p in self.encoder.parameters():
                p.requires_grad = True

    def extract_span_vector(self, hidden_state, piece_for_char, span_start, span_end):
        """Trích xuất embedding của span ký tự từ last_hidden_state của encoder."""
        # hidden_state: [seq_len, enc_dim]
        # piece_for_char: list các subword index cho từng ký tự
        seq_len = hidden_state.size(0)
        cls_vec = hidden_state[0] # token [CLS]

        if span_start is None or span_end is None or span_start >= span_end or span_start >= len(piece_for_char):
            return cls_vec

        end_clamped = min(span_end, len(piece_for_char))
        subword_indices = {piece_for_char[i] for i in range(span_start, end_clamped) if 0 <= piece_for_char[i] < seq_len}

        if not subword_indices:
            return cls_vec

        idx_tensor = torch.tensor(sorted(list(subword_indices)), dtype=torch.long, device=hidden_state.device)
        span_pieces = hidden_state[idx_tensor] # [K, enc_dim]
        span_mean = span_pieces.mean(dim=0)

        # Kết hợp span mean và context CLS
        mention_vec = 0.6 * span_mean + 0.4 * cls_vec
        return mention_vec

    def save_head(self, folder, extra_meta=None):
        """Lưu riêng biệt trọng số của Linking Head và cấu hình."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        head_path = folder / "linking_head.pt"
        torch.save(self.head.state_dict(), head_path)

        meta = {
            "format": "linking_head_v1",
            "enc_dim": self.head.enc_dim,
            "proj_dim": self.head.proj_dim,
            "geo_dim": self.head.geo_dim,
            "extra_meta": extra_meta or {}
        }
        (folder / "linking_config.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_head(self, folder, device="cpu"):
        """Nạp trọng số của Linking Head từ file."""
        folder = Path(folder)
        head_path = folder / "linking_head.pt"
        config_path = folder / "linking_config.json"

        if not head_path.exists() or not config_path.exists():
            raise FileNotFoundError(f"Không tìm thấy checkpoint linking head tại {folder}")

        meta = json.loads(config_path.read_text(encoding="utf-8"))
        state_dict = torch.load(head_path, map_location=device)
        self.head.load_state_dict(state_dict)
        self.head.to(device)
        return meta
