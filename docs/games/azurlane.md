# 碧蓝航线（AzurLane）解包指南

> 状态：🕐 待实现（适配器 stub）。拿到第一个样本后按本文档流程验证。

## 一、游戏与资源概况

| 项目 | 内容 |
| --- | --- |
| 资源目录 | `AssetBundles/` 下按 **painting（立绘）/ live2d / spinepainting** 等分类 |
| 引擎 | Unity |
| 内容物 | 立绘（painting）、Live2D（Cubism3）、Spine 3.8 |
| 资源后缀 | `.ab` |

## 二、解包流程（待样本后填充）

```powershell
python -m waifu_unpack azurlane --input <资源目录> --out output --types spine,live2d,painting --progress
```

1. 把资源文件夹拷到 `samples/azurlane/`。
2. 扫描 `painting` 分类：提取切片 PNG（用户拍板：**只导切片，不做 Mesh 重组**；分辨率取游戏内原分辨率）。
3. 扫描 `live2d` 分类：Cubism3，`moc3/model3.json` 解剖后复用 `core/live2d.py`。
4. 扫描 `spinepainting` 分类：Spine 3.8，复用 `core/spine.py`（与 IA 同构）。

## 三、注意事项

1. **立绘切片**：`painting` = Mesh + Texture2D 切片，导出文件名需利用 atlas/Mesh 里的原始切片名。
2. **Live2D 待解剖**：`.bytes` 常见在 MonoBehaviour 里，需确认 `moc3/model3/physics3/textures` 的包装位置。
3. **Spine 3.8**：与 IA 结构相近（atlas/skel 是 TextAsset），可直接复用配对/贴图链逻辑。
4. 命名：角色名/皮肤名大概率有规则目录名，heroes 表可按 `names/azurlane.json`（待建）维护。

## 四、当前缺口

- 无样本（`samples/azurlane/` 空）。
- 适配器只声明接口，`extract` 抛 `NotImplementedError`。