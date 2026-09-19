# IdleAngels（爱神故事）解包指南

> 状态：✅ 端到端已通。本文档对应第 1 款游戏专用流程与注意事项。

## 一、游戏与资源概况

| 项目 | 内容 |
| --- | --- |
| 安卓包名 | `com.mujoysg.hxbb` |
| 引擎 | Unity（外层壳 2017.4.16f1，内层内容 2021.3.58f1） |
| 内容物 | **纯 Spine**，无 Live2D |
| 资源后缀 | `.ab`（`spine_*.ab`） |
| 加密 | 无加密、无版本抹除；但见下方"**双层嵌套**" |

## 二、资源获取与放置

- 从手机/模拟器把最外层资源文件夹拷出，例如 `samples/idleangels/`。
- 工具递归扫描 `*.ab/.bundle/*.unity3d/*.asset/*.bytes`，无扩展名文件按魔数嗅探兜底。
- 样本规模：445 个 `spine_*.ab`，约 844MB。

## 三、解包流程（一图流）

```powershell
python -m waifu_unpack idleangels --input <资源目录> --out output --progress
```

1. 扫描输入目录，逐个打开 `.ab`（`BundleReader.open`）。
2. 提取 Spine 三件套：`atlas`（TextAsset）+ `skel`（TextAsset）+ 贴图（Texture2D）。
3. 按内容配对骨架与 atlas（人物/背景两套），贴图走 Material 链精确配对。
4. 输出到 `output/idleangels/<bundle文件名>/angel|bg/`。
5. 增量状态按 bundle MD5 记录在 `.waifu-unpack-state.json`。

## 四、输出结构

```
output/idleangels/
  spine_ars_mr/            ← 目录名 = bundle 文件名（去 .ab），永不撞名
    angel/                 ← 人物模型（区域最多的一套）
      aruisiMR.atlas      aruisiMR.skel      aruisiMR.png
    bg/                    ← 背景模型（其余套）
      aruisiMR.atlas      aruisiMR.skel      aruisiMR.png
  .waifu-unpack-state.json ← 增量状态（不算导出物）
```

要点：
- 一个 bundle 通常出**两套模型**：`angel/`（人物）与 `bg/`（背景）；只有一套时仅 `angel/`。
- 贴图文件名必须 = **atlas 第一行引用的名字**（大小写原样），否则 Spine 预览对不上。
- 相同 bundle 内多套同名 `base` 追加 `_2`、`_3`…。

## 五、命名规则（names/idleangels.json）

- **三个名字来源**：
  1. bundle 文件名缩写（`spz`）——打包标签，**非权威**，不参与命名；
  2. bundle 内 TextAsset 的 **m_Name**（如 `aruisiMR`）——权威角色 id，多为拼音；
  3. 中文展示名——仅作检索索引，运行时不入目录。
- 表结构：`characters`（m_Name → 角色中文）、`files`（bundle文件名 → `{cn, m}` 检索索引）。
- **皮肤成分**：`IR/MR/MR+/UR/UR+/SSR`（品质，原字母显示）、`np/nvpu`=女仆、`muyu`=沐浴、`hunsha`=婚纱、`qiujin`=囚禁（缚神系列）、`shatan`=沙滩、节日词（端午/圣诞/万圣节/春节/新年/周年庆/感恩节）、数字伴生皮肤保留数字。
- 星级口诀（参考）：`SSR+ UR UR+ MR IR`；新人物一般 `MR` 即本体。
- 查中文 → 文件名 → 目录：直接搜 `files` 表里 `cn` 字段。

## 六、注意事项与已知坑（务必先读）

1. **双层嵌套**：外层是空 config 壳（TextAsset `cfg_init` 内容 "bye"），真实模型在内层。
   `BundleReader` 已递归解开，无需手工处理。前置脏字节 `0x00` 也由魔数嗅探兜底。
2. **同名多套模型必按内容配对**：`luxifaIR.atlas×2`、`luxifaIR.skel×2`、`luxifaIR 贴图×2`，
   交叉配对会在 Spine 预览里报 Region not found。`SpineExport` 用 atlas 区域名与骨架 token
   重叠度贪心配对，再把区域多的一套当人物（`angel/`）。
3. **贴图 Material 链**：能精确配对就走材料链（SpineAtlasAsset → materials → `_MainTex`）；
   配不上按名兜底时，键要去掉 `.png/.jpg` 扩展名对齐 Texture2D 的 `m_Name`。
4. **同名贴图互抢**：同 bundle 多套同名贴图，名兜底会取走已被前一套用的那张。
   现在 `_match_textures` 通过 `used_pngs` 记录已占用贴图字节，角色/背景各拿各的。
5. **贴图缺失告警**：atlas 引用的贴图在 bundle 内找不到（如 `jialiB.png`）——
   贴图可能存放在独立 HD/显存包，属待办问题，不影响骨架与 atlas 导出。
6. **atlas 尺寸写 4096 但贴图 2048**：游戏默认画质降采样产物，均匀缩放正常预览，别当 bug。
7. **增量不回删**：输入里删掉 bundle，历史输出与状态保留；`--force` 才全量重跑。
8. **中文显示乱码**：Windows 控制台 GBK，日志里中文乱码不影响文件本身（UTF-8）。
9. **全量耗时**：445 个 bundle 约数十分钟，务必加 `--progress` 看进度。
10. **纯数字 npc 名**：`00_B…68_A` 这类无角色名，`files` 表留空，输出目录仍用 bundle 文件名。

## 七、命名表维护说明

- `characters` 已自动填充 204 条（从全部 bundle 的 m_Name 拼音翻译）。
- `files` 已自动生成 247 条；未映射的 bundle 留空（回退英文），用户可手工补 `cn`。
- 皮肤词表（`skins`）当前为空；如需精细皮肤中文名，按上面第五节清单补。

## 八、验证方法

- 单 bundle 冒烟：用临时目录放 1 个 `.ab`，跑 `--progress`，检查 `angel/`、`bg/` 三件套齐全。
- 用 Spine 官方编辑器/预览器对每个 `angel/`、`bg/` 目录的 `.atlas`+`.skel`+`.png` 做预览。
- 检查状态文件：`output/idleangels/.waifu-unpack-state.json`。