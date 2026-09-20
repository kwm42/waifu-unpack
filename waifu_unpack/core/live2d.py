"""Live2D (Cubism) 模型资源组装：从 Unity bundle 提取 moc3 模型。

产出物为 Cubism3 原生格式（碧蓝航线等游戏）：
    model3.json          模型配置（本模块组装最小有效结构）
    <映射> .moc3         核心模型二进制
    physics3.json        物理配置（可选）
    textures/xxx.png     部件贴图

碧蓝航线的 live2d 是**烘焙式 Cubism prefab**（非 TextAsset 包装）：
- bundle 内是大量 ArtMesh GameObject + CubismRenderer/CubismDrawable 组件，
  容器 key 形如 `Assets/ArtResource/Live2d/<key>/<key>.prefab`；
- 原生 `.moc3` 二进制内嵌在 MonoBehaviour(CubismMoc) 的序列化字节里
  （从 `MOC3` 魔数起直到该对象序列化数据末尾）；
- `physics3.json` 是 TextAsset（m_Name 形如 `<key>.physics3`）；
- 贴图是 Texture2D（m_Name 如 `texture_00`/`texture_01`）；
- 原生 `model3.json` 不在 bundle 内，由本模块组装最小有效结构。
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    import UnityPy

log = logging.getLogger(__name__)

_MOC3_MAGIC = b"MOC3"
_PHYSICS_SUFFIX = ".physics3"


@dataclass
class Live2DExport:
    """一个可独立加载的 Live2D 模型。"""

    base: str
    model3_json: dict
    moc3: bytes
    physics3_json: dict | None = None
    textures: dict[str, bytes] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


def iter_live2d_exports(env: "UnityPy.Environment") -> list[Live2DExport]:
    """扫描一个 Cubism 烘焙 bundle，返回其中可组成的 Live2D 模型列表。

    每个 bundle 通常只含一个模型。moc3 取自 CubismMoc（缺失则不产出）；
    physics3 与贴图按需可选，缺失只记日志不影响整体导出。
    """
    objects = list(env.objects)

    moc3: bytes | None = None
    moc_base = ""
    physics: dict | None = None
    textures: dict[str, bytes] = {}
    missing: list[str] = []

    for obj in objects:
        try:
            if obj.type.name == "MonoBehaviour":
                r = obj.read()
                script = getattr(r, "m_Script", None)
                if script is None or not getattr(script, "path_id", None):
                    continue
                sname = _script_name(script)
                if sname == "CubismMoc" and moc3 is None:
                    raw = obj.get_raw_data()
                    i = raw.find(_MOC3_MAGIC)
                    if i >= 0:
                        moc3 = raw[i:]
                        moc_base = str(getattr(r, "m_Name", "")).strip()
                    else:
                        missing.append("CubismMoc 对象内未找到 MOC3 魔数")
            elif obj.type.name == "TextAsset":
                ta = obj.read()
                name = str(getattr(ta, "m_Name", ""))
                if name.lower().endswith(_PHYSICS_SUFFIX) and physics is None:
                    try:
                        physics = json.loads(
                            _text_asset_bytes(getattr(ta, "m_Script", None)).decode("utf-8", "replace")
                        )
                    except (ValueError, UnicodeDecodeError):
                        missing.append(f"physics3 解析失败: {name}")
            elif obj.type.name == "Texture2D":
                img = obj.read().image
                if img is None:
                    continue
                if img.mode not in ("RGBA", "RGB"):
                    img = img.convert("RGBA")
                name = str(getattr(obj.read(), "m_Name", "")).strip() or f"texture_{len(textures)}"
                textures[name] = _image_to_png_bytes(img, name)
        except Exception:  # noqa: BLE001 - 单个对象失败不影响整体
            continue

    if not moc3:
        missing.append("moc3（未找到 CubismMoc 组件）")
        return []

    base = moc_base
    if not base:
        for obj in objects:
            if obj.type.name == "TextAsset":
                n = str(getattr(obj.read(), "m_Name", ""))
                if n.lower().endswith(_PHYSICS_SUFFIX):
                    base = n.rsplit(".", 1)[0]
                    break

    model3 = _build_model3_json(base, sorted(textures), physics is not None)

    return [
        Live2DExport(
            base=base,
            model3_json=model3,
            moc3=moc3,
            physics3_json=physics,
            textures=textures,
            missing=missing,
        )
    ]


def _script_name(script) -> str:
    """通过 PPtr 读出 MonoScript 的名字。"""
    try:
        return str(getattr(script.read(), "m_Name", ""))
    except Exception:  # noqa: BLE001
        return ""


def _text_asset_bytes(script) -> bytes:
    if isinstance(script, str):
        return script.encode("utf-8", "surrogateescape")
    if isinstance(script, (bytes, bytearray)):
        return bytes(script)
    return str(script).encode("utf-8", "replace")


def _build_model3_json(base: str, texture_names: list[str], has_physics: bool) -> dict:
    refs = {
        "Moc": f"{base}.moc3",
        "Textures": [f"{n}.png" for n in texture_names],
    }
    if has_physics:
        refs["Physics"] = f"{base}.physics3.json"
    return {
        "Version": 3,
        "FileReferences": refs,
        "Groups": [],
        "HitAreas": [],
    }


def _image_to_png_bytes(img: Image.Image, name: str) -> bytes:
    """导出 PNG。并行兼容 Auto 处理 16 位模式。"""
    if img.mode == "I;16":
        img = img.point(lambda i: i * (1 / 256)).convert("L")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()