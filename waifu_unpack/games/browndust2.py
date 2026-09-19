"""棕色尘埃2 (Brown Dust 2) 适配器（待实现）。

已知情况：
- Unity 版本头被抹掉（显示 5.x.x 0.0.0），需 forced_unity_version
- 本地缓存目录全为 hash 文件名，无 container path
- 仅 Spine 4.1（atlas/skel 为 TextAsset），立绘在 illust bundle
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class BrownDust2:
    key = "browndust2"
    display_name = "棕色尘埃2 (Brown Dust 2)"
    supported_types = ("spine", "painting")
    forced_unity_version = "2022.3.22f1"

    def __init__(self, names=None):  # noqa: ANN001
        self.names = names or {}

    def is_bundle_file(self, rel: str) -> bool:
        return rel.lower().endswith(".bundle") or "data" in rel.lower()

    def extract(self, env, types, bundle_stem=""):  # noqa: ANN001 - 暂未实现
        raise NotImplementedError("棕色尘埃2适配器待实现（题目明确后开发）")