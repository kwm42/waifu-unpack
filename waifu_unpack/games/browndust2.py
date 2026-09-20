"""棕色尘埃2 (Brown Dust 2) 适配器。

已知情况（见 docs/game-research.md）：
- Unity 版本头被抹掉（显示 5.x.x / 0.0.0），需 forced_unity_version = 2022.3.22f1。
  修复方式：包头不能改字节（破坏 LZ4），走 UnityPy.config.FALLBACK_UNITY_VERSION。
- 本地缓存目录 `Shared/<bundleName>/<hash>/__data` 全为 hash 文件名，
  真实 bundle 内容是 `__data`（无扩展名）。逻辑路径在
  `com.unity.addressables/file.json` 里（bundleName ↔ readableName）。
- 仅 Spine 4.1（atlas/skel 为 TextAsset），立绘为整图（Texture2D）。

导出结构（每 bundle 一套目录，目录名 = 逻辑路径推导出的角色标识）：
    out_root/browndust2/<角色>/angel|bg/<base>.atlas|.skel|<贴图>.png
    out_root/browndust2/<角色>/illust/<贴图名>.png          （painting 整图）
"""

from __future__ import annotations

import logging
from pathlib import Path

import UnityPy

from waifu_unpack.core import spine
from waifu_unpack.core.catalog import Catalog, char_key_from_name, readable_dirname
from waifu_unpack.games.base import DEFAULT_SKIN, ExportArtifact, GameAdapter, sanitize_component

log = logging.getLogger(__name__)


class BrownDust2(GameAdapter):
    key = "browndust2"
    display_name = "棕色尘埃2 (Brown Dust 2)"
    supported_types = ("spine", "painting")
    forced_unity_version = "2022.3.22f1"

    def __init__(self, names=None) -> None:  # noqa: ANN001
        super().__init__(names)
        self._catalog: Catalog | None = None

    # ------------------------------------------------------------------
    # bundle 判别
    # ------------------------------------------------------------------
    def is_bundle_file(self, rel: str) -> bool:
        # UnityWebRequest 缓存：真实数据文件固定叫 __data（无扩展名）
        if Path(rel).name == "__data":
            return True
        return rel.lower().endswith((".bundle", ".ab", ".unity3d"))

    def iter_bundles(self, input_dir: Path):
        self._catalog = Catalog.discover(input_dir)
        yield from super().iter_bundles(input_dir)

    # ------------------------------------------------------------------
    # 组装导出物
    # ------------------------------------------------------------------
    def extract(
        self,
        env: UnityPy.Environment,
        types: frozenset[str],
        bundle_stem: str = "",
    ) -> list[ExportArtifact]:
        label = self._dir_label(env, bundle_stem)
        artifacts: list[ExportArtifact] = []

        if "spine" in types:
            artifacts.extend(self._extract_spine(env, label))
        if "painting" in types:
            artifacts.extend(self._extract_painting(env, label))

        return _dedupe(artifacts)

    def _extract_spine(self, env, label: str) -> list[ExportArtifact]:
        artifacts: list[ExportArtifact] = []
        for exp in spine.iter_spine_exports(env):
            role_dir = "angel" if exp.role == "character" else "bg"
            log.info("Spine: %s / %s (%s)", label, role_dir, exp.stem)
            artifacts.append(
                self.artifact_in(label, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.atlas", exp.atlas_text.encode("utf-8"))
            )
            artifacts.append(
                self.artifact_in(label, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.skel", exp.skel_bytes)
            )
            for png_name, png_bytes in exp.textures.items():
                artifacts.append(self.artifact_in(label, DEFAULT_SKIN, f"{role_dir}/{png_name}", png_bytes))
            for miss in exp.missing_textures:
                log.warning("  贴图缺失: %s", miss)
        return artifacts

    def _extract_painting(self, env, label: str) -> list[ExportArtifact]:
        """BD2 立绘是整张 Texture2D，直接存 PNG（与碧蓝的切片不同）。"""
        import io

        artifacts: list[ExportArtifact] = []
        for obj in env.objects:
            try:
                if obj.type.name != "Texture2D":
                    continue
                tex = obj.read()
                img = tex.image
                if img is None:
                    continue
                name = str(tex.m_Name) or f"tex_{obj.path_id}"
                if img.mode == "I;16":
                    img = img.point(lambda i: i * (1 / 256)).convert("L")
                elif img.mode not in ("RGBA", "RGB"):
                    img = img.convert("RGBA")
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                artifacts.append(self.artifact_in(label, DEFAULT_SKIN, f"illust/{name}.png", buf.getvalue()))
            except Exception as exc:  # noqa: BLE001
                log.warning("立绘贴图 %r 导出失败: %s", obj.path_id, exc)
        return artifacts

    # ------------------------------------------------------------------
    # 目录命名
    # ------------------------------------------------------------------
    def _dir_label(self, env, bundle_stem: str) -> str:
        """每 bundle 一个目录。取 catalog 推导的角色标识；查不到时兜底逻辑路径尾段。"""
        bundle_name = self._bundle_name(env)
        entry = None
        if bundle_name and self._catalog is not None:
            entry = self._catalog.resolve(bundle_name)
        readable = entry.readable_name if entry else ""

        char_key = entry.lookup_char_key() if entry else None
        if not char_key:
            char_key = char_key_from_name(bundle_stem) or char_key_from_name(readable)
        if char_key:
            return self.resolve_identity(char_key).char

        if readable:
            seg = readable_dirname(readable).split("/")[-1]
            if seg:
                return sanitize_component(seg)
        return sanitize_component(bundle_stem or "unknown")

    def _bundle_name(self, env: UnityPy.Environment) -> str | None:
        """从 bundle 内 AssetBundle 对象的 m_Name 拿 bundleName（形如 `xxx.bundle`）。"""
        for obj in env.objects:
            try:
                if obj.type.name != "AssetBundle":
                    continue
                name = str(obj.read().m_Name)
                return name[:-7] if name.lower().endswith(".bundle") else name
            except Exception:  # noqa: BLE001 - 单个对象失败不影响整体
                continue
        return None


def _dedupe(artifacts: list[ExportArtifact]) -> list[ExportArtifact]:
    """同名变体可能共享贴图，按输出路径去重。"""
    seen: set[str] = set()
    deduped: list[ExportArtifact] = []
    for a in artifacts:
        if a.relpath in seen:
            continue
        seen.add(a.relpath)
        deduped.append(a)
    return deduped