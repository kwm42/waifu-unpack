"""碧蓝航线适配器。

已知情况（spinepainting 样本已验证）：
- 资源按分类目录存放：`AssetBundles/painting / live2d / spinepainting/...`
- 样本为无扩展名文件（如 `spinepainting/jishang_3_asmr_res`），头是 UnityFS v8，
  版本串被抹成 `5.x.x`（与 BD2 同类混淆），真实版本 `2022.3.x`，
  需 `forced_unity_version` fallback（2022.3.51f1 可打开 51f1/62f3 样本）。
- 内容物为 Spine 3.8：atlas/skel 是 TextAsset，贴图是 Texture2D，
  atlas 常见**多页**（多张 png，material 顺序对应页面），复用 core/spine.py。
- live2d：烘焙式 Cubism prefab，.moc3 内嵌 CubismMoc，physics3 是 TextAsset，
  贴图是 Texture2D（复用 core/live2d.py）。
- painting：一张大 Texture2D + Sprite（textureRect 定义内容区），只导切片 PNG，
  不做 Mesh 重组（复用 core/painting.py）。

导出结构（out_root 默认 = 项目根/output）：
    output/azurlane/<bundle文件名>/angel|bg/<base>.atlas|.skel|<贴图>.png
    output/azurlane/<bundle文件名>/live2d/<base>.moc3|<base>.model3.json|
        <base>.physics3.json|<贴图>.png
    output/azurlane/<bundle文件名>/illust/<key>.png
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import UnityPy

from waifu_unpack.core import live2d, painting, spine
from waifu_unpack.games.base import DEFAULT_SKIN, GameAdapter

log = logging.getLogger(__name__)

# 常见资源扩展名。spinepainting/live2d 等样本无扩展名，
# is_bundle_file 对无扩展名文件也当作潜在 bundle 传给魔数嗅探兜底。
_COMMON_EXTS = (".ab", ".bundle", ".unity3d", ".asset", ".bytes")


class AzurLane(GameAdapter):
    key = "azurlane"
    display_name = "碧蓝航线 (Azur Lane)"
    supported_types = ("spine", "live2d", "painting")
    bundle_exts = _COMMON_EXTS
    # 版本串被抹成 `5.x.x`；51f1 的 fallback 可同时解析 62f3 样本
    forced_unity_version = "2022.3.51f1"

    def is_bundle_file(self, rel: str) -> bool:
        p = Path(rel)
        if p.suffix.lower() in _COMMON_EXTS:
            return True
        # 无扩展名也当作潜在 bundle（打开失败由 CLI 跳过）
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
            for exp in spine.iter_spine_exports(env):
                role_dir = "angel" if exp.role == "character" else "bg"
                log.info("Spine: %s / %s (%s)", loc, role_dir, exp.stem)
                artifacts.append(
                    self.artifact_in(
                        loc, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.atlas",
                        exp.atlas_text.encode("utf-8"),
                    )
                )
                artifacts.append(
                    self.artifact_in(
                        loc, DEFAULT_SKIN, f"{role_dir}/{exp.stem}.skel",
                        exp.skel_bytes,
                    )
                )
                for png_name, png_bytes in exp.textures.items():
                    artifacts.append(
                        self.artifact_in(loc, DEFAULT_SKIN, f"{role_dir}/{png_name}", png_bytes)
                    )
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

        if "live2d" in types:
            loc = sanitize_component(bundle_stem or "live2d")
            for exp in live2d.iter_live2d_exports(env):
                base = exp.base or bundle_stem or "model"
                log.info("Live2D: %s / %s", loc, base)
                artifacts.append(
                    self.artifact_in(
                        loc, DEFAULT_SKIN, f"live2d/{base}.moc3", exp.moc3
                    )
                )
                model3 = json.dumps(exp.model3_json, ensure_ascii=False, indent=2).encode(
                    "utf-8"
                )
                artifacts.append(
                    self.artifact_in(
                        loc, DEFAULT_SKIN, f"live2d/{base}.model3.json", model3
                    )
                )
                if exp.physics3_json is not None:
                    physics3 = json.dumps(
                        exp.physics3_json, ensure_ascii=False, indent=2
                    ).encode("utf-8")
                    artifacts.append(
                        self.artifact_in(
                            loc, DEFAULT_SKIN, f"live2d/{base}.physics3.json", physics3
                        )
                    )
                for png_name, png_bytes in exp.textures.items():
                    artifacts.append(
                        self.artifact_in(
                            loc, DEFAULT_SKIN, f"live2d/{png_name}.png", png_bytes
                        )
                    )
                for miss in exp.missing:
                    log.warning("Live2D 缺失: %s", miss)

        if "painting" in types:
            loc = sanitize_component(bundle_stem or "painting")
            for exp in painting.iter_painting_exports(env):
                log.info("Painting: %s / %s", loc, exp.stem)
                artifacts.append(
                    self.artifact_in(
                        loc, DEFAULT_SKIN, f"illust/{exp.stem}.png", exp.png
                    )
                )
                for miss in exp.missing:
                    log.warning("Painting 缺失: %s", miss)

        return artifacts