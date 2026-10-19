# 永恒追问 · Eternal Questioning

> 一支用代码逐帧渲染的歌词 PV：每一帧都是时间 `t` 的纯函数。没有剪辑软件，没有手工关键帧。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

- 成片：1920×1080 / 24 fps / 4:22.8（262.8 s）
- 画面素材：大都会艺术博物馆 Open Access 公版版画 + AI 生成的铜版刻线人物层
- 字体：思源宋体 SC（Noto Serif SC）、Georgia

---

## 一、这是什么

这不是“用软件剪出来”的 MV，而是一个**可复现的渲染器**：

```
t ──► 找到当前 SHOT（一段机位）──► 逐条 CUE 求值 ──► 后期 ──► 一帧 RGB
```

一部片子的全部设计都写成数据（`shots_v19.json`）：机位、场域状态、中间层、每个字的字号/落位/出现时刻、后期强度。改一个数，重渲一遍，成片就变。

### 已实现的能力

| 模块 | 说明 |
|---|---|
| 2.5D 摄像机 | 真实针孔模型：`z` 深度、层间视差、景深（aperture/focus）、滚转 |
| 每句一个机位 | `beats`：在句首落定，句内只做慢推；`accents` 短脉冲重音 |
| 文字排版 | 每个字独立时间与字号/落位/旋转；整块 + 单字两级安全区夹取，永不越界 |
| 场域翻转 | 第二句首字后 0.75 s 渐变到 mosaic / light / ink 变体（全片 33 处） |
| 中间层 | 9 位人像各出现一次，`yaw` 透视转卡，第二句被“照白”或“压暗” |
| 后期节点 | scanline / glitch / 溢光按段落给，不再是全片一个强度 |
| 审计 | `audit.py` 30+ 条硬规则（R01–R36）：转场、机位、文字、图层、场域 |

---

## 二、流水线

```
歌词 ─► whisper ASR 对时 ─► 文字分镜表（每句落位/逐字规格）
     ─► apply_textboard2.py  ─► shots_v19.json
     ─► pv.build frames      ─► 成片 mp4
```

| 脚本 | 作用 |
|---|---|
| `_build/diag.py` | 从 mp3 标签取歌词 |
| `_build/align.py` / `align_lines.py` | 逐字对时（ASR + 字数一一对应） |
| `_build/apply_textboard2.py` | 分镜表 → cue 参数（字号/落位/逐字/机位/场域） |
| `_build/finalize_v19.py` | 定稿：人像瘦身、透视转卡、场域翻面、景深 |
| `_build/beat.py` | BPM / 拍点估计（谱通量 + 自相关） |
| `_build/pv/` | 渲染引擎（camera / puppet / block / scene / link / gpu） |
| `_build/audit.py` | 规则审计，退出码 0 = 全过 |

---

## 三、目录

```
_build/pv/            渲染引擎
_build/*.py           对齐、排版、合成、审计
_build/shots_v19.json 全片数据（机位/文字/图层/后期）
PV_分镜表_v19.md      定稿分镜
PV_文字分镜表.md      逐字排版设计
PV_参考片逐帧研究.md  参考片六场逐帧研究
PV_审计规则.md        规则条文
```

---

## 四、怎么跑

```powershell
cd _build

# 1) 生成全片数据
python apply_textboard2.py
python finalize_v19.py

# 2) 审计（0 FAIL 才渲）
python audit.py --shots shots_v19.json

# 3) 抽静帧看构图 / 字号
python -m pv.build stills --shots shots_v19.json --times 20,90,158,250

# 4) 全片（NVENC；GPU 后期会自动启用）
python -m pv.build frames --shots shots_v19.json --start 0 --end 6307 `
  --out ../out/eternal_questioning_1080p.mp4 --workers 8 --crf 20
```

依赖：Python 3.12+、NumPy、Pillow、OpenCV、SciPy、ffmpeg（NVENC 可选）、cupy（可选，GPU 后期）。

> **素材不在仓库里**：`_build/assets/`、`assets/met_full/`、音频与成片都在 `.gitignore` 中。
> 自行渲染需要先下载 MET 公版版画，并用 `_build/gen.mjs` 重新生成 AI 人物层。

---

## 五、素材与许可

- 版画：The Metropolitan Museum of Art Open Access（Public Domain）
- 字体：Noto Serif SC（SIL OFL 1.1）、Georgia（系统字体）
- 音乐 / 歌词：Suno 生成，权利归作者
- AI 人物层：由 gpt-image 系列模型生成

---

## 六、致谢

- 参考项目：[**MisakaZentai/world-execute-me-dsh-pv**](https://github.com/MisakaZentai/world-execute-me-dsh-pv)
- 成片发布：[Bilibili · BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)
- 参考片：[《过期童话》](https://www.bilibili.com/video/BV1xCai6aE9g/)

---

## License

GNU General Public License v3.0 —— 见 [LICENSE](LICENSE)。

---

# Eternal Questioning

> A lyric PV rendered frame by frame in code. Every frame is a pure function of time `t` — no NLE, no hand-made keyframes.

- Output: 1920×1080 / 24 fps / 262.8 s
- Plates: The Met Open Access engravings + AI-generated engraved portrait layers
- Type: Noto Serif SC, Georgia

## What it is

```
t ──► current SHOT ──► evaluate CUEs ──► post ──► one RGB frame
```

All direction lives in data (`shots_v19.json`): camera, environment state, middle layer, per-glyph size/position/timing, post strength. Change a number, re-render, and the film changes.

**Capabilities**

- 2.5D pinhole camera: depth `z`, layer parallax, depth of field (aperture/focus), roll
- One camera pose per lyric line (`beats`) plus short `accents` on the downbeat
- Typography as a layout layer: per-glyph timing and size, two-stage safe-area clamping
- Environment flip inside every two-line shot (mosaic / light / ink, 33 times)
- Nine portraits, each once; `yaw` perspective card turn, then washed out or dimmed
- Section-based post nodes (scanline / glitch / halation)
- 30+ machine-checkable rules in `audit.py` (R01–R36)

## Pipeline

```
lyrics ─► Whisper ASR alignment ─► text storyboard ─► apply_textboard2.py
       ─► shots_v19.json ─► pv.build frames ─► mp4
```

## Render

```powershell
cd _build
python apply_textboard2.py
python finalize_v19.py
python audit.py --shots shots_v19.json
python -m pv.build frames --shots shots_v19.json --start 0 --end 6307 `
  --out ../out/eternal_questioning_1080p.mp4 --workers 8 --crf 20
```

Requirements: Python 3.12+, NumPy, Pillow, OpenCV, SciPy, ffmpeg (NVENC optional), cupy (optional).

> **Assets are not in this repository.** `_build/assets/`, `assets/met_full/`, audio and renders are gitignored. To render, fetch the Met public-domain plates and regenerate the AI portrait layers with `_build/gen.mjs`.

## Credits

- Reference project: [**MisakaZentai/world-execute-me-dsh-pv**](https://github.com/MisakaZentai/world-execute-me-dsh-pv)
- Release: [Bilibili · BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)
- Plates: The Met Open Access (public domain); Font: Noto Serif SC (OFL); Music/lyrics: Suno; AI layers: gpt-image

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
