"""Quản lý tính trước và lưu cache embedding của ứng viên danh mục (Candidate Cache).
Được tính toán bằng Shared ViDeBERTa Encoder đóng băng.
Bắt buộc gắn kèm hash encoder/tokenizer/danh mục/cấu hình để ngăn chặn dùng sai cache.
"""

import hashlib
import json
import torch
from pathlib import Path


def compute_file_sha256(filepath):
    """Tính mã băm SHA-256 của một file."""
    p = Path(filepath)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_cache_validation_hash(encoder_path, tokenizer_path, clean_dir, config_dict=None):
    """Tính mã băm toàn diện kiểm tra tính hợp lệ của cache ứng viên."""
    h = hashlib.sha256()

    # 1. Mã băm encoder và tokenizer
    h.update(compute_file_sha256(encoder_path).encode("utf-8"))
    h.update(compute_file_sha256(tokenizer_path).encode("utf-8"))

    # 2. Mã băm danh mục hành chính
    clean_p = Path(clean_dir)
    for fname in sorted(["moi_tinh_xa.csv", "cu_tinh_huyen_xa.csv", "doi_chieu_xa_cu_moi.csv"]):
        f_file = clean_p / fname
        if f_file.exists():
            h.update(compute_file_sha256(f_file).encode("utf-8"))

    # 3. Mã băm cấu hình
    if config_dict:
        h.update(json.dumps(config_dict, sort_keys=True).encode("utf-8"))

    return h.hexdigest()


class CandidateCacheManager:
    """Quản lý tra cứu và lưu trữ biểu diễn vector ứng viên được tính trước."""

    def __init__(self, cache_file=None, meta_file=None):
        self.key_to_idx = {}
        self.cand_metadata = {}
        self.embeddings = None # torch.FloatTensor [N, enc_dim]
        self.validation_hash = ""
        self.enc_dim = 384

        if cache_file and Path(cache_file).exists():
            self.load_cache(cache_file, meta_file)

    @staticmethod
    def get_cand_key(cay, ma):
        """Khóa định danh ứng viên duy nhất."""
        return f"{cay}_{ma}"

    def build_candidate_texts(self, danh_muc):
        """Tạo chuỗi văn bản biểu diễn ngữ cảnh chuẩn cho toàn bộ đơn vị trong danh mục."""
        cand_list = []
        for dv in danh_muc.don_vi.values():
            key = self.get_cand_key(dv.cay, dv.ma)
            # Xây dựng text có ngữ cảnh địa bàn cha
            parent_names = []
            cur = dv
            while cur.ma_cha:
                parent = danh_muc.don_vi.get((cur.cay, cur.ma_cha))
                if not parent:
                    break
                parent_names.append(parent.ten)
                cur = parent

            if parent_names:
                full_text = f"{dv.ten}, {', '.join(parent_names)}"
            else:
                full_text = dv.ten

            cand_list.append({
                "key": key,
                "cay": dv.cay,
                "ma": dv.ma,
                "cap": dv.cap,
                "ten": dv.ten,
                "text": full_text
            })
        return cand_list

    def precompute_and_save(self, danh_muc, encoder_model, tokenizer, encode_text_fn,
                             save_dir, validation_hash, batch_size=32, device="cpu"):
        """Tính toán embedding cho toàn bộ ứng viên và lưu cache kèm hash."""
        save_p = Path(save_dir)
        save_p.mkdir(parents=True, exist_ok=True)
        cache_file = save_p / "candidate_cache.pt"
        meta_file = save_p / "candidate_cache_meta.json"

        cand_list = self.build_candidate_texts(danh_muc)
        encoder_model.eval()
        if hasattr(encoder_model, "head") and hasattr(encoder_model, "encoder"):
            encoder = encoder_model.encoder
        else:
            encoder = encoder_model
        if hasattr(encoder, "to"):
            encoder.to(device)

        vecs = []
        key_to_idx = {}
        metadata_map = {}

        with torch.no_grad():
            for idx, item in enumerate(cand_list):
                txt = item["text"]
                enc = encode_text_fn(txt, tokenizer)
                input_ids = torch.tensor([enc["input_ids"]], dtype=torch.long, device=device)
                att_mask = torch.ones_like(input_ids)
                hidden = encoder(input_ids=input_ids, attention_mask=att_mask).last_hidden_state
                # Mean pool toàn chuỗi đại diện
                cand_vec = hidden.mean(dim=1).squeeze(0).cpu()
                vecs.append(cand_vec)
                key = item["key"]
                key_to_idx[key] = idx
                metadata_map[key] = {
                    "cay": item["cay"],
                    "ma": item["ma"],
                    "cap": item["cap"],
                    "ten": item["ten"],
                    "text": item["text"]
                }
                if (idx + 1) % 2000 == 0 or (idx + 1) == len(cand_list):
                    print(f"  [Cache] Đã tính trước {idx + 1}/{len(cand_list)} ứng viên...")

        embeddings_tensor = torch.stack(vecs, dim=0) # [N, enc_dim]

        # Lưu tensor
        torch.save({
            "embeddings": embeddings_tensor,
            "key_to_idx": key_to_idx
        }, cache_file)

        # Lưu metadata
        meta = {
            "format": "candidate_cache_v1",
            "total_candidates": len(cand_list),
            "enc_dim": embeddings_tensor.size(1),
            "validation_hash": validation_hash,
            "metadata_map": metadata_map
        }
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        self.embeddings = embeddings_tensor
        self.key_to_idx = key_to_idx
        self.cand_metadata = metadata_map
        self.validation_hash = validation_hash
        self.enc_dim = embeddings_tensor.size(1)

        return meta

    def load_cache(self, cache_file, meta_file=None, expected_hash=None, device="cpu"):
        """Nạp cache từ đĩa và xác minh hash chặt chẽ."""
        cache_p = Path(cache_file)
        if not cache_p.exists():
            raise FileNotFoundError(f"Không tìm thấy file cache: {cache_file}")

        meta_p = Path(meta_file) if meta_file else cache_p.parent / "candidate_cache_meta.json"
        if not meta_p.exists():
            raise FileNotFoundError(f"Không tìm thấy file metadata cache: {meta_p}")

        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        actual_hash = meta.get("validation_hash", "")

        if expected_hash and actual_hash != expected_hash:
            raise ValueError(
                f"Cache hash mismatch! Expected {expected_hash}, but cache contains {actual_hash}. "
                "Cần tính toán lại cache ứng viên tương thích với encoder/danh mục hiện tại."
            )

        data = torch.load(cache_p, map_location=device)
        self.embeddings = data["embeddings"].to(device)
        self.key_to_idx = data["key_to_idx"]
        self.cand_metadata = meta.get("metadata_map", {})
        self.validation_hash = actual_hash
        self.enc_dim = self.embeddings.size(1)
        return meta

    def get_candidate_vector(self, cay, ma):
        """Lấy vector embedding của ứng viên theo (cay, ma) với độ trễ O(1)."""
        key = self.get_cand_key(cay, ma)
        idx = self.key_to_idx.get(key)
        if idx is None or self.embeddings is None:
            return None
        return self.embeddings[idx]

    def has_candidate(self, cay, ma):
        """Kiểm tra ứng viên có trong cache không."""
        return self.get_cand_key(cay, ma) in self.key_to_idx
