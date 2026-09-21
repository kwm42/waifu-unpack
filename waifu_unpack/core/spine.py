"""Spine 模型资源组装：从 Unity bundle 中提取并组合成可用的 spine 工程目录。

产出物为 Spine 原生格式：
    base.atlas  (TextAsset，内容为 atlas 文本)
    base.skel   (TextAsset，二进制/JSON 骨架)
    <贴图>.png

商家常见的存法：TextAsset 的 m_Name 带 `.asset` / `.txt` / `.bytes` 后缀，
这里统一剥掉后再与 atlas 内容里引用的贴图文件名对齐。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Optional

from PIL import Image

if TYPE_CHECKING:
    import UnityPy

log = logging.getLogger(__name__)

TEXT_EXTENSIONS = (".txt", ".asset", ".bytes", ".json", ".skel", ".atlas")
SKEL_EXTENSIONS = (".skel", ".json")
ATLAS_EXTENSIONS = (".atlas",)
_STRIP_TAIL_RE = re.compile(r"\.(?:asset|txt|bytes)$", re.IGNORECASE)
_TEXTURE_REF_RE = re.compile(r"^\s*(\S+?\.(?:png|jpe?g))$", re.IGNORECASE)
# 无后缀骨架的判定：内容以 Spine JSON 头（"{"skeleton":")开头。
# 部分游戏（如交错战线）的骨架 TextAsset 不带 .skel/.json 后缀，靠内容签名识别。
_SPINE_JSON_HEAD = b'{"skeleton"'


@dataclass
class SpineExport:
    """一个独立的 spine 模型（已配齐骨架+atlas，贴图尽量配齐）。

    base 用于身份解析（角色/皮肤目录）；role 决定次级目录
    （character=人物 / background=背景）；variant>0 表示同角色目录下的
    多套变体，文件名加 `_N` 后缀区分。
    """

    base: str
    atlas_text: str
    skel_bytes: bytes
    role: str = "character"
    variant: int = 0
    textures: dict[str, bytes] = field(default_factory=dict)
    missing_textures: list[str] = field(default_factory=list)
    container: str = ""

    @property
    def stem(self) -> str:
        """导出文件名用的基名（变体加 _N 后缀，从 _2 起）。"""
        return self.base if self.variant == 0 else f"{self.base}_{self.variant + 1}"


def _clean_asset_name(name: str) -> str:
    """去掉 Unity 导出的资源名尾巴（.asset/.txt/.bytes），转小写对比。"""
    return _STRIP_TAIL_RE.sub("", name)


def _asset_stem(name: str) -> str:
    """去掉后缀（含 .atlas/.skel/.json），得到分组主键。"""
    return re.sub(r"\.(?:atlas|skel|json)$", "", _clean_asset_name(name), flags=re.IGNORECASE)


def _is_spine_json(data: bytes) -> bool:
    """内容疑似 Spine JSON 骨架（用于无后缀命名识别）。"""
    head = data[:64].lstrip()
    return head.startswith(_SPINE_JSON_HEAD)


def _text_asset_bytes(script) -> bytes:
    """TextAsset.m_Script 可能是 bytes/str 或含 surrogate 的 str，统一还原成字节。"""
    if isinstance(script, str):
        return script.encode("utf-8", "surrogateescape")
    if isinstance(script, (bytes, bytearray)):
        return bytes(script)
    return str(script).encode("utf-8", "replace")


def iter_spine_exports(env: "UnityPy.Environment") -> list[SpineExport]:
    """扫描一个 bundle，返回其中可组成的 spine 模型列表。

    同名资产可能有多套（如人物/背景两套模型），处理策略：
    1. atlas 区域名与骨架 token 重叠度贪心配对（避免交叉配错）；
    2. 贴图通过 SpineAtlasAsset -> Material._MainTex 链精确配对；
    3. 区域数最多的一套作为人物（character），其余作为背景（background）。
    """
    objects = list(env.objects)

    text_assets: list[tuple[str, int, bytes, str]] = []
    for obj in objects:
        try:
            if obj.type.name == "TextAsset":
                ta = obj.read()
                text_assets.append(
                    (
                        str(ta.m_Name),
                        obj.path_id,
                        _text_asset_bytes(ta.m_Script),
                        _obj_container(obj),
                    )
                )
        except Exception:  # noqa: BLE001 - 单个对象失败不影响整体
            continue

    atlases: dict[str, list[tuple[int, str, str]]] = {}
    skeletons: dict[str, list[bytes]] = {}
    for name, pid, data, container in text_assets:
        base = _asset_stem(name)
        low = _clean_asset_name(name).lower()
        if low.endswith(ATLAS_EXTENSIONS):
            atlases.setdefault(base, []).append(
                (pid, data.decode("utf-8", errors="replace"), container)
            )
        elif low.endswith(SKEL_EXTENSIONS):
            skeletons.setdefault(base, []).append(data)
        # 无后缀命名：若内容像 Spine JSON 骨架，也当骨架处理（交错战线等）
        elif "." not in low and _is_spine_json(data):
            skeletons.setdefault(base, []).append(data)

    if not atlases and not skeletons:
        return []

    png_by_pid, png_by_name, atlas_to_textures = _texture_plan(objects)
    used_pngs: set[bytes] = set()

    exports: list[SpineExport] = []

    # 以 atlas 为核心组装；区域数最多者视为人物，其余为背景
    for base, atlas_list in sorted(atlases.items()):
        skel_list = skeletons.pop(base, [])
        pairs = _pair_sets(skel_list, atlas_list)
        pairs.sort(key=lambda p: (len(_atlas_regions(p[2])), len(p[0])), reverse=True)

        for idx, (skel_data, atlas_pid, atlas_text) in enumerate(pairs):
            if idx == 0:
                role, var = "character", 0
            else:
                role, var = "background", idx - 1
            textures, missing = _match_textures(
                atlas_text, atlas_pid, png_by_pid, png_by_name, atlas_to_textures,
                used_pngs,
            )
            exp = SpineExport(
                base=base,
                role=role,
                variant=var,
                atlas_text=atlas_text,
                skel_bytes=skel_data,
                textures=textures,
                missing_textures=missing,
                container=_container_for(atlas_pid, atlas_list),
            )
            for miss in exp.missing_textures:
                log.warning(
                    "atlas %r (role=%s) 引用的贴图 %r 在 bundle 内未找到",
                    base,
                    role,
                    miss,
                )
            exports.append(exp)

        if len(pairs) < len(atlas_list):
            log.warning(
                "同名 atlas 共 %d 套，只配对出 %d 个（缺配套骨架的 atlas 已跳过）",
                len(atlas_list),
                len(pairs),
            )

    # 没有 atlas 的骨架（可能是被包进 SkeletonDataAsset 的情况，先记日志）
    for base, skel_list in skeletons.items():
        for idx, skel_data in enumerate(skel_list):
            role = "character" if idx == 0 else "background"
            stub = base if idx == 0 else f"{base}_{idx + 1}"
            log.info("骨架 %r 无配套 atlas，仅尝试直接输出原始文件", stub)
            exports.append(
                SpineExport(
                    base=base, role=role, variant=idx, atlas_text="", skel_bytes=skel_data
                )
            )
    return exports


def _match_textures(
    atlas_text: str,
    atlas_pid: int,
    png_by_pid: dict[int, bytes],
    png_by_name: dict[str, list[bytes]],
    atlas_to_textures: dict[int, list[int]],
    used_pngs: set[bytes],
) -> tuple[dict[str, bytes], list[str]]:
    """按 atlas 页面引用名取贴图：多页 atlas 逐页精确配对，失败按名兜底。

    碧蓝航线的 atlas 可能是多页（多个 `xxxx.png`，对应多个 Material）；SpineAtlasAsset
    的 `materials[]` 顺序与 atlas 页面顺序一一对应，因此这里按位置对齐逐页精确配对。
    used_pngs 记录"已被前几套精确配对使用的贴图字节"，
    名字兜底时跳过它们，避免同 bundle 多套同名贴图互抢（角色/背景各拿各的）。
    返回 (贴图, 缺失列表)。
    """
    refs = _atlas_texture_refs(atlas_text)
    mat_pids = atlas_to_textures.get(atlas_pid) or []
    textures: dict[str, bytes] = {}
    missing: list[str] = []
    for idx, ref in enumerate(refs):
        exact = png_by_pid.get(mat_pids[idx]) if idx < len(mat_pids) else None
        if exact is not None:
            textures[ref] = exact
            used_pngs.add(exact)
            continue
        want = re.sub(r"\.(?:png|jpe?g)$", "", ref, flags=re.IGNORECASE).lower()
        candidates = png_by_name.get(want) or []
        png = next((b for b in candidates if b not in used_pngs), None)
        if png is None and candidates:
            png = candidates[0]
        if png is not None:
            textures[ref] = png
            used_pngs.add(png)
        else:
            missing.append(ref)
    return textures, missing


def _atlas_regions(atlas_text: str) -> set[str]:
    """提取 atlas 中的区域名（去掉 page 文件名、属性行、空行）。"""
    regions: set[str] = set()
    for line in atlas_text.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.endswith((".png", ".jpg", ".jpeg")) or ":" in line:
            continue
        if lower.startswith(("rotate", "xy", "size", "orig", "offset", "index")):
            continue
        regions.add(line)
    return regions


def _skel_tokens(skel_data: bytes) -> frozenset[str]:
    """粗略抽取骨架中出现的标识符 token，与 atlas 区域名做交集估计配对。"""
    return frozenset(
        m.decode() for m in re.findall(rb"[A-Za-z][A-Za-z0-9_]{2,39}", skel_data)
    )


def _pair_sets(
    skel_list: list[bytes], atlas_list: list[tuple[int, str, str]]
) -> list[tuple[bytes, int, str]]:
    """按内容把骨架与 atlas 做贪心最优配对，返回 [(skel, atlas_pid, atlas), ...]。"""
    if len(atlas_list) == 1 and len(skel_list) == 1:
        apid, atext, _ = atlas_list[0]
        return [(skel_list[0], apid, atext)]

    used_skel: set[int] = set()
    used_atlas: set[int] = set()
    pairs: list[tuple[bytes, int, str]] = []
    while True:
        best: Optional[tuple[float, int, int]] = None
        for si, sk in enumerate(skel_list):
            if si in used_skel:
                continue
            sktoks = _skel_tokens(sk)
            for ai, (_, atext, _) in enumerate(atlas_list):
                if ai in used_atlas:
                    continue
                regs = _atlas_regions(atext)
                score = len(regs & sktoks) / max(len(regs), 1)
                if best is None or score > best[0]:
                    best = (score, si, ai)
        if best is None or best[0] <= 0:
            break
        _, si, ai = best
        apid, atext, _ = atlas_list[ai]
        pairs.append((skel_list[si], apid, atext))
        used_skel.add(si)
        used_atlas.add(ai)
    return pairs


def _obj_container(obj) -> str:
    """取 UnityPy 对象容器路径（如 Assets/.../xxx），没有则空串。"""
    try:
        return str(getattr(obj, "container", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _container_for(atlas_pid: int, atlas_list: list[tuple[int, str, str]]) -> str:
    """按 atlas path_id 从列表里取 container 路径。"""
    for pid, _atext, container in atlas_list:
        if pid == atlas_pid:
            return container
    return ""


def _atlas_texture_refs(atlas_text: str) -> list[str]:
    refs: list[str] = []
    for line in atlas_text.splitlines():
        m = _TEXTURE_REF_RE.match(line)
        if m and not line.lstrip().startswith("-"):
            refs.append(m.group(1))
    return refs


def _texture_plan(objects) -> tuple[dict[int, bytes], dict[str, list[bytes]], dict[int, list[int]]]:
    """扫描贴图与 SpineAtlasAsset/Material 的引用关系。

    返回 (png_by_pid, png_by_name, atlas_to_textures)：
    - png_by_pid: Texture2D object path_id -> PNG 字节
    - png_by_name: 小写贴图名 -> [PNG 字节, ...]（同名多张时全保留）
    - atlas_to_textures: TextAsset(atlas) path_id -> [Texture2D path_id, ...]
      按 SpineAtlasAsset.materials[] 顺序对应 atlas 各页面（多页 atlas 逐页匹配）。
    """
    png_by_pid: dict[int, bytes] = {}
    png_by_name: dict[str, list[bytes]] = {}
    material_main_tex: dict[int, int] = {}
    atlas_mbs: list[tuple[int, list]] = []

    # 第一遍：收集贴图 PNG、Material->_MainTex 链，缓存 Atlas MonoBehaviour。
    # 不能单遍处理 Atlas：它的 materials[] 指向的 Material 未必已在此前遍历到，
    # 单遍会把"恰好先遍历到的 Material"当成唯一结果（碧蓝多页贴图曾只配到 1 张）。
    for obj in objects:
        r = obj.read()
        t = obj.type
        if t.name == "Texture2D":
            img = r.image
            if img is None:
                continue
            if img.mode not in ("RGBA", "RGB"):
                img = img.convert("RGBA")
            buf = _image_to_png_bytes(img, str(getattr(r, "m_Name", "")))
            png_by_pid[obj.path_id] = buf
            tex_name = str(getattr(r, "m_Name", "")).lower()
            if "." in tex_name:
                tex_name = tex_name.split(".")[0]
            png_by_name.setdefault(tex_name, []).append(buf)
        elif t.name == "Material":
            tex_pid = _material_main_texture(r)
            if tex_pid is not None:
                material_main_tex[obj.path_id] = tex_pid
        elif t.name == "MonoBehaviour":
            m_name = str(getattr(r, "m_Name", ""))
            if m_name.endswith("_Atlas"):
                atlas_pid = _pptr_id(getattr(r, "atlasFile", None))
                if atlas_pid is not None:
                    atlas_mbs.append((atlas_pid, getattr(r, "materials", None) or []))

    # 第二遍：把 Atlas 的 materials[] 按顺序解析成对应各页面的贴图 path_id 列表。
    atlas_to_textures: dict[int, list[int]] = {}
    for atlas_pid, mats in atlas_mbs:
        texs: list[int] = []
        for mat_pptr in mats:
            mp = _pptr_id(mat_pptr)
            if mp in material_main_tex:
                texs.append(material_main_tex[mp])
        if texs:
            atlas_to_textures[atlas_pid] = texs
    return png_by_pid, png_by_name, atlas_to_textures


def _pptr_id(pptr) -> Optional[int]:
    if pptr is None:
        return None
    pid = getattr(pptr, "path_id", None)
    return pid if isinstance(pid, int) else None


def _material_main_texture(mat) -> Optional[int]:
    """Material.m_SavedProperties.m_TexEnvs['_MainTex'].m_Texture.path_id"""
    props = getattr(mat, "m_SavedProperties", None)
    if props is None:
        return None
    envs = getattr(props, "m_TexEnvs", None)
    target = None
    if isinstance(envs, dict):
        target = envs.get("_MainTex")
    elif envs:
        envs = dict(envs)
        target = envs.get("_MainTex")
    if target is None:
        return None
    return _pptr_id(getattr(target, "m_Texture", None))


def _image_to_png_bytes(img: Image.Image, name: str) -> bytes:
    """导出 PNG。异步兼容 Auto 处理 16 位模式。"""
    import io

    if img.mode == "I;16":
        img = img.point(lambda i: i * (1 / 256)).convert("L")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()