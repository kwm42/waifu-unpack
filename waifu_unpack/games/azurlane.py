"""碧蓝航线适配器（待实现）。

已知情况：
- 资源在 AssetBundles/ 下，painting(立绘) / live2d / spinepainting 等分类目录
- 立绘 = Mesh + Texture2D 切片（先只导切片，不改组合）
- Live2D = Cubism3，moc3 在 MonoBehaviour / TextAsset 里
- Spine 3.8，atlas/skel 是 TextAsset
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class AzurLane:
    key = "azurlane"
    display_name = "碧蓝航线 (Azur Lane)"
    supported_types = ("spine", "live2d", "painting")

    def __init__(self, names=None):  # noqa: ANN001
        self.names = names or {}

    def is_bundle_file(self, rel: str) -> bool:
        return rel.lower().endswith(".ab")

    def extract(self, env, types, bundle_stem=""):  # noqa: ANN001 - 暂未实现
        raise NotImplementedError("碧蓝航线适配器待实现（下一个里程碑）")