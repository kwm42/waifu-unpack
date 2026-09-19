"""IdleAngels 适配器。

已知情况（用户已手工跑通）：
- 资源在安卓目录，.ab 文件可直接读取（无加密、无版本抹除）
- 内容物为 Spine 模型：atlas / skel / 贴图以 TextAsset + Texture2D 存放
- 输出目录名 = bundle 文件名（去 .ab，如 spine_spz_np/），names.json 的
  files 表提供"文件名 <-> 中文"检索索引，不做中文归并

导出结构（out_root 默认 = 项目根/output）：
    output/<game>/<bundle文件名>/angel|bg/<base>.atlas|.skel|<贴图>.png
"""

from __future__ import annotations

import logging
from pathlib import Path

import UnityPy

from waifu_unpack.core import spine
from waifu_unpack.core.painting import export_painting_textures
from waifu_unpack.games.base import DEFAULT_SKIN, GameAdapter

log = logging.getLogger(__name__)

# 常见资源扩展名。如果样本里还有别的扩展名，往这里加即可；
# 另外 is_bundle_file 会对无扩展名文件做魔数嗅探兜底。
_COMMON_EXTS = (".ab", ".bundle", ".unity3d", ".asset", ".bytes")


class IdleAngels(GameAdapter):
    key = "idleangels"
    display_name = "Idle Angels"
    supported_types = ("spine", "painting")
    bundle_exts = _COMMON_EXTS

    def is_bundle_file(self, rel: str) -> bool:
        p = Path(rel)
        if p.suffix.lower() in _COMMON_EXTS:
            return True
        # 无扩展名也可以读取文件头的魔数决定(交给 CLI 统一处理)
        return p.suffix == ""

    def extract(
        self,
        env: UnityPy.Environment,
        types: frozenset[str],
        bundle_stem: str = "",
    ) -> list:
        from waifu_unpack.games.base import ExportArtifact, sanitize_component

        artifacts: list[ExportArtifact] = []

        if "spine" in types:
            loc = sanitize_component(bundle_stem or "spine")
            meta = self.names.get("files", {}).get(bundle_stem, {})
            label = f"{meta.get('cn', '')} ({loc})" if meta.get("cn") else loc
            for exp in spine.iter_spine_exports(env):
                role_dir = "angel" if exp.role == "character" else "bg"
                log.info("Spine: %s / %s (%s)", label, role_dir, exp.stem)
                artifacts.append(self.artifact_in(loc, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.atlas", exp.atlas_text.encode("utf-8")))
                artifacts.append(self.artifact_in(loc, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.skel", exp.skel_bytes))
                for png_name, png_bytes in exp.textures.items():
                    artifacts.append(self.artifact_in(loc, DEFAULT_SKIN, f"{role_dir}/{png_name}", png_bytes))
                for miss in exp.missing_textures:
                    log.warning("  贴图缺失: %s", miss)

            # 同名变体共享贴图，按输出路径去重
            seen: set[str] = set()
            deduped: list[ExportArtifact] = []
            for a in artifacts:
                if a.relpath in seen:
                    continue
                seen.add(a.relpath)
                deduped.append(a)
            artifacts = deduped

        if "painting" in types and bundle_stem:
            # 角色以外的静态大图（活动图/头像/图标等），原样保留切图
            stem = sanitize_component(bundle_stem)
            for obj in env.objects:
                try:
                    if obj.type.name != "Texture2D":
                        continue
                    tex = obj.read()
                    img = tex.image
                    if img is None:
                        continue
                    name = str(tex.m_Name) or f"tex_{obj.path_id}"
                    if img.mode not in ("RGBA", "RGB"):
                        img = img.convert("RGBA")
                    import io

                    buf = io.BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    artifacts.append(
                        self.artifact_in("_painting", stem, f"{name}.png", buf.getvalue())
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning("立绘贴图 %r 导出失败: %s", obj.path_id, exc)

        return artifacts