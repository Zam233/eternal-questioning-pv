# -*- coding: utf-8 -*-
"""Build layered (camera + props + type) shots for all 74 lyric lines.

Everything is data-driven: each section owns a palette, a camera move, a prop
pool and a rotation of type behaviours. Type is always drawn last, so a prop can
never eat a sung syllable.
"""
import json, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DUR = 262.80
CAP = 6.0            # a lyric line never owns more than this many seconds

# ---------------------------------------------------------------- lyric + concept
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
    "真理之光总会抵达": ("真理", "dawn", "VERITAS", "真理之光", "—"),
    "请务必再追问一下": ("追问", "dawn", "QUAERE", "再追问一次", "—"),
}

# section -> (palette, camera keys, prop pool, type kinds, glitch)
SEC = {
    "verse1":  dict(pal="sepia", props=["brazier", "column_a", "stele", "bust_b"],
                    kinds=["line", "wave", "vertical", "line"],
                    cam=[(0.0, 0.000, 0.004, 0.000, 0.0), (1.0, 0.016, -0.006, 0.070, 0.30)],
                    glitch=[0.03, 0.10], zt=0.30),
    "verse2":  dict(pal="gold", props=["arch", "book", "column_b", "frame"],
                    kinds=["line", "vertical", "dossier", "line"],
                    cam=[(0.0, -0.012, 0.000, 0.050, -0.20), (1.0, 0.020, 0.004, 0.000, 0.18)],
                    glitch=[0.05, 0.16], zt=0.31),
    "pre":     dict(pal="steel", props=["gear", "frame", "book", "column_b"],
                    kinds=["punch", "cut", "scatter", "line"],
                    cam=[(0.0, 0.000, 0.010, 0.000, 0.0), (1.0, -0.010, -0.008, 0.100, -0.45)],
                    glitch=[0.15, 0.45], zt=0.30),
    "chorus":  dict(pal="ivory", props=["book", "drapery", "frame", "gear"],
                    kinds=["bleed", "line", "echo", "line"],
                    cam=[(0.0, 0.000, 0.000, 0.000, 0.0), (1.0, 0.010, 0.006, 0.085, 0.35)],
                    glitch=[0.22, 0.55], zt=0.32),
    "verse3":  dict(pal="rust", props=["chain", "gear", "stele", "book"],
                    kinds=["vertical", "stamp", "line", "scan"],
                    cam=[(0.0, 0.014, 0.000, 0.020, 0.25), (1.0, -0.014, -0.010, 0.105, -0.35)],
                    glitch=[0.10, 0.28], zt=0.30),
    "verse4":  dict(pal="cold", props=["frame", "arch", "chain", "gear"],
                    kinds=["line", "tilt", "strike", "bleed"],
                    cam=[(0.0, 0.012, 0.006, 0.030, -0.20), (1.0, -0.018, -0.004, 0.000, 0.15)],
                    glitch=[0.10, 0.30], zt=0.31),
    "bridge":  dict(pal="ash", props=["drapery", "ladder", "arch"],
                    kinds=["line", "vertical", "quiet", "line"],
                    cam=[(0.0, 0.000, 0.000, 0.000, 0.0), (1.0, 0.006, 0.004, 0.030, 0.10)],
                    glitch=[0.02, 0.06], zt=0.29),
    "verse5":  dict(pal="rust", props=["chain", "frame", "gear", "book"],
                    kinds=["radial", "cut", "scan", "scatter"],
                    cam=[(0.0, -0.010, 0.008, 0.000, 0.0), (1.0, 0.012, -0.010, 0.110, -0.40)],
                    glitch=[0.18, 0.44], zt=0.30),
    "chorus2": dict(pal="gold", props=["drapery", "arch", "book", "frame"],
                    kinds=["bleed", "ignite", "line", "dots"],
                    cam=[(0.0, 0.000, 0.010, 0.060, 0.15), (1.0, 0.014, -0.008, 0.000, -0.12)],
                    glitch=[0.14, 0.34], zt=0.32),
    "outro":   dict(pal="ivory", props=["drapery", "arch"],
                    kinds=["line", "quiet"],
                    cam=[(0.0, 0.000, 0.004, 0.020, 0.0), (1.0, 0.008, -0.004, 0.000, 0.06)],
                    glitch=[0.02, 0.0], zt=0.31),
}


def norm(t):
    return t.replace("\u201c", '"').replace("\u201d", '"').strip()


def load():
    p = os.path.join(HERE, "timing_auto.json")
    if not os.path.exists(p):
        p = os.path.join(HERE, "lines.json")
    rows = json.load(io.open(p, encoding="utf-8"))
    for r in rows:
        r["text"] = norm(r["text"])
    return rows


def build():
    rows = load()
    # cap absurd spans (wordless tail after a line becomes an interlude shot)
    for r in rows:
        if r["t1"] - r["t0"] > CAP:
            r["t1"] = r["t0"] + CAP

    shots, i, plate = [], 0, 1
    while i < len(rows):
        a = rows[i]
        b = rows[i + 1] if i + 1 < len(rows) and rows[i + 1]["section"] == a["section"] else None
        group = [a] + ([b] if b else [])
        sec = a["section"] if a["section"] in SEC else "verse1"
        cfg = SEC[sec]
        first, last = group[0], group[-1]
        concept, bg, latin, cap_txt, yr = DESIGN.get(first["text"], ("", "dawn", "", "—", ""))

        cues = []
        for k, ln in enumerate(group):
            kind = cfg["kinds"][(plate + k) % len(cfg["kinds"])]
            cues.append(dict(
                kind=kind, text=ln["text"], t0=ln["t0"], t1=ln["t1"] + 0.30,
                layout=("low_left", "up_right", "center", "low_center")[(plate + k) % 4],
                px=170, words=[{"t0": w["t0"]} for w in ln.get("words", [])],
                glow=0.8 if sec in ("chorus", "chorus2") else 0.5,
                seed=(plate * 37 + k * 11) & 0xFFFF))

        pool = cfg["props"]
        mid = pool[plate % len(pool)]
        near = pool[(plate + 2) % len(pool)]
        layers = [dict(t="bg", src=bg, idx=0, z=1.00, palette=cfg["pal"], fit=1.06)]
        if mid != near:
            layers.append(dict(t="prop", src=mid, z=0.60,
                               x=(0.24 if plate % 2 else 0.76), y=0.70, h=0.42))
            layers.append(dict(t="prop", src=near, z=0.24,
                               x=(0.88 if plate % 2 else 0.12), y=0.62, h=0.92,
                               depth_blur=0.7))
        else:
            layers.append(dict(t="prop", src=mid, z=0.55,
                               x=(0.22 if plate % 2 else 0.78), y=0.72, h=0.50))
        for c in cues:
            layers.append(dict(t="type", z=cfg["zt"], cue=c))

        shots.append(dict(
            t0=max(0.0, first["t0"] - 0.30), t1=last["t1"] + 0.55,
            seed=(plate * 41 + 7) & 0xFFFF, palette=cfg["pal"],
            glitch=cfg["glitch"], trans_in=("flash" if plate % 7 == 0 else None),
            cam=dict(keys=cfg["cam"], seed=plate % 13, handheld=1.0),
            caption=dict(no="PLATE %02d" % plate, txt=cap_txt, yr=yr),
            anno=dict(t=concept, latin=latin) if concept else None,
            anno_pos=("br" if plate % 2 else "bl"),
            layers=layers))
        plate += 1
        i += len(group)

    shots.sort(key=lambda s: s["t0"])
    # fill instrumental gaps with wordless shots
    filled = []
    for idx, sh in enumerate(shots):
        filled.append(sh)
        if idx + 1 >= len(shots):
            continue
        gap = shots[idx + 1]["t0"] - sh["t1"]
        if gap > 2.0:
            g0, g1 = sh["t1"], shots[idx + 1]["t0"]
            filled.append(dict(
                t0=g0, t1=g1, seed=(900 + idx) & 0xFFFF, palette="ash", glitch=[0.05, 0.18],
                trans_in="flash", cam=dict(keys=[(0.0, 0.0, 0.0, 0.0, 0.0),
                                                (1.0, 0.008, 0.0, 0.05, 0.1)], seed=idx),
                caption=dict(no="PLATE —", txt="间奏 · 无词", yr=""),
                layers=[dict(t="bg", src="stars", idx=0, z=1.0, palette="ash", fit=1.05),
                        dict(t="prop", src="drapery", z=0.24, x=0.86, y=0.62, h=0.85,
                             depth_blur=1.0)]))
        elif gap > 0.02:
            sh["t1"] = shots[idx + 1]["t0"]

    filled.sort(key=lambda s: s["t0"])
    for idx in range(len(filled) - 1):
        if filled[idx]["t1"] > filled[idx + 1]["t0"]:
            filled[idx]["t1"] = filled[idx + 1]["t0"]

    # ---------------- head: title + credits
    first_t = filled[0]["t0"]
    filled.insert(0, dict(
        t0=0.0, t1=max(2.0, first_t), seed=101, palette="cold", glitch=[0.06, 0.02],
        cam=dict(keys=[(0.0, 0.0, 0.0, 0.0, 0.0), (1.0, 0.010, 0.004, 0.055, 0.2)], seed=1),
        caption=dict(no="PLATE 00", txt="序 · 爱智", yr=""),
        credits=dict(t0=3.4, t1=first_t - 1.0, y=0.735, x=0.5, gap=58, size=28,
                     anchor="ca",
                     lines=["填词：Gemini 3.7 Flash",
                            "图片素材：GPT-Image 2.5",
                            "PV制作：DeepSeek-V4.1f-1017"]),
        layers=[dict(t="bg", src="cave", idx=0, z=1.00, palette="cold", fit=1.05),
                dict(t="prop", src="column_a", z=0.24, x=0.90, y=0.62, h=0.95, depth_blur=0.8),
                dict(t="type", z=0.30, cue=dict(kind="bleed", text="追问", t0=1.8, t1=first_t - 0.8,
                                                layout="center", px=430, words=[], glow=1.0,
                                                seed=11))]))

    # ---------------- tail: end card
    last_t = filled[-1]["t1"]
    filled.append(dict(
        t0=last_t, t1=DUR + 0.6, seed=931, palette="ivory", glitch=[0.0, 0.0],
        cam=dict(keys=[(0.0, 0.0, 0.004, 0.020, 0.0), (1.0, 0.006, -0.004, 0.000, 0.05)], seed=9),
        caption=dict(no="", txt="", yr=""),
        credits=dict(t0=last_t + 2.0, t1=DUR - 2.0, y=0.42, x=0.5, gap=62, size=30,
                     anchor="ca",
                     lines=["填词：Gemini 3.7 Flash",
                            "图片素材：GPT-Image 2.5",
                            "PV制作：DeepSeek-V4.1f-1017"]),
        layers=[dict(t="bg", src="dawn", idx=0, z=1.00, palette="ivory", fit=1.05),
                dict(t="prop", src="drapery", z=0.30, x=0.86, y=0.66, h=0.70, depth_blur=1.2)]))

    filled.sort(key=lambda s: s["t0"])
    for idx in range(len(filled) - 1):
        if filled[idx]["t1"] > filled[idx + 1]["t0"]:
            filled[idx]["t1"] = filled[idx + 1]["t0"]

    op = os.path.join(HERE, "shots.json")
    json.dump(filled, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("shots", len(filled), "| plates", plate - 1,
          "| last t1", round(filled[-1]["t1"], 2))


if __name__ == "__main__":
    build()
