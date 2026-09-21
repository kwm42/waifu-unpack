# samples 样本目录规范

`samples/` 是**本地验证用真实资源**，体积大，已加入 `.gitignore`（不入库、不提交）。
解包代码、文档的改动才提交；样本更新后无需、也不会进 git。

## 总则

- 各个子目录 = 每款游戏的**真实 bundle 文件**，从游戏资源目录整体拷贝而来。
- **更新样本**：把"新增/更新的 bundle 文件"拷进对应子目录即可（`robocopy /E` 整目录同步最省事）。
- 约定与解包一致：**只增、不改、不删**；已有文件不要改名/移动。
- 目录里只放 bundle 文件，不要放压缩包/可执行文件/普通文本——它们会被当成潜在 bundle
  扫描并逐个尝试打开（无扩展名即放行），无关文件越多扫描越慢。
- 解包输出 **不放在 samples**，统一写 `output/`（CLI `--out output` / 交互脚本默认）。

## 目录 / 文件格式

### azurlane 碧蓝航线（来源：`…AssetBundles\live2d | spinepainting | painting\`）

| 子目录 | 文件命名 | 内容物 | 现状 |
| --- | --- | --- | --- |
| `azurlane/live2d/` | 无扩展名 `<角色>_<皮肤>`（如 `aijier_4`） | 烘焙式 Cubism prefab：`.moc3` 内嵌 `CubismMoc`、`physics3` 为 TextAsset、贴图 `texture_0x` | 269 个 |
| `azurlane/spinepainting/` | 无扩展名 `<角色>_<皮肤>[_res]…`（如 `telafaerjia_res`） | Spine 3.8：`atlas/skel` 为 TextAsset + 多页贴图 | 456 个 |
| `azurlane/painting/` | 无扩展名，多数 `<角色>_<皮肤>_tex` | 静态立绘：大 Texture2D + Sprite（±Mesh），无骨骼动画 | 10737 个（当前不处理） |

要点：
- 每个文件都是一个 UnityFS v8 bundle，版本串被抹成 `5.x.x`，适配器靠
  `forced_unity_version="2022.3.51f1"` fallback 打开；个别无法解析的文件会警告并计入"失败"。
- 文件名 = 输出目录名（`output/azurlane/<类型>/<文件名>/…`）。
- `painting/` 目录那个文件里没有动画数据，只在跑 `--types painting` 时当静态图导出切片。

### idleangels（来源：安卓安装包，`*_sp` 角色 bundle）

| 子目录 | 文件命名 | 内容物 | 现状 |
| --- | --- | --- | --- |
| `idleangels/` | `.ab` 后缀（如 `spine_luxifair_cshs.ab`） | Spine：atlas/skel TextAsset + 贴图 | 445 个 |

### browndust2（来源：本地缓存 `…Shared\<bundleName>\<hash>\__data`）

| 子目录 | 文件 | 内容物 | 现状 |
| --- | --- | --- | --- |
| `browndust2/com.unity.addressables/` | 目录与 json | Addressables 目录（bundleName ↔ 逻辑名，含 `file.json`） | 已有 |
| `browndust2/Shared/<bundle>/<hash>/__data` | 无扩展名 `__data` | 真实 bundle（Spine 4.1 / chibi 帧图 / ui 贴图） | 187 个。其中**主类三包 170 个全量**（illustspine 1 + illustspecial 1 + isolated-cutscene 168，已全量解包 0 失败），其余覆盖各分类样本。来源 `F:\live2d\棕色尘埃2` 现为 2026 版 `file.json`（2023 条 bundle），缺 193 个 bundle 目录不在本地全量源里 |

## 更新/验证流程

```powershell
# 1. 同步样本（示例：把游戏新出的 live2d 文件拷过来）
robocopy "F:\live2d\碧蓝航线\AssetBundles\live2d" "samples\azurlane\live2d" /E /MT:32

# 2. 解包（交互脚本：选游戏 → 选输入目录 → 增量解包）
python unpack_menu.py

# 或直接 CLI：
python -m waifu_unpack azurlane --input samples\azurlane\live2d --out output --types live2d --progress
```

跑完用 `--dry-run` 复查是否还有待处理：
`python -m waifu_unpack azurlane --input samples\azurlane\live2d --out output --types live2d --dry-run`
（`output/<游戏>/pending.txt` 会列出仍未处理的文件。）

> 陷阱：`samples/out/`（老测试输出）和 `output/` 都是**解包产物**，不要把产物当输入喂回工具。