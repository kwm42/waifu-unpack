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

## 碧蓝航线 AzurLane ✅ spinepainting / live2d / painting 均已打通

### 游戏本体

- 安卓端资源在 `AssetBundles/` 下，分 `painting`（立绘）/ `live2d` / `spinepainting` 等分类目录。
- 样本文件**无扩展名**（如 `spinepainting/jishang_3_asmr_res`），头是 UnityFS v8。
- 版本串被抹成 **`5.x.x`**（不是 BD2 的 `0.0.0`），真实版本在 revision 字段
  （`2022.3.51f1` / `2022.3.62f3`），靠 `forced_unity_version="2022.3.51f1"`
  FALLBACK 机制解析（51f1 实测可打开 62f3 样本）。
- `painting` = 大图 + Sprite 切片（**只导切片 PNG**，用户拍板，已落地，按 textureRect 裁切）；
  `live2d` = 烘焙式 Cubism prefab（已落地，含原生 moc3，见下方「azurlane live2d」节）；
  `spinepainting` = **Spine 3.8**（已打通）。

### 样本结构（sample: spinepainting/telafaerjia_res，17 对象）

```
TextAsset 'telafaerjia.skel'  (1123536 B, 头 \x1c 二进制 Spine 3.8)
TextAsset 'telafaerjia.atlas' (14083 B, 引用 5 个 page: telafaerjia.png/2/3/4/5)
MonoBehaviour 'telafaerjia_Atlas'        ← SpineAtlasAsset: atlasFile + materials[]
MonoBehaviour 'telafaerjia_SkeletonData'
Material 'telafaerjia_telafaerjia' ... 'telafaerjia_telafaerjia5'  (×5, 每 page 一个)
Texture2D 'telafaerjia' ... 'telafaerjia5'  (4096×4096/2048, ×5)
```

### 多页 atlas 配对（踩坑，勿重复）

- atlas 是**多页**：一个 `.atlas` 引用多张 png，`SpineAtlasAsset.materials[]`
  **顺序**与 atlas 页面一一对应，Material `_MainTex` 即该页贴图。
- 旧 `_texture_plan` 单遍扫描 + `break` 只取第一张 → 多页 atlas 所有页全配成同一张
  （telafaerjia 5 张贴图内容各异却全被配成页面 1，仅首次样本恰好漏显）。
- 另一个隐蔽坑：**单遍扫描时 Atlas MonoBehaviour 可能先于其 Material 被遍历**，
  会只收集到"恰好已见过的 Material"（telafaerjia 只剩第 4 个）。修法是两遍：
  先收贴图 bitmap 与 Material 链，再解析 Atlas 的 materials[] → 逐页精确配对
  （`atlas_to_textures` 为 atlas_pid → [tex_pid,...]）。
- 名字兜底（atlas page 名 = Texture2D.m_Name+`.png`）保留为保底。

## 棕色尘埃2 BrownDust2 ✅ 首个样本已打通（myroom 贴图 bundle）

### 游戏本体

- 安卓包 `com.neowizgames.browndust2`，Unity 引擎，**仅 Spine 4.1**，无 Live2D。
- **"加密"实为 Unity 版本头被抹**：bundle 头显示 `5.x.x` 且版本串 `0.0.0`，
  让 UnityPy 解析失败。绕过见下方「版本头被抹的正确姿势」。

### 资源结构与目录清单（文件放在 `com.unity.addressables/`）

- `file.json`：Addressables **bundle 清单**（2023 条），字段：
  `bundleName`（磁盘目录名）/ `readableName`（逻辑路径）/ `hash`（子目录名）/
  `fileHash` / `size` / `bundleType`（Remote 2013 / Local 10）。
  角色 key 形如 `char060302`（char + 6 位数字），212 个去重角色。
- `catalog_alpha.json`：65MB 的 ContentCatalogData，asset 地址（285,756 条）在
  `m_InternalIds`，asset↔bundle 映射在压缩分段 `m_KeyDataString / m_BucketDataString /
  m_EntryDataString`（Addressables 二进制格式，先用 file.json 的 bundleName↔readableName
  就够了，暂未反序列化三段）。
- `catalog_alpha.hash`：目录哈希（32 字节），一般用不到。

### 本地缓存磁盘布局（关键）

- 不是 `.bundle` 扩展名文件，而是 **UnityWebRequest 缓存目录**：

  ```
  Shared/<bundleName>/<hash>/__data   ← 真实 bundle（无扩展名，固定叫 __data）
  Shared/<bundleName>/<hash>/__info   ← 缓存元数据（4 行文本，非 bundle）
  ```

- `<bundleName>` = file.json 的 `bundleName`；`<hash>` = 该条的 `hash` 字段。
  `is_bundle_file` 据此判断：文件名 == `__data` 即视为 bundle，`__info` 忽略。
- 样本：`samples/browndust2/Shared/006b27eb4c9d701a12f2f9e553e42bab/
  a7313786577fc9ea037b24b6c55239c0/__data`（227,671 字节）。
  对应逻辑路径 `common-spritetexture-myroom_assets_common/char060302/myroom`。

### 样本内容（myroom 贴图 bundle）

- 90 个对象：**Texture2D ×73 + Sprite ×16 + AssetBundle ×1**，无 atlas/skel（是贴图包，不是 Spine）。
- 73 张 128×128 贴图 = `Char060302_<姿势>_<方向>_<帧>`（Idle/Move/Sit × 8 方向），
  container key 形如 `Char060302_Idle_BR_01.png`，面向 myroom（休息室）场景。
- AssetBundle.m_Name = `<bundleName>.bundle`（`006b27eb....bundle`），
  可用它反查 catalog 拿逻辑路径，不依赖 rel 文本解析。

### 版本头被抹的正确姿势（踩坑，勿重复）

- **不能直接改头部字节**：BundleFile 头的版本串是 `string_to_null`（无长度前缀），
  直接替换会破坏头字节对齐/长度，LZ4 解压直接报
  `Decompression failed ... Error code: 8`。
- 且旧 `_maybe_fix_blanked_header` 假设的 v7/v8 len-prefixed 布局与该头不符
  （formatVersion 字段读出来也不是 7/8），对 BD2 根本不会触发。
- **正解 = UnityPy 官方 fallback**：`UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.22f1"`
  （BundleFile 与 SerializedFile 解析版本时都读它）。`BundleReader` 已封装为
  `forced_unity_version`，打开前临时设置、用完还原，用 `warnings` 屏蔽烦人告警。
- 若 2022.3.22f1 有 bundle 解析失败，备选 **2022.2.17f1** 可换。

### 输出语义（BD2 适配器 v1）

- 目录名 = catalog `readableName` 推导的角色标识（优先 `charXXXXXX` 查 names 表中文，
  没有则取逻辑路径尾段），**不再用 hash 文件目录名**（不可读、会撞名）。
- spine（复用 `core/spine.py`）：`<角色>/angel|bg/<base>.atlas|.skel|<贴图>.png`。
- painting（整图，非切片）：`<角色>/illust/<贴图名>.png`。
- 该适配器尚未拿到真实 Spine（atlas/skel）样本，`_extract_spine` 路径待真实 spine
  bundle 验证；myroom 样本只走了 painting 路径。

### azurlane live2d（烘焙式 Cubism prefab，2026-09 已验证）

- 样本：`samples/azurlane/live2d/` 下 `aijier_4` / `dafeng_7` / `guanghui_7`
  （**无扩展名文件**，UnityFS v8，版本串抹成 `5.x.x`，真实 2022.3.51f1 等，
  同 spinepainting 用 `forced_unity_version="2022.3.51f1"` 打开）。
- **结构**：5.9k~8.3k 个对象 = GameObject/Transform（`ArtMesh558`/`Part60`…）+
  MeshFilter/MeshRenderer + MonoBehaviour（`CubismRenderer`/`CubismDrawable`/
  `CubismParameter`/`CubismPart`）+ AnimationClip×32，容器 key 形如
  `Assets/ArtResource/Live2d/<key>/<key>.prefab` —— 模型被**烘焙成 Unity Mesh/组件**。
- **关键数据位**：原生 `.moc3` 二进制内嵌在 **CubismMoc** MonoBehaviour 序列化字节里，
  从 `MOC3` 魔数起到对象末尾（aijier 4622976 / dafeng 4637632 / guanghui 4073280 字节，
  头 = `MOC3` + u32 版本(4/5) + 信息块偏移表）；`<key>.physics3` 是 TextAsset；
  贴图是 Texture2D（`texture_00` 4096² 等）；**没有原生 model3.json**。
- **产出**：提取 `.moc3` + `.physics3.json` + `texture_0x.png`，由 `core/live2d.py`
  组装最小可行 `model3.json`（Groups/HitAreas 置空，官方 Cubism Viewer 可加载）。

### azurlane painting（大图 + Sprite 切片，2026-09 已验证）

- 样本：`samples/azurlane/painting/` 下 `haitian_3_rw_tex` / `kalvbudisi_2_tex` /
  `maliluosi_3_doa_tex`（无扩展名，UnityFS v8，版本串 `5.x.x`，同前用 forced_unity_version）。
- **结构**：对象极少（3~7 个）= Texture2D 若干 + Sprite + 可选 Mesh + AssetBundle。
  haitian 有两套（Sprite×2 / Texture×2 / Mesh×2，贴图 2048×1790 与 1792 各一张）；
  kalvbudisi 无 Mesh，maliluosi 有 Mesh。
- **关键数据位**：Sprite 的 `m_RD.texture`（PPtr，指大图）+ `m_RD.textureRect`（内容矩形，
  x=0, y=0, 宽高≈纹理减去右/下透明 padding）；`m_IndexBuffer` / `m_PhysicsShape` /
  Mesh = 立绘网格与碰撞形状（**不做 Mesh 重组，用户拍板只导切片 PNG**）。
- **产出**：`core/painting.py` 按 textureRect 从大图裁出内容区（左下原点转左上），
  `illust/<key>.png`；同名多张自动 `_2/_3`。
- 注意：Unity 的 textureRect 原点在纹理左下；若 Sprite 缺 textureRect 越界则兜底整图。

## 已知问题与待办（新人不踩坑）

1. **版本头被抹**判据：`BLANKED_VERSIONS = {"0.0.0", ""}`（bundlereader.py）；版本字段在 offset 8。
   ⚠️ 碧蓝的版本串是 `5.x.x`（不在该集），走 `forced_unity_version` FALLBACK 解析，不触发改写。
2. **TextAsset 二进制 = surrogate str**：还原用 `encode("utf-8","surrogateescape")`。
3. **同名多套模型**：`_pair_sets` 按内容配对；贴图配对 = 两遍扫描 Material 链，多页 atlas 逐页精确配对。
4. **增量不回删**：输入里删掉的 bundle，历史输出与状态保留（约定）。
5. 待办：names 表填充（azurlane/idleangels/BD2）、
   BD2 真实 Spine 样本、bg HD 贴图是否独立 HD 包补。

## 样本清单

```
samples/
  idleangels/spine_dtslxf_cshs.ab   双层嵌套 Spine 样本（端到端验证用）
  azurlane/spinepainting/           3 个无扩展名 Spine 3.8 样本（已验证）：
    jishang_3_asmr_res   多页 atlas（3 页）   kewei_5_res   双模型（kewei_5+kewei_5T）
    telafaerjia_res      多页 atlas（5 页）
azurlane/live2d/  aijier_4 / dafeng_7 / guanghui_7（烘焙 Cubism prefab，已验证：
                       moc3 内嵌 CubismMoc / physics3 TextAsset / texture_00|01）
azurlane/painting/ haitian_3_rw_tex（Sprite×2 同名 _2） / kalvbudisi_2_tex /
                   maliluosi_3_doa_tex（大图 + Sprite 切片，已验证）
  browndust2/  com.unity.addressables/（file.json / catalog_alpha.json / catalog_alpha.hash）
               Shared/006b27eb.../a731.../__data + __info（myroom 贴图 bundle，已验证）
  browndust2   待补：真实 Spine（atlas/skel）bundle + illust 立绘 bundle
```

> 拿到新游戏的样本后：放到 `samples/<game>/`，对着 `python -m waifu_unpack <game> --input samples\<game> --out samples\out --verbose` 的输出逐条验证；解析不了先看 `open_bundle` 报错里的文件头 hex。