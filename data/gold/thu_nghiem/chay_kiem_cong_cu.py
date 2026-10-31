"""60-address mechanical harness ONLY. Both 'annotators' are dummy fixtures.
Never present this agreement or simulated review as real AI/human evidence.
"""
import copy,csv,json,re,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from gold_common import FIELDS,load_sample,output_csv,output_json
from kiem_nhan import validate_bundle,check_file
from dong_thuan import combine
from lay_mau_kiem import choose
from uoc_luong_sai_so import estimate,cp_upper
from anh_xa_hanh_chinh import Mapper

def run():
    samples=load_sample()[:60]
    assert len(samples)==60
    fixture=[]
    for r in samples:
        # A trivial VALID syntactic span only; not a semantic annotation.
        text=r["dau_vao"]
        match=re.search(r"\d+",text)
        spans=[]
        if match:
            spans=[{"truong":"so_nha","start":match.start(),
                    "end":match.end(),"van_ban":match.group()}]
        fixture.append({"id":r["id"],"dau_vao":text,
                        "spans":spans,"abstain":False,"ly_do_abstain":""})
    A={"bo_gan":"KIEM_CONG_CU_KHONG_PHAI_GOLD_NGUOI_VIET_FIXTURE","nhan":fixture}
    B=copy.deepcopy(A)
    B["bo_gan"]="KIEM_CONG_CU_KHONG_PHAI_GOLD_BAN_SAO_CO_HOC_KHONG_DOC_LAP"
    # One planned syntactic disagreement to exercise queue.
    target=next(i for i,r in enumerate(B["nhan"]) if r["spans"])
    B["nhan"][target]["spans"]=[]
    expected={r["id"]:r["dau_vao"] for r in samples}
    for data in (A,B):
        assert not validate_bundle(data,expected)
    output_csv(ROOT/"60_DAU_VAO_KIEM_CONG_CU.csv",samples,
               ("id","dau_vao"))
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_1_FILE_NHAN_VIET.json",A)
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_2_BAN_SAO_CO_HOC.json",B)
    for p in ROOT.glob("KIEM_CONG_CU_KHONG_PHAI_GOLD_*_*.json"):
        content,errors=check_file(p,expected)
        assert not errors,(p,errors)
    combined,queue=combine([A,B])
    assert len(queue)>=1
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_DONG_THUAN.json",combined)
    output_csv(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_HANG_DOI.csv",
               queue,("id","dau_vao","truong",A["bo_gan"],B["bo_gan"]))
    check=choose(combined,n=30,seed=20261030)
    output_csv(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_PHIEU_CHO_NGUOI.csv",
               check,("id","dau_vao","truong","gia_tri_dong_thuan",
                      "dung_sai","ghi_chu_nguoi_duyet"))
    # Synthetic-only exercise for the error-bound implementation.
    artificial=copy.deepcopy(check)
    for v in artificial:v["dung_sai"]="dung"
    artificial[0]["dung_sai"]="sai"
    output_csv(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_PHIEU_GIA_LAP.csv",
               artificial,("id","dau_vao","truong","gia_tri_dong_thuan",
                           "dung_sai","ghi_chu_nguoi_duyet"))
    cp_test=estimate(artificial)
    # This output MUST never be interpreted as verified human labels.
    cp_test["human_verified"]=False
    cp_test["synthetic_fixture_only"]=True
    cp_test["warning"]="CHỈ KIỂM CODE. KHÔNG CÓ NGƯỜI DUYỆT, KHÔNG PHẢI GOLD"
    cp_test["cp_zero_150"]=cp_upper(0,150)
    cp_test["cp_three_150"]=cp_upper(3,150)
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_CP_GIA_LAP.json",cp_test)
    mapper=Mapper()
    mapped=[{"id":r["id"],**mapper.admin_from_spans(r["spans"])} for r in fixture]
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_ANH_XA.json",mapped)
    result={"status":"TOOLING_ONLY_PASS","sample_size":60,"dummy_consensus_count":combined["nhat_tri_tat_ca"],
            "dummy_queue_rows":len(queue),"dummy_check_rows":len(check),
            "human_label_rows":0,"true_independent_AI_annotators":0,
            "not_gold":True}
    output_json(ROOT/"KIEM_CONG_CU_KHONG_PHAI_GOLD_KET_QUA.json",result)
    print("DEMO_TOOLING_PASS",json.dumps(result,ensure_ascii=False))
if __name__=="__main__":run()
