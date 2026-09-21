# AGENTS.md

解包瓦伊夫（二次元 waifu）游戏 Unity AssetBundle，转成原生 Spine / Live2D / 立绘 PNG 输出。Python 3.13 包 `waifu_unpack`，CLI 入口 `python -m waifu_unpack`。无 `pyproject.toml`、无测试、无 lint 配置；依赖在 `requirements.txt`（UnityPy 1.25.3、Pillow、numpy）。

## 知识都在 docs/ —— 先读，改变行为时必须同步更新

- `docs/conventions.md` — 输出结构、命名规则、增量语义、**强制文档同步表**、踩坑记录（Bug 档案）。
- `docs/architecture.md` — 分层、`GameAdapter` 抽象、UnityPy 1.x API、新增游戏清单。
- `docs/game-research.md` — 各游戏格式研究。
- `docs/games/<key>.md` — 各游戏解包指南 + 验证方法。

**文档同步规则（强制）：** 任何影响"行为/结论"的修改必须在同一改动中同步更新对应文档（输出/命名/增量改 `conventions.md`；代码分层/API/新坑改 `architecture.md`；格式结论改 `game-research.md`；重命名/删除文档时同步改 `docs/index.md` 与 `docs/README.md` 引用）。修过的 bug 必须追加进踩坑记录。需求先拍板在 `conventions.md`，再写代码。

## 开发流程（强制：先讨论后开发）

任何功能开发 / 行为变更（新游戏、新格式、输出结构调整、命名规则、增量语义、核心算法改动等），**动手写代码前必须先与用户详细讨论需求、确定细节，并输出设计方案**，方案经用户确认后才能进入开发阶段。流程固定两阶段：

**① 讨论阶段（只读，禁止编辑）：**
- 只能用只读工具推进：阅读文档/代码、搜索、跑 CLI 验证现状（`--list` / `--dry-run` / 对样本实际运行），不许编辑或新建任何文件。
- 产出：书面的需求理解 + 设计方案（改动点、输出/命名、增量语义、受影响代码与文档、风险/踩坑），向用户逐项确认，有歧义先问再定。

**② 开发阶段（用户确认方案后才可编辑代码）：**
- 用户明确认可方案后，才允许修改代码与按文档同步规则更新文档。
- 同一改动内连续完成：代码 → 同步文档 → 用样本验证。

例外（可免正式方案讨论，但仍须一句说明意图）：纯机械/低风险的改动，如修注释、重命名局部变量、微不足道的 bug 修整。

## 命令（一律在仓库根目录执行）

```
python -m waifu_unpack --list                              # 列出支持的游戏
python -m waifu_unpack <game> --input <dir> [--out output] [--types spine,live2d,painting]
python -m waifu_unpack <game> --input <dir> --out <out> --force   # 忽略增量状态，全量重跑
python -m waifu_unpack <game> --input <dir> --dry-run             # 只列待处理 -> out/<game>/pending.txt
python -m waifu_unpack browndust2 --source <完整游戏目录> --filter <关键词> --input samples\browndust2 --out output   # BD2 按关键词同步
python unpack_menu.py                                    # 交互式向导（薄壳，实际干活的是 CLI 子进程）
```

验证 = 对本地样本跑 CLI，例如 `python -m waifu_unpack idleangels --input samples\idleangels --out samples\out --verbose`。`samples/` 放真实（不入库）资源。注意 `--dry-run` 在打开 bundle 之前就短路，想真正跑到 `extract` 要用 `--force` 或对空的 out 目录首次运行。

## 各处职责

- `waifu_unpack/cli.py` — 参数解析、扫描、增量过滤、写文件、进度（薄控制器）。
- `waifu_unpack/games/<key>.py` — 每款游戏的 `GameAdapter` 子类：`is_bundle_file`、`extract`，可选 `forced_unity_version` / `bundle_exts`。
- `waifu_unpack/games/__init__.py` — `_REGISTRY` 映射 key -> `("模块路径", "类名")`，**延迟导入**（UnityPy 很重，不要在模块顶层 eager import）。
- `waifu_unpack/core/` — `bundlereader`（嵌套/前置脏字节/版本头被抹修复）、`incremental`（MD5 状态）、`spine` / `live2d` / `painting` 组装、`catalog` + `sync_from_source`（仅 BD2）。
- `waifu_unpack/names/<key>.json` — `characters`/`skins` 中文名查找表。
- `output/` — 默认导出根目录，每款游戏一个子目录。

## 新增 / 注册一款游戏

1. 写 `games/<key>.py` 子类（见 `docs/architecture.md` §七）。
2. 在 `games/__init__.py` 的 `_REGISTRY` 登记 + **同步 `unpack_menu.py` 里的 `GAMES` 列表**（文件里有提示注释要同步）。
3. 建 `names/<key>.json`（空表也行——自动回退英文 id）。
4. 用样本验证，再按文档同步规则更新文档。

## 踩坑提示（来自 Bug 档案；完整清单见 `docs/conventions.md`）

- TextAsset 二进制回来是带 surrogate 的 `str` —— 一律走 `_text_asset_bytes` / `str.encode("utf-8", "surrogateescape")`，千万别直接 `bytes(...)`。
- `env.objects` 必须先 `list(...)` 物化再遍历。
- 同名重复到处都是（一个 bundle 里多个 TextAsset / Texture2D / 模型）：按 `path_id` 收集成 list，**绝不能**按 `m_Name` 去重。
- 一个 bundle 里多套 Spine 模型，atlas↔skel 按区域名/token 重叠度配对，不是扫描顺序。
- 不要去手工改 bundle 头部的 Unity 版本字节；用 `UnityPy.config.FALLBACK_UNITY_VERSION`（BD2）。Bundlereader 会对每个 `UnityFS\x00` 魔数偏移重试打开，取对象数最多的结果。
- UnityPy 是 1.x API（`UnityPy.Environment`、`load_file(bytes, name=...)`），不是网上教程普遍的 0.x `AssetsManager`。
- 增量状态：`<out>/<game>/.waifu-unpack-state.json`；语义 = 只加/只改，输入中被删除的文件**不回删**历史输出。

## 环境（Windows / PowerShell 5.1）

- 命令串联用 `;` / `if ($?)` —— 没有 `&&`。含空格路径要加引号。
- 控制台中文乱码是 GBK 代码页问题，不是数据坏了；想看舒服先 `$env:PYTHONIOENCODING="utf-8"`。
- 磁盘上全是 UTF-8；JSON/PNG 产出用 UTF-8 / `PNG, optimize=True`。
- 提交信息是简短中文一行式（看 `git log`）。

## 语言约定（强制）

- **对所有对话的回复一律用中文**。
- **代码注释、docstring、新增/修改的文档一律用中文**。已存在的英文文档不必回翻，但新写和更新的内容用中文。