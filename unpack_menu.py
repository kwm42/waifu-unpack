"""交互式解包向导。

用法（在项目根目录）：
    python unpack_menu.py

支持的操作：
    1. 全量解包  —— 忽略增量状态，所有 bundle 重新处理
    2. 增量解包  —— 只处理新增 / 内容有变化的 bundle（推荐）
    3. 检查待解包 —— 不处理，仅列出尚未解包或已变化的 bundle（含清单文件）
    4. 更换输入目录 / 内容类型
    0. 退出

实现说明：本脚本只是"薄壳"，所有实际操作（解包 / 扫描比对）都交给
python -m waifu_unpack 子进程，避免在父进程加载 UnityPy 造成内存翻倍。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "output"

# 每款游戏: (key, 显示名, 默认支持的 types)。
# 修改 waifu_unpack/games/__init__.py 的 REGISTRY 时请同步这里。
GAMES: list[tuple[str, str, str]] = [
    ("azurlane", "碧蓝航线 (Azur Lane)", "spine,live2d,painting"),
    ("idleangels", "Idle Angels", "spine,painting"),
    ("browndust2", "棕色尘埃2 (Brown Dust 2)", "spine,painting"),
    ("jiaocuozhanxian", "交错战线 (CrossCore)", "spine,painting"),
]


def _ask_choice(title: str, choices: list[tuple[str, str]]) -> int:
    """choices: [(标签, 说明)]，返回序号（1 起），0 表示取消。"""
    print(f"\n== {title} ==")
    for i, (label, desc) in enumerate(choices, 1):
        print(f"  [{i}] {label}" + (f"  ({desc})" if desc else ""))
    print("  [0] 返回 / 取消")
    while True:
        raw = input("选择: ").strip()
        if raw == "0":
            return 0
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return int(raw)
        print("无效输入，请重试。")


def _candidates(game_key: str) -> list[Path]:
    cands: list[Path] = []
    base = ROOT / "samples" / game_key
    if base.is_dir():
        cands.append(base)
        for sub in sorted(p for p in base.iterdir() if p.is_dir()):
            cands.append(sub)
    return cands


def pick_input_dir(game_key: str) -> Path:
    cands = _candidates(game_key)
    while True:
        print(f"\n== 选择输入目录（{game_key}）==")
        for i, c in enumerate(cands, 1):
            print(f"  [{i}] {c}")
        print(f"  [{len(cands)+1}] 手动输入完整路径")
        print("  [0] 返回")
        raw = input("选择: ").strip()
        if raw == "0":
            return Path("")
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(cands):
                return cands[n - 1]
            if n == len(cands) + 1:
                raw = input("输入目录完整路径: ").strip().strip('"')
                if raw:
                    p = Path(raw)
                    if p.is_dir():
                        return p
                    print("目录不存在，请重试。")
            else:
                print("无效选择，请重试。")
        else:
            p = Path(raw).expanduser()
            if p.exists():
                return p
            print("目录不存在，请重试。")


def pick_types(supported: str) -> str:
    print(f"\n== 内容类型（默认全部: {supported}）==")
    raw = input(f"输入类型（逗号分隔，直接回车用全部 [{supported}]）: ").strip()
    if not raw:
        return supported
    allowed = set(supported.split(","))
    chosen = [t.strip().lower() for t in raw.split(",") if t.strip()]
    bad = [t for t in chosen if t not in allowed]
    if bad:
        print(f"忽略不支持的类型: {bad}")
        chosen = [t for t in chosen if t not in bad]
    return ",".join(chosen) or supported


def build_cmd(game_key: str, input_dir: Path, types: str, force: bool = False, dry: bool = False) -> list[str]:
    cmd = [
        sys.executable, "-m", "waifu_unpack", game_key,
        "--input", str(input_dir),
        "--out", str(OUT_ROOT),
        "--types", types,
        "--progress",
    ]
    if force:
        cmd.append("--force")
    if dry:
        cmd.append("--dry-run")
    return cmd


def run_child(cmd: list[str]) -> int:
    print("\n" + " ".join(cmd))
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.call(cmd, cwd=str(ROOT), env=env)


def main() -> int:
    os.system("")  # 让 Windows 控制台支持 ANSI
    print("waifu-unpack 交互式解包向导")
    print(f"  支持游戏: {', '.join(f'{k}={v}' for k, v, _ in GAMES)}")

    while True:
        choice = _ask_choice("选择游戏", [(k, v) for k, v, _ in GAMES])
        if choice == 0:
            print("再见。")
            return 0
        game_key, _, default_types = GAMES[choice - 1]

        input_dir = pick_input_dir(game_key)
        if not input_dir:
            continue
        types = pick_types(default_types)

        while True:
            act = _ask_choice(
                f"操作（{game_key}，输入: {input_dir}，类型: {types}）",
                [
                    ("全量解包", "忽略增量状态，所有文件重新处理"),
                    ("增量解包", "只处理新增/有变化的文件"),
                    ("检查待解包文件", "不处理，只列出未解包/已变化的文件"),
                    ("更换输入目录/类型", ""),
                ],
            )
            if act == 0:
                break
            if act == 1:
                run_child(build_cmd(game_key, input_dir, types, force=True))
            elif act == 2:
                run_child(build_cmd(game_key, input_dir, types, force=False))
            elif act == 3:
                run_child(build_cmd(game_key, input_dir, types, dry=True))
            elif act == 4:
                new_dir = pick_input_dir(game_key)
                if new_dir:
                    input_dir = new_dir
                    types = pick_types(default_types)
    return 0


if __name__ == "__main__":
    sys.exit(main())