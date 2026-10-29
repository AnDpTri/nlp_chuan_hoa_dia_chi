"""Đọc tên tương đối trong manifest Windows/Linux mà không sửa bytes dữ liệu."""

from pathlib import Path, PurePosixPath


def tu_manifest(root, name):
    normalized = str(name).replace('\\', '/')
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or '..' in relative.parts or ':' in normalized or not relative.parts:
        raise ValueError('Đường dẫn manifest không hợp lệ: ' + str(name))
    root = Path(root).resolve()
    target = root.joinpath(*relative.parts).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Đường dẫn manifest vượt thư mục gốc: ' + str(name))
    return target
