"""Additional blind 24x50 mixture of 800 real candidates + 400 synthetic inputs.

Does not access synthetic construction answers or original OSM tags.
Never tells outside annotator source group. Separate private ID origin map.
"""
import csv,hashlib,json,random,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
GOLD=HERE.parent
sys.path.insert(0,str(GOLD))
from tao_goi_gan_nhan import generate
from gold_common import output_csv,sha256

SEED=20261030
def main():
    sources={
        "real":GOLD/"mau_ung_vien.csv",
        "synthetic":HERE/"tong_hop_dau_vao.csv"
    }
    items=[]
    private={}
    for kind,path in sources.items():
        with path.open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        for r in rows:
            if r["id"] in private:raise ValueError("ID collision between real and synthetic")
            private[r["id"]]=kind
            items.append({"id":r["id"],"dau_vao":r["dau_vao"]})
    if len(items)!=1200:raise AssertionError("Expected exactly 1200 inputs")
    random.Random(SEED).shuffle(items)
    sealed=HERE/"goi_tron_ung_vien_va_tong_hop"
    priv=HERE/"nguon_id_RIENG_KHONG_GUI_AI.json"
    if sealed.exists() or priv.exists():raise FileExistsError("Blind mixed package already exists")
    schema=json.loads((GOLD/"SCHEMA_NHAN.json").read_text(encoding="utf8"))
    convention=(GOLD/"QUY_UOC_NHAN.md").read_text(encoding="utf8")
    sealed.mkdir()
    for number,rows,prompt in generate(items,convention,schema,50):
        folder=sealed/f"goi_{number:02d}"
        folder.mkdir()
        output_csv(folder/"dau_vao.csv",rows,("id","dau_vao"))
        (folder/"PROMPT_GAN_NHAN.txt").write_text(prompt,encoding="utf8")
    priv.write_text(json.dumps({"seed":SEED,
         "note":"DO NOT SEND THIS FILE WITH PACKAGES; identifies synthetic inputs",
         "source_by_id":private},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("MIXED_BLIND_PACKAGES_PASS",len(items),"packages",len(list(sealed.iterdir())),
          "source_counts",{"real":800,"synthetic":400},flush=True)
if __name__=="__main__":main()
