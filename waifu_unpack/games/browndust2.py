"""Brown Dust 2 (棕色尘埃2) 适配器。

资源格式（样本 + 参考程序已核实）：
- 资源目录是来源地目录，典型的 `Shared/<bundleName>/<hash>/__data`（__data 即 bundle 本体）。
- bundle 是无版本串的 Unity Bundle（版本被抹），`forced_unity_version = "2022.3.22f1"`
  fallback 可打开（与参考程序的 ArknightsStudioCLI `--unity-version 2022.3.22f1` 一致）。
- 内容物：Spine 为裸 TextAsset(atlas/skel) + Texture2D；另有 chibi 小人帧、costume 立绘/图标、
  skill 图标、对话框头像、壁纸等离散贴图，均按资产名（m_Name）正则归类。
- `names/browndust2.json` 由参考程序的 `mapping.json` 转换而成（characters/skins 两表），
  `resolve_identity` 查角色/皮肤（值形如 "Alec\\The_Destruction" 或仅角色名）。

输出结构（参考程序资产分类，可映射的角色/皮肤放由其决定的多级目录）：
    output/browndust2/spine/character/<角色>/<皮肤>/<base>.atlas|.skel|<贴图>.png
    output/browndust2/spine/interaction|light_novel_talk|npc|skill_cutscene/<角色>/[<皮肤>/]<base>...
    output/browndust2/spine/special_animation|miscellaneous/<base>...
    output/browndust2/ui/costume_face|costume_icon|costume_skill_face|skill_icons|
        speech_bubble_faces|wallpapers|skill_cutscene_background/<base>.png
    output/browndust2/chibis/<角色>/<皮肤>/<帧>.png
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import UnityPy

from waifu_unpack.core import spine
from waifu_unpack.games.base import GameAdapter

log = logging.getLogger(__name__)

# 参考程序 postExtraction.py 的分类正则（脚本原样移植）
_CATEGORY_RE = [
    ("character", r"^char[0-6][\d_c]*\.(?:png|atlas|skel)"),
    ("interaction", r"^illust_dating[\d_]*\.(?:png|atlas|skel)"),
    ("light_novel_talk", r"^illust_talk[_\d]*\.(?:png|atlas|skel)"),
    ("npc", r"^npc[_ellin|\d]*\.(?:png|atlas|skel)"),
    ("skill_cutscene", r"^cutscene_char[\d_a]*\.(?:png|atlas|skel)"),
    (
        "special_animation",
        r"^(specialillust)?(illust_special)?(illust_pack)?(story_pack)?[\d_]*\.(?:png|atlas|skel)",
    ),
    (
        "miscellaneous",
        r"^(avatarbodyaccessory)?(colosseumskip)?(pvpskip)?(event_bt)?(Interaction)?"
        r"(RhythmHitAnim)?[\d_]*\.(?:png|atlas|skel)",
    ),
]

_UI_RE = [
    ("costume_face", r"^illust_inven_char[\d_c]*\.png"),
    ("costume_icon", r"^icon_costume[\d_]*\.png"),
    ("costume_skill_face", r"^illust_skill_char[\d_]*\.png"),
    ("skill_icons", r"^skillicon[\d_]*\.png"),
    ("speech_bubble_faces", r"^illust_(npc)?face[\d_]*\.png"),
    (
        "wallpapers",
        r"^(bg_idcard_bg|bg_home_wallpaper|bg_guild|bg_goldencolosseum|bg_homedefault)[\d_a-z]*\.png",
    ),
]

_CHIBI_RE = r"^Char[01][\d]{5}_(GetItem|Idle|Move|Rest|Sit|Talent|Victory)?_?[\S]*\.png"

# 参考程序的手工修补（硬编码修复，与 mapping.json 配套）
_SKIP_CHAR_PNG = {"char000201_1"}
_SKIP_SKILL_CUTSCENE = {"char061303"}
_CHAR_REMAP = {"char101601": "char060401"}
_NPC_LOEN_TO_CHAR = "npc300501"  # Loen: npc -> character/Loen/Last_Hope (char003201)
_CHIBI_NOT_ALLOWED = {"char000302", "char000404", "char001103", "char002901", "char050201"}
_AVATAR_ALLOWED = {"avatarbodyaccessory_1006", "avatarbodyaccessory_1007"}
_ICON_SHORT_IDS = {
    "icon_costume101_",
    "icon_costume201_",
    "icon_costume202_",
    "icon_costume204_",
    "icon_costume301_",
    "icon_costume401_",
    "icon_costume501_",
    "icon_costume601_",
}
_SKIP_ICON = {"icon_costume001103_"}
_FACE_NOT_ALLOWED = {
    "illust_face800001_32",
    "illust_face00440101_1260",
    "illust_face00440106_1261",
    "illust_face00440107_1262",
    "illust_npcface00040172_963",
    "illust_npcface0000070172_850",
    "illust_npcface0000080172_851",
    "illust_npcface00080172_1752",
    "illust_npcface0000130101_906",
    "illust_npcface0000140101_907",
    "illust_npcface0000170101_918",
    "illust_npcface0016090101_1126",
    "illust_npcface0016090101_1126_1",
    "illust_npcface81460101_1658",
    "illust_npcface4000260172_1106",
    "illust_npcface4000270172_1107",
    "illust_npcface4000290101_1109",
    "illust_npcface4000300101_1110",
    "illust_npcface4000310101_1111",
    "illust_npcface4000350101_1112",
    "illust_npcface4000360101_1113",
    "illust_npcface4000370101_1114",
    "illust_npcface4000510101_1127",
    "illust_npcface4000710172_1246",
    "illust_npcface4000720172_1247",
    "illust_npcface4000720172_1248",
    "illust_npcface4000720172_1249",
    "illust_npcface4000720172_1250",
    "illust_npcface4000730172_1248",
    "illust_npcface4000740172_1249",
    "illust_npcface4000750172_1250",
    "illust_npcface4000920172_1366",
    "illust_npcface4001060172_1482",
    "illust_npcface4001070172_1483",
    "illust_npcface4001080172_1484",
    "illust_npcface4001240172_1655",
    "illust_npcface4001250172_1656",
    "illust_npcface4001260172_1657",
    "illust_npcface4001380172_1681",
    "illust_npcface4001390172_1682",
    "illust_npcface4001400172_1683",
    "illust_npcface4001440172_1680",
    "illust_npcface40004101177_1125",
}

# 参考程序 fixAtlasFiles：atlas 文本内贴图引用修复
_ATLAS_FIXES = (
    ("char060401", "char101601", "char060401"),
    ("char000402", ".skel.png", ".png"),
    ("char003201", "npc300501", "char003201"),
    ("cutscene_char061002", "Char061002", "char061002"),
    ("cutscene_char061092", "char061092_A", "char061092"),
)


class BrownDust2(GameAdapter):
    key = "browndust2"
    display_name = "棕色尘埃2 (Brown Dust 2)"
    supported_types = ("spine", "painting")
    bundle_exts = ("__data", ".bundle", ".ab", ".unity3d")
    forced_unity_version = "2022.3.22f1"

    def is_bundle_file(self, rel: str) -> bool:
        name = Path(rel).name
        return name == "__data" or Path(rel).suffix.lower() in self.bundle_exts

    # ------------------------------------------------------------------
    # 资源同步：从来源地目录按关键词复制 __data 到工作目录
    # ------------------------------------------------------------------
    def sync_from_source(
        self, source_dir: Path, keywords: list[str], dst_dir: Path
    ) -> int:
        """按 readableName 关键词把匹配 bundle 的 `Shared/<b>/<h>/__data` 复制过来。

        返回复制数（已存在且大小一致则跳过）。catalog 读取优先 file.json，
        缺失时退回 catalog_alpha.json 的 m_KeyDataString 解码。
        """
        from waifu_unpack.core.catalog import Catalog

        cat = _load_catalog_from_dir(source_dir)
        if cat is None:
            return 0
        matches = cat.match_keywords(keywords)
        log.info("关键词 %s 命中 %d 个 bundle", keywords, len(matches))

        copied = 0
        have = 0
        for entry in matches:
            rel = Path("Shared") / entry.bundle_name / entry.hash / "__data"
            rel = Path(str(rel).replace("\\", "/"))
            src = source_dir / rel
            if not src.is_file():
                log.info("源缺失，跳过: %s", rel)
                continue
            dst = dst_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_file() and dst.stat().st_size == src.stat().st_size:
                have += 1
                continue
            import shutil

            shutil.copy2(src, dst)
            copied += 1
            log.info("已复制: %s", rel)
        log.info("复制完成: 已复制 %d, 已存在 %d", copied, have)
        return copied

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------
    def extract(
        self,
        env: UnityPy.Environment,
        types: frozenset[str],
        bundle_stem: str = "",
        *,
        input_dir: Path | None = None,
        rel: str = "",
    ) -> list:
        from waifu_unpack.games.base import ExportArtifact

        artifacts: list[ExportArtifact] = []
        if "spine" in types:
            artifacts.extend(self._extract_spine(env))
        if "painting" in types:
            artifacts.extend(self._extract_painting(env, input_dir=input_dir, rel=rel))

        # 同名变体共享贴图 / 多 bundle 共有素材，输出路径去重
        seen: set[str] = set()
        deduped: list[ExportArtifact] = []
        for a in artifacts:
            if a.relpath in seen:
                continue
            seen.add(a.relpath)
            deduped.append(a)
        return deduped

    # ------------------------------------------------------------------
    # spine / painting 内部实现
    # ------------------------------------------------------------------
    def _extract_spine(self, env: UnityPy.Environment) -> list:
        from waifu_unpack.games.base import ExportArtifact

        artifacts: list[ExportArtifact] = []
        for exp in spine.iter_spine_exports(env):
            base = self._fix_base(exp.base)
            cat = self._categorize(f"{base}.atlas")
            if not cat:
                # 参考程序 filterPaths：不匹配任何分类正则的资产直接丢弃
                # （如 Censorship bundle 里名字带 _c 的 spine：cutscene_char[\d_a]*
                # 不含 'c' 字符，参考同样不匹配）
                log.info("无法归类，跳过: %s", base)
                continue
            if cat == "skill_cutscene" and "char061303" in base:
                # 参考程序 mapSkillCutsceneSpines：跳过 Summer Nebris 的 PNG 系列
                continue
            if cat == "miscellaneous" and "avatarbodyaccessory" in base and base not in _AVATAR_ALLOWED:
                # 参考程序 mapMiscellaneousSpines：只保留白名单内的 avatarbodyaccessory
                continue
            mapped = _mapping_id(base, "_", 0 if cat == "character" else 1)
            if cat in ("special_animation", "miscellaneous"):
                # 参考程序 mapSpecialAnimatioSpines / mapMiscellaneousSpines：
                # 无角色映射，整类平铺到 spine/<cat>/ 下，文件名小写
                folder = f"spine/{cat}"
                base = base.lower()
            else:
                role, skin = self._resolve_role_skin(mapped, cat)
                folder = _join_role_skin("spine", cat, role, skin)
            # 参考程序 mapSkillCutsceneSpines：解包树父目录名长于 20 时并入子目录。
            # UnityPy 侧相应信息在 atlas 的 container 路径（Assets/.../<layer>/<file>），
            # 取最后一段目录名作为 layer。
            if cat == "skill_cutscene" and exp.container:
                layer = Path(exp.container.replace("\\", "/")).parent.name
                if len(layer) > 20:
                    folder = f"{folder}/{layer}"
            atlas_text = self._fix_atlas_text(base, exp.atlas_text)
            artifacts.append(
                ExportArtifact(f"{folder}/{base}.atlas", atlas_text.encode("utf-8"))
            )
            artifacts.append(ExportArtifact(f"{folder}/{base}.skel", exp.skel_bytes))
            for png_name, png_bytes in exp.textures.items():
                if re.sub(r"\.png$", "", png_name, flags=re.IGNORECASE) in _SKIP_CHAR_PNG:
                    # 参考程序 mapCharacterSpines：跳过该 PNG（解包残留件）
                    continue
                artifacts.append(ExportArtifact(f"{folder}/{png_name}", png_bytes))
            for miss in exp.missing_textures:
                log.warning("  贴图缺失: %s", miss)
        return artifacts

    def _extract_painting(
        self,
        env: UnityPy.Environment,
        input_dir: Path | None = None,
        rel: str = "",
    ) -> list:
        from waifu_unpack.games.base import ExportArtifact

        artifacts: list[ExportArtifact] = []
        objects = list(env.objects)
        for obj in objects:
            try:
                if obj.type.name != "Texture2D":
                    continue
                tex = obj.read()
                img = tex.image
                if img is None:
                    continue
                img = img.convert("RGBA") if img.mode not in ("RGBA", "RGB") else img
                name = str(tex.m_Name)
                png = _png_bytes(img, name)
                container = str(getattr(obj, "container", "") or "")
                rel_out = self._painting_rel(name, png, container)
                if rel_out:
                    artifacts.append(ExportArtifact(rel_out, png))
            except Exception as exc:  # noqa: BLE001
                log.warning("贴图 %r 导出失败: %s", obj.path_id, exc)
        # skill 图标是 Sprite（非 Texture2D），其图集纹理在独立捆绑包
        # bufficongui1.spriteatlasv2 里。参考 extractSkillIcons 把
        # common-ui-texture 与 bufficongui 两类 bundle 合并进同一
        # AssetStudio 场景再抽 Sprite；这里同样把兄弟 bundle 并进同一
        # UnityPy Environment，skillicon_* 的 m_RD.texture 才能解析。
        artifacts.extend(self._extract_skill_icons(input_dir=input_dir))
        return artifacts

    def _extract_skill_icons(self, input_dir: Path | None) -> list:
        """从合并后的 ui-texture + bufficongui 场景提取 skillicon_* Sprite。

        参考 extractSkillIcons：可读名含 `common-ui-texture` 或 `bufficongui`
        的 bundle 为一组，组内 Sprite 的图集纹理互相引用。需把所有组员
        ``__data`` 读进同一个 UnityPy Environment 才能解析 Sprite.image。
        仅在未能通过 catalog 定位组员时静默返回空（如直接操作无 catalog 目录）。
        同一进程内对同一 input_dir 只合并一次（结果缓存到实例）。
        """
        from waifu_unpack.games.base import ExportArtifact

        if input_dir is None:
            return []
        cache_key = str(input_dir.resolve())
        cached = getattr(self, "_skill_icons_cache", None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        cat = _load_catalog_from_dir(input_dir)
        if cat is None:
            return []
        group: list[Path] = []
        for keyword in ("common-ui-texture", "bufficongui"):
            for entry in cat.match_keywords([keyword]):
                src = input_dir / "Shared" / entry.bundle_name / entry.hash / "__data"
                if src.is_file() and src not in group:
                    group.append(src)
        if not group:
            self._skill_icons_cache = (cache_key, [])
            return []
        log.info("skill_icons：合并 %d 个组员 bundle", len(group))

        env = UnityPy.Environment()
        with self._reader._fallback_version():
            for idx, src in enumerate(group):
                try:
                    env.load_file(src.read_bytes(), name=f"skillicons@{idx}")
                except Exception as exc:  # noqa: BLE001
                    log.warning("skill_icons 组员加载失败 %s: %s", src.name, exc)

        artifacts: list[ExportArtifact] = []
        seen: set[str] = set()
        for obj in env.objects:
            try:
                if obj.type.name != "Sprite":
                    continue
                spr = obj.read()
                name = str(spr.m_Name)
                if not re.match(r"^skillicon[\d_]*\.png$", f"{name}.png", re.IGNORECASE):
                    continue
                if name in seen:
                    continue
                seen.add(name)
                img = spr.image
                if img is None:
                    continue
                img = img.convert("RGBA") if img.mode not in ("RGBA", "RGB") else img
                artifacts.append(
                    ExportArtifact(f"ui/skill_icons/{name}.png", _png_bytes(img, name))
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("skill_icons：Sprite %r 导出失败: %s", obj.path_id, exc)
        self._skill_icons_cache = (cache_key, artifacts)
        return artifacts

    def _painting_rel(self, name: str, png: bytes, container: str = "") -> str | None:
        """按名称归类离散贴图，返回相对路径（不属于任何类返回 None）。"""
        from io import BytesIO
        from PIL import Image

        # 参考程序是对解包后的文件名（带 .png 后缀）做正则；UnityPy 的
        # Texture2D.m_Name 通常不带后缀，这里补上再匹配。
        stem = re.sub(r"\.png$", "", name, flags=re.IGNORECASE)
        filename = f"{stem}.png"
        for cat, pattern in _UI_RE:
            if re.match(pattern, filename, re.IGNORECASE):
                return self._ui_path(cat, stem, png)
        if re.match(_CHIBI_RE, filename, re.IGNORECASE):
            mapping_id = stem.split("_")[0].lower()
            if mapping_id in _CHIBI_NOT_ALLOWED:
                return None
            role, skin = self._resolve_role_skin(mapping_id, "")
            return f"{_join_role_skin('chibis', '', role, skin)}/{stem.lower()}.png"
        # 技能演出背景：参考程序 filterPaths 按 AssetStudio 解包路径里的
        # "Skillbackground_1" 目录段归类（见 sample 中 char061306back*.png 的
        # container=.../UI_ImgPiece/Skillbackground_1/...）
        if "Skillbackground_1" in container:
            return f"ui/skill_cutscene_background/{stem}.png"
        return None

    def _ui_path(self, cat: str, stem: str, png: bytes) -> str | None:
        from io import BytesIO
        from PIL import Image

        if cat == "costume_face":
            name = stem[:23]
            if name == "illust_inven_char101601":
                name = "illust_inven_char060401"
            if "censorship" in stem.lower():
                name = f"{name}_c"
            return f"ui/costume_face/{name}.png"

        if cat == "costume_icon":
            img = Image.open(BytesIO(png))
            if img.width < 200 or img.height < 200:
                return None
            if _SKIP_ICON & set([stem]):
                return None
            if any(sid in stem for sid in _ICON_SHORT_IDS):
                stem = stem.replace("costume", "costume000")
            if "icon_costume101601" in stem:
                stem = stem.replace("icon_costume101601", "icon_costume060401")
            return f"ui/costume_icon/{stem[:18]}.png"

        if cat == "costume_skill_face":
            if stem == "illust_skill_char020101_126":
                return None
            name = stem[:23]
            if name == "illust_skill_char101601":
                name = "illust_skill_char060401"
            return f"ui/costume_skill_face/{name}.png"

        if cat == "skill_icons":
            return f"ui/skill_icons/{stem}.png"

        if cat == "speech_bubble_faces":
            if stem in _FACE_NOT_ALLOWED:
                return None
            return f"ui/speech_bubble_faces/{stem}.png"

        if cat == "wallpapers":
            if "_eff_" in stem:
                return None
            return f"ui/wallpapers/{stem}.png"
        return None

    # ------------------------------------------------------------------
    # 分类 / 映射
    # ------------------------------------------------------------------
    def _categorize(self, filename: str) -> str:
        """返回 spine 子类；未匹配返回空字符串。"""
        for cat, pattern in _CATEGORY_RE:
            if re.match(pattern, filename, re.IGNORECASE):
                return cat
        return ""

    def _resolve_role_skin(self, mapped_id: str, cat: str) -> tuple[str, str]:
        from waifu_unpack.games.base import DEFAULT_SKIN

        if not mapped_id:
            return "miscellaneous", DEFAULT_SKIN
        if mapped_id == _NPC_LOEN_TO_CHAR:
            mapped_id = "char003201"  # Loen 由 npc 提升为角色
        identity = self.resolve_identity(mapped_id)
        return identity.char, identity.skin

    def _fix_base(self, base: str) -> str:
        for src, dst in _CHAR_REMAP.items():
            if src in base:
                base = base.replace(src, dst)
        if base.endswith("_A") and base.startswith("char061092"):
            base = base[:-2]
        return base

    def _fix_atlas_text(self, base: str, atlas_text: str) -> str:
        """参考程序 fixAtlasFiles：atlas 内的贴图引用名修正。"""
        for target, src, dst in _ATLAS_FIXES:
            if base == target and src in atlas_text:
                atlas_text = atlas_text.replace(src, dst)
        return atlas_text


# ----------------------------------------------------------------------
# 通用工具
# ----------------------------------------------------------------------
def _mapping_id(file_name: str, separator: str, max_count: int) -> str:
    """参考程序 getMappingId：超过 max_count 个分隔符时掐掉最后一段。"""
    if file_name.count(separator) <= max_count:
        return file_name
    parts = file_name.split(separator)
    return separator.join(parts[:-1])


def _join_role_skin(prefix: str, cat: str, role: str, skin: str) -> str:
    from waifu_unpack.games.base import DEFAULT_SKIN, sanitize_component

    parts = []
    if prefix:
        parts.append(prefix)
    if cat:
        parts.append(cat)
    parts.append(sanitize_component(role))
    if skin and skin != DEFAULT_SKIN:
        parts.append(sanitize_component(skin))
    return "/".join(parts)


def _png_bytes(img, name: str) -> bytes:
    from io import BytesIO

    if img.mode == "I;16":
        img = img.point(lambda i: i * (1 / 256)).convert("L")
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _load_catalog_from_dir(resource_dir: Path):
    from waifu_unpack.core.catalog import Catalog

    for candidate in sorted(resource_dir.rglob("*file*.json")):
        try:
            root = __import__("json").loads(candidate.read_text(encoding="utf-8"))
            if "bundles" in root:
                log.info("使用 catalog: %s", candidate)
                return Catalog.from_file_json(candidate)
        except Exception:  # noqa: BLE001
            continue
    alpha = resource_dir / "com.unity.addressables" / "catalog_alpha.json"
    if alpha.is_file():
        log.info("未找到 file.json，使用 catalog_alpha.json 解码")
        return Catalog.from_catalog_alpha(alpha)
    log.error("未在 %s 中找到 file.json 或 catalog_alpha.json", resource_dir)
    return None