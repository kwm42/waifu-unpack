"""Unity AssetBundle 读取与头部修复。

职责：
- 魔数嗅探（UnityFS / UnityWeb / UnityRaw / UnityArchive / Unityfs 等）
- 兼容"前缀脏字节/偏移"式混淆（如剥掉首个字节、前置垃圾头）
- 兼容"Unity 版本号被抹掉"式混淆（棕色尘埃2 等，通过外部指定版本绕过）
- 封装 UnityPy 的 Environment，向上层提供统一的 object 遍历接口
"""

from __future__ import annotations

import hashlib
import logging
import struct
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import UnityPy
import UnityPy.config

log = logging.getLogger(__name__)

UNITYFS_MAGIC = b"UnityFS\x00"
SERIALIZED_MAGICS = (b"UnityWeb", b"UnityRaw", b"UnityArchive", b"UnityFS\x00", b"Unityyu")

# BundleFile 头里 Unity 版本字段被置成这些值时，视为需要以显式版本解析
BLANKED_VERSIONS = {b"0.0.0", b""}


def _iter_unityfs_offsets(raw: bytes) -> list[int]:
    """返回文件内所有 `UnityFS\\x00` 魔数的偏移（含前置脏字节场景）。

    候选可能有多个（外层壳 + 内层真内容），open_bytes 会对每个候选
    都尝试解析并取对象最多的结果，因此这里只需枚举全部偏移。
    """
    offsets: list[int] = []
    start = 0
    while True:
        i = raw.find(UNITYFS_MAGIC, start)
        if i < 0:
            break
        offsets.append(i)
        start = i + 1
    return offsets


class BundleOpenError(RuntimeError):
    pass


class BundleReader:
    """按需打开一个 bundle。可整体配置一次、复用多次。"""

    def __init__(
        self,
        forced_unity_version: Optional[str] = None,
    ) -> None:
        self.forced_unity_version = forced_unity_version

    def digest(self, data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    def open(self, path: Path) -> UnityPy.Environment:
        """打开文件，返回 UnityPy Environment。

        若文件无法识别会抛 BundleOpenError，内含前 32 字节十六进制便于排查。
        """
        raw = path.read_bytes()
        return self.open_bytes(raw, name=str(path))

    def open_bytes(self, raw: bytes, name: str = "") -> UnityPy.Environment:
        """打开内存中的 bundle 数据。

        支持两类混淆：
        1) 前置脏字节（如最前方的 0x00）
        2) 双层嵌套——外层是旧引擎空壳，内层偏移处另有一个完整 UnityFS
           （查 IdleAngels 样本时发现的模式：外层 Unity 2017.4 壳、
            内层 UnityFS v8 / 2021.3.58f1 真内容）

        实现上扫描所有 `UnityFS\\x00` 候选偏移，逐个尝试解析，
        取对象数量最多的结果，最大化"拿到真实内容"的概率。
        """
        best_env: Optional[UnityPy.Environment] = None
        best_score = -1
        errors: list[str] = []
        failed_magic = True

        with self._fallback_version():
            for offset in _iter_unityfs_offsets(raw):
                failed_magic = False
                data = self._maybe_fix_blanked_header(raw[offset:])
                try:
                    env = UnityPy.Environment()
                    env.load_file(data, name=f"{name}@{offset:#x}")
                    score = len(list(env.objects))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"candidate@{offset:#x}: {exc}")
                    continue
                if score > best_score:
                    best_env, best_score = env, score

        if best_env is None:
            if failed_magic:
                raise BundleOpenError(
                    "无法识别 AssetBundle 魔数。最常见的几种情况：\n"
                    "  1) 文件不属于 Unity AB 资源\n"
                    "  2) 加密/混淆方式超出当前支持范围（请提供该游戏的样本）\n"
                    f"文件头: {raw[:32].hex(' ')}"
                )
            raise BundleOpenError(
                f"无法解析 bundle {name!r}:\n  " + "\n  ".join(errors[-5:])
            )
        return best_env

    @contextmanager
    def _fallback_version(self) -> Iterator[None]:
        """临时把 UnityPy 的全局 FALLBACK_UNITY_VERSION 设为强制版本。

        棕色尘埃2 把 Unity 版本串抹成 `0.0.0` / `5.x.x`，改动头部字节
        会破坏 LZ4 解压；正确做法是走 UnityPy 官方的 fallback 配置
        （BundleFile 与 SerializedFile 解析版本时都会读取它）。
        用完即还原，避免污染同进程其它 bundle。
        """
        if not self.forced_unity_version:
            yield
            return
        old = UnityPy.config.FALLBACK_UNITY_VERSION
        UnityPy.config.FALLBACK_UNITY_VERSION = self.forced_unity_version
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UnityPy.config.UnityVersionFallbackWarning)
                yield
        finally:
            UnityPy.config.FALLBACK_UNITY_VERSION = old

    def _maybe_fix_blanked_header(self, data: bytes) -> bytes:
        """若 BundleFile 头中的 Unity 版本字段为 0.0.0 且提供了显式版本，
        则直接改写该字段（保持字节长度一致或重建头长度前缀）。
        """
        if not self.forced_unity_version or len(data) < 16:
            return data

        try:
            version = struct.unpack_from("<i", data, 8)[0]
        except struct.error:
            return data

        if version not in (7, 8):
            # 版本号 0-6 的头布局不同，先不处理，保持原样
            return data

        # v7/v8: 魔数"UnityFS\0"(8) + version(i32) + unity_version(str)
        cursor = 8 + 4
        try:
            length = struct.unpack_from("<i", data, cursor)[0]
        except struct.error:
            return data
        if length < 0 or length > 256:
            return data

        old = data[cursor + 4 : cursor + 4 + length]
        if old not in BLANKED_VERSIONS:
            return data

        target = self.forced_unity_version.encode("utf-8")
        if len(target) == length:
            patched = bytearray(data)
            patched[cursor + 4 : cursor + 4 + length] = target
            log.info("已改写被抹掉的 Unity 版本字段 -> %s", self.forced_unity_version)
            return bytes(patched)

        # 长度不匹配时重建（需要整体移位，仅在魔数有效时尝试）
        patched = bytearray(data)
        patched[cursor + 4 : cursor + 4 + length] = target
        struct.pack_into("<i", patched, cursor, len(target))
        return bytes(patched)

    # ------------------------------------------------------------------
    # 遍历对象
    # ------------------------------------------------------------------
    def iter_objects(self, env: UnityPy.Environment) -> Iterator[UnityPy.Objects.Object]:
        for _, obj in env.container.items():
            yield obj