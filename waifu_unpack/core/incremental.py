"""增量状态管理：基于 bundle 内容哈希，只加不改不删。

状态文件是输出根目录下的 `.waifu-unpack-state.json`，
记录每个 bundle 相对路径 -> md5。规则：
- 新增 / 内容变化  -> 需要处理
- 未变化           -> 跳过
- 输入里被移除     -> 忽略（保留历史输出与状态记录）
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

STATE_FILENAME = ".waifu-unpack-state.json"


class StateStore:
    def __init__(self, out_root: Path) -> None:
        self.out_root = out_root
        self._path = out_root / STATE_FILENAME
        self._state: dict[str, dict] = {}
        self._dirty = False

    @classmethod
    def load(cls, out_root: Path) -> "StateStore":
        store = cls(out_root)
        if store._path.exists():
            try:
                data = json.loads(store._path.read_text(encoding="utf-8"))
                store._state = data.get("bundles", {})
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("状态文件损坏，重新开始增量基线: %s", exc)
                store._state = {}
        return store

    def needs_process(self, rel: str, digest: str) -> bool:
        record = self._state.get(rel)
        return record is None or record.get("md5") != digest

    def all_recorded(self) -> list[str]:
        return list(self._state)

    def mark_done(self, rel: str, digest: str, artifacts: list[str]) -> None:
        self._state[rel] = {"md5": digest, "artifacts": artifacts}
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        if not self.out_root.exists():
            self.out_root.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "bundles": self._state}
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self._path)
        self._dirty = False
        log.info("状态已保存: %s (%d 条)", self._path, len(self._state))