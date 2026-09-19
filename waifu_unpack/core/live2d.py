"""Live2D (Cubism) 模型资源组装：从 Unity bundle 提取 moc3 模型。

产出物为 Cubism3 原生格式（碧蓝航线等游戏）：
    model3.json          模型配置
    <映射> .moc3         核心模型二进制
    physics3.json        物理配置
    textures/xxx.png     部件贴图

注意：Live2D 在 Unity 里多数不是普通 TextAsset，而是包了一层
Cubism 的 MonoBehaviour（内含 .bytes 字段引用），不同游戏的包法不同，
因此具体解析逻辑放在各游戏适配器中，本模块只提供统一产出物与公共工具。

当前阶段（第一里程碑 = IdleAngels/Spine）不实现具体提取，
待碧蓝航线里程碑再落地。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class Live2DExport:
    """一个可独立加载的 Live2D 模型。"""

    base: str
    model3_json: dict
    moc3: bytes
    physics3_json: dict | None = None
    textures: dict[str, bytes] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


def iter_live2d_exports(env):
    raise NotImplementedError(
        "Live2D 提取将在碧蓝航线里程碑实现，"
        "当前版本仅支持 Spine。"
    )