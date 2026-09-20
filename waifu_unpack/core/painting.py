"""立绘切片资源组装：从 Unity bundle 提取 painting 切片 PNG。

碧蓝航线的 painting 样本 = **一张大 Texture2D + 一个 Sprite + 可选 Mesh**：
- Sprite 的 `m_RD.texture` 引用大图，`m_RD.textureRect` 定义实际内容矩形
  （大图右侧/下侧带透明 padding，立绘居中）；
- `m_IndexBuffer` / `m_PhysicsShape` / `Mesh` 是立绘的网格数据。

按用户拍板：**只导切片 PNG，不做 Mesh 重组** —— 按 Sprite.textureRect 从大图
裁出内容区（裁掉边缘 padding），保留透明背景。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PIL import Image

from waifu_unpack.core.live2d import _image_to_png_bytes

if TYPE_CHECKING:
    import UnityPy

log = logging.getLogger(__name__)


@dataclass
class PaintingExport:
    """一个立绘切片：name 为资源名，variant 对同 bundle 内同名资源编号。"""

    name: str
    png: bytes
    variant: int = 0
    missing: list[str] = field(default_factory=list)

    @property
    def stem(self) -> str:
        """导出文件名用的基名（同名变体加 _N 后缀，从 _2 起）。"""
        return self.name if self.variant == 0 else f"{self.name}_{self.variant + 1}"


def iter_painting_exports(env: "UnityPy.Environment") -> list[PaintingExport]:
    """扫描一个立绘 bundle，按 Sprite 内容矩形裁出切片 PNG。

    没有 Sprite 引用的 Texture2D 直接整图输出兜底。同名资源自动编号
    （variant 从 0 起，stem 到 _2/_3…），适配器无需再处理撞名。
    """
    objects = list(env.objects)

    tex_by_pid: dict[int, Image.Image] = {}
    tex_name: dict[int, str] = {}
    for obj in objects:
        try:
            if obj.type.name != "Texture2D":
                continue
            r = obj.read()
            img = r.image
            if img is None:
                continue
            if img.mode not in ("RGBA", "RGB"):
                img = img.convert("RGBA")
            tex_by_pid[obj.path_id] = img
            tex_name[obj.path_id] = str(getattr(r, "m_Name", "")).strip()
        except Exception:  # noqa: BLE001 - 单个对象失败不影响整体
            continue

    exports: list[PaintingExport] = []
    used_tex: set[int] = set()

    for obj in objects:
        try:
            if obj.type.name != "Sprite":
                continue
            r = obj.read()
            rd = getattr(r, "m_RD", None)
            if rd is None:
                continue
            pid = getattr(rd.texture, "path_id", None)
            img = tex_by_pid.get(pid)
            if img is None:
                continue
            rect = getattr(rd, "textureRect", None)
            name = str(getattr(r, "m_Name", "")).strip() or tex_name.get(pid) or f"sprite_{pid}"
            if rect is None:
                exports.append(PaintingExport(name, _image_to_png_bytes(img, name)))
            else:
                png, ok = _crop_sprite(img, rect.width, rect.height, rect.x, rect.y, name)
                entry = PaintingExport(name, png)
                if not ok:
                    entry.missing.append(f"sprite {name!r} textureRect 越界，已整图输出")
                exports.append(entry)
            used_tex.add(pid)
        except Exception as exc:  # noqa: BLE001 - 单个对象失败不影响整体
            log.warning("sprite %r 切片失败: %s", obj.path_id, exc)

    for pid, img in tex_by_pid.items():
        if pid in used_tex:
            continue
        name = tex_name.get(pid) or f"texture_{pid}"
        exports.append(PaintingExport(name, _image_to_png_bytes(img, name)))

    counts: dict[str, int] = {}
    for e in exports:
        n = counts.get(e.name, -1) + 1
        counts[e.name] = n
        e.variant = n
    return exports


def _crop_sprite(
    img: Image.Image, rect_w: float, rect_h: float, rect_x: float, rect_y: float, name: str
) -> tuple[bytes, bool]:
    """按 textureRect 裁出内容区。

    Unity 的 Sprite textureRect 原点在纹理左下角（UV 系），转成 PIL 左上原点。
    越界部分 clamp，全越界时返回整图并标记失败。
    """
    W, H = img.size
    left = max(0, round(rect_x))
    right = min(W, round(rect_x + rect_w))
    bottom_px = H - round(rect_y)
    top_px = H - round(rect_y + rect_h)
    top = max(0, top_px)
    bottom = min(H, bottom_px)
    if right <= left or bottom <= top:
        return _image_to_png_bytes(img, name), False
    return _image_to_png_bytes(img.crop((left, top, right, bottom)), name), True