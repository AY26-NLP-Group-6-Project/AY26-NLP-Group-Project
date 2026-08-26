# 选题 2 · Patch-Version-RAG：游戏补丁说明上的"版本感知 / 时间旅行"问答

> 推荐度：感觉最稳（独特、评测干净、演示直观） ｜ English: [README.md](README.md) ｜ [OneDrive 论文资料夹](Useful%20Paper.html)
> 一句话：以 League of Legends（或 Dota 2 / Minecraft）的全部补丁说明 + 英雄/物品页面为知识库，回答"13.5 版本 X 的 Q 技能冷却是多少？""X 什么时候被削弱？""14.1→14.10 之间 X 改了什么？""现在最新数值是？"，回答附补丁号引用；当检索到过期证据时明确警告。

---

## 1. 问题定义

### 1.1 任务形式化

- **输入**：自然语言问题 `q`，可显式或隐式带版本/时间信息。
- **知识库**：按版本组织的文档集合 `D = {d_{e,v}}`，`e` 为实体（英雄/技能/物品/地图机制），`v` 为版本号（如 `14.10`），每个版本的补丁说明段落 + 该版本快照下的实体页面。
- **输出**：答案 + 引用（补丁号 / 页面版本）+ "时效性状态"（`current / outdated / changed-in-between`）。
- **四类问题**（构成评测集的四个均衡子集）：
  1. **点时间查询（point-in-time）**："在 13.5 版本，Ahri 的 Q 基础伤害是多少？"
  2. **变更检测（change detection）**："Ahri 的 Q 上一次被削弱是哪个版本？""Zhonya 在 2024 年被改过几次？"
  3. **区间差异（diff）**："从 14.1 到 14.10，Yasuo 有哪些改动？"
  4. **最新状态（latest）**："现在 Kai'Sa 的 W 冷却是多少？"（要求系统找最新版本并声明版本号）
  另加一个对抗子集：**过期陷阱**——问题不带版本，但语料中同一实体多版本数值并存，系统必须选最新并提示历史变化（对应"证据冲突"研究线）。

### 1.2 为什么这个题目"值得做"

- [VersionRAG](https://arxiv.org/abs/2510.08109)（预印本，2025-10）报告朴素 RAG 在版本敏感问题上为 58%，GraphRAG 为 64%，其 VersionQA benchmark 只有 **100 题 / 34 文档**。本项目的 1,000+ 题新领域数据集是明确增量，但只有在许可允许发布、题目自然且人工核验充分时，才可进一步讨论资源论文价值。
- 同时覆盖两条 2025–2026 热线：**时间/版本感知 RAG**（TG-RAG、ChronoQA、IA-RAG）与 **证据冲突**（CONFLICTS、MAGIC、"Does RAG know when retrieval is wrong"）。
- 标注相对可控：若 wiki 模板和模块在 pilot 中可稳定解析，可半自动生成 QA 再逐条人工核验；**IAA >90% 只是待检验目标，不能预先保证**。
- 同届几乎不可能撞题；演示（时间轴滑块）直观。

### 1.3 评分点对应

| 作业评分点 | 本项目对应 |
|---|---|
| KB（20） | 版本化语料抓取与解析、版本-实体-变更三元组抽取、按"实体 × 版本"切分 |
| 检索（40） | 混合检索 + 版本过滤/路由 + 版本图索引 + 重排；元数据（时间线）检索是作业列出的创新方向 |
| 下游（40） | 版本感知生成、过期证据警告、变更摘要、EM/F1 + RAGAS |

---

## 2. 数据与知识库

### 2.1 候选语料（择一，首选 LoL）

| 游戏 | 来源 | 规模 | 许可/备注 |
|---|---|---|---|
| **League of Legends** | [官方 LoL Wiki](https://wiki.leagueoflegends.com) 与 [Riot 补丁说明](https://www.leagueoflegends.com/en-us/news/tags/patch-notes/) | 历史补丁与实体变更有望超过 10k chunk，须用 pilot 实测 | 先验证当前 Wiki API、robots 与文本复用/署名条款；Riot 内容和素材仍受版权及开发者政策约束 |
| Dota 2 | Valve 官方 changelog + Liquipedia / dota2.fandom | 类似 | Liquipedia CC BY-SA |
| Minecraft (Java) | Minecraft Wiki 版本历史页 | 大 | CC BY-NC-SA |
| 备选非游戏 | PyTorch / Python / Kubernetes changelog + 各版本文档 | 大 | 更"正经"但趣味性低 |

### 2.2 解析与切分

- 第一周先对 100 个页面/补丁验证 MediaWiki API、模板覆盖率与许可；只有 pilot 通过后才用 `mwparserfromhell` 解析 patch history，抽取 `(entity, ability, field, old_value, new_value, patch)` 变更三元组。
- 文档单元：`patch_note_chunk`（一个补丁中一个实体的全部改动，200–400 词）+ `entity_snapshot_chunk`（某版本下实体数值表，由三元组回放生成）。
- 元数据：`{entity, entity_type, patch, patch_date, season, change_type ∈ {buff, nerf, adjust, rework, new, removed}}`；版本号规范化为可比较的元组。
- 存储：JSONL + Pyserini 索引 + FAISS；版本图（实体节点 —变更边→ 版本节点）存 NetworkX / SQLite。

### 2.3 评测集（≥ 1,000 题，IAA ≥ 80%）

- 从三元组半自动生成四类问题模板，再改写成自然语言；**每题人工核验**答案、黄金证据、自然度与歧义。至少抽 20%–30% 由两名标注者独立核验，在裁决前分别计算答案一致率与问题可接受度 IAA，不能把两项合成一个不透明指标。
- 总计 ≥1,000 题，四类各约 250；其中 100–200 题同时标为过期陷阱（属于总数而非含糊的额外集合），另按类型报告。
- 格式：JSONL `{"qid","question","type","entity","patch_ref","answer","evidence_ids"}`，并附 qrels（每题的黄金 chunk）。
- 额外：50 题"自由形式变更摘要"题（区间 diff）配人工参考摘要，用 ROUGE/BERTScore + RAGAS。

---

## 3. 基线水准

| 层面 | 现有水平 | 来源 |
|---|---|---|
| 版本 QA | VersionQA 上，作者报告 naive RAG 58%、GraphRAG 64%、VersionRAG 90%；保留精确数字时在最终报告补表号 | [VersionRAG，预印本](https://arxiv.org/abs/2510.08109) |
| 时间图 RAG | 支持时间图、分层摘要和增量更新设计；旧版 0.599/0.405、6× 等精确数字在未补表号前删除 | [TG-RAG，预印本](https://arxiv.org/abs/2510.13590) |
| 时间敏感 QA 数据集 | 5,176 个中文新闻问题，涵盖 absolute/aggregate/relative 时间类型，支持问题类型设计 | [ChronoQA，预印本](https://arxiv.org/abs/2508.12282) |
| 冲突处理 | 支持 outdated/conflicting context 的分类和生成器行为分析；不把跨数据集现象写成游戏场景的既定结论 | [CONFLICTS](https://arxiv.org/abs/2506.08500)、[context compliance](https://arxiv.org/abs/2605.14473)（均为预印本） |
| 内部 v0 | BM25 / bge 稠密 / RRF / 重排（**不做版本过滤**）→ 预计 point-in-time 与 latest 类准确率 50–65%，diff/变更检测更低 | 本项目 |

---

## 4. 方式方法

### 4.1 架构

```
q ─► 意图分类 (point/change/diff/latest) + 实体/版本抽取 (规则 + 小模型)
  ─► 路由:
      point   → 版本过滤后的 混合检索 (BM25+dense+RRF) → 重排
      change  → 版本图上按实体遍历变更边 → 取相关 patch chunks
      diff    → 版本区间内该实体的全部变更 → 聚合
      latest  → 取最大版本快照 + 最近 N 次变更
  ─► 冲突/时效检查: 若候选中同一字段多版本值并存 → 标 outdated/current
  ─► LLM 生成 (引用 patch 号; 变更摘要; 过期警告)
  ─► UI: 时间轴滑块 + 实体卡片 + 变更表
```

### 4.2 检索创新（Q3，各自消融）

1. 混合检索 + 交叉编码重排（基本要求）。
2. **版本感知过滤/加权**：把版本约束变成硬过滤或软加权（距目标版本越近分越高）；对照"无版本约束"。
3. **版本图索引 + 路由（增强项）**：先证明简单版本元数据过滤有效，再实现 VersionRAG/TG-RAG 风格的图，避免把完整图系统设成最低交付条件。
4. **切分策略对比**：patch-note chunk vs 实体快照 chunk vs 两者并存；late chunking / contextual header 对照（见[共用 OneDrive 论文资料夹](../Common%20Useful%20Paper.html)）。
5. **查询改写**：把口语问题改写为"实体 + 字段 + 版本"的规范查询（HyDE / G-RAG 假设答案法对照）。

### 4.3 下游创新（Q5，需消融）

1. **过期证据警告与冲突感知生成**：同一字段多值时列出时间线并明确"截至 vX 为…"，参考 CONFLICTS 的 outdated 类型处理。
2. **变更摘要生成**：区间 diff 题用结构化三元组 + LLM 生成可读摘要，ROUGE/BERTScore 评估。
3. **自检忠实度**：答案中的每个数值必须能在引用 chunk 中找到（字符串/数值级核对），否则标黄。
4. **迭代检索**："X 上次被削弱后胜率如何"这类需要两跳的问题走 agentic 追加检索（可选）。
5. 可选：小模型 (Qwen3-1.7B/4B) 在生成题上 SFT，对比 zero-shot 8B。

### 4.4 评估

- 检索：P@k、R@k、MRR、nDCG@10（`ir_measures`）；按问题类型分别报告；**版本命中率**（top-k 中是否包含目标版本 chunk）。
- 生成：EM / F1（数值题）、ROUGE-L / BERTScore（摘要题）、RAGAS faithfulness / answer relevance / context precision；过期陷阱子集单独报告"是否提示过期"。
- 系统：延迟、索引时间、token 用量（对比 GraphRAG 类方法的成本）。

---

## 5. 验收标准（先宽松）

| 项目 | 最低门槛 | 期望 |
|---|---|---|
| KB | ≥ 10k chunk、≥ 100k 词，覆盖 ≥ 100 个补丁 | 全量补丁 + 全英雄快照 |
| 评测集 | ≥1,000 题、四类分层均衡、逐条人工核验；独立重标子集的答案一致率与可接受度均 ≥0.80 | ≥1,200 题，其中过期陷阱 ≥150 |
| 检索 | 版本感知混合检索相对 v0 nDCG@10 提升 ≥ 5 pt | 版本命中率@5 ≥ 0.85 |
| 生成 | point/latest EM ≥ 0.70；change 类 EM ≥ 0.55；diff 类 ROUGE-L ≥ 0.35 | point ≥ 0.85；过期陷阱提示率 ≥ 0.7 |
| RAGAS | faithfulness ≥ 0.8 | ≥ 0.9 |
| 性能 | 端到端 ≤ 5 s | ≤ 2 s（图路径查询更快） |
| UI | 时间轴滑块 + 引用可点击；5 条示例查询计时 | — |

---

## 6. 论文校验与用途（[OneDrive 论文资料夹](Useful%20Paper.html)）

| 已核验来源 | 用途与边界 |
|---|---|
| [VersionRAG](https://arxiv.org/abs/2510.08109)（预印本） | **直接模板**：版本化 QA、层级版本图、意图路由与隐式变更检测；100 题/34 文档是已核验的规模依据。 |
| [TG-RAG](https://arxiv.org/abs/2510.13590)（预印本） | 时间图、层级时间摘要和增量更新思路；是否作强基线取决于代码可运行性与实现成本。 |
| [ChronoQA](https://arxiv.org/abs/2508.12282)（预印本） | absolute/aggregate/relative 时间问题的数据构造方法，直接支持题型设计。 |
| [IA-RAG](https://arxiv.org/abs/2606.06044)（预印本） | 区间代数与 before/after 推理，只是 interval-diff 的可选增强，并非离散补丁版本的直接基线。 |
| [CONFLICTS](https://arxiv.org/abs/2506.08500) / [context compliance](https://arxiv.org/abs/2605.14473)（预印本） | outdated/conflict taxonomy 与生成器失败分析；适合过期证据警告，不直接证明游戏域准确率。 |
| [Temporal robustness](https://arxiv.org/abs/2503.17073)（预印本） | 支持“从时效语料检索而非依赖参数记忆”的动机。 |
| [HippoRAG 2](https://arxiv.org/abs/2502.14802) / [LightRAG](https://arxiv.org/abs/2410.05779) | 图检索对照；只有图路径确实实现时才作为实验基线引用。 |
| [When to use graphs in RAG](https://arxiv.org/abs/2506.05690)（预印本） | 帮助论证何时版本图比简单元数据过滤更有价值。 |
| [共用 OneDrive 论文资料夹](../Common%20Useful%20Paper.html) | 切分、LiveRAG 与通用评估论文；具体方法只在实际实现时引用。 |

---

## 7. 挑战点

1. **wikitext 解析**：patch history 模板格式多年演变，需要写健壮的解析器并抽样人工检查；这是 KB 组的主要工作量。
2. **版本快照回放**：遗漏一次变更会污染后续快照；用 [Data Dragon](https://developer.riotgames.com/docs/lol#data-dragon) 的版本静态文件抽查，但官方说明其更新是手动的、可能不即时，版本号也不一定与客户端完全一致，所以它是交叉验证源而非绝对真值。
3. **问题自然度**：模板题需改写与人工润色；可让组员在不知道模板的情况下重写真实意图，不再依赖 Reddit 问句，以免引入额外数据授权问题。
4. **过期陷阱设计**：需保证语料中确实存在多版本数值并存，且"最新"定义清晰（数据截止日期写入报告）。
5. **评审口味**：教授和博后他们组更常做情感/观点类任务；报告需强调“知识演化 + 证据冲突”是通用 NLP 问题，游戏只是干净实验床，并讨论向软件文档/政策文件迁移。
6. **版权与政策**：在 pilot 中保存 Wiki 当前复用条款快照并按要求署名；遵守 [Riot 开发者政策](https://developer.riotgames.com/policies/general)，学校项目也应放置其要求的法律声明，不分发受版权保护的图片/素材。

---

## 8. 其他注意事项

- **分工**：KB 组 2 人（抓取、解析、快照回放、QA 生成脚本）；检索组 2 人（索引、版本图、路由、消融）；下游组 1–2 人（生成、过期警告、评估、UI）。核验标注全员参与。
- **时间表**：W1–2 解析器与三元组抽取 + v0；W3–4 QA 生成与核验开始 + UI；W5–7 版本图/路由/冲突处理 + 消融；W8–9 评估与失败分析；W10 报告。
- **论文化路径**：资源 + 系统论文（"PatchQA: a version-aware RAG benchmark over evolving game knowledge"）→ LREC-COLING / ECIR / CIKM short / SIGIR resource track；卖点是规模（>1k 题、数百版本）、四类问题与过期陷阱、开源解析器。
- **备选领域切换成本低**：若担心游戏题材，将同一套流程换到 PyTorch/Kubernetes changelog + 版本文档，方法不变。

---

## 9. 参考链接

- LoL Wiki Patch History Project：https://wiki.leagueoflegends.com/en-us/League_of_Legends_Wiki_talk:Patch_History_Project
- LoL Wiki 补丁分类：https://wiki.leagueoflegends.com/en-us/Category:Patch_notes ；Riot 官方补丁说明：https://www.leagueoflegends.com/en-us/news/tags/patch-notes/
- Riot Data Dragon（各版本静态数据，用于校验）：https://developer.riotgames.com/docs/lol#data-dragon
- TG-RAG 代码：https://github.com/hanjiale/Temporal-GraphRAG ；ECT-QA：https://huggingface.co/datasets/austinmyc/ECT-QA
- CONFLICTS：https://github.com/google-research-datasets/rag_conflicts
- HippoRAG：https://github.com/osu-nlp-group/hipporag ；LightRAG：https://github.com/HKUDS/LightRAG
- 工具：mwparserfromhell、Pyserini、FAISS、NetworkX、ir_measures、RAGAS、vLLM/Ollama、Gradio
