# 碧蓝航线（AzurLane）解包指南

> 状态：✅ spinepainting / live2d / painting 均已打通（各 3 个样本验证）。

## 一、游戏与资源概况

| 项目 | 内容 |
| --- | --- |
| 资源目录 | `AssetBundles/` 下按 **painting（立绘）/ live2d / spinepainting** 等分类 |
| 引擎 | Unity（样本 UnityFS v8，版本串被抹成 `5.x.x`，真实 2022.3.51f1 / 2022.3.62f3） |
| 内容物 | spinepainting = Spine 3.8；live2d = 烘焙式 Cubism prefab（含原生 .moc3）；painting = 立绘（大图 + Sprite 切片） |
| 资源后缀 | 样本为**无扩展名文件**（如 `jishang_3_asmr_res`、`aijier_4`、`haitian_3_rw_tex`） |

## 二、解包流程（spinepainting 已验证）

```powershell
python -m waifu_unpack azurlane --input samples\azurlane\spinepainting --out samples\out --types spine --progress
```

产出（输出结构见 [conventions.md](../conventions.md#输出结构azurlane)）：

```
output\azurlane\spine\
  jishang_3_asmr_res\angel\    ← 目录名 = bundle 文件名；整套模型（人物与背景同包的一套）
    jishang_3_asmr.atlas   jishang_3_asmr.skel
    jishang_3_asmr.png    jishang_3_asmr2.png    jishang_3_asmr3.png
  kewei_5_res\angel\
    kewei_5.atlas   kewei_5.skel   kewei_5.png   kewei_52.png
    kewei_5T.atlas  kewei_5T.skel  kewei_5T.png
  telafaerjia_res\angel\
    telafaerjia.atlas  telafaerjia.skel  telafaerjia.png ... telafaerjia5.png
```

一个 bundle 内的多套模型（如 `kewei_5` 与 `kewei_5T`）基名不同，各自独立成文件，
仍都在 `angel/`；若同 bundle 内含**同名多套**（人物+背景）则走 `bg/`（与 IdleAngels 同规则）。

## 三、解包流程（live2d 已验证）

```powershell
python -m waifu_unpack azurlane --input samples\azurlane\live2d --out samples\out --types live2d --progress
```

产出（可直接拖进官方 Cubism Viewer 加载）：

```
output\azurlane\live2d\
  aijier_4\
    aijier_4.moc3   aijier_4.model3.json   aijier_4.physics3.json
    texture_00.png  texture_01.png
  dafeng_7\   （1 张贴图时只有 texture_00.png）
  guanghui_7\
```

- `.moc3` 是**烘焙式 Cubism prefab**里内嵌的**原生 moc3 二进制**（CubismMoc 组件原始字节，
  从 `MOC3` 魔数起），版本 v4/v5 均可提取。
- `model3.json` 由工具**组装最小结构**（`Groups`/`HitAreas` 为空）：官方查看器可正常加载，
  只是没有表情分组/HitArea 标签。moc3 内自带的网格、部件、参数、动画均完整。

## 四、解包流程（painting 已验证）

```powershell
python -m waifu_unpack azurlane --input samples\azurlane\painting --out samples\out --types painting --progress
```

产出（`painting/` 目录，立绘 PNG）：

```
output\azurlane\painting\
  haitian_3_rw_tex\illust\    ← 目录名 = bundle 文件名
    haitian_3_rw.png  haitian_3_rw_2.png   ← 同名 2 张（贴图尺寸不同），变体 _2
  kalvbudisi_2_tex\illust\kalvbudisi_2.png
  maliluosi_3_doa_tex\illust\maliluosi_3_doa.png
```

- 样本 = **一张大 Texture2D + 一个 Sprite + 可选 Mesh**：Sprite 的 `m_RD.textureRect`
  定义内容区（大图边缘是透明 padding），切片 = 按 textureRect 裁出内容区 PNG
  （保留透明背景）。用户拍板：**只导切片 PNG，不做 Mesh 重组**。
- mesh / `m_IndexBuffer` / `m_PhysicsShape` 是立绘网格数据，当前忽略。

## 五、注意事项

1. **spinepainting 与 IdleAngels 同构**：atlas/skel 是 TextAsset，贴图是 Texture2D，
   直接复用 `core/spine.py`。⚠️ 差异：atlas 常为**多页**（页面数 = 贴图数），
   靠 `SpineAtlasAsset.materials[]` 顺序精确逐页配对（已修复，勿回退成单遍）。
2. **版本被抹成 `5.x.x`**：头部不是 `0.0.0`，`_maybe_fix_blanked_header` 不会改写，
   靠 `forced_unity_version="2022.3.51f1"` 的 FALLBACK 机制解析（与 BD2 姿势一致，
   实测 51f1 fallback 可打开 62f3 样本）。
3. 样本文件**无扩展名**：`is_bundle_file` 对无扩展名文件也放行，读取失败由 CLI 跳过。
4. **命名**：bundle 文件名即 `spinepainting/<角色key>_<皮肤key>_res` / `live2d/<角色key>_<皮肤key>`
   / `painting/<角色key>_<皮肤key>_tex`，目录名原样。`names/azurlane.json`（characters/skins 表）待填充中文。
5. **live2d = 烘焙式 Cubism prefab**：没有原生 model3.json，moc3 在 CubismMoc 序列化字节里
   （勿找 TextAsset），physics3 是 TextAsset，贴图是 Texture2D —— 详见
   game-research.md「azurlane live2d」节与 conventions.md 踩坑 11。
6. **painting 切片**：Sprite 的 `textureRect` 为左下原点（Unity UV 系），转 PIL 左上原点裁切；
   同 bundle 内同名 Sprite 自动出 `_2/_3` 变体；越界时兜底整图输出（详见 conventions.md 踩坑 12）。

## 六、当前缺口

- `names/azurlane.json` 中文映射表为空。