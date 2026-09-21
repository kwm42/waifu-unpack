# 项目约定与决策记录

## 需求决策（用户拍板，勿改）

| 主题 | 决定 |
| --- | --- |
| 技术栈 | Python + CLI，**源码分发**（不做 exe） |
| 产出格式 | **原生模型格式**：Spine `.skel/.atlas/.png`；Live2D `moc3+model3.json+physics3.json+textures`（**不含** motion/expression，后续可加） |
| 静态立绘 | 碧蓝航线等拆身为切片+Mesh 的，**只导切片 PNG**，不做 Mesh 重组；分辨率=游戏内原分辨率 |
| 输出层级 | **每个 ab/bundle 单独一套目录**，不做同角色合并（皮肤可能重名）。目录名 = `角色中文`（本体）或 `角色中文-<皮肤/品质/数字>`（合成标签）；同 bundle 多套模型仍走 `angel/`、`bg/` 子目录 |
| 皮肤保留 | **全部皮肤**都保留，按 bundle 数自然扩展 |
| 增量 | 按 bundle 内容 MD5：**新增/变化才处理，未变跳过，输入删除不回删**（只加不改不删） |
| 资源来源 | **本地目录扫描**（手机/模拟器拷出的文件夹） |
| 命名 | 英文 id 归一化后查 `names/<game>.json`（characters/skins 两表），查不到回退英文 id |
| 首个游戏 | IdleAngels（用户确认最简单、可验证），随后碧蓝航线，再 BD2 |
| 包名 | 仓库目录 `waifu-unpack`，Python 包 `waifu_unpack`（下划线，包名不能用连字符）。曾提议改 src 布局，未确认，暂不动 |

## 文档同步规则（强制）

**任何对"行为/结论"有影响的修改，必须在同一改动中同步更新相关文档**，不得只改代码。

| 改了什么 | 必须同步哪份文档 |
| --- | --- |
| 新游戏适配器 / 新样本/新格式结论 | `game-research.md`（格式研究）+ `README.md`（状态清单） |
| 输出结构 / 命名规则 / 增量语义 / 需求变化 | `conventions.md` |
| 代码分层 / API 用法 / 核心算法 / 新坑 | `architecture.md`（含 Bug 档案→`conventions.md` 踩坑记录） |
| API 调用方式（如 UnityPy 版本升级） | 本文件"环境备忘" + `architecture.md` §UnityPy 1.x 关键 API |

细则：

- 修过的 bug 必须追加到 `conventions.md`「踩坑记录」，供后人/AI 避免重犯。
- 新游戏格式结论（加密/嵌套/配对等）必须写入 `game-research.md`，附样本路径。
- 需求一旦拍板变化，先改 `conventions.md` 需求决策表，再改代码。
- 删除或重命名文档时同步更新 `docs/index.md` 与 `README.md` 的引用。

## 输出结构（IdleAngels v3，用户拍板 2026-09）

```
out_root/idleangels/<bundle文件名>/angel/   ← 人物模型（区域最多的一套）
                                   bg/      ← 背景模型（其余套）
  每套三件套：<基名>.atlas  <基名>.skel  <atlas引用的贴图名>.png
```

- **目录名 = bundle 文件名**（如 `spine_spz_np.ab` → 目录 `spine_spz_np/`）。同一 ab 内多套模型仍走 `angel/`、`bg/` 子目录；同名变体文件名追加 `_2`、`_3`…。
- `names.json` 只作**查找索引**：`files{ "spine_spz_np": {"cn": "水瓶座-女仆"} }`，搜中文 → 文件名 → 目录。运行时纯按文件名，不做中文归并，永不撞名。
- 贴图文件名 = **atlas 第一行引用的名字**（大小写原样），文件与 atlas 同目录，这套裁切才正确。
- 状态文件 `<out>/<game>/.waifu-unpack-state.json` 不算导出物。

## 输出结构（碧蓝航线，2026-09）

```
out_root/azurlane/spine/<bundle文件名>/angel/   ← 人物/单套模型
                                      bg/  ← 背景模型（同名多套时）
   每套三件套：<基名>.atlas  <基名>.skel  <atlas各页引用的贴图名>.png

out_root/azurlane/live2d/<bundle文件名>/ <- Live2D 模型一套
   <基名>.moc3  <基名>.model3.json  <基名>.physics3.json（有则）  <贴图名>.png

out_root/azurlane/painting/<bundle文件名>/illust/ <- 立绘切片 PNG（painting）
   <key>.png   （同 bundle 内有同名多张时 <key>_2.png、<key>_3.png…）
```

- **目录名 = bundle 文件名**（样本无扩展名，如 `spinepainting/jishang_3_asmr_res` → `jishang_3_asmr_res/`）。
- spinepainting 大多一套模型直接进 `angel/`；同 bundle 若含同名多套（人物+背景）才走 `bg/`。
- **多页 atlas**：一个 `.atlas` 引用多张 png，逐页导出（`telafaerjia.png`、`telafaerjia2.png`…），
  贴图文件名 = atlas 页面引用名原样。
- live2d 为**烘焙式 Cubism prefab**：`moc3` 从 `CubismMoc` 组件原始字节提取；`model3.json`
  原包没有，运行时由 `core/live2d.py` 组装最小结构；贴图名 = m_Name（`texture_00`…）。
- painting 为**大图 + Sprite 切片**：按 `Sprite.m_RD.textureRect` 从 Texture2D 裁出内容区
  （裁掉边缘透明 padding，保留 alpha），不做 Mesh 重组；输出到 `illust/`。
- `names/azurlane.json`（characters/skins，同 IdleAngels 语义）待填充中文，无映射用英文 id。

## 输出结构（棕色尘埃2，2026-09 参考程序移植完成）

```
out_root/browndust2/
  spine/character/<角色>/<皮肤>/<基名>.atlas|.skel|<贴图>.png   ← 角色战斗立绘
  spine/interaction|light_novel_talk|npc/<角色>/[<皮肤>/]<基名>... ← 互动/轻小说/npc
  spine/special_animation|miscellaneous/                        ← 特殊动画/杂项
  ui/costume_face|costume_icon|costume_skill_face|skill_icons|
     speech_bubble_faces|wallpapers|skill_cutscene_background/<基名>.png
  chibis/<角色>/<皮肤>/<帧>.png                                  ← 小人帧动画贴图
```

- 角色/皮肤来自 `names/browndust2.json`（characters/skins 两表），值沿用官方英文
  （BD2 无中文译名）；查不到回退英文 id（皮肤=哨兵 `默认` 省略层级）。
- 资产归类与命名规则移植自**参考程序** `postExtraction.py`（分类正则 / `getMappingId` /
  `mapCharacterSpines` 等的 naming；含硬编码修补：`char101601→char060401`、
  `char061092_A` 去尾、`npc300501`(Loen) 提升为角色 `char003201`、skill_cutscene 黑名单、
  costume_icon 尺寸/截断、speech_bubble_faces 黑名单、`fixAtlasFiles` 贴图引用改写）。
- **spine**：一个 bundle 可含多个角色（illustspine 全家桶），按资产名逐模型归类，
  复用 `core/spine.py` 组装三件套；**painting**：离散贴图按名归入 ui/* 与 chibis/。
- 来源地目录（完整游戏资源）虚拟：CLI `--source <目录> --filter <关键词>` 会按
  readableName 关键词把匹配 bundle 的 `Shared/<b>/<h>/__data` 复制到 `--input`，
  再正常解包（`core/catalog.py` + `sync_from_source`）。

## 命名规则 v3（IdleAngels，用户拍板 2026-09）

**三名字来源**：bundle 文件名（目录名，权威）/ m_Name（Unity 资源对象名，真实角色 id）/ 中文（仅索引）。

- m_Name = **`[人物核心] + [皮肤成分]`**，皮肤成分可空（空 = 本体）。
- 品质档（`IR` `MR` `MR+` `UR` `UR+` `SSR` `SSR+`）**按原字母显示**；服装/节日译中文；变体字母（`A/B/C/S/H`、`V1/V3/V4`）、**数字伴生皮肤保留原样**（`sn1`→`少女狮子-1`）。
- 星级口诀（用户口述，仅参考不参与逻辑）：`SSR+ UR UR+ MR IR`；新人物一般 `MR` 即本体，有些女神 `SSR+` 为本体。

**皮肤成分词表**：

| 类别 | 成分 | 显示 | 示例 |
| --- | --- | --- | --- |
| 品质（原字母） | `IR` `MR` `MR+` `UR` `UR+` `SSR` `SSR+` | 原字母 | `spzir`→水瓶座-IR |
| 服装 | `np` `/` `nvpu` | 女仆 | `spznp`→水瓶座-女仆 |
| 服装 | `muyu` `/` `my` | 沐浴 | `juxiezuomuyu`→巨蟹座-沐浴 |
| 服装 | `hunsha` | 婚纱 | `weinasihunsha`→维纳斯-婚纱 |
| 服装 | `qiujin` `/` `qj` | 囚禁（缚神系列） | `fuxiqiujin`→伏羲-囚禁 |
| 服装 | `shatan` | 沙滩 | `MiJiaLeV1shatan` |
| 服装 | `sdj` | 待确认（`mdssdj`/`mlsdj`） | — |
| 节日 | `duanwu` `shengdan` `wanshengji` `chunjie` `xinnian` `zhounianqing` `ganenjie` | 端午/圣诞/万圣节/春节/新年/周年庆/感恩节 | — |
| 变体（原样） | `A/B/C/S/H`、`V1/V3/V4` | 原样 | `jialiA`→-A |
| 数字伴生 | `0/1/2...` | 保留数字 | `sn1`→少女狮子-1 |

## 命名规则（names/*.json）

```json
{
  "characters": { "<英文id>": { "cn": "中文角色名" } },
  "skins":      { "<皮肤key>": { "char": "<characters键>", "cn": "中文皮肤名" } }
}
```

- 键字符集：小写字母、数字、下划线（匹配 `resolve_identity._canonical_id`）。
- 无映射时目录名 = 英文 id 原样，皮肤 = 哨兵 `默认`（省略层级）。

### IdleAngels 名字解析结论（2026-09 全量扫描）

- **角色 id ≠ 文件名**。文件名 `spine_<bundle>_<后缀>.ab` 的缩写（如 `spz`）只是 bundle 名；**真实角色 id 来自 bundle 内 TextAsset 的 `m_Name`**（如 `spzir`），多为**拼音**（`aruisi`=阿瑞斯、`shouniang_shizi`=少女·狮子座、`panduolai`=潘多拉）。
- `characters` 键 = m_Name 去掉 `.atlas/.skel` 后的小写规范化（`fuxiir`、`juxiezuoir`、`athenassr`）。
- 后缀表（皮肤/品质标记，`characters` 已按角色归并）：`IR/MR/UR/SSR/C(A/B/S/H)`=品质档，`nvpu`=女仆、`hunsha`=婚纱、`qiujin`=囚禁、`muyu`=沐浴、`shatan`=沙滩、`duanwu`=端午、`shengdan`=圣诞、`wanshengji`=万圣节、`chunjie`=春节、`zhounianqing`=周年庆、`qkjs/qj`=春节/节日变体。
- 已验证命名线索：`luxifair`=路西法（m_Name 实锤）、`shouniang_shizi` 里自带"少女"前缀，"少女·星座"是一类特殊角色。
- **未映射 = 确定性不足**（212 个）：统一纯数字 `NN_A/B` 系（npc 皮肤，无角色名）；`jiali`、`shenqinger`、`beimihu`、`zhirinvzun`、`newYZ`、`UR+` 等暂无法确认，留空（输出用英文 id）。用户校正时直接改/补 `characters` 即可。
- 生成方式：读全部 `spine_*.ab` 取 TextAsset m_Name → 拼音翻译成表（`scan_all_names.py` 思路，未入库）。

## 增量语义（StateStore）

- 基线键：bundle 相对输入目录的 posix 路径 → 内容 **MD5**。
- 每个记录还存 `artifacts[]`（该 bundle 产出的文件相对列表），用于审计/排障。
- `--force` 会全量重跑并覆盖状态与文件。
- 状态文件写盘 = 临时文件 + `replace`，防半截。

## 代码约定

- 类型注解 `from __future__ import annotations`；docstring 中文。
- 包/模块命名：全小写下划线；常量大写。
- 适配器惰性注册（`games/__init__.py` `_REGISTRY`），避免 import 时拉起 UnityPy。
- `env.objects` 先物化 `list(...)` 再遍历（防御生成器语义差异）。
- TextAsset 二进制统一走 `_text_asset_bytes`（surrogateescape）。
- 贴图导出用 `PNG, optimize=True`；I;16 先转 L。

## 踩坑记录（Bug 档案）

1. **TextAsset 二进制 → surrogate str**：直接 `bytes(m_Script)` 抛 `TypeError`，被静默吞掉 → 骨架表为空。
   修：`str.encode("utf-8","surrogateescape")`。
2. **大小写失配**：角色名含大写（`luxifaIR`），`引用名.lower()` 与保留大小写的贴图键对不上。
   修：大小写不敏感匹配，且输出文件名用 atlas 引用原名。
3. **同名 TextAsset 用 dict 当键**：m_Name 相同（`luxifaIR.atlas`×2）→ 只留一套。
   修：收集成 list，按 `_asset_stem` 分组，变体全保留。
4. **多套同名模型交叉配错**：身体骨架配了魔法贴图集 → 预览器打不开。
   修：`_pair_sets` 按区域名与骨架 token 重叠度（cov=1.00 精确命中）配对。
5. **同名贴图按名去重**：两张不同的 `luxifaIR.png` 剩一张。
   修：`_texture_plan` 按 `path_id` 存全部，Material 链精确指配。
6. **`artifact_in` 缩进被顶格**：手改导致整段方法移出类（AttributeError: no 'iter_bundles'）。
   修：缩进回到类内。教训：改 Python 类方法用最小 diff。
7. **去重列表推导写反**：`a if (a in seen) or seen.add(a)` 把首现元素全丢。
   修：显式 for 循环。
8. **BD2 版本头被抹，误改头部字节**：头版本串是 `string_to_null`（无长度前缀）且位置/长度
   对不上 v7/v8 len-prefixed 假设，直接替换 → 破坏头对齐 → **LZ4 解压报 Error code: 8**。
   修：改走 UnityPy 官方机制 `UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.22f1"`
   （`BundleReader._fallback_version()` 上下文管理器，打开期间设置并还原）。
   教训：改投 UnityPy 官方配置项，别手工改格式字节。
9. **单遍扫描 Atlas/Material 链只配到第一张贴图**：`_texture_plan` 遇 `_Atlas` MonoBehaviour
   时 `break` 只取第一个见过的 Material → 多页 atlas 所有页全配成同一张
   （碧蓝 `telafaerjia` 5 页内容各异却全同页 1）。
   修：两遍扫描——先收 Texture2D 与原 Material 链，再解析 Atlas 的 `materials[]`。
10. **遍历顺序依赖隐蔽坑**：单遍时 Atlas MonoBehaviour 可能**先于**其 Material 出现，
    只收集到"恰好已见过的 Material"（telafaerjia 只剩第 4 个），与上一坑互为变体。
    修：两遍扫描一并解决。多页 atlas 的 `atlas_to_textures` = atlas_pid → [tex_pid,...]，
    页面顺序 = `materials[]` 顺序。
11. **Live2D 不是 TextAsset 拼接**（碧蓝 live2d 样本）：全 bundle 是烘焙式 Cubism prefab
    （ArtMesh GameObject + CubismRenderer/Drawable），**没有原生 model3.json**；
    moc3 是内嵌在 `CubismMoc` MonoBehaviour 序列化字节里的二进制
    （从 `MOC3` 魔数起一直延伸到对象末尾，头部 `MOC3`+u32 版本+信息块偏移表，v4/v5 均此）。
    修：`core/live2d.py` 从 CubismMoc 原始数据找 `MOC3` 提取，physics3 取 TextAsset，
    贴图取 Texture2D，`model3.json` 自行组装最小结构（Groups/HitAreas 缺数据置空，官方查看器可加载）。
    教训：烘焙式 Cubism 模型的本体数据在 MonoBehaviour 的**原始序列化字节**里，别找 TextAsset。
12. **painting 切片别把 padding 一起导出**（碧蓝 painting 样本）：Texture2D 是带边缘填充的大图，
    直接整图输出会带一圈透明/杂边；且 Sprite 的 `textureRect` 是**左下原点**（Unity UV 系），
    转 PIL 左上原点要 y 翻转：`top = 纹高 - (y+h)`, `bottom = 纹高 - y`。
    修：`core/painting.py` 按 `Sprite.m_RD.textureRect` 裁切并 clamp 越界；同 bundle 同名 Sprite
    （如 haitian 的两张 1790/1792 贴图）自动 `_2/_3` 编号。贪心教训：样本里"一个 bundle 一张图"
    不一定真，先数 Sprite 数量再写去重。
13. **BD2 资产名无扩展名，正则要对"文件名"匹配**：UnityPy 的 `Texture2D.m_Name`（如
    `Char060302_Idle_BR_01`）**不带 `.png`**，而参考程序正则是对"解包后文件名"（含后缀）写的；
    `re.match(pattern, m_Name)` 直接不命中。修：匹配前补上后缀 `f"{name}.png"`。
14. **BD2 spine 资产名带后缀，映射 key 不能带**：TextAsset `m_Name` 带 `.atlas/.skel`
    （`char003892.atlas`），直接把整名丢进 `getMappingId` 会让 key 变成 `char003892.atlas`,
    names 表查不中 → 目录退化成 `spine/character/char003892.atlas/`。修：正则匹配用全名，
    映射 key 用去后缀的 stem（参考程序对 `filePath.stem` 做 `getMappingId`）。

## 环境备忘

- 解释器：`E:\Programs\Python\Python313\python.exe`（仓库内直接 `python` 可用）。
- 依赖：`UnityPy==1.25.3`、`Pillow`（numpy 顺带装）。
- PowerShell 5.1：串联用 `;` / `if ($?)`；路径含空格加引号；中文日志显示乱码是 GBK 控制台，文件本身 UTF-8。