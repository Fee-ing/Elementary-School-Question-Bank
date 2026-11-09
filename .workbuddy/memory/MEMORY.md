# 小学题库项目 · 长期记忆

## 范围约束
- **仅小学（1~6 年级）**。xianning 仓库含 385 套全学段试卷，但按用户要求只解析 140 套小学卷；初中/高中 245 套在 `parse_xianning` 内被 `norm_grade_num(grade) > 6` 过滤掉，不入库。
- Word_PDF 版 xianning 资源本地未克隆，未解析。

## 核心字段
- `difficulty_weight`：0.10~1.00 浮点难度权重，越高越难，用于组卷按难度分配。
- `difficulty`：基础(<0.40)/中等(0.40~0.70)/提高(>0.70)。
- congcong 显式难度 1-5 映射：基础 0.25/0.38、中等 0.55、提高 0.82/0.92。

## 已知数据修正
- congcong 语文「部首查字法/填数字」源标 `calculation`，已规则化为「填空题」（`语文 且 type=calculation → 填空题`）。

## 复现与组卷
- 归一化：`python3 build_dataset.py`（读 `_sources/`，生成 `data/`、`output/` 的 jsonl/csv/db）。
- 智能组卷：`python3 smart_paper.py --grade 三年级 --subject 数学 --total 20`，支持 `--band-ratio` 与 `--target-weight` 两策略，输出到 `output/组卷样例/`。

## 关键源仓库
- congcong-school（34,213，全科，AI生成需复审）｜ xianning（3,734 小学真题卷）｜ xiaoyang111222（5,736）｜ holidaysss（10,000 四则运算，跨年级）｜ h517061544（7,020）｜ mastomato（3,574）。
