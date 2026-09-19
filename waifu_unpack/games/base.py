"""游域适配器抽象基类 与 公共工具。

新增一款游戏 = 子类化 GameAdapter 并注册到 games/__init__.py 的 REGISTRY。
适配器需要回答四个问题：
 1) 哪些输入文件是 bundle（is_bundle_file）
 2) bundle 打开是否需要特殊处理（forced_unity_version 等）
 3) bundle 内容如何组装成导出物（extract）
 4) 导出物如何命名/归类（resolve_identity）
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator, Optional

import UnityPy

from waifu_unpack.core.bundlereader import BundleReader

log = logging.getLogger(__name__)

_SUPPORTED = ("spine", "live2d", "painting")

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# 皮肤名查不到时的回退值；为它时不生成皮肤层级目录，避免无意义的"默认/"层
DEFAULT_SKIN = "默认"


@dataclass
class ExportArtifact:
    """一个待写入文件：out_root 下的相对路径 + 内容。"""

    relpath: str
    data: bytes


@dataclass
class Identity:
    """角色/皮肤的可读标签。"""

    char: str
    skin: str = DEFAULT_SKIN


def sanitize_component(name: str, fallback: str = "unknown") -> str:
    """把名字清洗成安全的目录名/文件名。"""
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or fallback


class GameAdapter(ABC):
    key: str = ""
    display_name: str = ""
    supported_types: tuple[str, ...] = _SUPPORTED
    forced_unity_version: Optional[str] = None
    # 若配置了扩展名白名单，则加速文件筛选
    bundle_exts: tuple[str, ...] = ()

    def __init__(self, names: Optional[dict] = None) -> None:
        self.names = names or {}
        self._reader = BundleReader(forced_unity_version=self.forced_unity_version)

    # ------------------------------------------------------------------
    # 子类必须实现
    # ------------------------------------------------------------------
    def is_bundle_file(self, rel: str) -> bool:
        """判断某个输入文件是否是需要处理的 bundle。"""
        raise NotImplementedError

    def extract(
        self,
        env: UnityPy.Environment,
        types: frozenset[str],
        bundle_stem: str = "",
    ) -> list[ExportArtifact]:
        """把一个已打开的 bundle 组装成导出物列表。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 子类按需覆写
    # ------------------------------------------------------------------
    def open_bundle(self, raw: bytes, name: str) -> UnityPy.Environment:
        return self._reader.open_bytes(raw, name)

    def digest(self, raw: bytes) -> str:
        return self._reader.digest(raw)

    def resolve_identity(self, base: str) -> Identity:
        """base -> (角色, 皮肤)。默认策略：查 names 表兜底原样。"""
        key = _canonical_id(base)
        skins = self.names.get("skins", {})
        chars = self.names.get("characters", {})
        if key in skins:
            entry = skins[key]
            char = entry.get("char") or key
            char_cn = chars.get(char, {}).get("cn") or sanitize_component(char)
            return Identity(char_cn, entry.get("cn") or sanitize_component(key))
        if key in chars:
            return Identity(chars[key].get("cn") or sanitize_component(key))
        return Identity(sanitize_component(base), DEFAULT_SKIN)

    # ------------------------------------------------------------------
    # 通用工具
    # ------------------------------------------------------------------
    def artifact_in(self, char: str, skin: str, rel: str, data: bytes) -> ExportArtifact:
        parts = [sanitize_component(char)]
        if skin and skin != DEFAULT_SKIN:
            parts.append(sanitize_component(skin))
        path = PurePosixPath(*(parts + [rel])).as_posix()
        return ExportArtifact(path, data)

    def iter_bundles(self, input_dir: Path) -> Iterator[tuple[Path, str]]:
        """扫描输入目录，产出 (绝对路径, 相对目录)."""
        for file in sorted(input_dir.rglob("*")):
            if not file.is_file():
                continue
            rel = file.relative_to(input_dir).as_posix()
            if self.is_bundle_file(rel):
                yield file, rel

    def names_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "names" / f"{self.key}.json"


def load_names(key: str) -> dict:
    """读取 games 对应的 names/<key>.json，缺失时返回空表。"""
    path = Path(__file__).resolve().parent.parent / "names" / f"{key}.json"
    if not path.exists():
        log.debug("未找到名字映射表 %s，将使用英文 id 命名", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("名字映射表 %s 解析失败: %s", path, exc)
        return {}


def _canonical_id(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", s.lower())