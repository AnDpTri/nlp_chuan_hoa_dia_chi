"""Dựng run ranker mới cùng CNN v3_tc: train_ranker gốc + bản sao có số điện thoại/ghi chú ở cuối câu
(nhãn mã hành chính và chi tiết giữ nguyên). Không dùng dev.
Dùng: tao_ranker_hau_to.py <run_dir_moi>"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import json, random, shutil, sys
from pathlib import Path

GOC = dd.TRAIN_RUN / 'v3_tc'
HAU_TO = ['{s} - {dt}', '{s}, SĐT {dt}', '{s} ĐT: {dt_cach}', '{s} (gọi trước khi giao)', '{s} - giao giờ hành chính',
          '{s}, Việt Nam - {dt}', '{s} sdt:+84{dt9}', '{s}. Liên hệ {dt}', '{s} | {dt}', '{s} - ghi chú: để ở bảo vệ']


def dt(rng):
    return '0' + rng.choice('35789') + ''.join(rng.choice('0123456789') for _ in range(8))


def main(moi):
    moi = Path(moi)
    if moi.exists():
        sys.exit('run đã tồn tại')
    (moi / 'data').mkdir(parents=True)
    shutil.copy(GOC / 'char_cnn.pt', moi / 'char_cnn.pt')
    shutil.copytree(GOC / 'snapshot', moi / 'snapshot')
    rng = random.Random(20261031)
    rows = [json.loads(l) for l in open(GOC / 'data' / 'train_ranker.jsonl', encoding='utf-8')]
    out = list(rows)
    for r in rows:
        if rng.random() < .5:
            so = dt(rng)
            text = rng.choice(HAU_TO).format(s=r['text'].rstrip(), dt=so, dt_cach=f'{so[:4]} {so[4:7]} {so[7:]}', dt9=so[1:])
            out.append({**r, 'id': r['id'] + '_ht', 'text': text, 'nfc': text})
    with open(moi / 'data' / 'train_ranker.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(len(rows), '->', len(out))


if __name__ == '__main__':
    main(sys.argv[1])
