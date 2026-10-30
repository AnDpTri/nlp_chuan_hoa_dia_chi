"""Kiểu dữ liệu dùng chung giữa các bước của pipeline.

Mọi bước giao tiếp với nhau qua các kiểu ở đây, để có thể thay cách làm
của một bước mà không phải sửa các bước khác.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DonVi:
    """Một nút trong cây hành chính (cũ hoặc mới)."""

    ma: str
    cap: str  # "tinh" | "huyen" | "xa"
    loai: str  # "Tỉnh", "Thành phố", "Quận", "Phường", "Xã", ...
    ten: str
    ma_cha: str | None
    cay: str  # "cu" | "moi"


@dataclass(frozen=True)
class UngVien:
    """Một đoạn trong chuỗi đầu vào có thể là một đơn vị hành chính."""

    bat_dau: int  # vị trí token bắt đầu (tính cả)
    ket_thuc: int  # vị trí token kết thúc (không tính)
    ma: str
    cay: str
    kieu_khop: str  # "chinh_xac" | "khong_dau" | "khac_dau" | "viet_tat" | "sai_chinh_ta" | "khac_loai"
    diem: float
    cap: str = ""
    co_tien_to: bool = False


@dataclass
class DuongDi:
    """Một giả thuyết; từng ứng viên giữ mốc riêng, cay có thể là 'tron'."""

    cay: str
    ung_vien: list[UngVien]
    diem: float


@dataclass
class KetQua:
    """Đầu ra cho một địa chỉ, đúng các trường trong bai_toan.md mục 3."""

    so_nha: str = ""
    ngo_ngach_hem: str = ""
    thon_xom: str = ""
    duong: str = ""
    xa_phuong: str = ""  # tên chính thức sau sáp nhập
    ma_xa: str = ""
    tinh: str = ""
    ma_tinh: str = ""
    dia_chi_chuan: str = ""
    canh_bao: list[str] = field(default_factory=list)
    xa_moi_ung_vien: list[dict[str, str]] = field(default_factory=list)
    dau_vet: list[dict] = field(default_factory=list)
    phan_chua_phan_loai: str = ""
    thong_ke: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DonViNhan:
    """Một đơn vị hành chính đã nhận ra trong địa chỉ: cấp, mã và mốc (cũ/mới) của mã."""

    cap: str  # "tinh" | "huyen" | "xa"
    ma: str
    cay: str  # "cu" | "moi"


@dataclass
class DiaChiSach:
    """Địa chỉ sạch có cấu trúc, giao diện duy nhất giữa tiền xử lý và chuyển đổi.

    Chỉ chứa giá trị đã chọn, không chứa token, điểm hay giả thuyết của beam;
    một địa chỉ sạch dựng tay hoặc đọc từ nguồn khác cũng đưa thẳng vào chuyển đổi được.
    """

    so_nha: str = ""
    ngo_ngach_hem: str = ""
    thon_xom: str = ""
    duong: str = ""
    phan_chua_phan_loai: str = ""
    don_vi: list[DonViNhan] = field(default_factory=list)
    # Các cách hiểu điểm gần bằng (kể cả cách đã chọn); rỗng nghĩa là chỉ có đúng một cách hiểu.
    cach_hieu_gan: list[list[DonViNhan]] = field(default_factory=list)
    ma_xa: str = ""
    ma_huyen: str = ""
    ma_tinh: str = ""
    xa: str = ""
    huyen: str = ""
    tinh: str = ""
    cay: str = ""
    canh_bao_giua: list[str] = field(default_factory=list)
    canh_bao_sau: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    dau_vet: list[dict] = field(default_factory=list)
    thong_ke: dict = field(default_factory=dict)
    chuoi: str = ""


@dataclass
class NoiBoTienXuLy:
    """Trạng thái trung gian của tiền xử lý; chỉ tiền xử lý (và bằng chứng hợp đồng) dùng, không qua chuyển đổi."""

    records: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    crf_context: object = None
    ranked: list = field(default_factory=list)
    close: list = field(default_factory=list)
    score: float = 0.0
    spans: list = field(default_factory=list)
    chi_tiet_truoc_duong: dict = field(default_factory=dict)  # chi tiết trước bước khôi phục tên đường
    name_evidence: object = None

