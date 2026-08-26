# 选题 1 · Energy-Opinion-RAG：面向东南亚能源转型的"条件式观点 RAG"

> 推荐度：有条件可选，需要解决数据授权 ｜ English: [README.md](README.md) ｜ [OneDrive 论文资料夹](Useful%20Paper.html)
> 一句话：用户询问核能 / SMR / 碳税 / 电价等议题时，系统检索**获准使用的公开平台样本**与官方文件，呈现采样话语中的主观性、立场、条件与框架，附证据、时间范围和覆盖度说明；结果不外推为“新加坡总体民意”。

---

## 1. 问题定义

### 1.1 任务形式化

- **输入**：自然语言查询 `q`（可含 Singlish / 中英马混杂），可选时间窗口 `[t0, t1]`、国家/子版块过滤。
  例："在获准采集的平台样本中，人们如何讨论 SMR？"、"对碳税涨价有哪些支持和反对理由？"、"gahmen build nuclear plant can or not"
- **知识库**：
  - `KB_opinion`：Reddit 帖子与评论（r/singapore, r/malaysia, r/indonesia, r/Philippines, r/nuclear, r/energy, r/ClimateChange 等），保留时间戳、子版块、分数、父评论 ID。
  - `KB_fact`：EMA / NCCS / MTI / IAEA / IEA 官方文件、Wikipedia 能源条目、新闻报道，作为"事实索引"。
- **输出**（结构化 + 自然语言摘要）：
  1. 与 `q` 相关的观点证据集合 `E = {e_1..e_k}`（每条附来源链接、时间、子版块）；
  2. 核心标签：`subjectivity ∈ {objective, opinion}`；对观点句再标 `stance ∈ {pro, anti, neutral/unclear}`。`condition_present` 与 frames 只作多标签增强项，不把“conditional”强行设成互斥类别；
  3. 采样条件下的聚合分布及时间序列，同时展示语料来源、时间范围、检索覆盖与样本量，避免把检索结果解释为人口统计民调；
  4. **冲突标记（可选增强）**：只核查数字、日期和明确政策状态。例如把“EMA 已批准在新加坡部署 SMR”与 EMA 明确表示尚未作出部署决定的文件对照；
  5. 覆盖度说明：本次回答覆盖了哪些视角（perspective coverage），避免只呈现多数派。

### 1.2 为什么是"能源转型"而不只是"核能"

作业要求 KB ≥ 10,000 文档 / 100,000 词。NUS LKYSPP 2026 工作论文报告的新加坡核能子集只有 **2,157 条**评论；据此推断单一核能主题可能不足。因此领域暂定为 **东南亚能源转型**（核能、太阳能、EV、碳税、电价/电力进口、氢能、天然气依赖），核能是焦点实例。最终范围必须在获批数据上重新计数后确定。

### 1.3 子任务与评分点对应

| 作业评分点 | 本项目对应 |
|---|---|
| KB 构建（20） | 双语料（观点 + 事实）、清洗、Singlish 处理、按评论/段落切分、`eval.xls` |
| 检索（40） | BM25 + 稠密 + RRF + 重排；创新：Singlish 查询归一化、观点覆盖度重排、时间/元数据过滤 |
| 下游任务（40） | MVP：主观性 + 立场分类、带来源限定的观点摘要；增强项从条件/框架、讽刺、冲突中最多选择 1–2 个并消融 |

---

## 2. 数据与知识库

### 2.1 数据来源（须先完成授权门槛）

| 来源 | 获取方式 | 用途 | 备注 |
|---|---|---|---|
| Reddit 研究数据 | [Reddit for Researchers](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program)（RFR） | `KB_opinion` 候选主体 | 需先获批，并满足大学隶属、伦理审查/豁免、用途限制、删除与不再分发要求；未获批前不可把 Reddit 定为主语料 |
| 第三方历史镜像 | [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift)、[Academic Torrents 条目](https://academictorrents.com/details/186a0f85a52ff4f1b08677cd312423ace9b34976) | 仅作来源可用性记录 | 能访问不等于获授权；Academic Torrents 元数据未给出明确许可，未经书面批准/合规确认不用于本项目 |
| HardwareZone 等论坛 | 不默认抓取 | 仅作潜在备选 | 必须先逐站核对 ToS、robots、版权与研究伦理；不能仅因页面公开就视为可批量复用 |
| 官方/事实文件 | EMA、NCCS、MTI 新闻稿；IAEA/IEA 报告；Wikipedia 能源相关条目 | `KB_fact` | 公开许可，PDF → 文本 |
| 新闻 | CNA / Straits Times 公开摘要、Wikipedia 引文、TODAY 等 | `KB_fact` 补充 | ST 有付费墙，只取公开部分 |
| 通用情感/讽刺数据 | SST-2、IMDB、[SARC](https://arxiv.org/abs/1704.05579)、[climatebert/climate_sentiment](https://huggingface.co/datasets/climatebert/climate_sentiment) | 训练/预训练候选 | 分别核对数据卡、许可与域差异；“公开可访问”不自动等于允许任何训练用途 |
| Singlish 资源 | [SingBERT](https://huggingface.co/zanelim/singbert)（r/singapore + HWZ 预训练）、[singlish-to-english-synthetic](https://huggingface.co/datasets/gabrielchua/singlish-to-english-synthetic)、[AudioLLMs/Singlish](https://github.com/AudioLLMs/Singlish) | 查询归一化、分类 backbone | |

**规模结论尚未验证**：旧版“年评论量百万、筛后 3–10 万”没有可复现实测依据，现删除。第一周应先完成 RFR/其他语料授权，再用获准样本运行固定关键词与去重流程，报告原始数、保留数、唯一作者数、时间覆盖、词数和估计置信区间；若无法证明 ≥10k passages / ≥100k words，则立即换合法开放语料或换题。

### 2.2 清洗与切分

- 遵守获批访问计划的删除/保留规则；去除 `[deleted]/[removed]`、bot、< 5 词评论和重复（MinHash），不公开用户名或可回溯的原文数据包。
- Reddit 评论天然是"段落"，一般不再切分；长帖 > 300 词按语义切分（`semantic chunking`），并保留 `parent_id` 做 parent-document retrieval（回答时展示上下文）。
- 官方文件：按章节切分 200–400 词，附标题路径（contextual chunk header）。
- 元数据：`{id, source, subreddit, country, created_utc, score, parent_id, url, lang_flags}`。
- 存储：JSONL（原始） + Lucene/Pyserini 索引（稀疏） + FAISS / Qdrant（稠密）。

### 2.3 评测集（作业硬性要求：≥ 1,000 条人工标注、IAA ≥ 80%、均衡）

- **分类评测集 `eval.xls`**：≥ 1,000 条评论，必填字段 `text | subjectivity | stance | source | date`；`condition_present | frames | sarcasm` 仅在 pilot IAA 达标后增加。
  - 先按 subjectivity 分层，再在观点句中平衡 pro / anti；neutral/unclear 与客观信息不能混为一类。不要为了“均衡”而伪造总体分布，训练/测试采样策略与自然语料分布分别报告。
  - 三名标注者先独立标 50–100 条；主任务报告 raw agreement 与 Fleiss' κ（或 Krippendorff's α）。全量可分工，但必须保留足够大的独立重叠子集计算 IAA，之后才由第三人裁决。
- **检索评测集 `retrieval_qrels.jsonl`**：先做 ≥50 条查询 × pooled top-10 的人工 0/1/2 相关性标注，并标视角；只有工时允许时再扩 top-30。
- **生成评测集**：30–50 条查询的人工参考摘要（用于 RAGAS 的 answer relevance 与人工评价）。

---

## 3. 基线水准（我们要对比/超越的对象）

| 层面 | 现有水平 | 来源 |
|---|---|---|
| 同题研究 | 作者报告 6,853 条评论（SG 2,157）及 64% neutral；具体模型、标注与 +17.5pp 等数字若用于最终报告，需引用正文页/表，不从摘要外推 | [NUS/LKYSPP working paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7005979) |
| 观点型 RAG | 34 个 benchmark / 1 个观点合成任务及 79.2% 人类偏好为该预印本的作者报告结果 | [O-RAG，预印本](https://arxiv.org/abs/2604.12138) |
| 多视角检索 | 现有检索器经常不能覆盖全部已知视角，支持单独评估 perspective coverage | [BERDS](https://arxiv.org/abs/2409.18110) |
| 证据冲突 | 支持把知识冲突分型并测试生成器行为；不再写未经页码支撑的“25% 开放域问题”概括 | [CONFLICTS，预印本](https://arxiv.org/abs/2506.08500) |
| 检索内部基线 | BM25 → 稠密 (bge-m3) → 混合 RRF → + 重排，逐级报告 nDCG@10 / MRR / R@20 | 本项目 v0 |

**内部 v0 基线**（第 3 周内完成）：BM25 (Pyserini) + `bge-m3` + RRF + `bge-reranker-v2-m3`；分类器 = 微调 `roberta-base`（或 SingBERT）的“主观性 → 立场”两阶段模型；生成器用可复现的小型/8B 模型简单 prompt。所有后续创新以 v0 为对照做消融。

---

## 4. 方式方法

### 4.1 系统架构预览

```
query ─► [可选 Singlish/多语归一化 + 时间/国家意图解析]
      ─► 稀疏 BM25 ─┐
      ─► 稠密 bge-m3 ┴► RRF ─► cross-encoder 重排 ─► 观点覆盖度重排 (MMR / BERDS-style)
      ─► 证据集 E ─► 核心分类器 (主观性→立场; 可选 condition/frames/讽刺)
                  ─► 可选事实核对: 从 KB_fact 检索, 冲突检测
                  ─► LLM 生成: 样本限定分布 + 摘要 + 引用 + 覆盖度说明
      ─► UI (Gradio/Streamlit): 饼图/时间线/证据卡片/来源链接
```

### 4.2 检索模块（Q3 创新点，各自可消融）

1. **混合检索 + 重排**（课程基本要求）：BM25 + bge-m3 稠密 + RRF；`bge-reranker-v2-m3` 或 `jina-reranker-v2` 精排。
2. **Singlish/混语查询归一化（可选）**：先用规则/提示改写，同时保留原查询做双路检索；`singlish-to-english-synthetic` 规模不足 1k，只能作小型辅助集，不能单独支撑“微调后可泛化”的主张。
3. **观点覆盖度重排**：对 top-50 证据先打 pro/anti/neutral 及可选 condition/frame 标签，再用 MMR 或视角配额重排；用 BERDS 式 coverage 评估。配额用于答案覆盖，不能反过来当作自然语料比例。
4. **时间与元数据检索**：`created_utc` 过滤 + 时间衰减打分；按国家/子版块 facet；支持"2025 预算案后 vs 前"对比。
5. **Parent-document / 线程上下文**：命中评论时把父评论一起送入生成器，缓解 Reddit 回复缺上下文。

### 4.3 下游模块（Q5 创新点，需消融）

1. **核心两阶段分类**：主观性 → 立场；condition/frames 为可选多标签。对比 (a) 微调 DeBERTa-v3 / SingBERT；(b) LLM zero/few-shot；(c) 检索相似已标注样本的 RAG 增强分类。
2. **讽刺检测子任务（可选）**：SARC 只能提供跨域预训练信号；不得简单把检测为讽刺的样本“翻转极性”，应在自标注子集上验证处理规则。
3. **O-RAG 式分布保真**：输出分布与语料真实分布的 Wasserstein 距离作为指标，检验"检索是否偏向多数派"。
4. **冲突感知生成（可选）**：只对数字、日期和明确政策状态抽取断言，再在 `KB_fact` 检索并判断支持/矛盾/无足够证据。
5. **自检忠实度**：生成后逐句回溯引用（claim-level citation），无法归因的句子标黄。
6. 可选：SenticNet 词典/概念级特征作为符号侧信号（与教授和博后他们组的工具方向对齐）。

### 4.4 评估

- 检索：P@5/10、R@20、MRR、nDCG@10（`ir_measures`）；perspective coverage@k；延迟。
- 分类：每级 P/R/F1（macro）；IAA 报告。
- 生成：RAGAS faithfulness / answer relevance / context precision；人工 Likert（3 人 × 30 查询）。
- 系统：QPS、索引时间、显存/成本、可扩展性讨论。

---

## 5. 验收标准（先宽松，后期可上调）

| 项目 | 最低门槛（必须） | 期望 |
|---|---|---|
| KB | ≥10k 获准使用的 passages、≥100k 词、去重且统计齐全 | 多来源/时间段覆盖 + ≥2k 事实段落 |
| 评测集 | ≥ 1,000 条 `eval.xls`，主任务 raw agreement ≥ 0.80，去重且分层均衡；独立重标子集可复算 IAA | κ/α ≥ 0.7；附检索 qrels ≥ 50 查询 |
| 检索 | 混合 > 单独 BM25 和单独稠密（nDCG@10 提升 ≥ 3 pt）；≥ 1 个创新点有正向消融 | ≥ 2 个创新点正向；coverage@10 提升 ≥ 10 pt |
| 分类 | 主观性 F1 ≥0.75；立场 macro-F1 ≥0.60 | 立场 ≥0.70；可选模块各自报告指标 |
| 生成 | RAGAS faithfulness ≥0.75；每个结论有证据和样本限定说明 | ≥0.85；若实现冲突模块，再单报其 precision |
| 性能 | 单查询端到端 ≤ 5 s（本地 8B 模型） | ≤ 3 s |
| UI | Gradio/Streamlit 可演示 5 条查询并记录耗时 | 时间线 + 分布图 + 证据卡片 |
| 报告 | 回答 Q1–Q5，含消融表、示例查询前后对比、失败案例 | 附 slides |

---

## 6. 论文校验与用途（[OneDrive 论文资料夹](Useful%20Paper.html)）

| 已核验来源 | 为什么有用 / 使用边界 |
|---|---|
| [O-RAG](https://arxiv.org/abs/2604.12138)（预印本） | 核心立论、coverage/fidelity/fairness 与分布指标；作者报告的具体数字需标明是其结果。 |
| [DIVERGE](https://arxiv.org/abs/2602.00238)（预印本） | 观点条件化检索的增强项，不宜在课程 MVP 中先做多 agent。 |
| [BERDS](https://arxiv.org/abs/2409.18110) / [PerSphere](https://arxiv.org/abs/2412.12588) | 直接支持 perspective retrieval 与 summarisation 评估。 |
| [CONFLICTS](https://arxiv.org/abs/2506.08500)（预印本） | 支持冲突分类与行为评估；不是“所有开放域问题冲突率”的通用统计。 |
| [Code-switching survey](https://arxiv.org/abs/2510.07037) | 支持归一化与多语 embedding 的选择；[MNSC/Singlish 工作](https://arxiv.org/abs/2501.01034)侧重口语/音频，不是文本检索的直接证据。 |
| [Retrieval-augmented financial sentiment](https://arxiv.org/abs/2310.04027) | 可作检索增强分类模板，但金融域结果不能直接当作本任务预期提升。 |
| [LACA](https://arxiv.org/abs/2508.09515) | ACL 2025 的跨语 ABSA 伪数据方法，仅作可迁移思路，不能证明 Singlish 伪标注有效。 |
| [SARC](https://arxiv.org/abs/1704.05579) | Reddit 讽刺预训练候选；与新加坡能源话语仍有明显域差异。 |
| [NUS/LKYSPP working paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7005979) | 同题背景与规模参考；引用具体标签流程、框架或结果前需对照正文，不写成已同行评审 SOTA。 |
| [共用 OneDrive 论文资料夹](../Common%20Useful%20Paper.html) | 通用 RAG、评估、切分、LiveRAG 与图方法背景。 |

---

## 7. 挑战点

1. **数据授权是 go/no-go 门槛**：未获 RFR 或其他来源的书面许可、学校伦理批准/豁免前，不开始 Reddit 全量收集，也不承诺此题。
2. **条件表达的标注一致性**：条件改为 `condition_present` 多标签，不与 pro/anti 互斥；先做 50–100 条试标、迭代两轮。
3. **中性/信息类评论占多数**：评测集可分层抽样，但必须另报自然分布，避免把平衡测试集的比例当成现实比例。
4. **讽刺、Singlish 与混语**：均可单列分析子集，但只有 pilot 证明有效且工时允许时才升为模型模块。
5. **观点 vs 事实边界**：冲突检测先限制为数字/政策/时间类可核查断言。
6. **算力与敏感性**：优先小模型与可复现基线；不做用户画像，遵守 RFR 的匿名化、保留、删除和不再分发要求。

---

## 8. 其他注意事项

- **ToS / 许可**：按 Reddit 的 [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)、[数据访问说明](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)与 RFR 批准条件执行；去用户名并不能替代访问授权。官方文件也应逐项记录转载/存储条件。
- **重叠风险（>30% 即 0 分）**：往届常见"Reddit 加密货币/电影情感分析"；本项目在领域（能源转型）、任务（条件式立场 + 覆盖度 + 冲突）与数据（双语料 + Singlish）上都有区分，实现细节不外传。
- **分工建议（5–6 人）**：KB 组 2 人（抓取/清洗/标注协调）；检索组 2 人（索引/混合/重排/Singlish/覆盖度）；下游组 2 人（分类器/生成/冲突/RAGAS/UI）。标注全员参与（每人约 400 条，含重叠）。
- **时间表（截止 2026-11-07）**：
  - W1–2（~9/13）：确认 RFR/其他语料授权和伦理状态；仅对获准样本量化，完成指南 v1、试标 50–100 条和 v0 索引。若授权或规模门槛失败，立即换语料/换题。
  - W3–4：v0 全流程跑通 + UI；正式标注开始。
  - W5–7：检索创新 + 下游创新 + 消融；标注完成、IAA 计算。
  - W8–9：RAGAS/人工评估、失败案例分析、性能测试。
  - W10：报告 + slides + 打包（KB、查询结果、eval、代码 README）。
- **后续研究可能性**：若取得可发布的数据许可并完成严谨评估，可再考虑观点 RAG 数据/系统论文；不要在课程提案阶段宣称“第一个”，除非补做系统性文献检索。

---

## 9. 参考链接

- SenticNet 项目页（气候韧性 → 核能公众看法）：https://sentic.net/projects
- Reddit for Researchers：https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program
- BERDS 代码/数据：https://timchen0618.github.io/berds/
- CONFLICTS 数据集：https://github.com/google-research-datasets/rag_conflicts
- SingBERT：https://huggingface.co/zanelim/singbert ；Singlish→English 合成数据：https://huggingface.co/datasets/gabrielchua/singlish-to-english-synthetic
- 新加坡核能官方资料：[EMA 2025 可行性与安全研究](https://www.ema.gov.sg/news-events/news/media-releases/2025/ema-to-conduct-study-on-safety-technical-feasibility-of-advanced-nuclear-energy-technologies)、[EMA 2026 说明](https://www.ema.gov.sg/news-events/news/feature-stories/2026/understanding-advanced-nuclear-energy-technologies-how-singapore-is-assessing-its-potential)
- 工具：Pyserini、FAISS/Qdrant、sentence-transformers (bge-m3)、ir_measures、RAGAS、vLLM/Ollama、Gradio
