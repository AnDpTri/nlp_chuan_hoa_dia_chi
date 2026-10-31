"""Blind mixed-package ID privacy and synthetic recovery checks."""
from __future__ import annotations
import csv,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
GOLD=ROOT/"data/gold"
HERE=GOLD/"tong_hop"
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(GOLD))
from tao_goi_tron_id_an import records_and_map
from tach_nhan_tu_goi_tron_id_an import read_mixed_labels

class BlindMixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping=json.loads((HERE/"doi_chieu_id_tron_an_RIENG_KHONG_GUI_AI.json")
            .read_text(encoding="utf8"))["source_by_pseudo_id"]
        cls.package_dir=HERE/"goi_tron_mau_id_an"

    def test_pseudonyms_are_nondisclosing_nonoverlapping(self):
        self.assertEqual(len(self.mapping),1200)
        originals={m["id_goc"] for m in self.mapping.values()}
        self.assertEqual(len(originals),1200)
        self.assertFalse(set(self.mapping)&originals)
        self.assertTrue(all(k.startswith("UNGVIEN_") and len(k)==12
                            for k in self.mapping))
        self.assertEqual(sum(m["loai_RIENG"]=="synthetic" for m in self.mapping.values()),400)
        self.assertEqual(sum(m["loai_RIENG"]=="real" for m in self.mapping.values()),800)

    def test_reproducibility_and_package_field_secrecy(self):
        rows,expected=records_and_map()
        self.assertEqual(expected,self.mapping)
        files=sorted(self.package_dir.glob("goi_*/dau_vao.csv"))
        self.assertEqual(len(files),24)
        actual=[]
        for f in files:
            with f.open(encoding="utf-8-sig",newline="") as stream:
                dataset=list(csv.DictReader(stream))
            self.assertEqual(len(dataset),50)
            self.assertEqual(set(dataset[0]),{"id","dau_vao"})
            actual.extend(dataset)
            prompt=(f.parent/"PROMPT_GAN_NHAN.txt").read_text(encoding="utf8")
            self.assertNotIn("loai_RIENG",prompt)
            self.assertNotIn("source_by_pseudo_id",prompt)
        self.assertEqual(actual,rows)

    def test_recover_400_from_24_pseudonymous_mixed_model_outputs(self):
        # Reuse sealed candidate labels as a fixture, with a mock package reader.
        # No answer file is opened. Tests ID-only reconciliation and completeness.
        sources={}
        for p in [GOLD/"gan_nhan_codex/codex_gpt_800.json",
                  HERE/"codex_gpt_tong_hop_400.json"]:
            b=json.loads(p.read_text(encoding="utf8"))
            sources.update({row["id"]:row for row in b["nhan"]})
        def mock_read(path,expected):
            n=int(Path(path).stem.split("_")[-1])
            rows=[]
            for pseudo,text in expected.items():
                original=self.mapping[pseudo]["id_goc"]
                row=sources[original].copy()
                self.assertEqual(row["dau_vao"],text)
                row["id"]=pseudo
                rows.append(row)
            return {"bo_gan":"codex_gpt","nhan":rows},[]
        files=[Path(f"goi_{n:02d}.json") for n in range(1,25)]
        with patch("tach_nhan_tu_goi_tron_id_an.check_file",side_effect=mock_read):
            result=read_mixed_labels(files)
        self.assertEqual(len(result["nhan"]),400)
        self.assertEqual({x["id"]:x for x in result["nhan"]},
           {k:v for k,v in sources.items() if 801<=int(k.split("_")[-1])<=1200})

if __name__=="__main__":unittest.main()
