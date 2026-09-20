# 棕色尘埃2（Brown Dust 2）解包指南

> 状态：✅ 首个样本（myroom 贴图 bundle）已打通；Spine（atlas/skel）路径待真实 spine bundle 验证。

## 一、游戏与资源概况

| 项目 | 内容 |
| --- | --- |
| 引擎 | Unity（**版本头被抹**，显示 `5.x.x / 0.0.0`） |
| 内容物 | **仅 Spine 4.1**，无 Live2D；静态立绘在 illust bundle（整图，非切片） |
| 资源形态 | 本地缓存目录 `Shared/<bundleName>/<hash>/__data`，全部 hash 命名 |
| 目录清单 | `com.unity.addressables/file.json`（bundleName ↔ readableName ↔ hash ↔ size） |
| 适配器配置 | `forced_unity_version = 2022.3.22f1` |

## 二、解包流程（已验证）

```powershell
python -m waifu_unpack browndust2 --input <资源目录> --out output --types spine,painting --progress
```

1. 把手机/模拟器拷出的 `<资源目录>` 传进来（需含 `Shared/` 与 `com.unity.addressables/file.json`）。
2. `BundleReader` 自动识别 `__data`（UnityWebRequest 缓存数据文件），忽略 `__info`。
3. `Catalog.discover` 递归找到 `file.json`，建立 hash ↔ 逻辑路径映射。
4. 目录名 = 逻辑路径推导的角色标识（`charXXXXXX` → names 表中文，否则取路径尾段）。
5. Spine 4.1：复用 `core/spine.py`（atlas/skel 是 TextAsset，`_asset_stem` 已剥 `.txt/.bytes` 尾）。
6. 立绘（painting）：整张 Texture2D → PNG，放 `<角色>/illust/`。

### 已验证输出

```
samples\out\browndust2\
  char060302\
    illust\     ← painting 整图（myroom 的 73 张贴图）
      Char060302_Idle_BR_01.png ... Char060302_Rest.png
  .waifu-unpack-state.json
```

## 三、注意事项

1. **版本头被抹**：不要改头部字节（会破坏 LZ4 解压）；正解 = `UnityPy.config.FALLBACK_UNITY_VERSION`，
   已封装进 `BundleReader`（`forced_unity_version` 开关）。若 2022.3.22f1 解析失败可换 `2022.2.17f1`。
2. **hash 文件名 + 无 container path**：必须靠 `file.json` 还原身份，否则无法映射角色中文名。
3. **illust bundle**：立绘为整图（非切片），直接导 PNG，不走 Mesh 重组。
4. **Spine 路径未验证**：当前样本只有贴图包；拿到 atlas/skel bundle 后需确认
   `_extract_spine` 输出可被 Spine 4.1 预览器打开。

## 四、当前缺口

- 真实 Spine（atlas + skel + 贴图）bundle 样本，验证 `_extract_spine` 与配对逻辑。
- illust 立绘大 bundle（如 `common-specialillust_1_assets_all` 205MB）样本。
- `names/browndust2.json` 中文映射（先 `charXXXXXX` 键，再填中文）。