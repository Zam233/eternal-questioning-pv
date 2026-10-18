# -*- coding: utf-8 -*-
"""Build shots.json from the storyboard (PV_逐句分镜方案.md).

STORY rows are aligned 1:1 with the kept lyric lines (74 of them, in song order):
    (shot_id, kind, anchor, motion, trans_in, overrides)
Lines sharing a shot_id live inside one camera hold.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DUR = 262.80

# ---------------------------------------------------------------- design table
# lyric -> (concept, asset key, latin, caption, year)
DESIGN = {
    "有人用理念构筑": ("理念", "cave", "EIDOS", "洞喻", "前 4 世纪"),
    "名为本体的神话": ("本体", "cave", "ON", "存在", "前 5 世纪"),
    "逻各斯随波流转": ("逻各斯", "academy", "LOGOS", "学园", "前 387"),
    "直至阿卡德米亚": ("学园", "academy", "ACADEMIA", "阿卡德米亚", "前 387"),
    "洞穴里有人囚禁": ("囚禁", "cave", "SPELUNCA", "被缚者", "前 4 世纪"),
    "有人指认出虚华": ("虚华", "cave", "UMBRA", "墙上的影", "前 4 世纪"),
    "也有人饮下毒鸩": ("毒鸩", "hemlock", "PHARMAKON", "毒芹之杯", "前 399"),
    "将死生从容作答": ("从容", "socrates", "THANATOS", "临刑", "前 399"),
    "神谕中有座天城": ("天城", "celestial", "CIVITAS DEI", "上帝之城", "426"),
    "托名唤作耶和华": ("耶和华", "celestial", "DEUS", "启示", "5 世纪"),
    "有位手持信理的": ("信理", "scriptorium", "DOGMA", "抄经院", "9 世纪"),
    "托马斯意气风发": ("托马斯", "scriptorium", "THOMAS", "经院哲学", "13 世纪"),
    "唯名与唯实交锋": ("唯名", "disputation", "NOMEN", "共相之争", "12 世纪"),
    "将思辨翻覆揉轧": ("思辨", "disputation", "DIALECTICA", "经院辩证", "13 世纪"),
    "辩驳里有谁将信仰": ("信仰", "rose", "FIDES", "玫瑰窗", "13 世纪"),
    "用理性来传达": ("理性", "rose", "RATIO", "信仰寻求理解", "1078"),
    "神座在蒙昧后": ("神座", "idol", "SOLIUM", "神权", "14 世纪"),
    "渐渐崩塌": ("崩塌", "idol", "RUINA", "崩解", "15 世纪"),
    "怀疑将虚妄的幻象": ("幻象", "clockwork", "ILLUSIO", "钟摆宇宙", "17 世纪"),
    "拆下": ("拆", "clockwork", "DEPONERE", "拆去", "16 世纪"),
    "机械的眼把万物": ("机械", "clockwork", "MACHINA", "机械之眼", "17 世纪"),
    "剖析再刻画": ("剖析", "lens", "ANALYSIS", "光锥", "17 世纪"),
    "勾勒出泛神实体": ("泛神", "stars", "DEUS SIVE NATURA", "神即自然", "1677"),
    "惹世人皆惊诧": ("惊诧", "stars", "ADMIRATIO", "无限的星空", "17 世纪"),
    "于是有人用白板": ("白板", "slate", "TABULA RASA", "人心如白纸", "1690"),
    "记录属于知的萌芽": ("萌芽", "slate", "ORIGO", "知识的起源", "1690"),
    "有人把怀疑探遍": ("怀疑", "doubt", "DUBIUM", "普遍的怀疑", "1641"),
    "只为勘破因果的虚假": ("因果", "doubt", "CAUSA", "因果的错觉", "1739"),
    "批判在沉睡后绝醒": ("绝醒", "dawn", "CRITICA", "独断论之眠", "1781"),
    "立定先验伴时空刻划": ("先验", "stars", "A PRIORI", "星空与道德律", "1788"),
    "在普遍理性中通向": ("普遍", "pyramid", "UNIVERSALIS", "普遍历史", "1784"),
    "那名为\"绝对精神\"的终点啊": ("绝对精神", "pyramid", "ABSOLUT", "精神现象学", "1807"),
    "绝对唯心的体系": ("体系", "pyramid", "SYSTEMA", "体系", "1817"),
    "耸立在金字塔": ("金字塔", "pyramid", "PYRAMIS", "绝对的金字塔", "1817"),
    "暗藏着自我异化": ("异化", "forge", "ALIENATIO", "自我外化", "1807"),
    "扬弃重构的代码": ("扬弃", "forge", "AUFHEBUNG", "否定之否定", "1812"),
    "批判宗教的先驱": ("先驱", "forge", "FEUERBACH", "宗教的人本学", "1841"),
    "将迷雾荡涤振刷": ("迷雾", "industry", "NEBULA", "破除幻象", "1841"),
    "写下实践的新章": ("实践", "forge", "PRAXIS", "费尔巴哈提纲", "1845"),
    "待批判者再出发": ("批判", "industry", "CRITIQUE", "改变世界", "1845"),
    "是谁说盲目意志": ("意志", "abyss", "VOLUNTAS", "作为意志的世界", "1818"),
    "皆系于欲望惩罚": ("欲望", "commodity", "CUPIDO", "欲望的钟摆", "1818"),
    "又是谁宣布上帝已死": ("上帝已死", "idol", "DEUS MORTUUS", "快乐的科学", "1882"),
    "高歌超人的神话": ("超人", "abyss", "UEBERMENSCH", "查拉图斯特拉", "1883"),
    "工业与商品拜物": ("拜物", "industry", "FETISCH", "商品拜物教", "1867"),
    "将一切分割物化": ("物化", "commodity", "REIFICATIO", "物化意识", "1923"),
    "此在世界随生存的时间": ("此在", "forest", "DASEIN", "存在与时间", "1927"),
    "切分后升华": ("时间", "forest", "ZEIT", "时间性的绽出", "1927"),
    "逻辑厘清着世界的图画": ("图画", "ladder", "BILD", "逻辑哲学论", "1921"),
    "也守望沉默无言的断崖": ("断崖", "abyss", "SILENTIUM", "不可说者", "1921"),
    "直面事物本身 在现象里发芽": ("现象", "forest", "PHAENOMEN", "面向事情本身", "1901"),
    "\"凡不可说的 当保持沉默\"": ("沉默", "ladder", "TACERE", "凡不可说", "1921"),
    "有人说那微观权力": ("权力", "panopticon", "POTESTAS", "微观权力", "1975"),
    "潜藏在规训的种种技法": ("规训", "panopticon", "DISCIPLINA", "规训与惩罚", "1975"),
    "也有人批判技术理性": ("技术", "industry", "TECHNE", "工具理性", "1947"),
    "异化下的单向度化": ("单向度", "panopticon", "UNIDIMENSIO", "单向度的人", "1964"),
    "形而上崇高的大厦": ("大厦", "idol", "AEDIFICIUM", "形而上学", "—"),
    "随逻辑颠覆重构再崩塌": ("颠覆", "idol", "DECONSTRUCTIO", "解构", "1967"),
    "惟有直面荒谬决意自决的你我": ("荒谬", "sisyphus", "ABSURDUM", "西西弗的神话", "1942"),
    "从不被虚无压垮": ("虚无", "abyss", "NIHIL", "存在与虚无", "1943"),
    "哲学从不是什么": ("哲学", "dawn", "PHILOSOPHIA", "爱智", "—"),
    "远离于尘世悬空的童话": ("尘世", "dawn", "MUNDUS", "在世之中", "—"),
    "无论何时总有人": ("有人", "dawn", "ALIQUIS", "总有人", "—"),
    "燃尽自我追索几缕光华": ("光华", "dawn", "LUMEN", "燃尽自我", "—"),
    "思想的微芒指引着": ("微芒", "stars", "SCINTILLA", "思想的微光", "—"),
    "永恒追问本质的步伐": ("追问", "forest", "QUAESTIO", "永恒的追问", "—"),
    "化作公理守护着": ("公理", "stars", "AXIOMA", "化作公理", "—"),
    "反思着生命无数平凡的人啊": ("平凡", "dawn", "VITA", "无数平凡的人", "—"),
    "那是直面未知": ("未", "abyss", "IGNOTUM", "直面未知", "—"),
    "向死而生": ("向死而生", "forest", "SEIN ZUM TODE", "向死存在", "1927"),
    "自由自觉的坚韧灵魂啊": ("灵魂", "dawn", "ANIMA", "坚韧的灵魂", "—"),
    "你看啊": ("你看啊", "dawn", "ECCE", "光", "—"),
    "真理之光终会抵达": ("真理", "dawn", "VERITAS", "真理之光", "—"),
    "请务必再追问一下": ("追问", "dawn", "QUAERE", "再追问一次", "—"),
}

# shot_id, kind, anchor, motion, trans_in, extra(dict)
STORY = [
    # --- Verse 1
    (0,  "bleed",    "far_left",  "push",   None,      dict(fg=dict(side="left", strength=0.55, band=0.22))),
    (0,  "echo",     "center",    "still",  None,      dict(px=150, copies=11)),
    (1,  "wave",     "center",    "drift",  None,      dict()),
    (1,  "vertical", "right_v",   "drift_l", None,     dict()),
    (2,  "wave",     "low_left",  "still",  None,      dict(fg=dict(side="bottom", strength=0.6, band=0.24))),
    (2,  "line",     "low_right", "still",  None,      dict(swap=True)),
    (3,  "stamp",    "low_right", "orbit",  None,      dict(skew=10)),
    (4,  "line",     "center",    "push",   "flash",   dict(fg=dict(side="bottom", strength=0.7, band=0.3))),
    # --- Verse 2
    (5,  "vertical", "up_center", "rise",   None,      dict()),
    (5,  "watermark","bottom_right", "pull", None,     dict(px=400)),
    (6,  "dossier",  "low_left",  "still",  None,      dict()),
    (6,  "line",     "center",    "drift",  None,      dict(mode3d=True)),
    (7,  "collide",  "center",    "drift",  None,      dict()),
    (7,  "skew",     "center",    "drift",  None,      dict()),
    (8,  "vertical", "right_v",   "still",  None,      dict()),
    (9,  "line",     "center",    "still",  "flash",   dict(invert=True)),
    # --- Pre-chorus
    (10, "punch",    "center",    "push",   None,      dict()),
    (10, "fall",     "center",    "push",   None,      dict()),
    (11, "cut",      "center",    "still",  None,      dict()),
    (11, "bleed",    "center",    "still",  None,      dict(px=430)),
    (12, "vertical", "left_v",    "drift",  None,      dict()),
    (12, "stamp",    "center",    "orbit",  None,      dict(skew=14)),
    (13, "quiet",    "center",    "drift",  None,      dict(alpha=0.30)),
    (13, "echo",     "center",    "still",  "flash",   dict(px=130, copies=10)),
    # --- Chorus
    (14, "bleed",    "center",    "push",   "flash",   dict()),
    (14, "rise",     "center",    "still",  None,      dict()),
    (15, "echo",     "center",    "drift",  None,      dict(px=170, copies=12)),
    (15, "line",     "low_center","still",  None,      dict(strike=True)),
    (16, "line",     "center",    "push",   "flash",   dict()),
    (16, "line",     "center",    "still",  None,      dict(frame=True)),
    (17, "stamp",    "low_center","push",   None,      dict(skew=18)),
    (17, "bleed",    "center",    "rise",   "flash",   dict(px=380)),
    # --- Verse 3
    (18, "vertical", "right_v",   "push",   None,      dict()),
    (18, "tilt",     "center",    "push",   None,      dict()),
    (19, "shuffle",  "center",    "drift",  None,      dict()),
    (19, "stamp",    "up_left",   "creep",  None,      dict(skew=8)),
    (20, "quiet",    "low_right", "drift",  None,      dict(alpha=0.34)),
    (20, "scan",     "center",    "drift",  None,      dict()),
    (21, "punch",    "center",    "still",  None,      dict()),
    (22, "exit",     "center",    "drift",  "flash",   dict()),
    # --- Verse 4
    (22, "vertical", "left_v",    "still",  None,      dict()),
    (22, "tilt",     "low_right", "still",  None,      dict()),
    (23, "strike",   "center",    "drift",  None,      dict()),
    (23, "bleed",    "center",    "still",  None,      dict(px=400)),
    (24, "dossier",  "low_right", "drift",  None,      dict()),
    (24, "cut",      "center",    "still",  None,      dict(cut_amp=1.4)),
    (25, "quiet",    "center",    "still",  None,      dict(alpha=0.32)),
    (25, "floatup",  "center",    "still",  "flash",   dict()),
    # --- Bridge
    (26, "frame",    "center",    "creep",  None,      dict(w=0.46, h=0.22)),
    (27, "vertical", "right_v",   "still",  None,      dict(quiet=True)),
    (28, "split",    "center",    "creep",  None,      dict()),
    (29, "quiet",    "center",    "still",  "flash",   dict(alpha=0.20)),
    # --- Verse 5
    (30, "radial",   "center",    "push",   None,      dict()),
    (30, "cut",      "center",    "push_fast", "whip", dict()),
    (31, "scan",     "center",    "drift",  None,      dict()),
    (31, "squash",   "center",    "still",  None,      dict()),
    (32, "fall",     "center",    "drift",  None,      dict()),
    (32, "scatter",  "center",    "still",  None,      dict()),
    (33, "floatup",  "center",    "creep",  None,      dict()),
    (33, "still",    "center",    "still",  "flash",   dict()),
    # --- Chorus 2
    (34, "bleed",    "center",    "push",   "flash",   dict(px=430)),
    (34, "sink",     "center",    "pull",   None,      dict()),
    (35, "line",     "low_left",  "still",  None,      dict(px=90)),
    (35, "erode",    "center",    "still",  "whip",    dict()),
    (36, "dots",     "center",    "creep",  None,      dict()),
    (36, "tilt",     "center",    "creep",  None,      dict()),
    (37, "line",     "center",    "still",  None,      dict(frame=True)),
    (37, "dossier",  "low_center","still",  None,      dict(rows=8)),
    (38, "bleed",    "center",    "still",  None,      dict(px=520)),
    (38, "line",     "center",    "still",  None,      dict(px=110)),
    (39, "ignite",   "center",    "pull",   "flash",   dict()),
    # --- Outro
    (40, "line",     "center",    "still",  None,      dict(px=80)),
    (41, "line",     "center",    "creep",  None,      dict(track_open=True)),
    (41, "line",     "center",    "still",  None,      dict(px=90)),
]

SEC_PAL = {
    "verse1": ["sepia", "sepia", "gold", "sepia"],
    "verse2": ["sepia", "rust", "gold", "sepia"],
    "pre":    ["steel", "cold", "ash", "steel"],
    "chorus": ["gold", "ivory", "gold", "sepia"],
    "verse3": ["rust", "blood", "rust", "blood"],
    "verse4": ["steel", "cold", "steel", "ash"],
    "bridge": ["cold", "ash", "cold", "sepia"],
    "verse5": ["blood", "rust", "blood", "rust"],
    "chorus2": ["gold", "ivory", "gold", "ivory"],
    "outro":  ["ivory", "gold"],
}
GLITCH = {"verse1": [0.03, 0.12], "verse2": [0.05, 0.18], "pre": [0.16, 0.46],
          "chorus": [0.24, 0.62], "verse3": [0.10, 0.28], "verse4": [0.10, 0.30],
          "bridge": [0.02, 0.06], "verse5": [0.18, 0.44], "chorus2": [0.14, 0.34],
          "outro": [0.02, 0.0]}


def norm(t):
    return t.replace("\u201c", '"').replace("\u201d", '"').strip()


def load_lines():
    rows = []
    for ln in open(os.path.join(HERE, "kept_lines.txt"), encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln:
            continue
        i, sec, t0, t1, d, text = ln.split("|", 5)
        rows.append(dict(i=int(i), section=sec.strip(), t0=float(t0), t1=float(t1), text=norm(text)))
    return rows


def make_cues(line, row, sec, idx):
    """Turn a STORY row into one or two cues."""
    sid, kind, anchor, motion, trans, extra = row
    text = line["text"]
    t0, t1 = line["t0"], line["t1"]
    words = [{"t0": w["t0"]} for w in (line.get("words") or [])]
    e = dict(extra or {})
    glow = 0.85 if sec in ("chorus", "chorus2") else 0.5
    cues = []

    if kind == "split":
        cut = 4 if len(text) > 6 else 3
        for gi, (a, b) in enumerate([(0, cut), (cut, len(text))]):
            seg = text[a:b]
            ws = words[a:b]
            if not seg:
                continue
            spot = ("up_left", "low_right") if gi == 0 else ("low_left", "up_right")[0]
            cues.append(dict(kind="line", text=seg, t0=(ws[0]["t0"] if ws else t0),
                             t1=(ws[-1]["t1"] if ws else t1) + 0.4,
                             layout=spot, px=240, words=ws, glow=glow,
                             seed=(idx * 13 + gi) & 0xFFFF))
        return cues

    cue = dict(kind=kind, text=e.pop("text", text), t0=t0, t1=t1 + e.pop("hold", 0.35),
               layout=anchor, words=words, glow=glow,
               px=e.pop("px", None), seed=(idx * 37 + 5) & 0xFFFF)
    # boolean storyboard flags -> concrete kinds / params
    if e.pop("strike", False):
        cue["kind"] = "strike"
    if e.pop("frame", False):
        cue["kind"] = "frame"
    if e.pop("mode3d", False):
        cue["kind"] = "title3d"
    if e.pop("track_open", False):
        cue["tracking"] = 0.55
    if e.pop("quiet", False):
        cue["alpha"] = 0.35
    e.pop("shake", False)
    e.pop("swap", False)
    cue.update(e)
    if kind == "collide":
        cue["pair"] = text
    if kind == "radial":
        cue["radial"] = True
    cues.append(cue)
    return cues


def build():
    lines = load_lines()
    shots = []
    i = 0
    plate_no = 1
    while i < len(lines):
        sid = STORY[i][0]
        j = i
        while j + 1 < len(lines) and STORY[j + 1][0] == sid:
            j += 1
        group = lines[i:j + 1]
        sec = group[0]["section"] if group[0]["section"] in SEC_PAL else "verse1"
        first, last = group[0], group[-1]
        concept, asset, latin, cap_txt, yr = DESIGN.get(first["text"], ("", "dawn", "", "—", ""))
        motion = STORY[i][3]
        trans = STORY[i][4]
        invert = bool((STORY[i][5] or {}).get("invert"))

        cues = []
        for k, ln in enumerate(group):
            cues.extend(make_cues(ln, STORY[i + k], ln["section"], plate_no * 7 + k))
            if invert:
                for c in cues:
                    c.setdefault("color", (18, 14, 10))
        if invert:
            for c in cues:
                c["color"] = (18, 14, 10)

        pal_list = SEC_PAL[sec]
        pal_name = pal_list[(plate_no - 1) % len(pal_list)]
        sh = dict(
            t0=max(0.0, first["t0"] - 0.28), t1=last["t1"] + 0.55,
            kind=sec, seed=(plate_no * 41 + 7) & 0xFFFF,
            asset=[asset, 0], mode="plate", palette=pal_name,
            motion=motion, trans_in=trans,
            zoom=[1.0, 1.0],           # motion program drives it now
            cx=0.5 + (0.03 if plate_no % 2 else -0.03),
            cy=0.5 + (0.02 if plate_no % 3 == 0 else -0.02),
            plate_alpha=(0.80 if sec == "bridge" else 0.96),
            scrim=0.0, invert=invert,
            glitch=GLITCH.get(sec, [0.04, 0.14]),
            tear=0.10 if sec in ("verse5", "chorus") else 0.0,
            cues=cues,
            caption=dict(no="PLATE %02d" % plate_no, txt=cap_txt, yr=yr),
            anno=dict(t=concept, latin=latin) if concept else None,
        )
        if sec in ("chorus", "chorus2") and plate_no % 2 == 0:
            sh["beam"] = dict(angle=-20 if plate_no % 4 else 14, center=0.42,
                              width=0.13, amt=1.0, drift=0.3)
        if plate_no % 5 == 0 and concept:
            sh["ghost"] = dict(text=concept, size=760, alpha=0.14,
                               dx=0.10 if plate_no % 2 else -0.10, dy=0.05)
        if sec == "verse5":
            sh["whip_dir"] = 1 if plate_no % 2 else -1
        shots.append(sh)
        plate_no += 1
        i = j + 1

    # ---------------- intro
    first_t = lines[0]["t0"]
    shots.insert(0, dict(t0=first_t * 0.5, t1=first_t, kind="intro", seed=103,
                         asset=["academy", 0], mode="plate", palette="sepia",
                         motion="hand", trans_in=None, plate_alpha=0.92,
                         cues=[dict(kind="line", text="哲学史", t0=first_t * 0.5 + 0.5,
                                    t1=first_t - 0.2, layout="low_center", px=120,
                                    glow=0.6, words=[], seed=7)],
                         caption=dict(no="PLATE 00", txt="从洞穴到解构", yr="前 6C — 20C"),
                         glitch=[0.03, 0.09]))
    shots.insert(0, dict(t0=0.0, t1=first_t * 0.5, kind="intro", seed=101,
                         asset=["cave", 0], mode="plate", palette="cold",
                         motion="still", trans_in="flash_soft", plate_alpha=0.55,
                         cues=[dict(kind="bleed", text="追问", t0=1.6, t1=7.4, layout="center",
                                    px=470, glow=1.0, words=[], seed=11)],
                         caption=dict(no="PLATE 00", txt="序 · 爱智", yr=""),
                         credits=dict(t0=3.0, t1=9.0, y=0.74, x=0.5, gap=58, size=28,
                                      anchor="ca",
                                      lines=["填词：Gemini 3.7 Flash",
                                             "图片素材：GPT-Image 2.5",
                                             "PV制作：DeepSeek-V4.1f-1017"]),
                         glitch=[0.10, 0.03], beam=dict(angle=-14, center=0.42, width=0.2, amt=1.0)))

    # ---------------- "ah" interlude
    ah0, ah1 = 93.46, 108.22
    m2 = ah0 + (ah1 - ah0) * 0.48
    shots.append(dict(t0=ah0, t1=m2, kind="interlude", seed=907, asset=["pyramid", 0],
                      mode="plate", motion="still", trans_in="flash", palette="rust",
                      plate_alpha=0.92,
                      cues=[dict(kind="bleed", text="绝对", t0=ah0 + 1.2, t1=m2 - 0.6,
                                 layout="center", px=430, glow=1.1, words=[], seed=13)],
                      caption=dict(no="PLATE AH", txt="精神的阶梯", yr="1807"),
                      ghost=dict(text="精神", size=760, alpha=0.22, dx=0.12, dy=-0.08),
                      glitch=[0.18, 0.55], fg=dict(side="right", strength=0.6, band=0.24)))
    shots.append(dict(t0=m2, t1=ah1, kind="interlude", seed=911, asset=["stars", 0],
                      mode="light", motion="creep", trans_in=None, palette="gold",
                      plate_alpha=0.9, cues=[], caption=dict(no="PLATE AH", txt="空镜 · 星轨", yr=""),
                      glitch=[0.04, 0.10], beam=dict(angle=12, center=0.5, width=0.18, amt=1.3)))

    # ---------------- tail
    last_end = lines[-1]["t1"]
    shots.append(dict(t0=last_end, t1=246.0, kind="outro", seed=921, asset=["dawn", 0],
                      mode="light", motion="pull", trans_in="flash", palette="ivory",
                      plate_alpha=0.8, cues=[], caption=dict(no="", txt="", yr=""),
                      glitch=[0.02, 0.0], beam=dict(angle=-8, center=0.5, width=0.24, amt=1.3)))
    shots.append(dict(t0=246.0, t1=DUR + 0.6, kind="end", seed=931, asset=["dawn", 0],
                      mode="light", motion="still", trans_in=None, palette="gold",
                      plate_alpha=0.45, cues=[],
                      caption=dict(no="", txt="", yr=""),
                      credits=dict(t0=246.6, t1=259.0, y=0.42, x=0.5, gap=62, size=30,
                                   anchor="ca",
                                   lines=["填词：Gemini 3.7 Flash",
                                          "图片素材：GPT-Image 2.5",
                                          "PV制作：DeepSeek-V4.1f-1017"]),
                      glitch=[0.0, 0.0]))

    shots.sort(key=lambda s: s["t0"])

    # ---------------- close gaps
    INTER = [dict(asset=["stars", 0], pal="gold", cap=("PLATE A", "无声的间奏", "—")),
             dict(asset=["pyramid", 0], pal="rust", cap=("PLATE B", "断章", "—")),
             dict(asset=["forest", 0], pal="cold", cap=("PLATE C", "林间", "—")),
             dict(asset=["abyss", 0], pal="ash", cap=("PLATE D", "断崖", "—"))]
    filled, k = [], 0
    for idx, sh in enumerate(shots):
        filled.append(sh)
        if idx + 1 >= len(shots):
            continue
        gap = shots[idx + 1]["t0"] - sh["t1"]
        if gap > 2.2:
            sp = INTER[k % len(INTER)]
            k += 1
            filled.append(dict(t0=sh["t1"], t1=shots[idx + 1]["t0"], kind="interlude",
                               seed=(523 + k * 17) & 0xFFFF, asset=sp["asset"], mode="plate",
                               palette=sp["pal"], motion="still", trans_in="flash",
                               plate_alpha=0.9, cues=[],
                               caption=dict(no=sp["cap"][0], txt=sp["cap"][1], yr=sp["cap"][2]),
                               glitch=[0.05, 0.20],
                               beam=dict(angle=-16, center=0.44, width=0.16, amt=1.0)))
        elif gap > 0.02:
            sh["t1"] = shots[idx + 1]["t0"]

    shots = sorted(filled, key=lambda s: s["t0"])
    for idx in range(len(shots) - 1):
        if shots[idx]["t1"] > shots[idx + 1]["t0"]:
            shots[idx]["t1"] = shots[idx + 1]["t0"]

    op = os.path.join(HERE, "shots.json")
    json.dump(shots, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    nc = sum(len(s.get("cues") or []) for s in shots)
    kinds = {}
    for s in shots:
        for c in s.get("cues") or []:
            kinds[c.get("kind", "line")] = kinds.get(c.get("kind", "line"), 0) + 1
    print("shots", len(shots), "cues", nc, "| kinds:", dict(sorted(kinds.items(), key=lambda x: -x[1])))
    print("last t1", round(shots[-1]["t1"], 2))


if __name__ == "__main__":
    build()
