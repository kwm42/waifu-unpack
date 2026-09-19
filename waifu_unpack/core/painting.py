"""静态立绘（普通大图）提取。

碧蓝航线等游戏把立绘拆成 Texture2D 切片 + Mesh 引用；
本模块版本只导切片 PNG（Mesh 重组单项在后续里程碑提供）。
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def export_painting_textures(env, textures_out: Path, prefix: str = "tex") -> int:
    """把 bundle 内所有 Texture2D 直接导出为 PNG 到 textures_out，返回数量。

    仅面向"把切片完整保留"的场景；不做 alpha 通道合并 / mesh 重组。
    """
    import io

    from PIL import Image

    textures_out.mkdir(parents=True, exist_ok=True)
    count = 0
    for obj in env.objects:
        try:
            if obj.type.name != "Texture2D":
                continue
            tex = obj.read()
            img: Image.Image = tex.image
            if img is None:
                continue
            name = str(tex.m_Name) or f"{prefix}_{obj.path_id}"
            if img.mode not in ("RGBA", "RGB"):
                img = img.convert("RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            (textures_out / f"{name}.png").write_bytes(buf.getvalue())
            count += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("立绘贴图 %r 导出失败: %s", obj.path_id, exc)
    return count