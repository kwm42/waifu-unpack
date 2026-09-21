"""交错战线 (CrossCore) 适配器。

资源格式（已实测）：
- 资源目录 Custom/ 下全部是无扩展名 UnityFS，且带"诱饵头 + 真包"双层结构：
  第 1 个 UnityFS 魔数处是垃圾混淆头（头字段字节序被打乱），真实 bundle 从
  第 2 个 UnityFS 处开始。BundleReader 会扫描所有偏移并取对象最多的结果，
  因此本格无需特殊处理双层结构。
- Unity 版本串被抹成 "5.x.x"，但实测 UnityPy 无需强制版本即可完整解析。
- 可提取内容：
  * Spine 模型（prefabs_spine_<角色id>_skin|break_<皮肤名>_spine[_fhx]）：
    TextAsset 骨架（无后缀、JSON）+ `.atlas` TextAsset + 超大 Texture2D，
    三件套自包含于同一 bundle。
  * 立绘/大图（textures_bigs_character_<id>_<code>_draw[_face|_fhx] 等）：
    单张大 Texture2D + Sprite，按 Sprite.textureRect 裁切导出。
  * 剧情 CG / 背景 / 图集（textures_bigs_uis_*）、模块信息图、UI 图标等。

导出结构（out_root 默认 = 项目根/output）：
    output/jiaocuozhanxian/spine/<角色>/<skin|break>_<皮肤名>[_fhx]/<base>.atlas|.skel|<贴图>.png
    output/jiaocuozhanxian/painting/<角色>/<code后缀>.png
    output/jiaocuozhanxian/painting/ui/<尾部>.png
    output/jiaocuozhanxian/painting/icons/<尾部>.png
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import UnityPy

from waifu_unpack.core import painting, spine
from waifu_unpack.games.base import DEFAULT_SKIN, ExportArtifact, GameAdapter

log = logging.getLogger(__name__)

# 骨架类 bundle 名：prefabs_spine_<角色id5位>_skin|break_<皮肤名>_spine[_fhx]
# 注意与 prefabs_spinehx_*（小型 UI spine，无骨架 TextAsset）区分。
_SPINE_RE = re.compile(
    r"^prefabs_spine_(?P<role>[0-9]+)_(?P<kind>skin|break)_(?P<name>[a-z0-9]+)_spine(?P<fhx>_fhx)?$",
    re.IGNORECASE,
)

_UI_ROOTS = ("textures_bigs_uis_", "textures_bigs_moduleinfo_", "textures_bigs_team_", "textures_bigs_storead_")
_ICON_ROOTS = ("textures_uis_",)


class JiaoCuoZhanXian(GameAdapter):
    key = "jiaocuozhanxian"
    display_name = "交错战线 (CrossCore)"
    supported_types = ("spine", "painting")
    forced_unity_version = None

    def is_bundle_file(self, rel: str) -> bool:
        # Custom 目录下全部为无扩展名 bundle
        return Path(rel).suffix == ""

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
        artifacts: list[ExportArtifact] = []
        if "spine" in types and self._is_spine_bundle(bundle_stem):
            artifacts.extend(self._extract_spine(env, bundle_stem))
        if "painting" in types and self._is_painting_bundle(bundle_stem):
            artifacts.extend(self._extract_painting(env, bundle_stem))

        # 同名变体共享贴图，按输出路径去重
        seen: set[str] = set()
        deduped: list[ExportArtifact] = []
        for a in artifacts:
            if a.relpath in seen:
                continue
            seen.add(a.relpath)
            deduped.append(a)
        return deduped

    @staticmethod
    def _is_spine_bundle(bundle_stem: str) -> bool:
        return _SPINE_RE.match(bundle_stem) is not None

    @staticmethod
    def _is_painting_bundle(bundle_stem: str) -> bool:
        return (
            bundle_stem.startswith("textures_bigs_")
            or bundle_stem.startswith("textures_uis_")
        )

    # ------------------------------------------------------------------
    # spine
    # ------------------------------------------------------------------
    def _extract_spine(self, env: UnityPy.Environment, bundle_stem: str) -> list:
        artifacts: list[ExportArtifact] = []
        m = _SPINE_RE.match(bundle_stem)
        role = self.resolve_identity(m.group("role")).char
        skin = f"{m.group('kind')}_{m.group('name')}{m.group('fhx') or ''}"

        for exp in spine.iter_spine_exports(env):
            for rel, data in (
                (f"{exp.base}.atlas", exp.atlas_text.encode("utf-8")),
                (f"{exp.base}.skel", exp.skel_bytes),
            ):
                artifacts.append(self.artifact_in(role, skin, rel, data))
            for png_name, png_bytes in exp.textures.items():
                artifacts.append(self.artifact_in(role, skin, png_name, png_bytes))
            for miss in exp.missing_textures:
                log.warning("贴图缺失: %s", miss)
        return artifacts

    # ------------------------------------------------------------------
    # painting
    # ------------------------------------------------------------------
    def _extract_painting(self, env: UnityPy.Environment, bundle_stem: str) -> list:
        artifacts: list[ExportArtifact] = []
        exports = painting.iter_painting_exports(env)

        if bundle_stem.startswith("textures_bigs_character_"):
            parts = bundle_stem.split("_")
            role = self.resolve_identity(parts[3]).char
            tail = "_".join(parts[4:]) or bundle_stem
            for exp in exports:
                stem = tail if exp.variant == 0 else f"{tail}_{exp.variant + 1}"
                artifacts.append(self.artifact_in(role, DEFAULT_SKIN, f"{stem}.png", exp.png))
        elif bundle_stem.startswith("textures_uis_"):
            self._dump_group(exports, "icons", bundle_stem[len("textures_uis_"):], artifacts)
        else:
            for root in _UI_ROOTS:
                if bundle_stem.startswith(root):
                    self._dump_group(exports, "ui", bundle_stem[len(root):], artifacts)
                    break
        return artifacts

    @staticmethod
    def _dump_group(exports: list, group: str, tail: str, artifacts: list) -> None:
        for exp in exports:
            stem = tail if exp.variant == 0 else f"{tail}_{exp.variant + 1}"
            artifacts.append(
                ExportArtifact(f"painting/{group}/{stem}.png", exp.png)
            )