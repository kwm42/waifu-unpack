# 游戏资源格式研究结论

> 状态图例：✅ 已验证样本 / 🕐 待验证 / ❓ 待确认

## 通用知识（三款游戏共用）

- 角色内容物通常为 **Spine**（`atlas+skel` 是 TextAsset，贴图是 Texture2D）或 **Live2D Cubism3**。
- 一个 bundle 里可能塞**多套同名模型**（人物 + 背景/特效），必须按内容配对，不能按名/按大小猜。
- 同一 bundle 内 Texture2D 可能**同名多张**（每套模型各一张），最终文件名要看 atlas 里的引用名。
- 贴图来源贴合度：`atlas 第一行文件名` 就是运行时找的贴图名，导出文件名必须与它一致（大小写敏感）。

## IdleAngels（爱神故事）✅ 端到端已通

### 游戏本体

- 安卓包 `com.mujoysg.hxbb`，Unity 引擎，纯 **Spine**，无 Live2D。
- `.ab` 文件**直读即可**：无加密、无版本抹除（但见"样本结构"——是双层嵌套）。
- 文件名是英文缩写（如 `spine_dtslxf_cshs.ab`），角色英文 id 见文件内 TextAsset 名（如 `luxifaIR`），需要 `names/idleangels.json` 映射中文。

### 样本结构（关键！）

样本：`samples/idleangels/spine_dtslxf_cshs.ab`（4,604,025 字节），**双层嵌套**：

- **外层壳**（offset 0，但有前置脏字节 `0x00`，所以魔数在 **offset 1**）：
  UnityFS v6、引擎 **2017.4.16f1**。内容是空的 config 桩：TextAsset `cfg_init`（内容只有 "bye"）+ 1 个 AssetBundle，2 个对象。
- **内层真内容**（**offset 772** = `0x304`）：UnityFS v8、引擎 **2021.3.58f1**，**28 个对象**，
  包含真实模型。对象类型：GameObject、CanvasRenderer、MonoBehaviour(SkeletonGraphic 运行时)、
  MonoScript、Material、TextAsset、RectTransform、Texture2D、AssetBundle。
- 内层关键对象：
  - `TextAsset` **`luxifaIR.atlas`** ×2（**两套**：13062 字节=人物 117 区域 / 3097 字节=背景 28 区域）
  - `TextAsset` **`luxifaIR.skel`** ×2（两套：319150 字节=人物，配 13062 atlas；347702 字节=背景，配 3097 atlas）
  - `Texture2D` **`luxifaIR`** ×2（两张**内容不同**的 2048×2048 贴图，各配一套）
  - `MonoBehaviour` `luxifaIR_Atlas`（SpineAtlasAsset：`atlasFile` + `materials[]`）
  - `MonoBehaviour` `luxifaIR_SkeletonData`（`skeletonJSON` + `atlasAssets[]`）
  - `MonoBehaviour` `''`（SkeletonGraphic，字段 `skeletonDataAsset`…）

> 配对真相：**不能**按"每名取最大"或扫描顺序配——正确配对是
> 人物=skel 319150 + atlas 13062，背景=skel 347702 + atlas 3097；
> 交叉配对＝"骨头对不上图层"，Spine 预览器直接报 Region not found 打不开。
> 这正是我们做"内容配对"的原因。

### 输出语义

- 一个 bundle 出**两套模型**：人物（`angel/`）与背景（`bg/`），各自 `luxifaIR.atlas/.skel/.png`。
- 贴图精确配对走 Material 链：`_Atlas` MonoBehaviour → atlasFile → materials → `_MainTex`（见 architecture.md §五）。
- atlas 写 `size: 4096,4096` 但贴图是 2048×2048：游戏**默认画质降采样**产物，均匀缩放不影响预览，属游戏数据本身。
- bundle 命名 `spine_<缩写>_<缩写>.ab`，与导出无关。

## 碧蓝航线 AzurLane 🕐 待验证样本（适配器为 stub）

- 资源在 `AssetBundles/` 下，分 **painting（立绘）/ live2d / spinepainting** 等分类目录。
- **立绘 painting** = Mesh + Texture2D 切片，导出时**只导切片 PNG**（用户拍板：不做 Mesh 重组；分辨率取游戏内原分辨率）。
- **Live2D** = Cubism3：moc3 在 MonoBehaviour / TextAsset 里，需解剖具体包装方式（Cubism 3 的 .bytes 倒在 MonoBehaviour 里常见）。
- **Spine** 3.8，atlas/skel 是 TextAsset（与 IA 同构，可复用 `core/spine.py`）。
- 命名：角色/皮肤有约定目录名，多半可直接映射。

## 棕色尘埃2 BrownDust2 🕐 待验证样本（适配器为 stub）

- **仅 Spine 4.1**，无 Live2D。
- **"加密"实为 Unity 版本头被抹**：bundle 头版本显示 `5.x.x` 且版本串 `0.0.0`，
  让 UnityPy 解析失败。绕过：给 `forced_unity_version`（当前配置 **2022.3.22f1**；
  社区也有人用 2022.2.17f1，若失败可换）。
- 本地缓存目录**全部是 hash 文件名**、无 container path → 需要 **catalog 文件**还原逻辑路径。
- 静态立绘在 **illust** bundle 里。
- 立绘可能不是切片而是整图（待样本确认）。

## 已知问题与待办（新人不踩坑）

1. **版本头被抹**判据：`BLANKED_VERSIONS = {"0.0.0", ""}`（bundlereader.py）；版本字段在 offset 8。
2. **TextAsset 二进制 = surrogate str**：还原用 `encode("utf-8","surrogateescape")`。
3. **同名多套模型**：`_pair_sets` 按内容配对，`_texture_plan` 按 Material 链匹配贴图。
4. **增量不回删**：输入里删掉的 bundle，历史输出与状态保留（约定）。
5. 待办：names 表填充、碧蓝/BD2 样本收集与适配器、Live2D 组装、bg 的 HD 4096 贴图是否要从独立 HD 包补。

## 样本清单

```
samples/
  idleangels/spine_dtslxf_cshs.ab   双层嵌套 Spine 样本（唯一样本，端到端验证用）
  azurlane/    （空，待样本）
  browndust2/  （空，待样本）
```

> 拿到新游戏的样本后：放到 `samples/<game>/`，对着 `python -m waifu_unpack <game> --input samples\<game> --out samples\out --verbose` 的输出逐条验证；解析不了先看 `open_bundle` 报错里的文件头 hex。