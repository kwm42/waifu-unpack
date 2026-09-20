# waifu-unpack

从 Unity AssetBundle 解包二次元手游角色资源，输出**原生模型格式**，可直接用 Spine / Live2D 官方工具或在线预览器打开。

## 定位与范围

| 目标 | 说明 |
| --- | --- |
| Spine | `.skel`(二进制/JSON) + `.atlas` + `.png`，支持 3.x / 4.x |
| Live2D | `model3.json + .moc3 + physics3.json + textures`，Cubism3（不做 motion/expression，后续里程碑） |
| 静态立绘 | Texture2D 切片 PNG（碧蓝航线等拆分立绘先只导切片，不做 Mesh 重组） |
| 交付形态 | Python 源码 + CLI（不做 exe），增量式、可复跑 |

首批三款游戏，其余按同一 `GameAdapter` 插拔式追加：

- **IdleAngels**（爱神故事/天使恋曲）——**已打通端到端**（Spine）
- **碧蓝航线 AzurLane** —— 待实现（Spine 3.8 + Live2D Cubism3 + 立绘切片）
- **棕色尘埃2 BrownDust2** —— 待实现（Spine 4.1，版本头被抹）

## 环境

- Python 3.13（开发机: `E:\Programs\Python\Python313\python.exe`）
- [`requirements.txt`](../requirements.txt)：`UnityPy`、`Pillow`

安装：

```powershell
E:\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
```

UnityPy 当前版本 1.25.3。**1.x 的 API 与老教程（0.x `AssetsManager`）差别很大**，见 [architecture.md](./architecture.md#unitypy-1x-关键-api)。

## 快速上手

在仓库根目录执行：

```powershell
# 列出已支持的游戏
python -m waifu_unpack --list

# 处理 IdleAngels 资源：扫描 <资源目录> 下所有 bundle，增量导出到 <输出目录>
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录>

# --out 默认是项目根下 output/ 目录；指定 <输出目录> 可自定义
python -m waifu_unpack idleangels --input <资源目录>
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录>

# 忽略增量状态、强制全量重跑
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录> --force

# 全量跑建议加 --progress 显示进度（原地刷新第 x/总数 个 + 当前文件名）
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录> --progress

# 指定导出类型（默认只导 spine）
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录> --types spine,painting

# 详细日志
python -m waifu_unpack idleangels --input <资源目录> --out <输出目录> --verbose
```

> 资源目录 = 手机 / 模拟器拷出来的最外层文件夹（工具递归扫 `*.ab/.bundle/*.unity3d/*.asset/*.bytes` 及魔数嗅探兜底）。

### 当前可验证示例

```powershell
python -m waifu_unpack idleangels --input samples\idleangels --out samples\out
```

产出（详见 [conventions.md](./conventions.md#输出结构)）：

```
samples\out\idleangels\
  spine_luxifair_cshs\          ← 目录名 = bundle 文件名（去 .ab）
    angel\  ← 人物模型
      luxifaIR.atlas   luxifaIR.skel   luxifaIR.png
    bg\     ← 背景模型
      luxifaIR.atlas   luxifaIR.skel   luxifaIR.png
  .waifu-unpack-state.json   ← 增量状态
```

目录名取 bundle 文件名（永不撞名）；中文按 `names/idleangels.json` 的 `files` 表检索
（搜中文 → 文件名 → 目录），运行时不做中文归并。两套模型可分别拖进 Spine 编辑器 / Spine Preview 验证。

## 当前状态

- [x] 框架骨架（CLI / 包结构 / 适配器注册表）
- [x] bundle 读取：双层嵌套、前置脏字节、版本头被抹修复
- [x] 增量状态（MD5，只加不改不删）
- [x] Spine 组装：同名多套模型按内容配对 + Material 链精确定位贴图
- [x] IdleAngels 端到端
- [~] names/idleangels.json 中文映射填充（`files` 表 247/445 已自动生成，留空需人工补）
- [ ] 碧蓝航线（spine + live2d + painting）
- [~] 棕色尘埃2（forced_unity_version fallback + catalog 还原、myroom 贴图样本打通；待真实 Spine 样本）
- [ ] Live2D 组装落地

## 目录结构

```
waifu-unpack/
  waifu_unpack/            Python 包（下划线：包名不能用连字符）
    cli.py                 CLI 入口
    core/                  通用核心
      bundlereader.py      bundle 打开/头部修复
      incremental.py       增量状态
      spine.py             Spine 组装
      live2d.py            Live2D 骨架（未实现）
      painting.py          立绘切片
    games/                每款游戏一个适配器 + 注册表
    names/                每款游戏一张中文名映射表（json）
  samples/                 样本（见 game-research.md）
  docs/                    本文档
```

详细设计见 [architecture.md](./architecture.md)，各游戏解包指南见 [games/](./games/index.md)，格式研究见 [game-research.md](./game-research.md)。

> 约定：任何影响行为/结论的修改必须同步更新相关文档，见 [conventions.md](./conventions.md#文档同步规则强制)。