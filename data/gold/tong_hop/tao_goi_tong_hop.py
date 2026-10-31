"""Export the sealed 400 synthetic inputs into eight mixed 50-item blind prompt packages.
Does not read or open tong_hop_dap_an.json, ID mapping or provenance.
"""
import csv,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
GOLD=HERE.parent
sys.path.insert(0,str(GOLD))
from tao_goi_gan_nhan import generate
from gold_common import output_csv,sha256

def main():
    with (HERE/"tong_hop_dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=400 or len({r["id"] for r in rows})!=400:
        raise ValueError("Synthetic input not frozen to 400 unique items")
    schema=json.loads((GOLD/"SCHEMA_NHAN.json").read_text(encoding="utf8"))
    convention=(GOLD/"QUY_UOC_NHAN.md").read_text(encoding="utf8")
    dest=HERE/"goi_gan_nhan"
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir()
    for no,items,prompt in generate(rows,convention,schema,50):
        folder=dest/f"goi_{no:02d}"
        folder.mkdir()
        (folder/"PROMPT_GAN_NHAN.txt").write_text(prompt,encoding="utf8")
        output_csv(folder/"dau_vao.csv",items,("id","dau_vao"))
    print("BLIND_SYNTHETIC_PACKAGES_PASS",8,"SHA256",sha256(HERE/"tong_hop_dau_vao.csv"))
if __name__=="__main__":main()
