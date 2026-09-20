# 架构与代码走读

## 一、分层

```
cli.py                参数解析、扫目录、增量判断、写文件、汇总日志
  └ games/<key>.py    GameAdapter：判别 bundle、打开、组装导出物、命名
       └ core/        通用能力
            bundlereader   读取 bundle（嵌套/脏字节/版本修复）
            catalog        目录清单（Addressables file.json，BD2 用）
            incremental    增量状态
            spine / live2d / painting  内容组装
```

数据流（一次 `python -m waifu_unpack <game> --input ...`）：

```
iter_bundles(input)  ── rel + bytes ──▶ digest(rel 判增量)
  需要处理? ──▶ open_bundle(raw) ──▶ extract(env, types) ──▶ artifacts[]
  未变化?   ──▶ 跳过
artifacts ──▶ 写盘 + state.mark_done(rel, md5, 文件名列表) ──▶ state.save()
```

## 二、核心抽象：`GameAdapter`（games/base.py）

新增一款游戏 = 继承它，回答四件事，并注册（见"新增游戏"）。

| 方法 | 作用 |
| --- | --- |
| `is_bundle_file(rel)` | 判定输入文件是否为 bundle（可配合 `bundle_exts` 白名单加速） |
| `open_bundle(raw, name)` | 打开 bundle，默认走 `BundleReader`（多数游戏不用覆写） |
| `extract(env, types, bundle_stem)` | 把 bundle 组装成 `ExportArtifact[]`，按 `types` 分派给 core 模块 |
| `resolve_identity(base)` | 英文 id → `Identity(char, skin)`（查 names.json，查不到回退） |

其它公共件：

- `ExportArtifact(relpath, data)`：一个待写文件（`out_root` 下相对路径）。
- `Identity(char, skin)`：角色/皮肤中文标签。
- `artifact_in(char, skin, rel, data)`：拼 `out_root` 下相对路径的核心函数。
  **skin 等于哨兵 `DEFAULT_SKIN`（"默认"）时不生成皮肤层级**，避免无意义的 `默认/` 目录。
- `Register`：`games/__init__.py` 的 `_REGISTRY` 字典，值 = `(模块路径, 类名)` 延迟导入（UnityPy 重，避免首屏卡）。

### 命名映射 names.json

读入 `names/<game>.json`，格式：

```json
{
  "characters": { "luxifaIR": { "cn": "角色中文名" } },
  "skins": {
    "皮肤key": { "char": "角色的characters键", "cn": "皮肤中文名" }
  }
}
```

`resolve_identity` 顺序：先查 `skins`（拿到角色键再查 `characters`），再查 `characters`，都没有就用英文 id 原样并用 `DEFAULT_SKIN` 皮肤。字符集限定：小写字母、数字、下划线（`_canonical_id` 归一化）。

## 三、core/bundlereader.py

- `_iter_unityfs_offsets`：枚举文件内所有 `UnityFS\x00` 魔数偏移。
- `open_bytes`：对**每个候选偏移**尝试 `Environment.load_file`，**取对象数量最多的结果**。
  这天然兼容三种情况：
  1) 正常单包；
  2) 前置脏字节（如文件第一个字节是 `0x00`）；
  3) **双层嵌套**——外层是旧引擎空壳、内层偏移处另有真 UnityFS（IdleAngels 样本即此模式）。
- `_maybe_fix_blanked_header`：旧版"版本字段被抹成 `0.0.0`"的 v7/v8 len-prefixed 头布局
  修复（魔数8 + version(int32) + 长度前缀版本串）。⚠️ 对 BD2 **不适用**（它不是这个布局），
  BD2 的正确姿势见下。
- **版本头被抹的通用解法（BD2）**：不要改头部字节（BD2 的版本串是 `string_to_null`，
  位置/长度对不上，直接替换会破坏 LZ4 解压）。正解是设
  `UnityPy.config.FALLBACK_UNITY_VERSION = forced_unity_version`（BundleFile 与
  SerializedFile 解析版本时都会读它）。`BundleReader` 用 `_fallback_version()` 上下文
  管理器在打开期间临时设置并还原，同时用 `warnings` 屏蔽该 fallback 的烦人告警。
- 全部候选解析失败 → 抛 `BundleOpenError`，附文件头 hex 便于回传样本。

## 四、core/catalog.py（目录清单，BD2）

- 解析 Addressables 的 `file.json`：`bundleName`（磁盘目录名）↔ `readableName`（逻辑路径）
  ↔ `hash`（子目录名）↔ `size`。`Catalog.discover(base_dir)` 递归找
  `com.unity.addressables/file.json` 并加载。
- 用途：BD2 本地缓存是 `Shared/<bundleName>/<hash>/__data` 纯 hash 命名，
  靠它把 hash 还原成可读的角色/路径，也校验 size。
- 数据形态见 game-research.md「棕色尘埃2」节。

## 五、core/incremental.py

- 状态文件：`<out>/<game>/.waifu-unpack-state.json`，记录每个 bundle 相对路径 → `{md5, artifacts[]}`。
- 规则：md5 与记录一致 → 跳过；不一致/未记录 → 处理；输入中被删除 → **不清理**历史输出与记录（只加不改不删）。
- 写入用临时文件 + `replace`，避免半截状态。损坏的旧状态仅告警并按空基线重来。

## 六、core/spine.py（重点）

### 产出模型 `SpineExport`

```
base     身份名（resolve_identity 用）
role     "character" | "background"   → 次级目录（IdleAngels 映射 angel/、bg/）
variant  同角色目录内多套时从 0 起计；stem = base（variant=0）或 base_N（N≥2）
atlas_text / skel_bytes / textures{引用名: png} / missing_textures
```

### 组装流水线（iter_spine_exports）

1. **收集 TextAsset**：`(m_Name, path_id, bytes)`。⚠️ `m_Script` 可能是 `bytes`、
   **也可能是含 surrogate 的 `str`**（二进制 .skel 就是），必须
   `str.encode("utf-8", "surrogateescape")` 还原原始字节，不能直接 `bytes(...)`。
2. **分组**：`_asset_stem` 剥掉 `.asset/.txt/.bytes` 再剥 `.atlas/.skel/.json` 得到基名；
   同名变体**全部保留**（dict 键不能是 m_Name，否则同名多套被吃光）。
3. **配对**（`_pair_sets`）：同名多套时，按 atlas 区域名 ∩ 骨架 token 的**重叠度**贪心两两配对。
   这是血泪教训——同一 bundle 可能含"人物/背景"两套**同名**模型，
   按扫描顺序或"取最大"都会把骨架和贴图集**交叉配错**，预览器直接打不开。
4. **角色判定**：区域数最多的整套 = `character`，其余 = `background`。
5. **贴图**（`_texture_plan`）：一张 bundle 里可能有**多张**同名 Texture2D，不能按名去重。
   - 精确配对走 Material 链：`MonoBehaviour(名 *_Atlas)` → `atlasFile` → 
     `SpineAtlasAsset.materials[]` → `Material.m_SavedProperties.m_TexEnvs["_MainTex"].m_Texture.path_id`。
   - **多页 atlas**：一个 `.atlas` 可能引用多张 png（碧蓝航线常见），
     `materials[]` **顺序与 atlas 页面一一对应**，故 `atlas_to_textures` 存
     atlas_pid → [tex_pid,...] 列表，`_match_textures` 逐页精确配对。
   - ⚠️ `_texture_plan` 必须**两遍扫描**（先收 Texture2D/Material 链，再解析 Atlas），
     单遍时 `_Atlas` 可能先于其 Material 被遍历，会漏配（踩坑记录 9/10）。
   - 兜底：大小写不敏感按 `atlas 引用名`(如 `luxifaIR.png`) 匹配，同名多张取最大的。
   - 跳过多余的：名字兜底会跳过已被精确配对用过的贴图字节（`used_pngs`）。

### 已知格式细节（Spine 3.8/4.x）

- atlas/skel 是 `TextAsset`（m_Name 如 `luxifaIR.atlas` / `luxifaIR.skel`）；atlas 第一行 `xxxx.png` 即引用的贴图名。
- atlas 文本里 `size: 4096,4096` 但实际贴图可能是 2048——这是游戏**降采样**产物，
  均匀缩放不影响 uv 正确性，属游戏数据本身。
- 二进制 skel 头 `\x1c` + 7 字节 hash + 字符串表，字符串区包含 attachment 名（用于配对估分）。

## 七、UnityPy 1.x 关键 API

踩过的坑，务必记住：

| 旧写法（网上大多数教程，0.x） | 1.x 正确写法 |
| --- | --- |
| `AssetsManager()` / `am.load_file(path)` | `UnityPy.Environment()` |
| `env.load(files)` 传文件路径列表 | 传内存 bytes 用 `env.load_file(data, name=...)` |
| `obj.name` | `obj.read().m_Name`等，或 `obj.read_typetree()` |
| `BundleFile` 构造传 bytes | 需 `EndianBinaryReader`（一般用不到，`load_file` 已封装） |

其它：
- `env.objects` 在本机 1.25.3 是**可重复遍历的 list**，但 core 里仍先 `list(env.objects)` 物化防御。
- `MonoBehaviour` 是**类型树反序列化**的，字段直接 `getattr(r, "m_xxx")` 可取
  （`to_dict()`/`dict(r)` 不可用）。不确定有哪些字段用 `dir(r)` 过滤下划线。
- `Texture2D.image` 返回 PIL Image（RGBA/RGB），后台格式（ASTC 等 48 号之类）也能解。

## 八、新增一款游戏清单

1. `games/<key>.py`：继承 `GameAdapter`，实现 `is_bundle_file` / `extract`，
   （必要时覆写 `open_bundle`、设 `forced_unity_version`）。
2. `games/__init__.py`：`_REGISTRY` 加一行 `("模块路径", "类名")`。
3. `names/<key>.json`：建空表。
4. 放样本到 `samples/<key>/`，跑 `python -m waifu_unpack <key> --input samples\<key> --out samples\out --verbose` 验证。

## 九、开发环境提示（Windows / PowerShell）

- **控制台中文乱码 = 代码页问题，不是数据问题**：文件是 UTF-8，PowerShell 用 GBK 显示。
  无碍时忽略；需要看得舒服就 `$env:PYTHONIOENCODING="utf-8"` 再跑。
- 包根目录是仓库根，跑 `python -m waifu_unpack ...` 要在仓库根执行；
  `samples/` 下的临时脚本若 import 包，需 `$env:PYTHONPATH="D:\code\python\waifu-unpack"`。
- 系统是 win32、shell 是 PowerShell 5.1：多用 `;` 和 `if ($?)` 串联，别用 `&&`。