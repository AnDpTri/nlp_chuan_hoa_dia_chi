"""Export 50-row offline prompt packages for independently operated annotators.
NO API, network, AI model, or automatic real label calls.
"""
import argparse,json
from pathlib import Path
from gold_common import GOLD,load_sample,output_csv,FIELDS

def example():
    text="12 Trần Phú, Hà Nội"
    spans=[]
    for field,value in [("so_nha","12"),("duong","Trần Phú"),("tinh","Hà Nội")]:
        start=text.index(value)
        spans.append({"truong":field,"start":start,"end":start+len(value),"van_ban":value})
    return {"id":"VI_DU_KHONG_CO_TRONG_MAU","dau_vao":text,
            "spans":spans,"abstain":False,"ly_do_abstain":""}

def generate(sample,convention,schema,batch=50):
    for start in range(0,len(sample),batch):
        end=min(start+batch,len(sample))
        items=sample[start:end]
        yield start//batch+1,items,(
            "# HƯỚNG DẪN GÁN NHÃN ĐỘC LẬP — NHÃN ỨNG VIÊN, KHÔNG PHẢI GOLD\n\n"
            "Bạn là bộ gán nhãn chỉ nhận văn bản địa chỉ. Không có quyền xem hoặc dùng nhãn của bộ gán khác. "
            "Gán nhãn TỪNG ĐỊA CHỈ đúng theo thứ tự JSON cung cấp. "
            "Chỉ căn cứ chuỗi đầu vào; không suy diễn từ POI/tên cơ sở, tọa độ, URL, OSM tags hay danh sách mã. "
            "Thiếu thông tin để trống; không chắc thì abstain=true và nêu lý do; không chép đáp án mẫu khi không có bằng chứng. "
            "Không ghi mã xã, mã tỉnh, tên chính thức suy diễn hoặc danh mục hành chính trong đầu ra. "
            "Span phải chứa đúng văn bản nguyên gốc, dùng offset zero-based [start,end) theo ký tự Python; "
            "mọi span không chồng lấn. Nhãn hành chính xa/huyen/tinh đúng như xuất hiện trong chuỗi, không phải đơn vị đích. "
            "Một trường có thể có nhiều span nếu văn bản có nhiều đề cập. "
            "Nếu gặp xã cũ bị chia không có căn cứ theo thôn/số nhà, đánh dấu span tên xã nếu rõ và abstain với lý do. "
            "Quy ước dưới đây là NHÁP, những điểm chưa quyết phải abstain thay vì tự chọn. "
            "Trả ra một JSON duy nhất có hai khóa bo_gan và nhan. bo_gan phải là ID của hệ thống gán riêng.\n\n"
            "## QUY ƯỚC NHÁP (CHƯA ĐƯỢC CON NGƯỜI CHỐT)\n\n"
            +convention+"\n\n"
            "## SCHEMA OUTPUT\n\n"+json.dumps(schema,ensure_ascii=False,indent=2)+"\n\n"
            "## VÍ DỤ CÚ PHÁP (không phải dữ liệu khảo sát)\n\n"
            +json.dumps({"bo_gan":"TEN_BO_GAN_RIENG","nhan":[example()]},ensure_ascii=False,indent=2)
            +"\n\n## CÁC ĐỊA CHỈ CẦN GÁN NHÃN\n\n"
            +json.dumps([{"id":r["id"],"dau_vao":r["dau_vao"]} for r in items],
                        ensure_ascii=False,indent=2)+"\n"
        )

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--sample",type=Path,default=GOLD/"mau_ung_vien.csv")
    a.add_argument("--output-dir",type=Path,default=GOLD/"goi_gan_nhan")
    a.add_argument("--size",type=int,default=50)
    args=a.parse_args()
    if args.size<1:raise ValueError("size must be >=1")
    if args.output_dir.exists():raise FileExistsError(args.output_dir)
    rows=load_sample(args.sample)
    convention=(GOLD/"QUY_UOC_NHAN.md").read_text(encoding="utf8")
    schema=json.loads((GOLD/"SCHEMA_NHAN.json").read_text(encoding="utf8"))
    args.output_dir.mkdir(parents=True)
    count=0
    for no,items,prompt in generate(rows,convention,schema,args.size):
        folder=args.output_dir/f"goi_{no:02d}"
        folder.mkdir()
        (folder/"PROMPT_GAN_NHAN.txt").write_text(prompt,encoding="utf8")
        output_csv(folder/"dau_vao.csv",
                   [{"id":r["id"],"dau_vao":r["dau_vao"]} for r in items],
                   ("id","dau_vao"))
        count+=1
    print("OFFLINE_PACKAGES_CREATED",count,"addresses",len(rows),"no_api_calls")
if __name__=="__main__":main()
