# -*- coding: utf-8 -*-
"""
小学题库 统一整理脚本
- 读取 _sources/ 下各 GitHub 仓库的题库数据
- 归一化为统一 schema
- 输出：
    data/<年级>/<学科>.json          按年级+学科归档
    output/小学题库_统一格式.jsonl    每行一条，便于入库
    output/小学题库_统一格式.csv      关系型/SQL 入库用
    output/语文素材_诗词生字词语.json  jacksonrick 语文课内素材（非问答，单独存放）
"""
import os, re, json, csv, glob, collections
from html.parser import HTMLParser

SRC = os.path.join(os.path.dirname(__file__), "_sources")
OUT = os.path.join(os.path.dirname(__file__), "data")
OUT_UNI = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT_UNI, exist_ok=True)

GRADE_CN = {1:"一年级",2:"二年级",3:"三年级",4:"四年级",5:"五年级",6:"六年级",
             7:"七年级",8:"八年级",9:"九年级",10:"高一",11:"高二",12:"高三"}
GRADE_NUM = {"一年级":1,"二年级":2,"三年级":3,"四年级":4,"五年级":5,"六年级":6,
             "七年级":7,"八年级":8,"九年级":9,"高一":10,"高二":11,"高三":12}

def norm_grade_num(grade):
    """年级中文 -> 1..6 整数；跨年级/缺失 -> 0"""
    if isinstance(grade, int):
        return grade if 1 <= grade <= 6 else 0
    g = norm_grade(grade)
    return GRADE_NUM.get(g, 0)

# 难度等级 -> 权重(0.1~1.0)，越高越难
DIFF_WEIGHT = {
    "基础": 0.30, "basic": 0.30, "easy": 0.30, "低": 0.30, "简单": 0.30, "易": 0.30,
    "中等": 0.55, "standard": 0.55, "medium": 0.55, "中": 0.55,
    "提高": 0.80, "advanced": 0.80, "hard": 0.80, "高": 0.80, "难": 0.80,
    "挑战": 0.85, "challenge": 0.85,
}

def compute_difficulty_weight(grade_num, qtype, difficulty_raw):
    """返回 0.10~1.00 的难度权重（float, 2位小数）。
    有来源显式难度则直接映射；否则按 年级基线 + 题型偏移 启发式估算。"""
    if difficulty_raw is not None:
        s = str(difficulty_raw).strip().lower()
        if s in DIFF_WEIGHT:
            return round(DIFF_WEIGHT[s], 2)
        if s.isdigit():
            n = int(s)
            # 与 norm_diff 的等级划分对齐：1-2 基础 / 3 中等 / 4-5 提高
            return round({1:0.25,2:0.38,3:0.55,4:0.82,5:0.92}.get(n, 0.55), 2)
    # 启发式：年级越高越难，计算/简答比选择/判断更难
    base = {1:0.25, 2:0.35, 3:0.45, 4:0.60, 5:0.75, 6:0.90,
            7:0.92, 8:0.94, 9:0.96, 10:0.97, 11:0.98, 12:0.99}.get(grade_num, 0.50)
    delta = {"判断题":-0.05, "选择题":0.00, "填空题":0.05, "计算题":0.08,
             "简答题":0.12, "连线题":0.00, "其他":0.05}.get(qtype, 0.05)
    w = base + delta
    return round(min(max(w, 0.10), 1.00), 2)

def band_from_weight(w):
    if w < 0.40: return "基础"
    if w < 0.70: return "中等"
    return "提高"

records = []          # 统一问答记录
supplementary = []    # 语文素材（非问答）

def norm_grade(g):
    if isinstance(g, int):
        return GRADE_CN.get(g)
    if isinstance(g, str):
        s = g.strip()
        # 高中（必须最先判断，因为“高一”含“一”）
        for k in ("高一", "高二", "高三"):
            if s.startswith(k) or k in s: return k
        # 小学 / 初中（中文数字年级）
        for num, label in [("一","一年级"),("二","二年级"),("三","三年级"),
                           ("四","四年级"),("五","五年级"),("六","六年级"),
                           ("七","七年级"),("八","八年级"),("九","九年级")]:
            if num in s: return label
        if "-" in s or "跨" in s or "全" in s: return "跨年级"
    return "跨年级"

def norm_subject(s):
    # 注意：必须先把“英语”判定放在“语文(语)”之前，否则“英语”会被“语”子串误判为语文
    if not s: return "综合"
    low = str(s).lower()
    if "英语" in s or "english" in low or low == "eng" or s == "英": return "英语"
    if "语文" in s or "chinese" in low or s == "语": return "语文"
    if "数学" in s or "math" in low or s == "数": return "数学"
    if "科学" in s or "science" in low or s == "科": return "科学"
    if "道" in s or "法" in s or "品德" in s or "思政" in s or "思想政治" in s or "社会" in s: return "道法"
    if "历史" in s: return "历史"
    if "地理" in s: return "地理"
    if "生物" in s: return "生物"
    if "物理" in s: return "物理"
    if "化学" in s: return "化学"
    if "综" in s or "常" in s or "other" in low or s in ("综合",): return "综合"
    return "综合"

def norm_type(t):
    if not t: return "其他"
    t = str(t).lower()
    if "判断" in t or t=="judge" or "tf" in t: return "判断题"
    if "选择" in t or t in ("single","choice","multiple") or "单选" in t or "多选" in t: return "选择题"
    if "填空" in t or t=="fill" or "默写" in t or "听写" in t: return "填空题"
    if "计算" in t or t in ("calc","calculation","numeric") or "口算" in t or "应用" in t or "列式" in t: return "计算题"
    if "连线" in t: return "连线题"
    if "简答" in t or t=="word": return "简答题"
    return "其他"

def norm_diff(d):
    if d is None: return ""
    if isinstance(d, str):
        if d in ("基础","basic","easy","低"): return "基础"
        if d in ("中等","standard","medium","中"): return "中等"
        if d in ("提高","hard","advanced","高"): return "提高"
        if d.isdigit():
            n=int(d); return "基础" if n<=2 else ("中等" if n==3 else "提高")
        return d
    if isinstance(d, int):
        return "基础" if d<=2 else ("中等" if d==3 else "提高")
    return ""

def add(source, source_file, grade, subject, volume, chapter, topic, qtype,
        difficulty_raw, question, options, answer, explanation, knowledge_points):
    grade = norm_grade(grade) or "跨年级"
    subject = norm_subject(subject)
    qtype = norm_type(qtype)
    gnum = norm_grade_num(grade)
    # 难度权重
    weight = compute_difficulty_weight(gnum, qtype, difficulty_raw)
    # 难度等级（band）：有原始难度用原始映射，否则按权重反推，保证与权重一致
    band = norm_diff(difficulty_raw) if (difficulty_raw not in (None, "")) else band_from_weight(weight)
    rec = {
        "id": f"{source.split('/')[-1]}_{len(records)+1:05d}",
        "source": source,
        "source_file": source_file,
        "grade": grade,
        "subject": subject,
        "volume": volume or "全",
        "chapter": chapter or "",
        "topic": topic or "",
        "type": qtype,
        "difficulty": band,
        "difficulty_weight": weight,
        "difficulty_raw": "" if difficulty_raw is None else str(difficulty_raw),
        "question": (question or "").strip(),
        "options": options if isinstance(options, list) else None,
        "answer": ("" if answer is None else str(answer)).strip(),
        "explanation": (explanation or "").strip(),
        "knowledge_points": knowledge_points if isinstance(knowledge_points, list) else [],
    }
    if rec["question"]:
        records.append(rec)

# ---------------------------------------------------------------------------
# 1) thl529/question-bank  —— 36 个 JSON，文件名含 年级+学科+册
# ---------------------------------------------------------------------------
def parse_thl529():
    src = "thl529/question-bank"
    for f in sorted(glob.glob(os.path.join(SRC,"thl529_question-bank","*.json"))):
        name = os.path.basename(f)
        gm = re.search(r"([一二三四五六])年级", name)
        sm = re.search(r"(语文|数学|英语)", name)
        vm = re.search(r"(上|下)册", name)
        grade = norm_grade(gm.group(1)+"年级") if gm else "跨年级"
        subject = norm_subject(sm.group(1)) if sm else "综合"
        volume = vm.group(1) if vm else "全"
        d = json.load(open(f, encoding="utf-8"))
        qs = d.get("题目", []) if isinstance(d, dict) else d
        for it in qs:
            opts = it.get("选项") or {}
            if isinstance(opts, dict):
                options = [str(v) for v in opts.values()]
                ans = opts.get(it.get("答案")) if it.get("答案") in opts else it.get("答案")
            else:
                options = list(opts) if isinstance(opts, list) else None
                ans = it.get("答案")
            kp = it.get("知识点") or []
            if not isinstance(kp, list): kp = [str(kp)]
            add(src, name, grade, subject, volume, it.get("类别",""), it.get("类别",""),
                "选择题", it.get("难度"), it.get("题干"), options, ans,
                it.get("解析"), kp)

# ---------------------------------------------------------------------------
# 2) mastomato/zhixing-tv-quiz  —— questions.json（小学 grade 1-6）
# ---------------------------------------------------------------------------
def parse_mastomato():
    src = "mastomato/zhixing-tv-quiz"
    f = os.path.join(SRC,"mastomato_zhixing-tv-quiz","app/src/main/assets/questions.json")
    d = json.load(open(f, encoding="utf-8"))
    for it in d:
        g = it.get("grade")
        if not (isinstance(g,int) and 1<=g<=6): continue
        opts = [it.get("opt_a"),it.get("opt_b"),it.get("opt_c"),it.get("opt_d")]
        opts = [str(o) for o in opts if o not in (None,"")]
        ai = it.get("answer_index")
        ans = opts[ai] if isinstance(ai,int) and 0<=ai<len(opts) else it.get("answer")
        add(src, "questions.json", g, it.get("subject"), it.get("term"),
            it.get("chapter"), it.get("topic"), "选择题", None,
            it.get("text"), opts, ans, it.get("explain"), [])

# ---------------------------------------------------------------------------
# 3) zhubing3170/TvSafetyLock —— question-bank/questions.json
# ---------------------------------------------------------------------------
def parse_tvsafety():
    src = "zhubing3170/TvSafetyLock"
    f = os.path.join(SRC,"zhubing3170_TvSafetyLock","question-bank","questions.json")
    d = json.load(open(f, encoding="utf-8"))
    sec_map = {"chinese":"语文","english":"英语","math":"数学"}
    for sec, subj in sec_map.items():
        for it in d.get(sec, []):
            o = it.get("o") or []
            ai = it.get("a")
            ans = o[ai] if isinstance(ai,int) and 0<=ai<len(o) else ""
            add(src, "questions.json", it.get("g"), subj, "全", "", "",
                "选择题", None, it.get("q"), [str(x) for x in o], ans, "", [])

# ---------------------------------------------------------------------------
# 4) sijie-yin/pure-math-taxonomy —— primary_g1..g6.json（数学）
# ---------------------------------------------------------------------------
def parse_sijie():
    src = "sijie-yin/pure-math-taxonomy"
    for g in range(1,7):
        f = os.path.join(SRC,"sijie-yin_pure-math-taxonomy","data","_qbatches",f"primary_g{g}.json")
        if not os.path.exists(f): continue
        d = json.load(open(f, encoding="utf-8"))
        for it in d:
            opts = it.get("options")
            if isinstance(opts, list) and opts:
                options = [str(x) for x in opts]
                ans = it.get("answer")
                # 若是字母下标则解析
                if isinstance(ans,str) and ans in [o.get("label") for o in opts if isinstance(o,dict)]:
                    for o in opts:
                        if isinstance(o,dict) and o.get("label")==ans: ans=o.get("text"); break
            else:
                options = None
                ans = it.get("answer")
            add(src, f"primary_g{g}.json", g, "数学", "全", it.get("topicId"),
                it.get("topicId"), it.get("type"), it.get("difficulty"),
                it.get("prompt"), options, ans, it.get("explanation"), [])

# ---------------------------------------------------------------------------
# 4b) xiaoyang111222/cn-math-taxonomy —— 超全小学题库
#     data/questions.json (全学段) + data/topics.json(含 grade/semester/chapter)
#     小学段覆盖 数学(cnm) 英语(cne) 语文(cnc) 科学(cns) 道德与法治(cnd)
#     通过 topicId 前缀+topics.json 映射得到 年级/册/章节/学科
# ---------------------------------------------------------------------------
def parse_cnmath_taxonomy():
    src = "xiaoyang111222/cn-math-taxonomy"
    base = os.path.join(SRC, "xiaoyang111222_cn-math-taxonomy")
    tj = os.path.join(base, "data", "topics.json")
    qj = os.path.join(base, "data", "questions.json")
    if not (os.path.exists(tj) and os.path.exists(qj)):
        print("  (skip) xiaoyang data 缺失"); return
    topics = {t["id"]: t for t in json.load(open(tj, encoding="utf-8"))}
    SUBJ_PREFIX = {"cnm":"数学","cne":"英语","cnc":"语文","cns":"科学","cnd":"道法"}
    qs = json.load(open(qj, encoding="utf-8"))
    cnt = 0
    for it in qs:
        tid = it.get("topicId", "")
        m = re.match(r"([a-z]+)_([a-z]?)(\d+)", tid)
        if not m: continue
        prefix, gletter, _ = m.group(1), m.group(2), m.group(3)
        if prefix not in SUBJ_PREFIX: continue          # 跳过 初中/高中 学科
        if gletter != "p": continue                       # 仅小学(p)段
        topic = topics.get(tid)
        if not topic: continue
        grade = topic.get("grade")
        if not (isinstance(grade, int) and 1 <= grade <= 6): continue
        subject = SUBJ_PREFIX[prefix]
        volume = topic.get("semester") or "全"
        chapter = topic.get("chapter") or ""
        # 选项/答案解析
        choices = it.get("choices") or []
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            options = [str(c.get("text", "")) for c in choices]
            ans_key = it.get("answer")
            ans = ""
            for c in choices:
                if c.get("key") == ans_key:
                    ans = str(c.get("text", "")); break
            if not ans: ans = str(ans_key)
        else:
            options = None
            ans = it.get("answer")
        qtype = it.get("type")
        # 题型归一
        if qtype == "choice": qtype = "选择题"
        elif qtype == "numeric": qtype = "计算题"
        elif qtype in ("short","self"): qtype = "简答题"
        else: qtype = qtype
        add(src, "questions.json", grade, subject, volume, chapter,
            topic.get("name",""), qtype, it.get("difficulty"),
            it.get("prompt"), options, ans, it.get("explanation"), [])
        cnt += 1
    print(f"  xiaoyang 小学段录入: {cnt}")

# ---------------------------------------------------------------------------
# 5) Aden357-234/quiz-practice —— questions-1-3.js / questions-4-6.js
# ---------------------------------------------------------------------------
def parse_aden():
    src = "Aden357-234/quiz-practice"
    for f, grange in [("questions-1-3.js","1-3年级"),("questions-4-6.js","4-6年级")]:
        p = os.path.join(SRC,"Aden357-234_quiz-practice",f)
        txt = open(p, encoding="utf-8").read()
        m = re.search(r"=\s*(\[.*?\])\s*;", txt, re.S)
        arr = json.loads(m.group(1))
        for it in arr:
            opts = it.get("options") or []
            options = [str(o.get("text")) for o in opts]
            lab = {o.get("label"):o.get("text") for o in opts}
            ans = lab.get(it.get("answer"), it.get("answer"))
            add(src, f, grange, "综合", "全", "", "", it.get("type"),
                None, it.get("question"), options, ans, it.get("explanation"), [])

# ---------------------------------------------------------------------------
# 6) cy-0754/tiku-studio —— seed/questions-*.json（含 book 元数据）
# ---------------------------------------------------------------------------
def parse_cy0754():
    src = "cy-0754/tiku-studio"
    for f in sorted(glob.glob(os.path.join(SRC,"cy-0754_tiku-studio","seed","questions-*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        book = d.get("book", {})
        grade = norm_grade(book.get("grade"))
        subject = norm_subject(book.get("subject"))
        volume = "上" if "上" in str(book.get("semester","")) else ("下" if "下" in str(book.get("semester","")) else "全")
        title = book.get("title","")
        for it in d.get("questions", []):
            kp = it.get("knowledge_points") or []
            if not isinstance(kp, list): kp=[str(kp)]
            add(src, os.path.basename(f), grade, subject, volume, title,
                "/".join(kp), it.get("q_type"), it.get("difficulty"),
                it.get("stem"), None, it.get("answer"), it.get("analysis"), kp)

# ---------------------------------------------------------------------------
# 7) dezhiguan/quizmate —— bank/questions.json
# ---------------------------------------------------------------------------
def parse_quizmate():
    src = "dezhiguan/quizmate"
    f = os.path.join(SRC,"dezhiguan_quizmate","bank","questions.json")
    d = json.load(open(f, encoding="utf-8"))
    for it in d:
        opts = it.get("options")
        options = [str(x) for x in opts] if isinstance(opts,list) else None
        add(src, "questions.json", it.get("grade"), "数学", "全", "",
            it.get("topic"), it.get("qtype"), it.get("difficulty"),
            it.get("stem"), options, it.get("answer"), it.get("explain"), [])

# ---------------------------------------------------------------------------
# 8) h517061544/test —— grade3_question_bank.jsonl（三年级混合）
# ---------------------------------------------------------------------------
def parse_h517():
    src = "h517061544/test"
    f = os.path.join(SRC,"h517061544_test","grade3_question_bank.jsonl")
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line=line.strip()
            if not line: continue
            it = json.loads(line)
            subj = norm_subject(it.get("subject"))
            opts = it.get("options")
            options = [str(x) for x in opts] if isinstance(opts,list) else None
            add(src, "grade3_question_bank.jsonl", 3, subj, "全", "", "",
                it.get("type"), it.get("difficulty"), it.get("question"),
                options, it.get("answer"), it.get("explanation"), [])

# ---------------------------------------------------------------------------
# 9) r4c4gzpzyh …… —— questions1116.js（六年级科学）
# ---------------------------------------------------------------------------
def parse_science():
    src = "r4c4gzpzyh-gif/six-science-quiz"
    f = os.path.join(SRC,"r4c4gzpzyh-gif_six-science-quiz-second-20260530-build-by-sherry-su","questions1116.js")
    txt = open(f, encoding="utf-8").read()
    m = re.search(r"const QUESTIONS\s*=\s*(\[.*?\])\s*;", txt, re.S)
    arr = json.loads(m.group(1))
    for it in arr:
        opts = it.get("options") or []
        options = [str(x) for x in opts]
        ai = it.get("answer")
        ans = options[ai] if isinstance(ai,int) and 0<=ai<len(options) else ai
        add(src, "questions1116.js", it.get("grade",6), "科学", "全", "",
            it.get("category"), it.get("type"), it.get("difficulty"),
            it.get("question"), options, ans, it.get("explanation"), [])

# ---------------------------------------------------------------------------
# 10) holidaysss/Calculator —— Exercises.txt(GBK) + Answers.txt(UTF-8)
# ---------------------------------------------------------------------------
def parse_calc():
    src = "holidaysss/Calculator"
    ex = open(os.path.join(SRC,"holidaysss_Calculator","Exercises.txt"),encoding="gb18030",errors="replace").read().splitlines()
    an = open(os.path.join(SRC,"holidaysss_Calculator","Answers.txt"),encoding="utf-8",errors="replace").read().splitlines()
    for i, line in enumerate(ex, 1):
        m = re.match(r"\s*(\d+)\s*[.、]\s*(.*)", line)
        if not m: continue
        body = m.group(2).strip()
        # 去掉行内已填答案：形如 "= 51"
        body_clean = re.sub(r"=\s*.+$","= ?", body).strip()
        ans = ""
        if i-1 < len(an):
            am = re.match(r"\s*(\d+)\s*[.、]\s*(.*)", an[i-1])
            if am: ans = am.group(2).strip()
        add(src, "Exercises.txt", "跨年级", "数学", "全", "", "", "计算题",
            None, body_clean, None, ans, "", [])

# ---------------------------------------------------------------------------
# 语文素材：jacksonrick/learn-everyday（诗词/生字/词语，非问答）
# ---------------------------------------------------------------------------
def parse_chinese_material():
    src = "jacksonrick/learn-everyday"
    base = os.path.join(SRC,"jacksonrick_learn-everyday","api/app/seed/data")
    for f, kind in [("poems_primary.json","古诗词"),("chars_primary.json","生字"),
                    ("words_primary.json","词语")]:
        p = os.path.join(base, f)
        if not os.path.exists(p): continue
        d = json.load(open(p, encoding="utf-8"))
        items = d.get("items", d) if isinstance(d, dict) else d
        for it in items:
            it["_kind"] = kind
            it["source"] = src
            supplementary.append(it)

# ---------------------------------------------------------------------------
# 11) wuwangzhang1216/congcong-school（数据来自 ChinaTextbookStudyFree 的
#     GitHub Release：v1.8.3-web-resources/data.zip）
#     结构：books/<bookId>/outline.json(grade/subject/semester)
#            + books/<bookId>/lessons/*.json(questions[])
#     学科：g*=数学, chinese*=语文, english*=英语, science*=科学
#     每题含 question/options/answer/difficulty(1-5)/explanation/knowledge_point/type
# ---------------------------------------------------------------------------
def parse_congcong():
    src = "congcong-school"
    base = os.path.join(SRC, "congcong-school-data", "books")
    if not os.path.isdir(base):
        print("  (skip) congcong-school-data 缺失"); return
    SUBJ = {"math":"数学","chinese":"语文","english":"英语","science":"科学"}
    TYPE = {"choice":"选择题","true_false":"判断题","fill_blank":"填空题",
            "fill_blank_text":"填空题","calculation":"计算题","matching":"连线题",
            "word_order":"其他"}
    seen = set()      # 跨版本去重 (grade,subject,question,answer)
    cnt = 0; dropped = 0
    for bf in sorted(glob.glob(os.path.join(base, "*", "outline.json"))):
        out = json.load(open(bf, encoding="utf-8"))
        bid = out.get("bookId", "")
        if bid.startswith("science"): subj = "科学"
        elif bid.startswith("chinese"): subj = "语文"
        elif bid.startswith("english"): subj = "英语"
        elif bid.startswith("g"): subj = "数学"
        else: subj = "综合"
        grade = out.get("grade")
        if not (isinstance(grade, int) and 1 <= grade <= 6): continue
        volume = "上" if bid.endswith("up") else ("下" if bid.endswith("down") else "全")
        lessons_dir = os.path.join(os.path.dirname(bf), "lessons")
        if not os.path.isdir(lessons_dir): continue
        for lf in sorted(glob.glob(os.path.join(lessons_dir, "*.json"))):
            try:
                d = json.load(open(lf, encoding="utf-8"))
            except Exception:
                continue
            lesson_title = d.get("title", "")
            for q in d.get("questions", []):
                # 人工校正：congcong 语文中部分「部首查字法 / 填一个数字」类题目
                # 被源标为 calculation(计算题)，实际应为填空题
                if subj == "语文" and q.get("type") == "calculation":
                    qtype = "填空题"
                else:
                    qtype = TYPE.get(q.get("type"), "其他")
                opts = q.get("options") or []
                raw_ans = q.get("answer")
                ans = raw_ans
                options = None
                if qtype == "选择题" and isinstance(opts, list) and opts:
                    options = [str(o) for o in opts]
                    # 答案多为正确选项原文，转成字母
                    if isinstance(raw_ans, str):
                        if raw_ans in options:
                            ans = chr(ord("A") + options.index(raw_ans))
                        elif raw_ans in ("A","B","C","D","E","F"):
                            ans = raw_ans
                    elif isinstance(raw_ans, int) and 0 <= raw_ans < len(options):
                        ans = chr(ord("A") + raw_ans)
                key = (grade, subj, str(q.get("question","")).strip(),
                       str(ans).strip())
                if key in seen:
                    dropped += 1; continue
                seen.add(key)
                kp = q.get("knowledge_point") or []
                if not isinstance(kp, list): kp = [str(kp)]
                add(src, f"{bid}/lessons/{os.path.basename(lf)}", grade, subj,
                    volume, lesson_title, q.get("knowledge_point"), qtype,
                    str(q.get("difficulty")), q.get("question"),
                    options, ans, q.get("explanation"), kp)
                cnt += 1
    print(f"  congcong-school 录入: {cnt} (去重跳过 {dropped})")

# ---------------------------------------------------------------------------
# 12) chenzhuanxin/xianning-teaching-resources —— 期末真题试卷(HTML)
#     交付物/03_期末真题试卷/HTML/*.html（共 385 套：小学 140 + 初中/高中 245）
#     每文件 = 题卷(<div class="paper">) + 答案卷(<div class="paper ans">)
# ---------------------------------------------------------------------------
class _XNParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ans_mode = False; self.depth = 0
        self.q_open = False; self.a_open = False; self.in_analy = False
        self.in_no = False; self.in_sc = False; self.in_val = False; self.in_opts = False
        self.opt_line = None; self.q = None; self.a = None
        self.questions = []; self.answers = []; self.section = None
        self._part_depth = -1; self._opts_depth = -1; self._in_part = False
    def handle_starttag(self, tag, attrs):
        d = dict(attrs); cls = d.get("class","")
        if tag == "div":
            self.depth += 1
            if cls == "paper ans":
                self.ans_mode = True
            if not self.ans_mode:
                if cls == "part":
                    self.section = ""; self._in_part = True; self._part_depth = self.depth
                elif cls == "q":
                    self.q = {"no":"","text":"","opts":[],"section":self.section}
                    self.q_open = True; self.q_depth = self.depth
                elif cls == "no": self.in_no = True
                elif cls == "sc": self.in_sc = True
                elif cls == "opts":
                    self.in_opts = True; self._opts_depth = self.depth
                elif cls == "bline": pass
                elif self.in_opts and cls == "": self.opt_line = []
            else:
                if cls == "q":
                    self.a = {"no":"","topic":"","val":"","analy":""}
                    self.a_open = True; self.a_depth = self.depth
                elif cls == "q analy": self.in_analy = True
                elif cls == "no": self.in_no = True
                elif cls == "val": self.in_val = True
        elif tag == "span":
            d2 = dict(attrs); c2 = d2.get("class","")
            if c2 == "no": self.in_no = True
            elif c2 == "sc": self.in_sc = True
            elif c2 == "val": self.in_val = True
    def handle_endtag(self, tag):
        if tag == "span":
            self.in_no = False; self.in_sc = False; self.in_val = False
        if tag == "div":
            if self.in_opts and self.opt_line is not None and not self.ans_mode:
                t = "".join(self.opt_line).strip()
                if t: self.q["opts"].append(t)
                self.opt_line = None
            if self.q_open and self.depth == self.q_depth:
                self.q["text"] = re.sub(r"\s+"," ",self.q["text"]).strip()
                self.questions.append(self.q); self.q_open = False
            if self.a_open and self.depth == self.a_depth:
                self.a["topic"] = re.sub(r"\s+"," ",self.a["topic"]).strip()
                self.answers.append(self.a); self.a_open = False
            if self.ans_mode and self.in_analy: self.in_analy = False
            if self._in_part and self.depth == self._part_depth: self._in_part = False
            if self.in_opts and self.depth == self._opts_depth: self.in_opts = False
            self.depth -= 1
    def handle_data(self, data):
        if self.ans_mode:
            if self.in_analy and self.answers:
                self.answers[-1]["analy"] = (self.answers[-1]["analy"] + data).strip()
            elif self.a_open:
                if self.in_no: self.a["no"] = data
                elif self.in_val: self.a["val"] += data
                elif not self.in_no and not self.in_val: self.a["topic"] += data
        else:
            if self.in_opts:
                if self.opt_line is not None: self.opt_line.append(data)
            elif self.q_open:
                if self.in_no: self.q["no"] = data
                elif self.in_sc: pass
                else: self.q["text"] += data
            elif self._in_part: self.section += data

# 全学段年级前缀（小学 + 初中 + 高中），用于从文件名识别年级
XN_GRADES = ["一年级","二年级","三年级","四年级","五年级","六年级",
             "七年级","八年级","九年级","高一","高二","高三"]
def _xn_classify(q, a):
    opts = q["opts"]
    is_choice = bool(opts) and any(re.match(r"^[A-D][\.、\s]", o) for o in opts)
    if is_choice:
        # 把一行 "A. x  B. y  C. z  D. w" 拆成单独选项
        parts = re.split(r"(?=[A-D][\.、])", opts[0])
        options = [p.strip() for p in parts if p.strip()]
        return "选择题", options
    ans = (a.get("val") or "").strip()
    if ans in ("对","错","正确","错误","√","×","√．","×．","T","F"):
        return "判断题", None
    return "填空题", None

def parse_xianning():
    src = "xianning-teaching-resources"
    d = os.path.join(SRC, "xianning-teaching-resources", "交付物", "03_期末真题试卷", "HTML")
    if not os.path.isdir(d):
        print("  (skip) xianning HTML 缺失"); return
    cnt = 0; skipped = 0
    for f in sorted(glob.glob(os.path.join(d, "*.html"))):
        base = os.path.basename(f)
        grade = next((g for g in XN_GRADES if base.startswith(g)), None)
        if not grade:
            continue   # 仅解析已识别的学段（小学/初中/高中）
        rest = base[len(grade):]; subject = rest.split("_")[0]
        subject = "道法" if ("道德与法治" in subject or "思想政治" in subject) else norm_subject(subject)
        html = open(f, encoding="utf-8").read()
        # 学期（上下）
        if re.search(r"第一学期|上学期", html): volume = "上"
        elif re.search(r"第二学期|下学期", html): volume = "下"
        else: volume = "全"
        p = _XNParser(); p.feed(html)
        nq, na = len(p.questions), len(p.answers)
        for i in range(min(nq, na)):
            q = p.questions[i]; a = p.answers[i]
            qtype, options = _xn_classify(q, a)
            # 题干中的 〔标签〕 提取为 topic
            m = re.search(r"〔([^〕]+)〕", q["text"])
            topic = m.group(1) if m else ""
            question = re.sub(r"〔[^〕]*〕", "", q["text"]).strip()
            ans = (a.get("val") or "").strip()
            if qtype == "判断题":
                ans = {"T":"对","F":"错","√":"对","×":"错"}.get(ans, ans)
                options = None
            elif qtype == "填空题":
                options = None
                if q["opts"]:
                    question = question + "\n" + "\n".join(q["opts"])
            add(src, base, grade, subject, volume, q.get("section"), topic,
                qtype, None, question, options, ans, a.get("analy"), [])
            cnt += 1
        if nq != na:
            skipped += (na - nq) if na > nq else 0
    print(f"  xianning 期末真题 录入: {cnt} (遗漏尾随答案 {skipped})")

# ---- run all parsers ----
for fn in [parse_thl529, parse_mastomato, parse_tvsafety,
           parse_cnmath_taxonomy,
           parse_aden, parse_cy0754, parse_quizmate, parse_h517,
           parse_science, parse_calc, parse_chinese_material,
           parse_congcong, parse_xianning]:
    try:
        fn()
    except Exception as e:
        print("PARSER ERROR", fn.__name__, e)

print("total question records:", len(records))
print("supplementary (语文素材):", len(supplementary))

# ---- 按 年级/学科 归档 ----
by_grade = collections.defaultdict(lambda: collections.defaultdict(list))
for r in records:
    by_grade[r["grade"]][r["subject"]].append(r)

for grade, subs in by_grade.items():
    gdir = os.path.join(OUT, grade)
    os.makedirs(gdir, exist_ok=True)
    for subj, recs in subs.items():
        with open(os.path.join(gdir, f"{subj}.json"), "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=1)

# ---- 统一 JSONL ----
with open(os.path.join(OUT_UNI,"小学题库_统一格式.jsonl"),"w",encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False)+"\n")

# ---- 统一 CSV ----
cols = ["id","source","source_file","grade","subject","volume","chapter",
        "topic","type","difficulty","difficulty_weight","difficulty_raw","question",
        "options","answer","explanation","knowledge_points"]
with open(os.path.join(OUT_UNI,"小学题库_统一格式.csv"),"w",encoding="utf-8-sig",newline="") as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for r in records:
        w.writerow([
            r["id"], r["source"], r["source_file"], r["grade"], r["subject"],
            r["volume"], r["chapter"], r["topic"], r["type"], r["difficulty"],
            r["difficulty_weight"], r["difficulty_raw"], r["question"],
            json.dumps(r["options"], ensure_ascii=False) if r["options"] else "",
            r["answer"], r["explanation"],
            json.dumps(r["knowledge_points"], ensure_ascii=False),
        ])

# ---- 语文素材 ----
with open(os.path.join(OUT_UNI,"语文素材_诗词生字词语.json"),"w",encoding="utf-8") as fh:
    json.dump(supplementary, fh, ensure_ascii=False, indent=1)

# ---- SQLite 数据库（便于直接入库）----
import sqlite3
db_path = os.path.join(OUT_UNI, "小学题库.db")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, source TEXT, source_file TEXT, grade TEXT, subject TEXT,
  volume TEXT, chapter TEXT, topic TEXT, type TEXT, difficulty TEXT,
  difficulty_weight REAL, difficulty_raw TEXT, question TEXT,
  options TEXT, answer TEXT, explanation TEXT, knowledge_points TEXT)''')
for r in records:
    cur.execute('INSERT OR REPLACE INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (r["id"], r["source"], r["source_file"], r["grade"], r["subject"], r["volume"],
         r["chapter"], r["topic"], r["type"], r["difficulty"], r["difficulty_weight"],
         r["difficulty_raw"], r["question"],
         json.dumps(r["options"], ensure_ascii=False) if r["options"] else None,
         r["answer"], r["explanation"],
         json.dumps(r["knowledge_points"], ensure_ascii=False)))
con.commit()
print(f"\nSQLite 已生成: {db_path}  ({len(records)} 行, {os.path.getsize(db_path)} bytes)")

# ---- 统计 ----
print("\n===== 按年级/学科 题量 =====")
for grade in ["一年级","二年级","三年级","四年级","五年级","六年级",
              "七年级","八年级","九年级","高一","高二","高三","跨年级"]:
    if grade in by_grade:
        subs = by_grade[grade]
        tot = sum(len(v) for v in subs.values())
        print(f"  {grade}: 共 {tot} 题  { {k:len(v) for k,v in subs.items()} }")

print("\n===== 按来源 题量 =====")
bysrc = collections.Counter(r["source"] for r in records)
for s,c in bysrc.most_common():
    print(f"  {s}: {c}")

print("\n===== 按题型 题量 =====")
bytype = collections.Counter(r["type"] for r in records)
print("  ", dict(bytype))

# 保存统计供 README 使用
stats = {
    "grade": {g: sum(len(v) for v in s.values()) for g,s in by_grade.items()},
    "source": dict(bysrc),
    "type": dict(bytype),
    "total": len(records),
}
json.dump(stats, open(os.path.join(OUT_UNI,"_stats.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
