# 棕色尘埃2（Brown Dust 2）解包指南

> 状态：🕐 待实现（适配器 stub）。拿到第一个样本后按本文档流程验证。

## 一、游戏与资源概况

| 项目 | 内容 |
| --- | --- |
| 引擎 | Unity（**版本头被抹掉**，显示 `5.x.x 0.0.0`） |
| 内容物 | **仅 Spine 4.1**，无 Live2D；静态立绘在 illust bundle |
| 资源后缀 | `.bundle` 或本地缓存目录（全 hash 文件名） |
| 适配器配置 | `forced_unity_version = 2022.3.22f1` |

## 二、解包流程（待样本后填充）

```powershell
python -m waifu_unpack browndust2 --input <资源目录> --out output --types spine,painting --progress
```

1. 把本地缓存目录拷到 `samples/browndust2/`。
2. `BundleReader` 处理版本头被抹（`BLANKED_VERSIONS` 判据）。
3. 需要 **catalog 文件**还原 hash 文件名 → 逻辑路径/角色名。
4. Spine 4.1：复用 `core/spine.py`。
5. 立绘：确认是切片还是整图（待样本）。

## 三、注意事项

1. **版本头被抹**：版本字段在 offset 8，值 `0.0.0`；`forced_unity_version` 若解析失败可换 `2022.2.17f1`。
2. **hash 文件名 + 无 container path**：必须靠 catalog 还原身份，否则无法映射角色中文名。
3. **illust bundle**：立绘所在，确认导出形态（整图 or 切片）后再定输出结构。

## 四、当前缺口

- 无样本（`samples/browndust2/` 空）。
- 适配器只声明接口，`extract` 抛 `NotImplementedError`。