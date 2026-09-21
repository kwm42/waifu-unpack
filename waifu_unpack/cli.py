"""waifu-unpack 命令行入口。

用法：
    python -m waifu_unpack --list
    python -m waifu_unpack <游戏> --input <资源目录> --out <输出目录> [选项]

全量跑建议加 --progress 看进度：
    python -m waifu_unpack <游戏> --input <资源目录> --out <输出目录> --progress
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

log = logging.getLogger("waifu_unpack")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="waifu-unpack",
        description="解压二次元手游立绘：从 Unity AssetBundle 提取 Spine / Live2D / 静态立绘",
    )
    p.add_argument("game", nargs="?", help="游戏名，见 --list")
    p.add_argument("--list", action="store_true", help="列出已支持的游戏")
    p.add_argument("--input", type=Path, help="资源输入目录（安卓拷贝下来的那层）")
    p.add_argument(
        "--source",
        type=Path,
        help="来源地资源目录（游戏完整资源，如 F:\\live2d\\棕色尘埃2）；配合 --filter 从该目录复制需要的 bundle 到 --input",
    )
    p.add_argument(
        "--filter",
        default="",
        help="与 --source 连用：只复制 readableName 含这些关键词（逗号分隔）的 bundle，如 spine,cutscene",
    )
    p.add_argument("--out", type=Path, default=Path("output"), help="输出根目录 (默认 项目根/output)")
    p.add_argument(
        "--types",
        default="spine",
        help="要导出的内容类型，逗号分隔: spine,live2d,painting (默认 spine)",
    )
    p.add_argument("--force", action="store_true", help="忽略增量状态，重新处理所有文件")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="不导出，仅列出需要处理（未导出或已变化）的 bundle，并保存到 "
        "out/<游戏>/pending.txt（与 --force 连用则列出全部）",
    )
    p.add_argument("--progress", action="store_true", help="显示处理进度（原地刷新的进度行）")
    p.add_argument("--verbose", action="store_true", help="输出调试日志")
    return p


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _fmt_elapsed(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


class Progress:
    """原地刷新的进度行（写 stdout，避免与 stderr 的日志打架）。

    用法：update(done, status_label) 推进一行；finish() 清掉进度行。
    """

    def __init__(self, enabled: bool, total: int) -> None:
        self.enabled = enabled and total > 0
        self.total = total
        self._line = ""

    def update(self, done: int, label: str = "") -> None:
        if not self.enabled:
            return
        text = f"\r[{done}/{self.total}] {label}"
        if text != self._line:
            print(text, end="", flush=True)
            self._line = text

    def finish(self) -> None:
        if not self.enabled:
            return
        print(f"\r{' '*100}\r", end="", flush=True)
        self._line = ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        from waifu_unpack.games import get_adapter_meta

        metas = get_adapter_meta()
        for key, name in metas.items():
            print(f"  {key:<12} {name}")
        return 0

    args.input = args.input.expanduser().resolve() if args.input else None
    args.out = args.out.expanduser().resolve()
    if args.input is None:
        log.error("需要 --input 资源目录")
        return 2
    if not args.input.is_dir():
        log.error("输入目录不存在: %s", args.input)
        return 2

    setup_logging(args.verbose)

    from waifu_unpack.games import get_adapter

    try:
        adapter = get_adapter(args.game)
    except KeyError as exc:
        log.error("%s", exc)
        log.error("用 --list 查看支持的游戏")
        return 2

    if args.source is not None:
        source = args.source.expanduser().resolve()
        if not source.is_dir():
            log.error("来源目录不存在: %s", source)
            return 2
        keywords = [k.strip() for k in args.filter.split(",") if k.strip()]
        if not keywords:
            log.error("使用 --source 时需要 --filter 关键词（逗号分隔）")
            return 2
        sync = getattr(adapter, "sync_from_source", None)
        if sync is None:
            log.error("游戏 %s 不支持 --source 资源同步", adapter.key)
            return 2
        sync(source, keywords, args.input)

    types = frozenset(t.strip().lower() for t in args.types.split(",") if t.strip())
    unknown = types - set(adapter.supported_types)
    if unknown:
        log.warning("游戏 %s 不支持类型: %s (支持: %s)", adapter.key, sorted(unknown), adapter.supported_types)
    if not types & set(adapter.supported_types):
        log.error("没有可导出的类型，退出")
        return 2

    from waifu_unpack.core.incremental import StateStore

    game_out = args.out / adapter.key
    state = StateStore.load(game_out)

    from waifu_unpack.core.bundlereader import BundleOpenError

    t0 = time.time()
    scanned = processed = skipped = failed = 0

    bundles = list(adapter.iter_bundles(args.input))
    prog = Progress(args.progress, len(bundles))
    pending: list[str] = []
    for path, rel in bundles:
        scanned += 1
        prog.update(scanned, rel)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            log.warning("读取失败 %s: %s", rel, exc)
            failed += 1
            continue

        digest = adapter.digest(raw)
        if args.dry_run:
            if args.force or state.needs_process(rel, digest):
                pending.append(rel)
            continue

        if args.force or state.needs_process(rel, digest):
            try:
                env = adapter.open_bundle(raw, rel)
            except BundleOpenError as exc:
                log.warning("跳过（无法解析）: %s\n  %s", rel, exc)
                failed += 1
                continue
            try:
                artifacts = adapter.extract(
                    env,
                    types,
                    bundle_stem=Path(rel).stem,
                    input_dir=args.input,
                    rel=rel,
                )
            except NotImplementedError as exc:
                log.warning("跳过 %s: %s", rel, exc)
                continue
            written = _write_artifacts(game_out, artifacts)
            state.mark_done(rel, digest, written)
            processed += 1
        else:
            skipped += 1

    state.save()
    prog.finish()
    if args.dry_run:
        _report_pending(game_out, pending, args.force)
        log.info(
            "扫描 %d：待处理 %d（未导出或已变化）", scanned, len(pending),
        )
        return 0
    log.info(
        "完成: 扫描 %d，处理 %d，跳过(未变化) %d，失败/无法解析 %d，耗时 %.1fs (%.1f 个/秒)",
        scanned, processed, skipped, failed,
        time.time() - t0, scanned / max(time.time() - t0, 1e-9),
    )
    return 0


def _report_pending(game_out: Path, pending: list[str], force: bool) -> None:
    if not pending:
        log.info("没有需要处理的 bundle，全部已导出且内容未变化。")
        return
    for rel in pending:
        print(f"  {rel}")
    try:
        path = game_out / "pending.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(pending) + "\n", encoding="utf-8")
        log.info("%s 清单已写入 %s (%d 个)", "(强制全量)" if force else "待处理", path, len(pending))
    except OSError as exc:
        log.warning("无法写入清单: %s", exc)


def _write_artifacts(out_root: Path, artifacts) -> list[str]:
    written: list[str] = []
    try:
        for art in artifacts:
            dest = out_root / art.relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(art.data)
            written.append(art.relpath)
    except OSError as exc:
        log.error("写入失败 %s: %s", art.relpath, exc)
    return written


if __name__ == "__main__":
    sys.exit(main())