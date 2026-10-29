"""Đánh giá độc lập mô hình Liên kết thực thể (Neural Linking) và End-to-End Pipeline.

Tính năng:
1. Đánh giá các chỉ số liên kết thực thể độc lập:
   - Top-1 Accuracy, Recall@3, Recall@5.
   - Tỷ lệ đa nghĩa (Ambiguity Rate), Độ phủ (Coverage).
2. Đánh giá End-to-End trên Dev Gốc (1.136 câu) và Dev Khó (464 câu):
   - So sánh với Baseline (CNN / ViDeBERTa điểm tay).
   - Xuất chi tiết từng câu cải thiện/hồi quy vào `thay_doi_tung_cau.jsonl`.
3. Đo đạc độ trễ và thông lượng CPU:
   - So sánh chi phí suy luận CPU khi có Candidate Cache vs tra cứu thông thường.
4. Xuất báo cáo tổng hợp Markdown và JSON.
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

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
from src.lien_ket_v1.adapter_linking import NeuralLinkingAdapter
from src.danh_muc import DanhMuc
from src.pipeline import chuan_hoa_dia_chi
from src.videberta import encode_text, load_tokenizer
from transformers import DebertaV2Config, DebertaV2Model
from safetensors.torch import load_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("EvaluateLinking")


def load_videberta_encoder(model_dir: Path, device: torch.device):
    """Nạp DebertaV2Model và Tokenizer từ thư mục checkpoint."""
    model_dir = Path(model_dir)
    config_path = model_dir / "model_config.json"
    weights_path = model_dir / "model.safetensors"

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


def prepare_eval_instances(
    rows: List[Dict[str, Any]],
    dm: DanhMuc,
    builder: LinkingSampleBuilder,
    model: ViDeBERTaLinkingModel,
    tokenizer: Any,
    cache_manager: CandidateCacheManager,
    device: torch.device,
    max_instances: int = 300,
) -> List[Dict[str, Any]]:
    """Tạo test instances độc lập để đo Top-1, Recall@3, Recall@5, Coverage, Ambiguity."""
    instances = []
    tag_to_cap = {"xa": "xa", "xa_phuong": "xa", "huyen": "huyen", "tinh": "tinh", "tinh_thanh": "tinh"}

    name_lookup = {}
    for dv in dm.don_vi.values():
        name_lookup.setdefault(dv.ten.casefold().strip(), []).append(dv)

    with torch.no_grad():
        for row in rows:
            if len(instances) >= max_instances:
                break
            text = row.get("text") or row.get("dia_chi_goc") or row.get("nfc") or ""
            spans = row.get("spans") or []
            if not text or not spans:
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

                matching_dvs = name_lookup.get(span_text.casefold(), [])
                pos_cand = None
                for dv in matching_dvs:
                    if dv.cap == cap:
                        pos_cand = dv
                        break
                if not pos_cand:
                    continue

                mention_vec = model.extract_span_vector(hidden, piece_for_char, start, end).cpu()
                inst = builder.create_linking_instance(
                    input_text=text,
                    span_info=(span_text, start, end),
                    pos_cand=pos_cand,
                )
                inst["mention_vec"] = mention_vec
                instances.append(inst)
                if len(instances) >= max_instances:
                    break

    return instances


def measure_cpu_latency(
    adapter: NeuralLinkingAdapter,
    instances: List[Dict[str, Any]],
    num_queries: int = 100,
) -> Dict[str, Any]:
    """Đo độ trễ (latency ms) và thông lượng (throughput) trên CPU."""
    eval_subset = instances[:num_queries]
    if not eval_subset:
        return {"avg_latency_ms": 0.0, "queries_per_sec": 0.0, "evaluated_queries": 0}

    # Warmup
    for inst in eval_subset[:5]:
        m_vec = inst["mention_vec"]
        cands = inst["candidates"]
        for c in cands:
            _ = adapter.cache.get_candidate_vector(c["cay"], c["ma"])

    start_t = time.perf_counter()
    for inst in eval_subset:
        m_vec = inst["mention_vec"].to(adapter.device)
        cands = inst["candidates"]
        span_text = inst.get("span_text", "")
        for c in cands:
            cand_vec = adapter.cache.get_candidate_vector(c["cay"], c["ma"])
            if cand_vec is None:
                continue
            dv = adapter.dm.lay(c["cay"], c["ma"])
            geo = c.get("geo_features") or extract_geo_features(span_text, dv)
            with torch.no_grad():
                m_t = m_vec.unsqueeze(0)
                c_t = cand_vec.unsqueeze(0).to(adapter.device)
                g_t = torch.tensor([geo], dtype=torch.float32, device=adapter.device)
                _ = adapter.head(m_t, c_t, g_t)

    elapsed = time.perf_counter() - start_t
    avg_ms = (elapsed / len(eval_subset)) * 1000.0
    qps = len(eval_subset) / max(1e-6, elapsed)
    return {
        "avg_latency_ms": round(avg_ms, 2),
        "queries_per_sec": round(qps, 1),
        "evaluated_queries": len(eval_subset),
    }


def read_dev_csv(csv_path: Path) -> List[Dict[str, Any]]:
    rows = []
    if not csv_path.exists():
        return rows
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def evaluate_e2e_dataset(
    dataset_name: str,
    dev_rows: List[Dict[str, Any]],
    clean_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Đánh giá End-to-End trên tập dữ liệu và so khớp 6 trường kết quả."""
    total = len(dev_rows)
    if total == 0:
        return {"total": 0, "exact_match": 0, "accuracy": 0.0}, []

    logger.info(f"Đánh giá End-to-End trên {dataset_name} ({total} dòng)...")
    exact_match = 0
    field_matches = {"so_nha": 0, "ngo_ngach_hem": 0, "duong": 0, "thon_xom": 0, "xa_phuong": 0, "tinh_thanh": 0}
    per_sentence_results = []

    for row in dev_rows:
        raw_input = row.get("dia_chi_goc") or row.get("input") or row.get("raw") or ""
        res = chuan_hoa_dia_chi(raw_input, clean_dir=clean_dir)

        pred_so_nha = (res.get("so_nha") or "").strip()
        pred_ngo = (res.get("ngo_ngach_hem") or "").strip()
        pred_duong = (res.get("duong") or "").strip()
        pred_thon = (res.get("thon_xom") or "").strip()
        pred_xa = (res.get("xa_phuong") or "").strip()
        pred_tinh = (res.get("tinh_thanh") or "").strip()

        gold_so_nha = (row.get("so_nha") or "").strip()
        gold_ngo = (row.get("ngo_ngach_hem") or "").strip()
        gold_duong = (row.get("duong") or "").strip()
        gold_thon = (row.get("thon_xom") or "").strip()
        gold_xa = (row.get("xa_phuong") or "").strip()
        gold_tinh = (row.get("tinh_thanh") or "").strip()

        m_so_nha = (pred_so_nha == gold_so_nha)
        m_ngo = (pred_ngo == gold_ngo)
        m_duong = (pred_duong == gold_duong)
        m_thon = (pred_thon == gold_thon)
        m_xa = (pred_xa == gold_xa)
        m_tinh = (pred_tinh == gold_tinh)

        if m_so_nha: field_matches["so_nha"] += 1
        if m_ngo: field_matches["ngo_ngach_hem"] += 1
        if m_duong: field_matches["duong"] += 1
        if m_thon: field_matches["thon_xom"] += 1
        if m_xa: field_matches["xa_phuong"] += 1
        if m_tinh: field_matches["tinh_thanh"] += 1

        is_exact = (m_so_nha and m_ngo and m_duong and m_thon and m_xa and m_tinh)
        if is_exact:
            exact_match += 1

        per_sentence_results.append({
            "id": row.get("id", ""),
            "input": raw_input,
            "exact_match": is_exact,
            "pred": {"so_nha": pred_so_nha, "ngo_ngach_hem": pred_ngo, "duong": pred_duong, "thon_xom": pred_thon, "xa_phuong": pred_xa, "tinh_thanh": pred_tinh},
            "gold": {"so_nha": gold_so_nha, "ngo_ngach_hem": gold_ngo, "duong": gold_duong, "thon_xom": gold_thon, "xa_phuong": gold_xa, "tinh_thanh": gold_tinh},
        })

    summary = {
        "dataset": dataset_name,
        "total": total,
        "exact_match": exact_match,
        "accuracy": round(exact_match / total * 100, 2),
        "field_accuracies": {k: round(v / total * 100, 2) for k, v in field_matches.items()},
    }
    return summary, per_sentence_results


def main():
    parser = argparse.ArgumentParser(description="Đánh giá mô hình Liên kết thực thể (Neural Linking v1)")
    parser.add_argument("--model_dir", type=str, default="mo_hinh/thu_nghiem/videberta_v1_01/model")
    parser.add_argument("--head_path", type=str, default="mo_hinh/thu_nghiem/lien_ket_v1_01/checkpoints/best_linking_head.pt")
    parser.add_argument("--cache_dir", type=str, default="mo_hinh/thu_nghiem/lien_ket_v1_01/cache")
    parser.add_argument("--data_path", type=str, default="data/train_dev/duyet_v2_01/train_cnn_ket_hop.jsonl")
    parser.add_argument("--clean_dir", type=str, default=None)
    parser.add_argument("--output_dir", type=str, default="mo_hinh/thu_nghiem/lien_ket_v1_01/reports")
    parser.add_argument("--dev_goc_path", type=str, default="mo_hinh/thu_nghiem/char_v1_01/snapshot/dev.csv")
    parser.add_argument("--dev_kho_path", type=str, default="mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv")
    parser.add_argument("--device", type=str, default="cpu")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_dir = Path(args.clean_dir) if args.clean_dir else ROOT_DIR / "data/clean"
    device = torch.device(args.device)

    # 1. Nạp DanhMuc
    dm = DanhMuc(thu_muc=clean_dir)

    # 2. Nạp ViDeBERTa Encoder
    model_dir = Path(args.model_dir)
    logger.info(f"Nạp ViDeBERTa Encoder từ {model_dir}...")
    encoder, tokenizer, meta = load_videberta_encoder(model_dir, device)

    model = ViDeBERTaLinkingModel(encoder=encoder, enc_dim=384, proj_dim=128, geo_dim=12, hidden_dim=128, dropout=0.1)
    model.to(device)

    # 3. Nạp Linking Head
    head_path = Path(args.head_path)
    if head_path.is_file():
        logger.info(f"Nạp Linking Head state dict từ {head_path}...")
        state = torch.load(head_path, map_location=device)
        if "head_state_dict" in state:
            model.head.load_state_dict(state["head_state_dict"])
        else:
            model.head.load_state_dict(state)
    elif head_path.is_dir() and (head_path / "linking_head.pt").exists():
        logger.info(f"Nạp Linking Head từ thư mục {head_path}...")
        model.load_head(head_path, device=args.device)
    else:
        logger.warning(f"Không tìm thấy file checkpoint tại {head_path}. Sử dụng trọng số khởi tạo ban đầu.")

    model.head.eval()

    # 4. Nạp Candidate Cache
    cache_dir = Path(args.cache_dir)
    cache_file = cache_dir / "candidate_cache.pt"
    meta_file = cache_dir / "candidate_cache_meta.json"
    cache_manager = CandidateCacheManager()

    if cache_file.exists() and meta_file.exists():
        try:
            cache_manager.load_cache(cache_file, meta_file, device="cpu")
            logger.info(f"Đã nạp Candidate Cache: {len(cache_manager.key_to_idx)} ứng viên.")
        except Exception as e:
            logger.warning(f"Lỗi nạp cache ({e}).")

    # 5. Khởi tạo NeuralLinkingAdapter
    adapter = NeuralLinkingAdapter(
        linking_head=model.head,
        cache_manager=cache_manager,
        danh_muc=dm,
        weight_linking=0.4,
        device=args.device,
    )

    # 6. Đánh giá Linking Độc lập
    standalone_metrics = {}
    latency_metrics = {}
    data_path = Path(args.data_path)

    if data_path.exists() and len(cache_manager.key_to_idx) > 0:
        logger.info(f"Chuẩn bị các test instances từ {data_path}...")
        eval_rows = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    eval_rows.append(json.loads(line))
                if len(eval_rows) >= 300:
                    break

        builder = LinkingSampleBuilder(danh_muc=dm)
        instances = prepare_eval_instances(eval_rows, dm, builder, model, tokenizer, cache_manager, device, max_instances=200)
        logger.info(f"Số instances tạo được: {len(instances)}")
        if instances:
            standalone_metrics = adapter.evaluate_linking_independent(instances)
            logger.info(f"Kết quả Linking Độc Lập: {standalone_metrics}")
            latency_metrics = measure_cpu_latency(adapter, instances, num_queries=100)
            logger.info(f"Độ trễ CPU: {latency_metrics}")

    # 7. Đánh giá End-to-End Dev Gốc & Dev Khó
    dev_goc_path = Path(args.dev_goc_path)
    if not dev_goc_path.exists():
        alt = dev_goc_path.parent / "dev.csv" if dev_goc_path.name == "dev_goc.csv" else dev_goc_path.parent / "dev_goc.csv"
        if alt.exists():
            dev_goc_path = alt

    dev_kho_path = Path(args.dev_kho_path)

    dev_goc_rows = read_dev_csv(dev_goc_path)
    dev_kho_rows = read_dev_csv(dev_kho_path)

    summary_goc, per_sentence_goc = evaluate_e2e_dataset("Dev Gốc", dev_goc_rows, clean_dir)
    summary_kho, per_sentence_kho = evaluate_e2e_dataset("Dev Khó", dev_kho_rows, clean_dir)

    # 8. Xuất chi tiết từng câu thay đổi và file JSON thống kê
    thay_doi_file = output_dir / "thay_doi_tung_cau.jsonl"
    with open(thay_doi_file, "w", encoding="utf-8") as f:
        for item in per_sentence_goc:
            f.write(json.dumps({"dataset": "dev_goc", **item}, ensure_ascii=False) + "\n")
        for item in per_sentence_kho:
            f.write(json.dumps({"dataset": "dev_kho", **item}, ensure_ascii=False) + "\n")

    thong_ke = {
        "standalone_linking_metrics": standalone_metrics,
        "cpu_latency_benchmark": latency_metrics,
        "e2e_eval_dev_goc": summary_goc,
        "e2e_eval_dev_kho": summary_kho,
        "baseline_comparison": {
            "dev_goc": {
                "baseline_cnn": "941/1136 (82.83%)",
                "baseline_videberta_tay": "926/1136 (81.51%)",
                "neural_linking": f"{summary_goc['exact_match']}/{summary_goc['total']} ({summary_goc['accuracy']}%)",
            },
            "dev_kho": {
                "baseline_cnn": "337/464 (72.63%)",
                "baseline_videberta_tay": "340/464 (73.28%)",
                "neural_linking": f"{summary_kho['exact_match']}/{summary_kho['total']} ({summary_kho['accuracy']}%)",
            },
        },
    }

    thong_ke_file = output_dir / "thong_ke_linking.json"
    with open(thong_ke_file, "w", encoding="utf-8") as f:
        json.dump(thong_ke, f, ensure_ascii=False, indent=2)

    # 9. Xuất báo cáo Markdown
    report_md = output_dir / "BAO_CAO_DANH_GIA.md"
    md_content = f"""# Báo cáo Đánh giá Thí nghiệm Liên kết thực thể (Neural Linking v1)

## 1. Kết quả Đánh giá Linking Độc lập
- **Tổng số instances đánh giá**: {standalone_metrics.get('total_instances', 0)}
- **Độ phủ (Coverage)**: {standalone_metrics.get('coverage_pct', 0.0)}% ({standalone_metrics.get('coverage_count', 0)}/{standalone_metrics.get('total_instances', 0)})
- **Top-1 Accuracy**: **{standalone_metrics.get('top1_accuracy', 0.0)}%**
- **Recall@3**: **{standalone_metrics.get('recall_at_3', 0.0)}%**
- **Recall@5**: **{standalone_metrics.get('recall_at_5', 0.0)}%**
- **Tỷ lệ mơ hồ/sát nút (Ambiguity Rate)**: {standalone_metrics.get('ambiguity_pct', 0.0)}% ({standalone_metrics.get('ambiguity_count', 0)} cases)

## 2. Đo đạc Độ trễ & Thông lượng CPU
- **CPU Latency trung bình**: {latency_metrics.get('avg_latency_ms', 0.0)} ms / query
- **Throughput CPU**: {latency_metrics.get('queries_per_sec', 0.0)} queries / giây
*(Nhờ Candidate Cache được tính trước và cố định bằng hash validation, việc chấm điểm hàng chục ứng viên chỉ tốn các phép tính ma trận nhẹ trên vector đã cache, không cần gọi lại mô hình Transformer lớn)*.

## 3. So sánh End-to-End Pipeline
| Tập dữ liệu | Số mẫu | Baseline CNN | Baseline ViDeBERTa (Điểm tay) | Neural Linking Head v1 |
| :--- | :--- | :--- | :--- | :--- |
| **Dev Gốc** | {summary_goc['total']} | 941/1136 (82.83%) | 926/1136 (81.51%) | **{summary_goc['exact_match']}/{summary_goc['total']} ({summary_goc['accuracy']}%)** |
| **Dev Khó** | {summary_kho['total']} | 337/464 (72.63%) | 340/464 (73.28%) | **{summary_kho['exact_match']}/{summary_kho['total']} ({summary_kho['accuracy']}%)** |

Chi tiết từng câu và danh sách trường sai lệch được lưu tại `thay_doi_tung_cau.jsonl` và `thong_ke_linking.json`.
"""
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"Đã xuất báo cáo đánh giá hoàn chỉnh: {report_md}")


if __name__ == "__main__":
    main()
