"""游戏适配器注册表。

新增游戏时：新建 games/<key>.py，然后在 REGISTRY 登记即可。
REGISTRY 值可以是适配器类，也可以是 (模块路径, 类名) 延迟导入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waifu_unpack.games.base import GameAdapter

# 延迟导入，避免首屏 import 过重（UnityPy 较大）
_REGISTRY: dict[str, tuple[str, str]] = {
    "idleangels": ("waifu_unpack.games.idleangels", "IdleAngels"),
    "azurlane": ("waifu_unpack.games.azurlane", "AzurLane"),
    "browndust2": ("waifu_unpack.games.browndust2", "BrownDust2"),
    "jiaocuozhanxian": ("waifu_unpack.games.jiaocuozhanxian", "JiaoCuoZhanXian"),
}


def available_games() -> list[str]:
    return sorted(_REGISTRY)


def get_adapter(key: str) -> "GameAdapter":
    if key not in _REGISTRY:
        raise KeyError(
            f"未知游戏 {key!r}。可用: {', '.join(available_games())}"
        )
    module_name, class_name = _REGISTRY[key]
    import importlib

    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)
    from waifu_unpack.games.base import load_names

    return cls(names=load_names(key))

def get_adapter_meta() -> dict[str, str]:
    """返回 {key: 显示名} 用于 --list。"""
    metas: dict[str, str] = {}
    for key in _REGISTRY:
        try:
            adapter = get_adapter(key)
            metas[key] = adapter.display_name or key
        except (KeyError, ImportError) as exc:
            metas[key] = f"(加载失败: {exc})"
    return metas