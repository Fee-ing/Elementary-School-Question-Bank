# -*- coding: utf-8 -*-
"""
智能组卷脚本（小学阶段） —— 基于 difficulty_weight 难度权重
========================================================================
读取 output/小学题库.db，按「年级 + 学科 + 题型配额 + 难度策略」智能抽题组卷。

难度策略（两种，任选其一）：
  1) 难度带配比  --band-ratio 3:5:2   （基础:中等:提高，默认）
  2) 目标平均分  --target-weight 0.55 （让整卷 realized 平均难度尽量贴近目标值）

输出：
  - 一份 Markdown 试卷（题干 + 选项，不泄露答案）
  - 一份 Markdown 答案卷（答案 + 解析 + 难度标签）
  - 控制台打印难度分布与平均权重校验

仅处理小学（1~6 年级）。数据库若含初中/高中记录会被自动过滤。

用法示例：
  python3 smart_paper.py --grade 三年级 --subject 数学 --total 20
  python3 smart_paper.py --grade 六年级 --subject 语文 --total 25 --band-ratio 2:5:3
  python3 smart_paper.py --grade 四年级 --subject 英语 --total 18 --target-weight 0.50 --seed 7
  python3 smart_paper.py --grade 跨年级 --subject 科学 --total 30 --all-grades
"""
import os, sys, json, argparse, random, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "output", "小学题库.db")

PRIMARY = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
# 常见题型顺序（试卷排版用）
TYPE_ORDER = ["选择题", "判断题", "填空题", "计算题", "连线题", "简答题", "其他"]
BANDS = ["基础", "中等", "提高"]


def connect(db):
    if not os.path.exists(db):
        sys.exit(f"找不到数据库：{db}\n请先运行 build_dataset.py 生成题库。")
    return sqlite3.connect(db)


def band_of(weight):
    w = float(weight)
    if w < 0.40:
        return "基础"
    if w < 0.70:
        return "中等"
    return "提高"


def fetch_pool(cur, grade, subject, all_grades):
    """取候选题目（小学阶段）。返回 list[dict]。"""
    if all_grades or grade == "跨年级":
        grades = PRIMARY
    elif grade in PRIMARY:
        grades = [grade]
    else:
        sys.exit(f"年级参数错误：{grade}（仅支持 1~6 年级或 跨年级）")
    sql = (
        "SELECT id, grade, subject, type, difficulty, difficulty_weight, "
        "question, options, answer, explanation, knowledge_points, source "
        "FROM questions WHERE grade IN (%s) AND subject=?"
        % ",".join("?" * len(grades))
    )
    rows = cur.execute(sql, list(grades) + [subject]).fetchall()
    cols = ["id", "grade", "subject", "type", "difficulty", "difficulty_weight",
            "question", "options", "answer", "explanation", "knowledge_points", "source"]
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        d["difficulty_weight"] = float(d["difficulty_weight"])
        d["options"] = json.loads(d["options"]) if d["options"] else None
        d["knowledge_points"] = json.loads(d["knowledge_points"]) if d["knowledge_points"] else []
        out.append(d)
    return out


def default_quota(subject, total):
    """按学科给出一份合理的默认题型配额（数量合计=total）。"""
    if subject == "数学":
        return {"选择题": max(4, total // 5), "填空题": max(4, total // 4),
                "计算题": total - max(4, total // 5) - max(4, total // 4)}
    if subject == "语文":
        return {"选择题": max(4, total // 4), "填空题": max(4, total // 3),
                "判断题": max(3, total // 6),
                "其他": total - max(4, total // 4) - max(4, total // 3) - max(3, total // 6)}
    if subject == "英语":
        return {"选择题": max(6, total // 2), "填空题": max(4, total // 3),
                "判断题": total - max(6, total // 2) - max(4, total // 3)}
    if subject == "科学":
        return {"选择题": max(5, total // 2), "填空题": max(4, total // 3),
                "判断题": total - max(5, total // 2) - max(4, total // 3)}
    # 道法 / 综合 / 其他
    return {"选择题": max(5, total // 2), "判断题": max(4, total // 3),
            "填空题": total - max(5, total // 2) - max(4, total // 3)}


def sample_by_band(pool_by_type, quota, band_ratio, rng):
    """策略1：按难度带配比抽题。band_ratio 为 (基础,中等,提高) 权重元组。"""
    chosen = []
    rsum = sum(band_ratio) or 1
    for t, n in quota.items():
        sub = [q for q in pool_by_type.get(t, [])]
        if len(sub) <= n:
            chosen += sub
            continue
        # 按 ratio 把 n 拆到三个难度带
        counts = {}
        allocated = 0
        for i, b in enumerate(BANDS):
            c = (n * band_ratio[i]) // rsum if i < 2 else (n - allocated)
            counts[b] = max(0, c)
            allocated += counts[b]
        # 在每带内随机抽
        by_band = collections.defaultdict(list)
        for q in sub:
            by_band[band_of(q["difficulty_weight"])].append(q)
        picked = []
        for b in BANDS:
            cand = by_band.get(b, [])
            need = min(counts.get(b, 0), len(cand))
            picked += rng.sample(cand, need) if need else []
        # 若某带样本不足，用其余带补足，保持总数 n
        if len(picked) < n:
            used = set(id(q) for q in picked)
            rest = [q for q in sub if id(q) not in used]
            rng.shuffle(rest)
            picked += rest[: n - len(picked)]
        chosen += picked[:n]
    return chosen


def sample_by_target(pool_by_type, quota, target, rng):
    """策略2：目标平均分 —— 在每个题型内贪心挑选，使 realized 平均权重贴近 target。"""
    chosen = []
    for t, n in quota.items():
        sub = pool_by_type.get(t, [])
        if len(sub) <= n:
            chosen += sub
            continue
        chosen += pick_closest_mean(sub, n, target, rng)
    return chosen


def pick_closest_mean(pool, n, target, rng):
    """目标平均分抽题：使整卷 realized 平均难度权重贴近 target，
    同时强制 基础/提高 两带都至少出现（避免退化为清一色“中等”）。
    做法：按难度带分组 -> 计算各带代表均值 -> 枚举 (基础,中等,提高) 数量分配，
    取使带加权均值最接近 target 的组合 -> 各带随机抽相应数量。
    """
    bands = {"基础": [], "中等": [], "提高": []}
    for q in pool:
        bands[band_of(q["difficulty_weight"])].append(q)
    mu = {}
    for b, lst in bands.items():
        mu[b] = (sum(q["difficulty_weight"] for q in lst) / len(lst)) if lst else None
    avail = {b: len(lst) for b, lst in bands.items()}

    # 枚举数量分配 (a,b,c)，强制 a>=1 且 c>=1 保证难度带多样性
    best = None
    for a in range(1, n - 1):
        for b in range(1, n - a):
            c = n - a - b
            if c < 1:
                continue
            if avail["基础"] < a or avail["中等"] < b or avail["提高"] < c:
                continue
            if mu["基础"] is None or mu["中等"] is None or mu["提高"] is None:
                continue
            mean = (a * mu["基础"] + b * mu["中等"] + c * mu["提高"]) / n
            err = abs(mean - target)
            if best is None or err < best[0]:
                best = (err, a, b, c)
    if best is None:
        # 某带样本不足或不可行：退化为离 target 最近的 n 个
        pool2 = sorted(pool, key=lambda q: abs(q["difficulty_weight"] - target))
        s = pool2[:n]
        rng.shuffle(s)
        return s
    _, a, b, c = best
    sel = []
    for band, cnt in (("基础", a), ("中等", b), ("提高", c)):
        lst = bands[band]
        sel += rng.sample(lst, cnt) if cnt <= len(lst) else lst
    rng.shuffle(sel)  # 打乱顺序，避免同难度扎堆
    return sel


def render_question_body(q, idx):
    """渲染题干与选项（不泄露答案）。"""
    lines = [f"{idx}. （{q['type']}）{q['question']}"]
    opts = q.get("options")
    if opts:
        for k, o in enumerate(opts):
            lines.append(f"    {chr(65 + k)}. {o}")
    elif q["type"] == "判断题":
        lines.append("    （    ）")
    elif q["type"] == "填空题":
        lines.append("    ____________")
    return "\n".join(lines)


def build_paper(grade_label, subject, chosen, strategy_desc):
    chosen.sort(key=lambda q: (TYPE_ORDER.index(q["type"]) if q["type"] in TYPE_ORDER else 99,
                               q["grade"]))
    # 试卷
    paper = [f"# {grade_label}{subject} 智能组卷", ""]
    paper.append(f"> 组卷策略：{strategy_desc}　|　题量：{len(chosen)}　"
                 f"|　平均难度权重：{avg_weight(chosen):.3f}")
    paper.append("")
    idx = 1
    by_type = collections.OrderedDict()
    for t in TYPE_ORDER:
        by_type[t] = [q for q in chosen if q["type"] == t]
    for t, qs in by_type.items():
        if not qs:
            continue
        paper.append(f"## 一、{t}（共 {len(qs)} 题）")
        paper.append("")
        for q in qs:
            paper.append(render_question_body(q, idx))
            paper.append("")
            idx += 1
    # 答案卷
    answer = [f"# {grade_label}{subject} 智能组卷 · 答案与解析", ""]
    answer.append(f"> 平均难度权重：{avg_weight(chosen):.3f}　"
                  f"|　难度带分布：{band_dist(chosen)}")
    answer.append("")
    idx = 1
    for t, qs in by_type.items():
        if not qs:
            continue
        answer.append(f"## {t}")
        for q in qs:
            band = band_of(q["difficulty_weight"])
            ans = q["answer"] if q["answer"] else "（略）"
            expl = q["explanation"] if q["explanation"] else "（无解析）"
            answer.append(f"{idx}. 【{band} / w={q['difficulty_weight']:.2f}】答案：{ans}")
            answer.append(f"    解析：{expl}")
            idx += 1
        answer.append("")
    return "\n".join(paper), "\n".join(answer)


def avg_weight(chosen):
    if not chosen:
        return 0.0
    return sum(q["difficulty_weight"] for q in chosen) / len(chosen)


def band_dist(chosen):
    c = collections.Counter(band_of(q["difficulty_weight"]) for q in chosen)
    return " / ".join(f"{b}:{c.get(b,0)}" for b in BANDS)


def main():
    ap = argparse.ArgumentParser(description="小学智能组卷（基于 difficulty_weight）")
    ap.add_argument("--grade", default="三年级", help="年级：一年级~六年级 / 跨年级")
    ap.add_argument("--subject", default="数学", help="学科")
    ap.add_argument("--total", type=int, default=20, help="总题量")
    ap.add_argument("--db", default=DB_PATH, help="题库 sqlite 路径")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--all-grades", action="store_true", help="跨年级抽题（忽略 --grade 限制）")
    ap.add_argument("--band-ratio", default="3:5:2",
                    help="策略1 难度带配比 基础:中等:提高，如 3:5:2")
    ap.add_argument("--target-weight", type=float, default=None,
                    help="策略2 目标平均难度权重（0~1）。指定此项则启用目标平均分模式")
    ap.add_argument("--out", default=None, help="输出目录（默认 output/组卷样例）")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    con = connect(args.db)
    cur = con.cursor()

    grade_label = "跨年级" if (args.all_grades or args.grade == "跨年级") else args.grade
    pool = fetch_pool(cur, args.grade, args.subject, args.all_grades)
    if not pool:
        sys.exit(f"题库中无匹配记录：grade={grade_label} subject={args.subject}")
    print(f"候选题目数：{len(pool)}")

    quota = default_quota(args.subject, args.total)
    # 去掉数量为0的题型
    quota = {t: n for t, n in quota.items() if n > 0}
    print("题型配额：", quota)

    pool_by_type = collections.defaultdict(list)
    for q in pool:
        pool_by_type[q["type"]].append(q)

    if args.target_weight is not None:
        strategy = f"目标平均分 w≈{args.target_weight:.2f}"
        chosen = sample_by_target(pool_by_type, quota, args.target_weight, rng)
    else:
        try:
            br = tuple(int(x) for x in args.band_ratio.split(":"))
            assert len(br) == 3
        except Exception:
            sys.exit("--band-ratio 需为 基础:中等:提高 三段整数，如 3:5:2")
        strategy = f"难度带配比 基础:中等:提高={br[0]}:{br[1]}:{br[2]}"
        chosen = sample_by_band(pool_by_type, quota, br, rng)

    if len(chosen) < args.total:
        print(f"注意：候选不足，实际组卷 {len(chosen)} 题（目标 {args.total}）。")

    paper_md, answer_md = build_paper(grade_label, args.subject, chosen, strategy)

    out_dir = args.out or os.path.join(HERE, "output", "组卷样例")
    os.makedirs(out_dir, exist_ok=True)
    safe = f"{grade_label}_{args.subject}"
    p_path = os.path.join(out_dir, f"{safe}_试卷.md")
    a_path = os.path.join(out_dir, f"{safe}_答案.md")
    with open(p_path, "w", encoding="utf-8") as f:
        f.write(paper_md)
    with open(a_path, "w", encoding="utf-8") as f:
        f.write(answer_md)

    print("\n" + "=" * 48)
    print(f"组卷完成：{grade_label}{args.subject}  题量 {len(chosen)}")
    print(f"平均难度权重：{avg_weight(chosen):.3f}  （目标策略：{strategy}）")
    print(f"难度带分布：{band_dist(chosen)}")
    print("题型分布：", dict(collections.Counter(q["type"] for q in chosen)))
    print(f"试卷：{p_path}")
    print(f"答案：{a_path}")
    con.close()


if __name__ == "__main__":
    main()
