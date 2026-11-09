# 小学题库 · GitHub 采集与统一整理

> 工作区：`/Users/BGZB002/Downloads/小学题库`
> 采集日期：2026-11-09 ｜ 来源：GitHub 关键词搜索「小学 题库」+ 多轮扩展检索（英语/道法/科学/期末真题等）

## 1. 任务概述

1. 在 GitHub 搜索「小学 题库」相关仓库（共命中 **53** 个），并多轮扩展检索补充学科缺口；
2. 逐一检查每个仓库，判断是否包含可下载的**小学题库数据**（pdf / json / txt / csv / js 等）；
3. 将含数据的仓库克隆到工作区 `_sources/`；
4. 按**年级**整理归档（`data/<年级>/<学科>.json`）；
5. 归一化为**便于入库**的统一格式（JSONL / CSV / SQLite），并为每题增加**难度权重**字段用于组卷分配。

## 2. 检索与筛选结果

- 首轮命中 53 个仓库；扩展检索又发现 `xiaoyang111222/cn-math-taxonomy`（超全小学题库）等。
- 含数据的仓库中，已纳入统一问答题库；`jacksonrick/learn-everyday` 为语文课内素材（非问答，单独存放）；`cuigu/math-resource-library` 为 PDF 参考资料（未结构化）。
- **重大修复**：原先 `norm_subject` 因「语」子串匹配，把全部「英语」误判为「语文」（`mastomato` 的 1,983 道英语题被错标），已修复，英语学科现已正确恢复并跨 1–6 年级全覆盖。

| 仓库 | Star | 内容 | 年级 | 学科 | 题量 |
|---|---|---|---|---|---|
| `wuwangzhang1216/congcong-school` | 1.3k | 免费开源小学全科平台题库（数据来自 ChinaTextbookStudyFree 的 GitHub Release `v1.8.3-web-resources/data.zip`，**本轮新增**） | 1–6 年级 | 数/语/英/科 | 34,213（去重后）|
| `chenzhuanxin/xianning-teaching-resources` | 0 | 湖北省咸宁市中小学期末真题试卷（HTML，140 套小学卷，**本轮新增**） | 1–6 年级 | 数/语/英/科/道法 | 3,734 |
| `xiaoyang111222/cn-math-taxonomy` | 5 | 知识点题库（questions.json + topics.json） | 1–6 年级 | 数/英/语/科/道法 | 5,736（小学段）|
| `thl529/question-bank` | 1 | 选择题题库（36 个 JSON 文件） | 1–6 年级 | 语/数/英（上·下册） | 1,354 |
| `mastomato/zhixing-tv-quiz` | 0 | 电视答题 App 内置题库 | 1–6 年级（上） | 语/数/英/科 | 3,574（小学部分）|
| `h517061544/test` | 0 | 3 年级综合题库（jsonl） | 三年级 | 数/语/英/综合 | 7,020 |
| `r4c4gzpzyh-gif/six-science-quiz` | 0 | 六年级科学真题库（js） | 六年级 | 科学 | 1,116 |
| `Aden357-234/quiz-practice` | 0 | 常识/道法题库（js） | 1–3 / 4–6 | 综合 | 270 |
| `zhubing3170/TvSafetyLock` | 1 | 电视答题题库 | 1–6 年级 | 语/英 | 96 |
| `cy-0754/tiku-studio` | 1 | 自编卷种子题库 | 一年级 | 数/语 | 90 |
| `dezhiguan/quizmate` | 0 | 数学小题库 | 2–6 年级 | 数学 | 5 |
| `holidaysss/Calculator` | 5 | 四则运算自动生成题库 | 跨年级 | 数学 | 10,000 |
| `jacksonrick/learn-everyday` | 0 | 课内古诗词/生字/词语（**素材，非问答**） | 1–6 年级 | 语文 | 3,028 |
| `cuigu/math-resource-library` | 3 | PDF 习题/练习卷（**参考资料，未结构化**） | 四年级 | 数学 | —（PDF）|

> 重复/跳过：`meikis/cn-math-taxonomy` 是 `xiaoyang111222` 的近似子集（相同 `cnm_/cne_/cns_` 题号），为避免重复已跳过；`sijie-yin/pure-math-taxonomy`（旧版数学 864 题）已被 `xiaoyang111222` 的小学数学（1,136 题）覆盖，解析时不再单独计入。`mengxiaoyucc/MidAnswer`、`CC-1368/primary-school-math-bank` 等为答题/组卷**应用框架**，仓库内无原始数据；`superorcz/math-question-bank`、`cbicbicn/xxsjs` 为空仓库。
>
> 扩展检索中已并入的两个资源：`wuwangzhang1216/congcong-school`（题库以 GitHub Release 压缩包 `data.zip` 分发，已下载并解析，含 85 个教材分册、显式难度 1–5）；`chenzhuanxin/xianning-teaching-resources`（385 套期末真题，已稀疏克隆仅取 HTML 试卷，结构化解析 140 套小学卷的题干/选项/答案/解析）。

## 3. 统一数据格式（Schema）

所有题目归一到以下字段，**一行一条**，直接可用于数据库导入。

| 字段 | 说明 |
|---|---|
| `id` | 全局唯一 ID（来源缩写 + 序号） |
| `source` | 来源仓库 `owner/repo` |
| `source_file` | 原文件名 |
| `grade` | 年级：`一年级`…`六年级` / `跨年级` |
| `subject` | 学科：`语文`/`数学`/`英语`/`科学`/`道法`/`综合` |
| `volume` | 册：`上`/`下`/`全` |
| `chapter` | 章节 / 单元 |
| `topic` | 知识点 / 类别 |
| `type` | 题型：`选择题`/`判断题`/`填空题`/`计算题`/`连线题`/`简答题`/`其他` |
| `difficulty` | 难度（归一化等级）：`基础`/`中等`/`提高` |
| `difficulty_weight` | **难度权重**（0.10~1.00 浮点，越高越难），用于组卷时按难度分配题量 |
| `difficulty_raw` | 原始难度值（保留原样） |

### 难度权重（`difficulty_weight`）说明

- **已有来源难度**：直接映射为基础 0.30 / 中等 0.55 / 提高 0.80（覆盖 `basic/standard/advanced`、`easy/medium/hard`、`基础/中等/提高`、数值 `1/2/3` 等）。`congcong-school` 采用显式数值难度 `1–5`，映射为基础 `(1–2→0.25/0.38)` / 中等 `(3→0.55)` / 提高 `(4–5→0.82/0.92)`。
- **无来源难度时**：按「年级基线 + 题型偏移」启发式估算（一年级 0.25 → 六年级 0.90，计算/简答高于选择/判断）。
- 组卷用法示例：要出一份「基础 30% / 中等 50% / 提高 20%」的试卷，可按 `difficulty_weight` 分箱（<0.4 / 0.4–0.7 / >0.7）加权随机抽题。
| `question` | 题干 |
| `options` | 选项（JSON 数组，无则为空） |
| `answer` | 答案（已解析为文本） |
| `explanation` | 解析 |
| `knowledge_points` | 知识点（JSON 数组） |

## 4. 目录结构

```
小学题库/
├── _sources/                 # 原始仓库克隆（含全部源文件，便于溯源）
├── data/                     # 【按年级归档】小学问答题库
│   ├── 一年级/   数学.json 语文.json 英语.json 科学.json 道法.json
│   ├── 二年级/   ...
│   ├── 三年级/  数学.json 语文.json 英语.json 科学.json 道法.json 综合.json
│   ├── 四年级/  ...
│   ├── 五年级/  ...
│   ├── 六年级/  数学.json 语文.json 英语.json 科学.json 道法.json
│   └── 跨年级/   数学.json 综合.json
├── output/
│   ├── 小学题库_统一格式.jsonl      # 每行一条，最通用的入库格式
│   ├── 小学题库_统一格式.csv        # UTF-8-BOM，可直接导入 MySQL/Postgres/Excel
│   ├── 小学题库.db                  # 已建好的 SQLite 数据库（表 questions）
│   ├── 语文素材_诗词生字词语.json    # jacksonrick 课内素材（非问答）
│   └── _stats.json                  # 统计信息
├── build_dataset.py           # 归一化脚本（可复现）
└── README.md
```

## 5. 统计数据

**按年级 / 学科（问答题库合计 67,208 题）**

| 年级 | 数学 | 语文 | 英语 | 科学 | 道法 | 综合 | 小计 |
|---|---|---|---|---|---|---|---|
| 一年级 | 3,023 | 1,645 | 103 | 1,044 | 263 | — | 6,078 |
| 二年级 | 3,309 | 1,975 | 118 | 797 | 263 | — | 6,462 |
| 三年级 | 8,747 | 2,845 | 2,958 | 1,512 | 245 | 880 | 17,187 |
| 四年级 | 3,293 | 2,036 | 2,514 | 1,600 | 241 | — | 9,684 |
| 五年级 | 3,296 | 1,990 | 2,455 | 1,837 | 245 | — | 9,823 |
| 六年级 | 1,649 | 1,455 | 2,339 | 2,032 | 229 | — | 7,704 |
| 跨年级 | 10,000 | — | — | — | — | 270 | 10,270 |

**按来源**：congcong-school 34,213 ｜ holidaysss 10,000 ｜ h517061544 7,020 ｜ xiaoyang111222 5,736 ｜ xianning 3,734 ｜ mastomato 3,574 ｜ thl529 1,354 ｜ r4c4gzpzyh 1,116 ｜ Aden357 270 ｜ zhubing3170 96 ｜ cy-0754 90 ｜ dezhiguan 5

**按学科（合计）**：数学 36,317 ｜ 语文 14,946 ｜ 英语 10,487 ｜ 科学 8,822 ｜ 综合 1,150 ｜ 道法 1,466

**按题型**：选择题 29,837 ｜ 计算题 16,184 ｜ 填空题 12,494 ｜ 判断题 8,070 ｜ 连线题 383 ｜ 其他 239 ｜ 简答题 1

**难度权重**：均值约 0.45，范围 0.25–0.92（含 congcong 的 5 级显式难度：基础 0.25/0.38、中等 0.55、提高 0.82/0.92）

## 6. 如何入库

- **JSONL**：`output/小学题库_统一格式.jsonl`，每行一个 JSON 对象，适合 MongoDB / Elasticsearch / 日志型库。
- **CSV**：`output/小学题库_统一格式.csv`（UTF-8-BOM，首行为列名），可直接用 `LOAD DATA` / `COPY` 导入 MySQL、PostgreSQL，或 Excel 打开。
- **SQLite**：`output/小学题库.db` 已建好，表名 `questions`，可直接 `SELECT` 或 `ATTACH` 迁移至其他数据库。

示例（PostgreSQL 导入 CSV）：
```sql
CREATE TABLE questions (
  id text PRIMARY KEY, source text, source_file text, grade text, subject text,
  volume text, chapter text, topic text, type text, difficulty text,
  difficulty_weight real, difficulty_raw text, question text,
  options jsonb, answer text, explanation text, knowledge_points jsonb
);
COPY questions FROM '/path/小学题库_统一格式.csv' WITH (FORMAT csv, HEADER true);
```

## 7. 数据质量与注意事项

- **年级/学科覆盖已基本完整**：`xiaoyang111222` 补齐了 **科学（1–6 年级）** 与 **道德与法治（1–6 年级）**，并补全了英语（3–6 年级，小学英语本自三年级起）。目前 语/数/英/科/道法 五科均已覆盖 1–6 年级（英语自三年级起，符合课标）。
- **自动生成内容占比高**：`holidaysss/Calculator`（10,000 条四则运算）与 `h517061544/test`（7,020 条，含大量生成题）为程序生成的练习，难度/解析较浅，建议按需筛选或仅作练习用途。
- **`跨年级`**：`holidaysss`（四则运算）与 `Aden357`（常识/道法，原文件按 1–3 / 4–6 分段）不归属单一年级，归入 `跨年级`。
- **答案已解析为文本**：选择题答案由原字母/下标解析为选项文本，便于直接入库。
- **许可证**：各源仓库许可证不同（多为 MIT / 未声明），商用或二次分发前请逐一确认各仓库 LICENSE。
- **非问答素材**：`jacksonrick` 的诗词/生字/词语为课内语文素材，未计入问答题库，单独存放于 `output/语文素材_诗词生字词语.json`。
- **congcong-school（AI 生成，需教师复审）**：该库题目与课文由 AI 生成，README 明确说明仍在接受教师复审，偶有可能表述不清或答案有争议；部分题型（如语文「部首查字法」）源数据 `type` 标为 `calculation`，已按源归一为「计算题」，介意可后续人工校正。难度为显式 1–5 级，已映射为权重。
- **xianning 期末真题（真题卷，含解析）**：140 套小学卷均带参考答案与解析，题型归一为选择题/判断题/填空题（原卷的填空/计算/解答/应用题统一归入填空题以便检索，原始题型可据题干与 `chapter` 判断）。英语卷中阅读判断（T/F）答案已统一规范为「对/错」。少数英语卷答案页比题页多 4 条（阅读判断题的子项），已按题序对齐、丢弃尾随孤儿答案（共 40 条），不影响题目完整性。
- **congcong 版本去重**：同一知识点在 `2026 课标修订版`/`旧版`/`五四制`/`精通版`等多套教材分册中重复出现，已按「年级+学科+题干+答案」全局去重（跳过 47 条完全重复）。

## 8. 复现

```bash
# 重新执行归一化（读取 _sources/，生成 data/ 与 output/）
python3 build_dataset.py
```
