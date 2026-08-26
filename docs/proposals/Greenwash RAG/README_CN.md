# 选题 3 · Greenwash-RAG：SGX 可持续报告的漂绿风险感知证据 RAG

> 高上限，但也高风险（与教授和博后他们组的 ACL 2025 工作直接对齐，那他们可太懂了直接就是一个批判） ｜ English: [README.md](README.md) ｜ [OneDrive 论文资料夹](Useful%20Paper.html)
> 一句话：用户输入“公司 + 可持续声明”或环境议题，系统检索报告内证据，抽取 aspect–action 关系并区分 **已实施 / 计划中 / 无法确定**；视觉页面与外部证据是增强项。输出是带出处的风险筛查，不是对公司是否漂绿的确定判决。

---

## 1. 问题定义

### 1.1 任务形式化

- **输入**：`(company, claim_text)` 或 `(company, aspect)`（如"DBS 的碳中和目标进展"）；可选年份。
- **知识库**：
  - `KB_report`：SGX 上市公司 2020–2025 可持续报告 / 年报 ESG 章节（PDF → 文本段落 + 页面图像）。
  - `KB_external`：新闻（CNA、Business Times 公开部分、Eco-Business）、监管文件（SGX RegCo、MAS、NEA 碳税）、NGO 报告。
- **输出**：
  1. 证据集合（报告段落/页面截图 + 外部文章），附来源、页码、年份；
  2. A3CG 式标注：先判断是否存在 aspect–action pair；若存在，抽取 `aspect` span，并标 `action ∈ {implemented, planning, indeterminate}`。`indeterminate` 表示行动状态无法从文本确定，**不等于已证明漂绿**；
  3. 报告内一致性与跨年变化；外部证据 `supports / refutes / not_enough_info` 仅作可选的 AVeriTeC 式扩展；
  4. 风险信号：模糊措辞、缺少量化目标/目标年、前后不一致等，逐项附页码与规则依据，并显示“辅助筛查，非结论”。

### 1.2 为什么值得做

- 教授和博后他们组的 ACL 2025 论文 [A3CG](https://aclanthology.org/2025.acl-long.723/) 提供 aspect–action 标注体系、数据和 seen/unseen 评估；把句子分析扩展成报告内“检索证据 + 跨年比较”很自然。现有快速检索未发现完全同构系统，但在做系统性文献检索前不声称“目前无人做”。
- SGX 可持续报告与气候披露规则提供本地、跨年份语料；规则会演变，应引用[当前 SGX Rulebook](https://rulebook.sgx.com/rulebook/711b)和[可持续报告指南](https://rulebook.sgx.com/rulebook/practice-note-7f-sustainability-reporting-guide)，不只沿用“2016/2022”旧概括。表格/图表页可构成受控的视觉检索增强子集。
- 同时命中 SenticNet 项目页的"气候韧性（漂绿检测）"与"金融"两条线。

### 1.3 评分点对应

| 作业评分点 | 本项目对应 |
|---|---|
| KB（20） | PDF 抓取/解析（文本 + 页面图像）、按章节/页切分、公司/年份元数据、`eval.xls` |
| 检索（40） | MVP：文本混合检索 + 公司/年份过滤 + 重排；增强项：受控表格/图表子集的视觉页面检索与融合 |
| 下游（40） | MVP：A3CG 式 pair/no-pair、aspect span、action 分类和证据解释；外部事实核查只在标注工时充足时增加 |

---

## 2. 数据与知识库

### 2.1 数据来源

| 来源 | 获取方式 | 用途 | 备注 |
|---|---|---|---|
| SGX 上市公司可持续报告 | 公司官网 IR 页面、SGXNet；第三方索引仅作发现入口 | `KB_report` | 页面公开不自动等于可批量再分发；保存来源 URL、抓取日期、robots/条款与报告版权信息，只发布允许发布的派生数据 |
| A3CG 数据集 | [greenwashing-detection repo](https://github.com/SenticNet/greenwashing-detection)（`dataset/full`、3 folds） | 训练/对照 aspect–action 分类器 | 数据可访问；截至核验时仓库仍提示部分 code/model evaluation “coming soon”，不能写成完整代码可直接复现 |
| ClimateBERT 数据 | [climatebert/environmental_claims](https://huggingface.co/datasets/climatebert/environmental_claims)、`climate_detection`、`tcfd_recommendations` | 声明检测候选 | 分别核对数据卡、许可、标签定义与域差异 |
| 外部新闻/监管 | Eco-Business、CNA、SGX RegCo、MAS、NEA 公开页面 | 可选 `KB_external` | 逐站核对抓取和再利用条款；付费墙或不可稳定访问的内容不入核心 KB |
| Kaggle S&P500 ESG 报告 | [S&P 500 ESG reports](https://www.kaggle.com/datasets/jaidityachopra/esg-sustainability-reports-of-s-and-p-500-companies) | 扩充训练/背景 | 可选 |

**规模须实测**：旧版“约 600 家 × 5 年、平均 60 页”的组合估算没有固定名录与快照依据，现删除。第一周从多个行业抽 20–30 家、2–3 年做 pilot，报告可下载率、解析成功率、页数、文本 chunk 与词数，再外推到满足 10k chunks / 100k words 的最小公司数。视觉索引只覆盖自然包含表格/图表的受控页子集，不默认索引全部公司全页。

### 2.2 解析与切分

- 文本：`pymupdf`/`marker` 提取 + 表格用 `camelot`/`pdfplumber`；按标题层级切 200–400 词，chunk 前加"公司 | 年份 | 章节"上下文头（contextual chunk）。
- 视觉：每页渲染 150 dpi 图像，用 ColQwen2.5 / Qwen3-VL-Embedding 编码；页级 + 文本 chunk 级双索引，融合时页 → 其内 chunk 展开。
- 元数据：`{company, ticker, sector, year, page, section, has_table, has_chart}`。

### 2.3 评测集（≥ 1,000 条，IAA ≥ 80%）

- **`eval.xls`**：≥1,000 条 SGX 报告句子，含环境声明与对照句。标注 `has_aspect_action`、`aspect_span`，仅对 pair 样本标 `action ∈ {implemented, planning, indeterminate}`；可选 `specificity`。A3CG 原数据约 **33.2% 无 aspect–action pair**，所以必须保留 no-pair 类，不能只强行平衡三种 action。
  - A3CG 指南是起点，不保证本组 IAA。先独立双标 100 条；pair/no-pair 与 action 报 raw agreement/κ 或 α，span 用 token-level F1/overlap agreement；裁决后再扩全量。
- **外部核查集（可选）**：只有核心 1,000 条完成且能稳定找到证据时，再增加 claim + evidence + `supports/refutes/NEI` 子集；不要把“选择大公司以保证 refutes”变成有偏抽样后再声称总体表现。
- **检索 qrels**：先做 ≥50 条查询 × pooled top-10 人工相关性；自然形成的表格/图表页子集单独报告，不人为规定 1/3 答案必须来自视觉页。

---

## 3. 基线水准

| 层面 | 现有水平 | 来源 |
|---|---|---|
| aspect–action 分类 | A3CG 含 1,679 份 SGX 报告、2,004 个 statements，并显示 seen→unseen 泛化下降；论文明确说它不是确定性漂绿检测 | [A3CG，ACL 2025](https://aclanthology.org/2025.acl-long.723/) |
| 漂绿风险鲁棒性 | 对比学习、序数目标与门控调制是跨类别鲁棒性的候选方法；目前按预印本处理 | [Robust greenwashing LM](https://arxiv.org/abs/2601.21722) |
| 环境声明检测 | 提供专家标注的二分类环境声明数据与 ClimateBERT 基线；删除未附表号的“F1≈0.8+” | [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) |
| 视觉文档检索 | 支持视觉/文本/混合检索与生成的分项评测；公开记录未证明“ACL 2026 接收” | [ViDoRe V3，预印本](https://arxiv.org/abs/2601.08620) |
| RAG 事实核查 | 2025 冠军与效率数据应引用当年 overview/系统论文；2024 AIC-CTU 是前序系统，不是 2025 冠军论文 | [overview](https://aclanthology.org/2025.fever-1.15/)、[winner paper](https://aclanthology.org/2025.fever-1.22/)、[2024 predecessor](https://arxiv.org/abs/2410.11446) |
| 内部 v0 | 文本 BM25 + bge 稠密 + RRF + 重排；分类器 = A3CG 上微调 DeBERTa；核查 = LLM + top-5 外部证据 | 本项目 |

---

## 4. 方式方法

### 4.1 架构预览

```
(company, claim/aspect, year?) ─► 查询构造 (公司别名扩展, aspect 同义词)
   ─► 文本混合检索 (BM25 + bge-m3 + RRF) ─┐
   ─► 可选视觉页面检索 (ColQwen / Qwen3-VL-Emb) ┴► 跨模态融合 ─► 重排
   ─► 证据: 报告段落 + 可选页面截图/外部文章
   ─► 分类: aspect–action (A3CG 微调模型 / LLM+RAG)
   ─► 可选外部核查: NLI/LLM → supports/refutes/NEI
   ─► 漂绿风险解释生成 (引用页码; 模糊措辞高亮; 目标/时间/数值缺失检查)
   ─► UI: 公司选择 + 声明输入 + 证据页缩略图 + 风险卡片
```

### 4.2 检索创新（Q3）

1. 混合检索 + 交叉编码重排（基本要求）。
2. **视觉页面检索（增强项）**：只在自然表格/图表页子集上与文本检索融合；消融仅文本/仅视觉/融合，不把全页视觉索引设为最低交付。
3. **公司/年份元数据过滤 + 跨年份对比检索**（"2022 vs 2024 目标是否被悄悄改动"→ 时间线检索）。
4. **查询扩展**：aspect 同义词表（A3CG aspect 类别）+ HyDE 假设段落。
5. Contextual chunk header 与 late chunking 对照。

### 4.3 下游创新（Q5）

1. **RAG 增强的 aspect–action 分类**：先把同公司历史声明与报告内证据作为上下文，对比纯句子分类（A3CG 基线）。
2. **报告内证据核查**：先做同公司跨年检索和一致性比较；外部 AVeriTeC 式核查仅作第二阶段可选项。
3. **漂绿风险信号解释**：规则（无数字/无年份/模糊词典）+ LLM 解释，claim-level citation；始终称 risk signal，不输出公司级结论。
4. **跨类别泛化实验**：沿用 A3CG 的 seen/unseen aspect 划分，检验 RAG 上下文是否改善 unseen 泛化；这是有价值的课程实验，但不预先承诺论文结果。
5. 可选：SenticNet 概念级特征作为符号信号（与教授和博后他们组的工具方向对齐）。

### 4.4 评估

- 检索：P@k、R@k、MRR、nDCG@10；表格/图表页子集单列。
- 分类：aspect / action 的 macro P/R/F1；seen vs unseen。
- 核查：三分类 macro-F1；Ev2R 风格的证据召回（LLM 评估）。
- 生成：RAGAS faithfulness / answer relevance / context precision；人工 Likert。
- 系统：延迟、索引成本（视觉索引显存/磁盘）、可扩展性。

---

## 5. 验收标准（先宽松）

| 项目 | 最低门槛 | 期望 |
|---|---|---|
| KB | ≥10k chunk、≥100k 词；报告数由 pilot 的真实页数/解析率决定 | 多行业、多年份；受控视觉页子集 |
| 评测集 | `eval.xls` ≥1,000 条，含 no-pair；pair/action IAA ≥0.80，span agreement 单列 | 外部核查集与 qrels ≥50 仅在核心完成后增加 |
| 检索 | 混合检索优于单独 BM25/稠密；公司/年份过滤有正向消融 | 视觉融合在自然表格/图表子集有正向提升 |
| 分类 | action macro-F1 ≥ 0.70（seen）、≥ 0.55（unseen） | ≥ 0.78 / ≥ 0.65 |
| 核查 | 报告内跨年一致性子集有可复现指标 | 可选外部 supports/refutes/NEI macro-F1 ≥0.55 |
| 生成 | RAGAS faithfulness ≥ 0.75，所有风险提示可溯源到页码 | ≥ 0.85 |
| 性能 | 端到端 ≤ 8 s（视觉检索较重） | ≤ 4 s |
| UI | 公司 + 声明输入、证据页缩略图、5 条查询计时 | — |

---

## 6. 论文校验与用途（[OneDrive 论文资料夹](Useful%20Paper.html)）

| 已核验来源 | 用途与边界 |
|---|---|
| [A3CG](https://aclanthology.org/2025.acl-long.723/)（ACL 2025） | **核心依据**：pair/no-pair、aspect span、action、seen/unseen 协议；原文明确不作确定性漂绿检测，提案必须保留这条边界。 |
| [Robust greenwashing LM](https://arxiv.org/abs/2601.21722)（预印本） | 对比/序数/门控方法的候选增强；未复现前不称“可直接复用的强基线”。 |
| [Corporate greenwashing survey](https://arxiv.org/abs/2502.07541)（working paper） | 定义、数据与方法背景；其“缺少已验证漂绿案例数据”也支持使用风险筛查措辞。 |
| [SwissText 2025 ESG hints](https://aclanthology.org/2025.swisstext-1.3/) | 正式 proceedings 论文；用 150 份德国 DAX 报告研究语言具体性与内部支持，能支持 risk hints，但域与 SGX 不同。 |
| [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) | 环境声明检测数据与基线，可用于候选句筛选。 |
| [ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/)（EMNLP 2025） | 比通用 AVeriTeC 更贴近 ESG 承诺核查；建议新增至 OneDrive 并优先用于 verification related work。 |
| [ViDoRe V3](https://arxiv.org/abs/2601.08620) / [ColPali](https://arxiv.org/abs/2407.01449) | 视觉页检索依据；ViDoRe V3 目前按预印本标注，不写“ACL 2026”。 |
| [Qwen3-VL Embedding](https://arxiv.org/abs/2601.04720) / [UniDoc-Bench](https://arxiv.org/abs/2510.03663)（预印本） | 视觉 embedding/reranking 与多模态评测候选；不应同时承诺实现所有模型。 |
| [AVeriTeC 2025 overview](https://aclanthology.org/2025.fever-1.15/) / [winner system](https://aclanthology.org/2025.fever-1.22/) | 外部事实核查的可选流程。旧 `2024_AIC-CTU` PDF 是 2024 前序方法，不是 2025 冠军论文。 |
| [Ev2R](https://arxiv.org/abs/2411.05375) | 证据召回评估参考；仅在实现外部核查时需要。 |
| [共用 OneDrive 论文资料夹](../Common%20Useful%20Paper.html) | 通用 RAG、评估与切分背景。 |

---

## 7. 挑战点

1. **标注难度最高**：ESG 术语与"计划 vs 已实施 vs 模糊"边界需要一定领域理解；好在 A3CG 指南现成，但仍需 2 轮试标才能到 80% IAA。
2. **PDF 工程量**：报告排版复杂（双栏、图表、跨页表），文本抽取噪声大；视觉检索能绕过 OCR 但索引重（每页数百向量），需要控制规模或做向量池化。
3. **外部证据稀疏**：多数中小公司没有稳定外部报道，核查集会偏向 NEI；若做外部子集，按可获得性分层并公开抽样规则，不能为了“保证 refutes”只选大公司。
4. **算力**：ColQwen2.5-3B 编码 ~10k 页需要 GPU 数小时；生成用 8B 模型；无 GPU 时视觉检索改用 `vidore/colSmol-500M` 或云端。
5. **与教授和博后他们组的工作接近**：既对齐兴趣，也会更严格审视方法；必须明确区分“复用 A3CG”与本项目新增的检索、跨年比较和可选视觉部分。
6. **法律/声誉**：即使只输出“漂绿风险信号”也属敏感判断；UI 与报告必须持续显示“辅助筛查，非结论”，不对具体公司作漂绿定性。

---

## 8. 其他注意事项

- **分工**：KB 组 2 人（PDF 抓取解析、页面渲染、元数据、声明抽取）；检索组 2 人（文本/视觉双索引、融合、重排、消融）；下游组 2 人（分类器、核查、解释生成、RAGAS、UI）。
- **时间表**：W1–2 用 20–30 家公司做许可/下载/解析/规模 pilot 与试标；W3–4 扩到满足 KB 门槛并完成文本 v0 + UI；W5–7 做元数据检索、分类和消融，再按资源增加视觉/外部核查；W8–9 评估；W10 报告。
- **后续研究可能性**：若许可允许发布数据、核心实验严谨且系统性检索确认新颖性，可再与教授和博后他们组讨论后续研究；课程提案阶段不承诺合作、Q1/Q2 发表或“第一个系统”。
- **降级方案**：若视觉检索算力不足，退回纯文本 + 表格结构化抽取，仍满足作业要求。

---

## 9. 参考链接

- SenticNet 漂绿检测仓库（A3CG）：https://github.com/SenticNet/greenwashing-detection ；论文页：https://aclanthology.org/2025.acl-long.723/
- ClimateBERT 数据：https://huggingface.co/climatebert
- ViDoRe / ColPali 模型：https://huggingface.co/vidore ；Qwen3-VL-Embedding：https://huggingface.co/Qwen
- SustainabilityReports.com：https://www.sustainabilityreports.com/ ；SGX 可持续报告规则：https://www.sgx.com/regulation/sustainability-reporting
- NUS CGS × SGX 可持续报告审阅 2023：https://bschool.nus.edu.sg/cgs/wp-content/uploads/sites/7/2023/11/CGS-SGX-Sustainability-Reporting-Review-2023_Report.pdf
- AVeriTeC 2025 冠军代码：https://github.com/aic-factcheck/aic_averitec ；HerO：https://github.com/ssu-humane/HerO
- 工具：pymupdf/marker、pdfplumber、Pyserini、FAISS/Qdrant、colpali-engine、ir_measures、RAGAS、vLLM、Gradio
