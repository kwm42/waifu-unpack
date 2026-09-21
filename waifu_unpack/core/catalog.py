"""BD2 Addressables catalog 解析。

两种数据来源，作用等价（都对应磁盘 Shared/<bundleName>/<hash>/__data）：
  1. file.json（com.unity.addressables/files.json）—— 结构化的 manifest，
     bundles[] 每项含 bundleName / hash / readableName / fileHash / size / bundleType；
  2. catalog_alpha.json 的 m_KeyDataString —— Addressables 目录原始编码（base64），
     参考程序 decoder.py 的做法：抽可打印字符串并按 `^.+_<32hex>.bundle$` 过滤，
     得到 `<readableName>_<hash>.bundle`，尾部 32hex 即 hash。
"""

from __future__ import annotations

import base64
import json
import logging
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

log = logging.getLogger(__name__)

_BUNDLE_PATTERN = re.compile(r"^.+_[0-9a-fA-F]{32}\.bundle$")
_MIN_PRINTABLE_LENGTH = 4


@dataclass
class BundleEntry:
    """磁盘 Shared/<bundleName>/<hash>/__data 与地址目录可读名的映射。"""

    bundle_name: str
    readable_name: str
    hash: str = ""
    file_hash: str = ""
    size: int = 0
    bundle_type: str = ""

    @property
    def content(self) -> str:
        """分类用的内容名（去掉尾部 hash 段与路径分隔）。"""
        return self.readable_name


class Catalog:
    """BundleEntry 的按 hash / content 检索集。"""

    def __init__(self, entries: Iterable[BundleEntry]) -> None:
        self.bundles: list[BundleEntry] = list(entries)
        self._by_hash: dict[str, BundleEntry] = {}
        for e in self.bundles:
            if e.hash:
                self._by_hash.setdefault(e.hash.lower(), e)

    def __len__(self) -> int:
        return len(self.bundles)

    def __iter__(self) -> Iterator[BundleEntry]:
        return iter(self.bundles)

    def get(self, hash: str) -> BundleEntry | None:
        return self._by_hash.get(hash.lower())

    def match_keywords(self, keywords: Iterable[str]) -> list[BundleEntry]:
        """按 readableName 关键词（忽略大小写，任一命中）过滤。"""
        kws = {k.lower() for k in keywords if k}
        if not kws:
            return []
        return [
            e for e in self.bundles
            if any(k in e.readable_name.lower() for k in kws)
        ]

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------
    @classmethod
    def from_file_json(cls, path: Path) -> "Catalog":
        root = json.loads(Path(path).read_text(encoding="utf-8"))
        entries: list[BundleEntry] = []
        for b in root.get("bundles", []):
            entries.append(
                BundleEntry(
                    bundle_name=str(b.get("bundleName", "")),
                    readable_name=str(b.get("readableName", "")),
                    hash=str(b.get("hash", "")),
                    file_hash=str(b.get("fileHash", "")),
                    size=int(b.get("size", 0) or 0),
                    bundle_type=str(b.get("bundleType", "")),
                )
            )
        log.info("file.json: 解析出 %d 个 bundle", len(entries))
        return cls(entries)

    @classmethod
    def from_catalog_alpha(cls, path: Path) -> "Catalog":
        """从 catalog_alpha.json 的 m_KeyDataString 解码出 bundle 清单。"""
        decoded = decode_catalog_key_data_strings(path)
        entries: list[BundleEntry] = []
        for bundle in decoded:
            hash = bundle[-32:]
            name = bundle[:-33]
            entries.append(BundleEntry(bundle_name="", readable_name=name, hash=hash))
        log.info("catalog_alpha: 解码出 %d 个 bundle", len(entries))
        return cls(entries)


# ----------------------------------------------------------------------
# m_KeyDataString 解码（移植自参考程序 Myssal_Catalog_Decoder/decoder.py）
# ----------------------------------------------------------------------
def decode_catalog_key_data_strings(catalog_path: Path) -> list[str]:
    if not Path(catalog_path).is_file():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
    root = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    decoded: list[str] = []
    _find_and_decode_keys(root, decoded)
    log.info("catalog_alpha: 解码出 %d 条 bundle 串", len(decoded))
    return decoded


def _find_and_decode_keys(token, result: list[str]) -> None:
    if isinstance(token, dict):
        for key, value in token.items():
            if key == "m_KeyDataString":
                data = _safe_base64_decode(str(value))
                for s in _extract_printable_strings(data, _MIN_PRINTABLE_LENGTH):
                    if _BUNDLE_PATTERN.match(s):
                        result.append(s.replace(".bundle", ""))
            _find_and_decode_keys(value, result)
    elif isinstance(token, list):
        for item in token:
            _find_and_decode_keys(item, result)


def _safe_base64_decode(data: str) -> bytes:
    if not data:
        return b""
    data = data.strip()
    pad = len(data) % 4
    if pad:
        data += "=" * (4 - pad)
    try:
        return base64.b64decode(data, validate=False)
    except Exception:  # noqa: BLE001
        return b""


def _extract_printable_strings(data: bytes, min_length: int) -> list[str]:
    printable = set(string.printable)
    current: list[str] = []
    results: list[str] = []
    for b in data:
        ch = chr(b)
        if ch in printable and ch not in "\r\n\t\x0b\x0c":
            current.append(ch)
        else:
            if len(current) >= min_length:
                results.append("".join(current))
            current = []
    if len(current) >= min_length:
        results.append("".join(current))
    return results