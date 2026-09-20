"""AssetBundle 目录索引（棕色尘埃2 的 com.unity.addressables/file.json）。

该文件是 Addressables 的 bundle 清单，把磁盘上的 hash 文件名还原成逻辑路径：

- `bundleName`   : 磁盘目录名（`Shared/<bundleName>/<hash>/__data` 的第一段）
- `readableName` : 逻辑路径（如 `common-spritetexture-myroom_assets_common/char060302/myroom`）
- `hash`         : `Shared/<bundleName>/<hash>` 的第二段（与磁盘子目录一致）
- `size`         : 文件字节数（配合 MD5 校验是否下载完整）

典型磁盘布局（UnityWebRequest 缓存目录）：

    Shared/<bundleName>/<hash>/__data
    Shared/<bundleName>/<hash>/__info

可用它对上"磁盘 hash 文件 <-> 逻辑路径/签名字符串映射表"。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional

log = logging.getLogger(__name__)

# 角色 key 形态：char + 6 位数字（如 char060302）
_CHAR_KEY_RE = re.compile(r"\b(char\d{6})\b", re.IGNORECASE)

_REMOTE_TYPE = "Remote"


@dataclass(frozen=True)
class CatalogEntry:
    bundle_name: str
    readable_name: str
    hash: str
    file_hash: str
    size: int
    bundle_type: str

    @property
    def is_remote(self) -> bool:
        return self.bundle_type == _REMOTE_TYPE

    def lookup_char_key(self) -> Optional[str]:
        """从逻辑路径中提取角色 key（char+6 位数字），没有返回 None。"""
        m = _CHAR_KEY_RE.search(self.readable_name.replace("-", "/"))
        return m.group(1).lower() if m else None


class Catalog:
    """file.json 的解析结果：多种键可查 bundle 条目。"""

    def __init__(self) -> None:
        self.entries: list[CatalogEntry] = []
        self._by_bundle_name: dict[str, CatalogEntry] = {}
        self._by_hash: dict[str, CatalogEntry] = {}
        self._by_readable: dict[str, CatalogEntry] = {}

    # ------------------------------------------------------------------
    # 构建
    # ------------------------------------------------------------------
    @classmethod
    def from_file_json(cls, path) -> "Catalog":
        """解析 Addressables 的 file.json。"""
        data = json.loads(path.read_text(encoding="utf-8"))
        catalog = cls()
        for raw in data.get("bundles", []):
            entry = CatalogEntry(
                bundle_name=str(raw.get("bundleName", "")),
                readable_name=str(raw.get("readableName", "")),
                hash=str(raw.get("hash", "")),
                file_hash=str(raw.get("fileHash", "")),
                size=int(raw.get("size", 0)),
                bundle_type=str(raw.get("bundleType", "")),
            )
            if not entry.bundle_name:
                continue
            catalog.entries.append(entry)
            catalog._by_bundle_name[entry.bundle_name] = entry
            if entry.hash:
                catalog._by_hash.setdefault(entry.hash, entry)
            if entry.readable_name:
                catalog._by_readable.setdefault(entry.readable_name, entry)
        return catalog

    @classmethod
    def discover(cls, base_dir) -> Optional["Catalog"]:
        """在目录树下找 `com.unity.addressables/file.json` 并加载。

        找不到时返回 None（此时只能以 hash 文件名兜底，逻辑映射缺失）。
        """
        from pathlib import Path

        root = Path(base_dir)
        for candidate in sorted(root.glob("**/file.json")):
            try:
                catalog = cls.from_file_json(candidate)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("目录清单 %s 解析失败: %s", candidate, exc)
                continue
            log.info("已加载目录清单: %s (%d 条)", candidate, len(catalog.entries))
            return catalog
        return None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def resolve(self, bundle_name: str) -> Optional[CatalogEntry]:
        return self._by_bundle_name.get(bundle_name)

    def resolve_hash(self, digest: str) -> Optional[CatalogEntry]:
        return self._by_hash.get(digest)

    def resolve_readable(self, readable: str) -> Optional[CatalogEntry]:
        return self._by_readable.get(readable)

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:  # pragma: no cover - 调试输出
        return f"<Catalog {len(self.entries)} bundles>"


def char_key_from_name(name: str) -> Optional[str]:
    """从任意字符串中提取角色 key（char+6 位数字），归一化为小写。"""
    m = _CHAR_KEY_RE.search(str(name))
    return m.group(1).lower() if m else None


def readable_dirname(readable: str) -> str:
    """逻辑路径 → 安全的相对目录名（去掉 `_assets_*` 段与无意义的空段）。"""
    parts = [p for p in PurePosixPath(readable).parts if p]
    # 去掉 `xxx_assets_all` / `xxx_assets_ui` 这类资源段，保留语义段
    kept = [p for p in parts if not re.match(r"^[a-z0-9]+_assets_[a-z0-9]+$", p, re.IGNORECASE)]
    base = "/".join(kept) if kept else readable
    return base.strip("/")