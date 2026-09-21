# 棕色尘埃2（Brown Dust 2）✅ 端到端已通

> 状态：适配器已按参考程序逻辑重写完成，`spine` / `painting`（含 skill_icons）已用真实样本
> 全部分类验证。格式研究结论见 `game-research.md`「棕色尘埃2」节。

## 资源概况

- 安卓包 `com.neowizgames.browndust2`，Unity 引擎，仅 Spine 4.1，无 Live2D。
- 本地资源是 **UnityWebRequest 缓存目录**（纯 hash 命名）：
  `Shared/<bundleName>/<hash>/__data`（`__info` 是缓存元数据，忽略）。
- 逻辑路径/大小在 `com.unity.addressables/file.json`（`bundleName ↔ readableName ↔ hash`）；
  没有 file.json 时可从 `catalog_alpha.json` 的 `m_KeyDataString` 解码出 hash 清单。
- **版本头被抹**（`5.x.x / 0.0.0`）：不要改头部字节，靠
  `UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.22f1"` 打开（已踩坑，勿重犯）。

## 分类 → 来源 bundle

samples 覆盖 20 个 bundle（下表「样本」= 已同步到 `samples/browndust2/Shared`）。
bundleName 任何改动后建议 2.（可选）按关键词重同步。

| 输出分类 | 来源 bundle（readableName） | bundleName | 大小 | 样本 |
|---|---|---|---|---|
| character / light_novel_talk / npc | `common-ui-prefabs_assets_ui/prefabs/spine/illustspine` | `555d52b64287b546d2f27172dcf19341` | 103.5MB | ✅ |
| interaction / special_animation | `common-ui-prefabs_assets_ui/prefabs/spine/illustspecial` | `8ae2977d5a837a9470decf0f02fec7be` | 416.3MB | ✅ |
| skill_cutscene（+背景容器） | `isolated-cutscene<id>-group_assets_all_<hash>` ×168 | 例 `5807e41624428dcafab4bfb2411e9e48`（061306），其余 `000101`~`103501` | 共 1485.5MB | 1 个 |
| skill_icons（跨 2 类包合并） | `common-ui-texture_assets_all` + `-group1/2/3` + `common-ui-atlas_.../bufficongui1.spriteatlasv2` + `talentbufficongui1.spriteatlasv2` | `e4bfd8efb4f7693cf22e1ce8f96777aa`、`cddfb0d8a56fd0b092a1bbb62f6f469b`、`9c536ef485f6446e41756e3ddbcf058a`、`4cf4fc12e96d4a0c5aa518e5dffd2125`、`34c85a399408faa9c8cc062baef46233`、`0b446676e4cfcc1070bb616ab91f74e8` | 共 37.4MB | ✅ |
| wallpapers | `common-idcardbgcutscene_1_assets_all` + `-group1/2/3` ×4 | `414ebb5d6516759d9e566eeba67110dd`、`d3d08abfd5ba94d97fc66f32197da80d`、`acf0c5513ac7b4b194cc44638d1f2a2d`、`3a9eb24fad290337b59eedd9bc2e7f96` | 共 130.9MB | ✅ |
| costume_icon | `common-costumeicon_l_1_assets_all` | `b9b449058afaf6d5b3a08ace06978cd6` | 2.3MB | ✅ |
| costume_face | `common-illustinventory_1_assets_all` | `6ba93b46f265d74d52be32c02be4896d` | 5.1MB | ✅ |
| costume_skill_face | `common-illustskillcard_1_assets_all` | `4d4358296349a2fa26867045526c17c2` | 5.2MB | ✅ |
| speech_bubble_faces | `common-faceillust_1_assets_faceillust_1` | `f29c853e9884f7015d9a5071a7eae1a2` | 18.6MB | ✅ |
| chibis | `common-spritetexture...` ×271（myroom 每角色 1 个 + `-group1~7_assets_all` + `pack*/spritetexture`） | 例 group1 `c891630e13eef494325406c23ea1f637`、`e1be2c29297b33edcb5a474fda54e965` | 共 114.9MB | 2 个 |
| censorship（`_c` 资产被丢弃） | `common-censorship_assets_all_66901841a502f145829267cf2bd1c62d` | `d12230b913d2721c1738ce8f446aa609` | 42.3MB | ✅ |
| interactionvoice（未处理） | `common-interactionvoice_assets_bundleinteractionvoice/interaction_char<id>.bytes` ×21 | 例 `052ae1f9152ba047c621966efa2ab7b2` | 共 33.9MB | — |

> 主线骨架就 3 个主包：`illustspine`（角色 103.5MB）、`illustspecial`（互动/演出 416.3MB）、
> `isolated-cutscene`×168（技能演出 1485.5MB）。其余多为单个小包或 `spritetexture` 系列。

## 前置条件

全量/增量处理的必要条件：

1. **源目录**：完整游戏缓存目录（如 `F:\live2d\棕色尘埃2`），须含
   `Shared/<bundleName>/<hash>/__data` 与 `com.unity.addressables/file.json`（2023 条）。
   部分 bundle 本地缺目录时无法同步（2026 版源盘缺 193 个，主要即小包；主类 170 个全在）。
2. **磁盘空间**：主类三包同步需 ~2GB，spine 输出另需 ~2.9GB；全部分类则按需再加。
3. **目录匹配**：`samples/browndust2/Shared` 下 bundle 目录名 = file.json 的 `bundleName`
   （个别 bundle 的 Shared 目录名 ≠ bundleName，但主类三包实测一致）。
4. **增量语义**：状态按 bundle 内容 digest 记录于 `output/browndust2/.waifu-unpack-state.json`，
   未变化自动跳过；`--types`/关键词变化不会触发重跑，需 `--force`。
5. **skill_icons 特例**：`common-ui-texture` 与 `bufficongui` 必须**同步全组**，
   缺组员则 Sprite 图集解析失败（见下）。

## 解包流程

```powershell
# 1.（可选）从完整游戏资源按关键词同步样本（--source + --filter 必须连用）
#    关键词匹配 file.json 的 readableName；已存在且大小一致则跳过
$env:PYTHONIOENCODING="utf-8"
python -m waifu_unpack browndust2 --source "F:\live2d\棕色尘埃2" `
  --filter coolspine --input samples\browndust2 --out output

# 2. 解包（spine / painting；增量，未变化跳过）
python -m waifu_unpack browndust2 --input samples\browndust2 --out output --types spine,painting

# 3. --dry-run 查看还剩哪些待处理
python -m waifu_unpack browndust2 --input samples\browndust2 --out output --types spine,painting --dry-run
```

筛选关键词示例：`coolspine`、`spine/illustspine`、`isolated-cutscene061306`、
`common-spritetexture-myroom`、`spine/illustspecial`、`idcardbgcutscene`、
`costumeicon_l`、`illustskillcard`、`illustinventory`、`faceillust`、
`common-ui-texture`、`bufficongui`（**后两个必须同步全组**，见下）。可多个关键词逗号分隔。

## 输出结构

```
output/browndust2/
  spine/character/<角色>/<皮肤>/<基名>.atlas|.skel|<贴图>.png   ← 角色战斗立绘
  spine/interaction|light_novel_talk|npc/<角色>/[<皮肤>/]...   ← 互动/轻小说/npc
  spine/skill_cutscene/<角色>/<皮肤>[/<layer>]/               ← 技能演出 cutscene_char*
  spine/special_animation|miscellaneous/<基名>...             ← 特殊动画/杂项（平铺小写）
  ui/costume_face|costume_icon|costume_skill_face|skill_icons|
     speech_bubble_faces|wallpapers|skill_cutscene_background/<名>.png
  chibis/<角色>/<皮肤>/<帧>.png                                 ← 小人帧动画贴图
```

- 角色/皮肤目录名 = `names/browndust2.json` 值（官方英文，如 `Dalvi/Tricky_Lover`）；
  查不到回退英文 id（皮肤=哨兵 `默认`，省略层级）。
- 同一个 spine bundle 可含**多个角色**（illustspine 全家桶），按资产名逐模型归类，
  复用 `core/spine.py`；贴图精确配对走 Material 链。
- **注意资产名**：Texture2D 名不带 `.png`（分类正则按 `{name}.png` 匹配），
  TextAsset 名带 `.atlas/.skel`（映射 key 用去后缀 stem）。
- `special_animation` / `miscellaneous`：参考 mapSpecialAnimatioSpines /
  mapMiscellaneousSpines 无角色映射，**整类平铺** `spine/<cat>/` 且文件名小写。
- `skill_cutscene`：参考 mapSkillCutsceneSpines 在解包树父目录名 >20 字符时并入子目录；
  UnityPy 侧取 atlas 的 container 路径（`Assets/.../<layer>/<file>`）最后一段目录名为 layer。
- **skill_icons 是跨 bundle 分组**：`common-ui-texture_*` 里的 skillicon Sprite 引用的
  图集纹理在 `common-ui-atlas.../bufficongui1.spriteatlasv2`。单一 bundle 打开 Sprite.image
  报 `cab-... not found`；`_extract_skill_icons` 把 readableName 含 `common-ui-texture` 或
  `bufficongui` 的全部 bundle 读进同一 Environment 再抽（结果按 input_dir 缓存）。
  ⚠️ 若只同步了 texture 包没同步 bufficongui 组员，skill_icons 会缺失。

## 命名规则

`names/browndust2.json` 是 characters/skins 两表（characters 153 / skins 395），
由参考程序 mapping.json 5 表转换：含 `\` 的 key（资产 id）进 skins（`char`=角色名小写），
纯角色名进 characters；键/值均不区分大小写，key 小写规范化。
皮肤 key 映射示例：`char000101 → Lathel / Herb_Tracker`；`char060302 → Alec / Sword_Breaker`。

## 注意事项 / 已知坑

- 立绘是**整图**（非 Sprite 切片，不同于碧蓝）；无 Live2D。
- 分类归并的正则与硬编码修补均移植自参考程序（`char101601→char060401`、
  `char061092_A` 去尾、`npc300501`(Loen)→角色 `char003201`、costume_icon 尺寸/截断、
  speech_bubble_faces 黑名单、`fixAtlasFiles` 贴图引用改写、skill_cutscene 黑名单、
  avatarbodyaccessory 白名单、Censorship `_c` 资产的丢弃——参考 filterPaths 同样丢弃）。
- 增量状态、`--dry-run` 语义等同其它游戏（见 conventions.md）。

## 验证方法

- 样本 187 个 bundle。**主类三包（170 个）已全量解包**：扫描 187 / 处理 167 /
  跳过 20（此前样本）/ 失败 0，耗时 ~22min；spine 输出 7147 文件，~2.9GB：
  - `spine/character` 42 组（33 角色）；`spine/interaction` 14、
    `light_novel_talk` 6、`npc` 8、`special_animation` 15；
  - `spine/skill_cutscene` **171 组（68 角色）**，覆盖 `isolated-cutscene`×168。
- 分类抽样（此前 20 样本阶段实测，0 失败）：
  - interaction 160 / light_novel_talk 18 / npc 24 / skill_cutscene 8 /
    special_animation 60（illustspecial 包）；
  - ui/costume_face 206 / costume_icon 203 / costume_skill_face 206 /
    skill_cutscene_background 2（Skillbackground_1 container 段）/ speech_bubble_faces 1967 /
    wallpapers 306；**ui/skill_icons 1107 张**（108~112²，0 空文件）；
  - chibis 1518 帧。
- 拿输出 `spine/character/Dalvi/Tricky_Lover/char061306.atlas|.skel|.png` 丢进 Spine 预览器即可验证。