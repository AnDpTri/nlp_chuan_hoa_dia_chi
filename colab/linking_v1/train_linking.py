"""Huấn luyện Đầu liên kết thực thể (Neural Linking Head) với ViDeBERTa Encoder đóng băng.

Hỗ trợ:
- Encoder ViDeBERTa đóng băng 100% (chỉ head nhận gradient).
- Nạp và xác thực Candidate Cache (precomputed candidate representations) bằng hash SHA-256.
- Khai thác Hard Negatives và bảo vệ False Negatives (tránh phạt sáp nhập/đổi tên hợp lệ).
- Phân chia Train/Validation theo family_id (chống rò rỉ dữ liệu họ nguồn).
- Đo throughput pilot run và in bảng ETA chi tiết trước khi train full.
- Lưu checkpoint mỗi epoch và tự động resume.
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import DebertaV2Config, DebertaV2Model
from safetensors.torch import load_file

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.lien_ket_v1.mo_hinh_linking import NeuralLinkingHead, ViDeBERTaLinkingModel
from src.lien_ket_v1.cache_ung_vien import (
    CandidateCacheManager,
    compute_cache_validation_hash,
)
from src.lien_ket_v1.du_lieu_linking import (
    LinkingSampleBuilder,
    extract_geo_features,
    split_dataset_by_family,
)
from src.danh_muc import DanhMuc
from src.videberta import encode_text, load_tokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("TrainLinking")


def load_videberta_encoder(model_dir: Path, device: torch.device):
    """Nạp DebertaV2Model và Tokenizer từ thư mục checkpoint."""
    model_dir = Path(model_dir)
    config_path = model_dir / "model_config.json"
    weights_path = model_dir / "model.safetensors"

    if not config_path.exists() or not weights_path.exists():
        raise FileNotFoundError(f"Không tìm thấy model_config.json hoặc model.safetensors tại {model_dir}")

    meta = json.loads(config_path.read_text(encoding="utf-8"))
    config = DebertaV2Config.from_dict(meta["encoder_config"])
    encoder = DebertaV2Model(config)

    weights = load_file(str(weights_path), device="cpu")
    enc_weights = {k[len("encoder."):]: v for k, v in weights.items() if k.startswith("encoder.")}
    if enc_weights:
        encoder.load_state_dict(enc_weights)
    else:
        encoder.load_state_dict(weights, strict=False)

    tokenizer = load_tokenizer(model_dir)
    encoder.to(device).eval()
    return encoder, tokenizer, meta


class LinkingTensorDataset(Dataset):
    """Dataset chứa tensors phục vụ huấn luyện Neural Linking Head."""

    def __init__(self, items: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]]):
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        m_vec, c_vec, geo, label = self.items[idx]
        return m_vec, c_vec, geo, torch.tensor(label, dtype=torch.float32)


def collate_linking_batch(batch):
    m_vecs = torch.stack([x[0] for x in batch])
    c_vecs = torch.stack([x[1] for x in batch])
    geos = torch.stack([x[2] for x in batch])
    labels = torch.stack([x[3] for x in batch])
    return m_vecs, c_vecs, geos, labels


def extract_instances_from_rows(
    rows: List[Dict[str, Any]],
    dm: DanhMuc,
    builder: LinkingSampleBuilder,
    model: ViDeBERTaLinkingModel,
    tokenizer: Any,
    cache_manager: CandidateCacheManager,
    device: torch.device,
    max_items: Optional[int] = None,
) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]]:
    """Trích xuất các vector (mention_vec, cand_vec, geo_features, label) từ các dòng dữ liệu."""
    items = []
    model.eval()

    # Ánh xạ nhãn span sang cấp hành chính
    tag_to_cap = {
        "xa": "xa",
        "xa_phuong": "xa",
        "huyen": "huyen",
        "tinh": "tinh",
        "tinh_thanh": "tinh",
    }

    # Bảng tra cứu tên đơn vị nhanh
    name_lookup = {}
    for dv in dm.don_vi.values():
        name_lookup.setdefault(dv.ten.casefold().strip(), []).append(dv)

    with torch.no_grad():
        for row in rows:
            if max_items and len(items) >= max_items:
                break

            text = row.get("text") or row.get("dia_chi_goc") or row.get("nfc") or ""
            if not text or len(text) > 2048:
                continue

            spans = row.get("spans") or []
            if not spans:
                continue

            try:
                enc = encode_text(text, tokenizer)
            except Exception:
                continue

            input_ids = torch.tensor([enc["input_ids"]], dtype=torch.long, device=device)
            att_mask = torch.ones_like(input_ids)
            hidden = model.encoder(input_ids=input_ids, attention_mask=att_mask).last_hidden_state[0]
            piece_for_char = enc["piece_for_char"]

            for span in spans:
                if isinstance(span, list) and len(span) >= 3:
                    label, start, end = span[0], span[1], span[2]
                elif isinstance(span, dict):
                    label, start, end = span.get("label"), span.get("start"), span.get("end")
                else:
                    continue

                cap = tag_to_cap.get(label)
                if not cap or start >= end or end > len(text):
                    continue

                span_text = text[start:end].strip()
                if not span_text:
                    continue

                # Tìm positive candidate
                matching_dvs = name_lookup.get(span_text.casefold(), [])
                pos_cand = None
                for dv in matching_dvs:
                    if dv.cap == cap:
                        pos_cand = dv
                        break
                if not pos_cand:
                    continue

                # Trích xuất mention vector
                mention_vec = model.extract_span_vector(hidden, piece_for_char, start, end).cpu()

                # Tạo linking instance với hard negatives
                inst = builder.create_linking_instance(
                    input_text=text,
                    span_info=(span_text, start, end),
                    pos_cand=pos_cand,
                )

                for cand_info in inst["candidates"]:
                    cand_vec = cache_manager.get_candidate_vector(cand_info["cay"], cand_info["ma"])
                    if cand_vec is None:
                        continue
                    geo = torch.tensor(cand_info["geo_features"], dtype=torch.float32)
                    lbl = 1.0 if cand_info["is_positive"] else 0.0
                    items.append((mention_vec, cand_vec.cpu(), geo, lbl))

    return items


def run_pilot(
    head: NeuralLinkingHead,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    pilot_steps: int = 20,
) -> Tuple[float, float]:
    """Chạy pilot run để đo throughput và tính ETA."""
    logger.info(f"Bắt đầu Pilot Run ({pilot_steps} steps) để đo đạc thông lượng...")
    head.train()
    start_time = time.perf_counter()
    steps_done = 0
    samples_done = 0

    for i, (m_vecs, c_vecs, geos, labels) in enumerate(dataloader):
        if steps_done >= pilot_steps:
            break
        m_vecs = m_vecs.to(device)
        c_vecs = c_vecs.to(device)
        geos = geos.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = head(m_vecs, c_vecs, geos)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        steps_done += 1
        samples_done += m_vecs.size(0)

    elapsed = time.perf_counter() - start_time
    sec_per_step = elapsed / max(1, steps_done)
    samples_per_sec = samples_done / max(1e-6, elapsed)
    return sec_per_step, samples_per_sec


def evaluate_val_loss_and_acc(
    head: NeuralLinkingHead,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    """Đánh giá loss và accuracy trên tập validation."""
    head.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for m_vecs, c_vecs, geos, labels in dataloader:
            m_vecs = m_vecs.to(device)
            c_vecs = c_vecs.to(device)
            geos = geos.to(device)
            labels = labels.to(device)

            logits = head(m_vecs, c_vecs, geos)
            loss = criterion(logits, labels)
            total_loss += loss.item() * m_vecs.size(0)

            preds = (torch.sigmoid(logits) >= 0.5).float()
            correct += (preds == labels).sum().item()
            total += m_vecs.size(0)

    avg_loss = total_loss / max(1, total)
    acc = correct / max(1, total)
    return avg_loss, acc


def train_model(args):
    device = torch.device(
        "cuda" if (args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available())) else "cpu"
    )
    logger.info(f"Thiết bị sử dụng: {device} ({torch.cuda.get_device_name() if device.type == 'cuda' else 'CPU'})")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    clean_dir = Path(args.clean_dir) if args.clean_dir else ROOT_DIR / "data/clean"
    logger.info(f"Nạp danh mục từ {clean_dir}...")
    dm = DanhMuc(thu_muc=clean_dir)

    # 1. Nạp Encoder ViDeBERTa
    model_dir = Path(args.model_dir)
    logger.info(f"Nạp ViDeBERTa từ {model_dir}...")
    encoder, tokenizer, meta = load_videberta_encoder(model_dir, device)

    # 2. Khởi tạo ViDeBERTaLinkingModel và đóng băng 100% encoder
    model = ViDeBERTaLinkingModel(
        encoder=encoder,
        enc_dim=384,
        proj_dim=128,
        geo_dim=12,
        hidden_dim=128,
        dropout=0.1,
    )
    model.to(device)
    model.freeze_encoder()

    assert not any(p.requires_grad for p in model.encoder.parameters()), "LỖI: Encoder phải đóng băng hoàn toàn!"
    trainable_params = sum(p.numel() for p in model.head.parameters() if p.requires_grad)
    frozen_params = sum(p.numel() for p in model.encoder.parameters())
    logger.info(f"Encoder đóng băng 100%: {frozen_params:,} tham số.")
    logger.info(f"Linking Head huấn luyện: {trainable_params:,} tham số.")

    # 3. Quản lý Candidate Cache và Hash Validation
    cache_file = cache_dir / "candidate_cache.pt"
    meta_file = cache_dir / "candidate_cache_meta.json"
    expected_hash = compute_cache_validation_hash(
        encoder_path=model_dir / "model.safetensors",
        tokenizer_path=model_dir / "tokenizer.json",
        clean_dir=clean_dir,
    )
    logger.info(f"Cache Validation SHA-256 Hash: {expected_hash}")

    cache_manager = CandidateCacheManager()
    if cache_file.exists() and meta_file.exists():
        try:
            logger.info("Thử nạp Candidate Cache có sẵn...")
            cache_manager.load_cache(cache_file, meta_file, expected_hash=expected_hash, device="cpu")
            logger.info(f"Nạp Candidate Cache thành công: {len(cache_manager.key_to_idx)} ứng viên.")
        except Exception as e:
            logger.warning(f"Không thể tái sử dụng cache ({e}). Đang tính toán cache mới...")
            cache_manager.precompute_and_save(
                danh_muc=dm,
                encoder_model=encoder,
                tokenizer=tokenizer,
                encode_text_fn=encode_text,
                save_dir=cache_dir,
                validation_hash=expected_hash,
                device=device,
            )
    else:
        logger.info("Chưa có Candidate Cache. Đang tính trước biểu diễn ứng viên...")
        cache_manager.precompute_and_save(
            danh_muc=dm,
            encoder_model=encoder,
            tokenizer=tokenizer,
            encode_text_fn=encode_text,
            save_dir=cache_dir,
            validation_hash=expected_hash,
            device=device,
        )

    # 4. Chuẩn bị Dữ liệu Huấn luyện & Validation
    data_path = Path(args.data_path)
    logger.info(f"Đọc dữ liệu từ {data_path}...")
    rows = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
            if args.max_samples and len(rows) >= args.max_samples:
                break

    split_res = split_dataset_by_family(rows, val_ratio=args.val_ratio, seed=args.seed)
    train_rows = split_res["train_rows"]
    val_rows = split_res["val_rows"]
    logger.info(f"Tách họ nguồn (Zero Leakage): Train={len(train_rows)} dòng ({len(split_res['train_families'])} họ), Val={len(val_rows)} dòng ({len(split_res['val_families'])} họ).")

    builder = LinkingSampleBuilder(danh_muc=dm)
    logger.info("Trích xuất tensors cho tập Train...")
    train_items = extract_instances_from_rows(train_rows, dm, builder, model, tokenizer, cache_manager, device)
    logger.info("Trích xuất tensors cho tập Validation...")
    val_items = extract_instances_from_rows(val_rows, dm, builder, model, tokenizer, cache_manager, device)

    logger.info(f"Tổng số cặp mẫu huấn luyện: Train={len(train_items):,}, Val={len(val_items):,}.")
    if not train_items:
        raise ValueError("Không trích xuất được mẫu huấn luyện nào từ dữ liệu đầu vào!")

    train_loader = DataLoader(
        LinkingTensorDataset(train_items),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_linking_batch,
    )
    val_loader = DataLoader(
        LinkingTensorDataset(val_items),
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_linking_batch,
    )

    # 5. Optimizer, Scheduler & Loss
    optimizer = torch.optim.AdamW(model.head.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()
    total_steps = len(train_loader) * args.epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, total_steps), eta_min=1e-5)

    # 6. Pilot Run & Bảng ETA
    steps_per_epoch = len(train_loader)
    sec_per_step, samples_per_sec = run_pilot(
        head=model.head,
        dataloader=train_loader,
        optimizer=optimizer,
        criterion=criterion,
        device=device,
        pilot_steps=args.pilot_steps,
    )
    sec_per_epoch = sec_per_step * steps_per_epoch
    total_sec_est = sec_per_epoch * args.epochs

    logger.info("=" * 65)
    logger.info("BẢNG ƯỚC LƯỢNG THỜI GIAN HUẤN LUYỆN (ETA):")
    logger.info(f"  - Thiết bị:                  {device.type.upper()} ({torch.cuda.get_device_name() if device.type == 'cuda' else 'CPU'})")
    logger.info(f"  - Tổng số cặp train:         {len(train_items):,}")
    logger.info(f"  - Batch size:                {args.batch_size}")
    logger.info(f"  - Steps mỗi epoch:           {steps_per_epoch}")
    logger.info(f"  - Tốc độ đo được (Pilot):    {samples_per_sec:.1f} samples/s ({sec_per_step*1000:.1f} ms/step)")
    logger.info(f"  - Thời gian ước tính 1 epoch: {sec_per_epoch:.1f}s ({sec_per_epoch/60:.2f} phút)")
    logger.info(f"  - Tổng thời gian ({args.epochs} epochs): {total_sec_est:.1f}s ({total_sec_est/60:.2f} phút)")
    logger.info("=" * 65)

    # 7. Checkpoint Resume
    start_epoch = 1
    best_val_loss = float("inf")
    history = []

    if args.resume:
        ckpts = sorted(output_dir.glob("checkpoint_epoch_*.pt"))
        if ckpts:
            latest_ckpt = ckpts[-1]
            logger.info(f"Tìm thấy checkpoint: {latest_ckpt.name}. Tiến hành resume...")
            state = torch.load(latest_ckpt, map_location=device)
            model.head.load_state_dict(state["head_state_dict"])
            optimizer.load_state_dict(state["optimizer_state_dict"])
            if "scheduler_state_dict" in state:
                scheduler.load_state_dict(state["scheduler_state_dict"])
            start_epoch = state["epoch"] + 1
            best_val_loss = state.get("val_loss", float("inf"))
            logger.info(f"Đã resume từ epoch {state['epoch']}. Bắt đầu epoch tiếp theo: {start_epoch}.")

    # 8. Vòng lặp huấn luyện chính
    logger.info(f"Bắt đầu huấn luyện từ epoch {start_epoch} đến {args.epochs}...")
    for epoch in range(start_epoch, args.epochs + 1):
        model.head.train()
        epoch_loss = 0.0
        epoch_correct = 0
        epoch_total = 0
        t0 = time.perf_counter()

        for step, (m_vecs, c_vecs, geos, labels) in enumerate(train_loader, 1):
            m_vecs = m_vecs.to(device)
            c_vecs = c_vecs.to(device)
            geos = geos.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            logits = model.head(m_vecs, c_vecs, geos)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            scheduler.step()

            epoch_loss += loss.item() * m_vecs.size(0)
            preds = (torch.sigmoid(logits) >= 0.5).float()
            epoch_correct += (preds == labels).sum().item()
            epoch_total += m_vecs.size(0)

            if step % max(1, steps_per_epoch // 5) == 0 or step == steps_per_epoch:
                cur_loss = epoch_loss / epoch_total
                cur_acc = epoch_correct / epoch_total
                logger.info(f"Epoch {epoch:02d}/{args.epochs:02d} | Step {step:04d}/{steps_per_epoch:04d} | Train Loss: {cur_loss:.4f} | Train Acc: {cur_acc*100:.2f}%")

        epoch_time = time.perf_counter() - t0
        train_loss = epoch_loss / max(1, epoch_total)
        train_acc = epoch_correct / max(1, epoch_total)

        # Đánh giá trên Validation
        val_loss, val_acc = evaluate_val_loss_and_acc(model.head, val_loader, criterion, device)
        logger.info(
            f"--> EPOCH {epoch:02d} ({epoch_time:.1f}s) | "
            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc*100:.2f}% | "
            f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.2f}%"
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "time_seconds": round(epoch_time, 2),
        })

        # Lưu checkpoint epoch
        ckpt_path = output_dir / f"checkpoint_epoch_{epoch:02d}.pt"
        torch.save({
            "epoch": epoch,
            "head_state_dict": model.head.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "val_loss": val_loss,
            "val_acc": val_acc,
            "validation_hash": expected_hash,
        }, ckpt_path)
        logger.info(f"Đã lưu checkpoint: {ckpt_path.name}")

        # Lưu best head
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_head(output_dir, extra_meta={"best_epoch": epoch, "val_loss": val_loss, "val_acc": val_acc})
            # Tạo thêm bản sao best_linking_head.pt ở thư mục output
            torch.save(model.head.state_dict(), output_dir / "best_linking_head.pt")
            logger.info(f"--> [BEST] Cập nhật best linking head (Val Loss: {best_val_loss:.4f})")

    # Lưu lịch sử huấn luyện
    history_file = output_dir / "training_history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    logger.info(f"Hoàn thành toàn bộ quá trình huấn luyện. Lịch sử lưu tại: {history_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Huấn luyện Đầu liên kết thực thể (Neural Linking Head)")
    parser.add_argument("--model_dir", type=str, default="mo_hinh/thu_nghiem/videberta_v1_01/model")
    parser.add_argument("--data_path", type=str, default="data/train_dev/duyet_v2_01/train_cnn_ket_hop.jsonl")
    parser.add_argument("--output_dir", type=str, default="mo_hinh/thu_nghiem/lien_ket_v1_01/checkpoints")
    parser.add_argument("--cache_dir", type=str, default="mo_hinh/thu_nghiem/lien_ket_v1_01/cache")
    parser.add_argument("--clean_dir", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val_ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pilot_steps", type=int, default=20)
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--resume", action="store_true")

    args = parser.parse_args()
    train_model(args)


if __name__ == "__main__":
    main()
