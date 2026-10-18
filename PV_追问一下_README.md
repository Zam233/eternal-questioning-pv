# 《永恒追问》PV · 制作说明

> 曲名《永恒追问》（工程文件名仍沿用 `追问一下.mp3`，不重命名音频）。

一支用代码逐帧渲染的**图版书式**歌词 MV —— 每一帧都是歌曲时间 `t` 的纯函数，不用剪辑软件，没有手工关键帧。

- 成片：`out/永恒追问_PV_1080p.mp4`（1920×1080 / 24fps / H.264 NVENC + AAC）
- 歌曲：`追问一下.mp3`（Suno 生成，4:22.8）
- 参考片：`过期童话.mp4`（逐帧拆解见下文第四节）
- 画面素材：**大都会艺术博物馆 Open Access 公版版画 71 张**（Public Domain）
- 字体：思源宋体 SC（Noto Serif SC，可变字体 Black 字重）、Georgia

---

## 一、整体思路

参考 [MisakaZentai/world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv)：不做时间轴剪辑，写一个"时间 → 画面"的函数。

```
t  ──►  找到当前 SHOT（一段固定机位）──► 逐条 CUE 求值 ──► 后期 ──► 一帧 RGB
```

**关键结构**（照参考片拆出来的）：

- 一个 **SHOT** 只管机位，通常持续 4–5 秒（一整句 7+7 的乐句）；
- 机位不动、或只做极慢的推拉，「**变的是字**」—— 一个 SHOT 里挂着好几条 **CUE**；
- **没有底部字幕条**：歌词本身就是动画，每个字落在它被唱出来的那一刻。

## 二、流水线

| 步骤 | 脚本 | 产物 |
|---|---|---|
| 1. 取歌词 | `_build/diag.py` | `lyrics_raw.txt`（Suno 写在 mp3 的 `lyrics-eng` 标签里） |
| 2. 对时间轴 | `_build/align.py` → `_build/align_lines.py` | `asr.json` → `lines.json`（**逐字**起止时间） |
| 3. 收素材 | `_build/fetch_met.mjs` | `assets/met_full/<主题>/<id>.jpg` |
| 4. 排版设计 | `_build/make_shots.py` | `shots.json`（46 个 SHOT / 143 条 CUE） |
| 5. 渲染出片 | `python -m pv.build frames --shots shots.json` | `out/永恒追问_PV_1080p.mp4` |

### 歌词对时

`openai-whisper`（small，CPU）转录，把 Suno 原文当 `initial_prompt` 喂进去。
实测**已知字数与 ASR 字数完全相等（583 = 583）**，故直接按字符序号一一对应取词级时间戳 ——
比模糊对齐稳得多，每句稳定落在 1.9–2.1 秒。逐字时间再传给 CUE，字就一个个跟着唱腔落位。

## 三、画面怎么搭出来的

### 一个 SHOT 里的图层（从前到后）

1. **图版**（plate）—— 公版版画，做百分位归一化 + 均值归一到 0.46 + **五套双色调调色板**（sepia / rust / steel / gold / cold / blood / ivory）
2. **纸纹**（paper）—— 低频噪声缓慢漂移
3. **光带**（beam）—— 斜切高斯高光
4. **远景巨字**（ghost）—— 极低对比度、反向视差
5. **主字 CUE**（type cues）—— 真正的内容层
6. **前景遮挡**（foreground）—— 见下
7. **图版编号 / 拉丁小标 / 概念词**（caption、anno）—— 制造书页的信息层次

### 前景遮挡：让字从版画后面穿过去

这是参考片最有效的"层次"手法。做法是把版画的同一区域**再画一次盖在字上面**，
但用**墨色的亮度做 alpha**（`alpha = ((0.62 - lum)/0.62)^1.5`）——
于是只有深色的线条和阴影挡住字，亮处仍是透明的。字看起来就"穿过"了版画。

### 排版系统：10 个锚点 + 长短句拆块

- 短句（≤5 字）整块放在池子里的某个锚点：`center / low_left / up_right / right_v / left_v / up_center / low_center / fill_low …`
- 长句（7 字）**拆成两块**（4+3 或 3+4），分别落在**互补锚点**上：
  `up_left + low_right`、`low_left + up_right`、`up_center + low_center`；
  两半各自跟着自己的唱词出现 —— 于是同一句话在画面上是对角生长的。
- 每块字号按 `可用宽度 / 字数` 反算，并在合成时再做一次安全区夹取，永不切边。

### 字动画（5 种）

`rise`（下沉浮上）/ `punch`（放大回弹）/ `shatter`（随机抖动）/ `flip`（小角度翻入）/ 竖排整块。

### 后期

- **故障**：随机横向切片位移 + 反色块；`amt>0.58` 叠加 RGB 通道错位
- **扫描线 / 颗粒 / 暗角**：三层固定叠加
- 图版编号与概念词**在故障之后**画，保证再乱也读得清

## 四、从参考片拆出来的规律

对 `过期童话.mp4` 每 2 秒抽 1 帧做宏观图，再对 40–48 秒每 5 帧抽 1 帧做微观图，得到：

| 观察 | 本片的对应做法 |
|---|---|
| 一个机位能撑 4–5 秒，中间只换字 | SHOT = 一个乐句，CUE 数条 |
| 字经常很小、贴着画面边角 | 10 个锚点里 6 个是边角位 |
| 字被前景物体遮挡（十字架挡住字） | `foreground()` 亮度键遮挡 |
| 一句话拆成两半、分散在画面两处 | `SPLIT_PAIRS` 互补锚点 |
| 段落之间冷暖色骤变（灰马赛克 → 暖褐油画） | 七套调色板按段落轮换 |
| 会有几秒完全没有字的空镜 | 间奏 SHOT / `interlude` |

## 五、重新渲染

```powershell
cd "K:\5A大作\_build"

# 抽静帧验片
python -m pv.build stills --shots shots.json --times 26,64,152,200

# 全片（默认走 NVENC）
python -m pv.build frames --shots shots.json --workers 6 --crf 20
```

- **GPU**：RTX 4070 Ti，默认 `h264_nvenc -preset p5 -rc vbr -cq <crf>`。
  想回到 CPU 编码：`$env:PV_CODEC="x264"`。
- **沙箱坑**：本机禁止命名管道，`multiprocessing.Pool` 会直接 `WinError 5`，
  所以渲染走 `ThreadPoolExecutor` + 单进程写 ffmpeg 管道（6 线程约 8–9 fps，全片约 12 分钟）。

## 六、换歌只要改三处

1. `pv/config.py` 的 `AUDIO`、`DUR`；
2. `make_shots.py` 的 `DESIGN`（每句 → 素材 / 拉丁小标 / 图版说明）；
3. `make_shots.py` 的 `SECTIONS`（每段的调色板、机位、故障强度、锚点池、动画）。

## 七、素材与许可

- 版画：The Metropolitan Museum of Art Open Access，**Public Domain**
- 字体：Noto Serif SC（SIL OFL 1.1）、Georgia（系统字体）
- 代码：自用，可随意改
- 歌词与音乐：Suno 生成，权利归作者

代码由 AI 协助完成，审美取舍与逐镜设计由作者决定。
