# 选题 3 · Greenwash-RAG：SGX 可持续承诺的跨年证据追踪

> 高上限，但也高风险（与教授和博后他们组的 ACL 2025 工作直接对齐，那他们可太懂了直接就是一个批判） ｜ English: [README.md](README.md) ｜ [OneDrive 论文资料夹](Useful%20Paper.html)
> 2026-09-10 精读原始文献并做完取数 pilot 后修订。
> 一句话：用户输入"公司 + 可持续承诺"或环境议题，系统跨年检索该公司报告内的相关证据，把每条声明标成已实施 / 计划中 / 无法确定，并输出一条带页码的承诺轨迹；研究上检验这些检索证据**是否改变并改善**了相对纯单句的 A3CG 分类。视觉页面与外部证据是增强项。输出是带出处的风险筛查，不是对公司是否漂绿的确定判决。

---

## 0. 项目目标一览

### 0.1 用户问题：为谁、解决什么

SGX 要求主板上市公司每年发布可持续报告（Listing Rule 711A），每份 40–150 页。分析师、投资者、监管人员与记者经常需要回答这样的问题：

> "公司 X 2021 年承诺的某项减排目标，后来兑现了吗？证据在哪几页？"

人工回答要翻 3–4 年的报告，并在大量模板化 ESG 文字里定位相关段落。系统的目标输出如下（示意，公司与引文均为虚构）：

```
2021  p.34  "we aim to reduce ... by 2025"            → planning
2022  p.41  "we remain committed to this target"      → planning
2023  p.38  "we continue to explore options"          → indeterminate
2024  —     该 aspect 未再出现
⚠ 风险信号：承诺连续 3 年只有 planning / indeterminate，未见 implemented 证据（辅助筛查，非结论）
```

现有方法做不好这件事，原因有三：

1. **单句判断会错。** A3CG 类模型一次只看一句。"We have achieved this target ahead of schedule" 单看不知道 "this target" 指什么；"Industry players are expected to reduce plastic packaging" 单看分不清是公司自己的行动还是在复述监管要求。这两类正是 A3CG 论文自己报告的头号失败模式：监督模型的 *ellipsis* 与 LLM 的 *unattributed statements*。
2. **ESG 报告高度模板化。** "We are committed to reducing our carbon footprint" 这类句子在几十家公司报告里几乎一字不差，不按公司过滤时稠密检索容易把别家公司的段落排到前面（待实测的假设）。
3. **没有跨年视角。** EmeraldMind、ML-Promise、A3CG 都不做跨年比较（见 §1.4）。

### 0.2 研究问题：新颖性在哪

- **RQ1**：加入检索到的报告内上下文，aspect–action 分类是否比纯单句更准？seen 与 unseen 类别分别看。
- **RQ2**：跨年检索能否正确还原一个承诺的轨迹（planning → implemented、长期停在 planning、被弱化、消失）？
- **RQ3**：公司/年份元数据过滤能否减少串公司的检索错误？

0.1 的用户功能要成立，这三个问题必须都有答案，所以研究问题和系统是同一件事，不需要做两套。**明确不做**：对公司下"是否漂绿"的判决。

### 0.3 如何量化（详见 §4.4 与 §5）

- **RQ1**：四种证据条件相对纯单句的 ΔF1 + 翻转分析 + 显著性检验。**这是主验收项。**
- **RQ2**：跨年轨迹完全匹配率与 transition F1。
- **RQ3**：nDCG@10 与自定义的 wrong-company@10 的消融对比。
- 作业硬指标（KB 规模、IAA、RAGAS、延迟）照常报告。

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
  4. 风险信号：模糊措辞、缺少量化目标/目标年、前后不一致等，逐项附页码与规则依据，并显示"辅助筛查，非结论"。

### 1.2 为什么值得做

- 教授和博后他们组的 ACL 2025 论文 [A3CG](https://aclanthology.org/2025.acl-long.723/) 提供 aspect–action 标注体系、数据和 seen/unseen 评估。**迄今 A3CG 上的所有已发表结果——包括该组自己 2026 年 1 月的后续工作——都只对孤立单句做分类。** 没有人问过"检索到的报告内证据 / 跨年证据是否会改变 action 标签"。这就是我们的切入点，见 §1.4。
- SGX 可持续报告与气候披露规则提供本地、跨年份语料；规则会演变，应引用[当前 SGX Rulebook](https://rulebook.sgx.com/rulebook/711b)和[可持续报告指南](https://rulebook.sgx.com/rulebook/practice-note-7f-sustainability-reporting-guide)，不只沿用"2016/2022"旧概括。表格/图表页可构成受控的视觉检索增强子集。
- 同时命中 SenticNet 项目页的"气候韧性（漂绿检测）"与"金融"两条线。

### 1.3 评分点对应

| 作业评分点 | 本项目对应 |
|---|---|
| KB（20） | PDF 抓取/解析（文本 + 页面图像）、按章节/页切分、公司/年份元数据、`eval.xls` |
| 检索（40） | MVP：文本混合检索 + 公司/年份过滤 + 重排；增强项：受控表格/图表子集的视觉页面检索与融合 |
| 下游（40） | MVP：A3CG 式 pair/no-pair、aspect span、action 分类和证据解释；外部事实核查只在标注工时充足时增加 |

### 1.4 与现有工作的定位（2026-09-10 修订）

之前的"现有快速检索未发现完全同构系统"这句**撤回**。我又找了一圈找到了以下工作，最终报告必须全部引用（让GPT告诉我们怎么放进来就行），否则新颖性检索会被视作没做完：

| 现有系统 | 它已经做了什么 | 与原 MVP 的重叠 |
|---|---|---|
| **EmeraldMind**，ACM Web Conference 2026（[arXiv 2512.11506](https://arxiv.org/abs/2512.11506)）+ **EmeraldApp** demo | 端到端漂绿检测领域 RAG：`EmeraldDB`（ESG 报告 chunk 向量库）+ `EmeraldGraph`（知识图谱，37 份报告抽出 53,748 实体 / 59,344 关系）；输出 `greenwashing / not / abstain` **加带证据的自然语言理由**；EM-RAG / EM-KGRAG / EM-HYBRID 三路消融；coverage 感知评测 | **高** —— 这就是我们原来的 MVP |
| **ML-Promise**，EMNLP 2025（[main.1028](https://aclanthology.org/2025.emnlp-main.1028/)） | 5 语种 ESG 报告上的 Promise Identification / Actionable Evidence / Clarity / Timing；证据**限定在同一份文档内**；同时有文本与图像 RAG 基线；κ 0.60–0.96 | **高** —— 这就是"报告内证据核查" |
| **SwissText 2025**（[swisstext-1.3](https://aclanthology.org/2025.swisstext-1.3/)） | 150 份德国 DAX 报告上用 ClimateBERT specificity + Sentence-BERT 内部佐证作为漂绿提示 | **高**（针对规则式风险信号部分） |
| **COGLM**，[arXiv 2601.21722](https://arxiv.org/abs/2601.21722)（2026-01，与 A3CG 同一组） | 对比 + 序数 + 门控 LoRA 微调，提升 A3CG 跨类别鲁棒性 | **完全重叠** —— 不要把对比/序数目标写成我们的创新 |

**仍然空着的口子，也就是我们应该主张的东西：**

1. **检索条件化的 aspect–action 分类。** A3CG 与 COGLM 都只做孤立单句。A3CG 自己的错误分析指出：监督模型头号失败模式是 *ellipsis*（缺上下文），LLM 头号失败模式是 *unattributed statements*（无归属陈述）——两者正好都是按公司范围检索能补上的。
2. **跨年 / 纵向声明追踪。** ML-Promise 是单年（2021 起）；EmeraldMind 完全没有时间维度；A3CG 跨 2017–2022 但从不做跨年比较。
3. **带页级出处的 SGX 纵向语料。** A3CG 自己的报告名录并未公开（见 §2.1），因此独立构建的 2020–2025 SGX 语料 + `{company, year, page, section}` 元数据本身就是有价值的产出，而且把覆盖范围推过了 A3CG 的 2022 截止点。

**主实验。** 同一个 aspect–action 分类器在四种证据条件下：`纯单句 → +局部上下文 → +同报告检索证据 → +跨年检索证据`，在我们自标、带 `{company, year, page}` 出处的 SGX 2023–2025 集上报告；seen/unseen 通过 A3CG 各 fold 的类别划分映射实现（见 §4.4）。A3CG 本身只发布孤立句子、没有来源文档，无法为它检索上下文，因此 A3CG 只用于训练和纯单句基线。检索质量（P@k、R@k、MRR、nDCG@10）是自变量，action F1 是因变量。EmeraldMind、ML-Promise、COGLM 都没回答过这个问题。

作业的 30% 重叠判零规则针对的是其他学生项目，不是已发表研究，所以以上都不构成合规问题——它是可信度问题，引用它们并说清楚差异即可解决。

---

## 2. 数据与知识库

### 2.1 数据来源

> 我已经使用爬虫准备好了数据，内部分发。数据仅仅作用于学术用途，不得二次分发，谢谢配合！

| 来源 | 获取方式 | 用途 | 备注 |
|---|---|---|---|
| SGX 上市公司可持续报告 | 公司官网 IR 页面、SGXNet；第三方索引仅作发现入口 | `KB_report` | **2026-09-10 实测：5/5 份一次下载成功，无需认证、无验证码。** SGXNet 的 PDF 可直连：`https://links.sgx.com/1.0.0/corporate-announcements/<ID>/<file>.pdf`；但 `api.sgx.com/announcements/...` 全部返回 `Missing Authentication Token`，枚举公告需走 SGX 网页端（Playwright）或逐公司 IR 抓取。`sgx.com/robots.txt` 是 `Allow: /` 且无 crawl-delay——仍需自行限速。页面公开不自动等于可批量再分发；保存来源 URL、抓取日期、robots/条款与报告版权信息，只发布允许发布的派生数据 |
| A3CG 数据集 | **[keanepotato/a3cg_greenwash](https://github.com/keanepotato/a3cg_greenwash)**（论文本身脚注引用的仓库） | 训练/对照 aspect–action 分类器 | **用这个仓库，不要用 `SenticNet/greenwashing-detection`。** 它除数据外还带 GRACE 完整实现、配置、评测 shell 脚本、预处理 BIO 数据和 `results/*_test_outputs.csv` 预测结果；训练好的 checkpoint 在 HF `keentomato/a3cg_greenwash_grace_f{1,2,3}`。"code coming soon" 对 GRACE 已过时（其余模型族仍在整理）。**两个坑：两个仓库都没有 LICENSE；论文脚注 2 承诺的公司名/年份名录并不在仓库里，因此无法复原他们那 1,679 份原始语料。** 建议就这两点发邮件问第一作者 |
| ClimateBERT 数据 | [climatebert/environmental_claims](https://huggingface.co/datasets/climatebert/environmental_claims)、`climate_detection`、`tcfd_recommendations`、**`climate_specificity`** | 声明检测候选；`climate_specificity` 直接服务于"模糊措辞"风险信号 | 全部为 **CC-BY-NC-SA-4.0**（非商用 + 相同方式共享），必须声明。已核验规模：environmental_claims 2,117/265/265，**正例仅 25%**（训练集 532/2,117）；climate_detection 1,300/400；tcfd_recommendations 1,300/400（5 类）；climate_specificity 1,000/320 |
| 外部新闻/监管 | Eco-Business、CNA、SGX RegCo、MAS、NEA 公开页面 | 可选 `KB_external` | 逐站核对抓取和再利用条款；付费墙或不可稳定访问的内容不入核心 KB |
| ML-Promise | `MLpromise.nlpfin.com` 跳转的公开 Google Drive 文件夹（"PromiseEval Dataset"） | 相关工作对照；可选的 promise/evidence 标签 | 可访问；英文部分仅约 200 条，且完全没有 SGX 覆盖 |
| Kaggle S&P500 ESG 报告 | [S&P 500 ESG reports](https://www.kaggle.com/datasets/jaidityachopra/esg-sustainability-reports-of-s-and-p-500-companies) | 扩充训练/背景 | 页面存在，但未登录读不到内容——只当可选背景，绝不作为依赖 |
| GreenClaims（Fornasiero） | 经 EmeraldMind 论文转引 | 仅作引用 | 目前唯一由第三方核实的漂绿标签集，但只有 **91 条、可用 51 条**，太小，不足以作为基础 |

**规模已实测，不再估算。** 5 份 pilot（SGX 中小盘 FY2024）实测 **219 页 / 63,035 词**，即**每份 12,607 词、43.8 页**，约 57% 的页面含可检出表格。

| 门槛 | 所需报告数 |
|---|---|
| ≥100,000 词 | **≈ 8 份** —— 轻松达标 |
| ≥10,000 chunks（300 词/块，约 42 块/份） | **≈ 240 份** ← 真正的约束 |
| ≥10,000 chunks（200 词/块） | ≈ 160 份 |

→ **目标：约 60–80 家公司 × 3–4 年 ≈ 240 份报告 ≈ 10,500 页 ≈ 300 万词。** Pilot 刻意选了中小盘；大盘（DBS、CapitaLand、Sembcorp）通常 80–150 页，混合市值取样可用更少报告达标。第一周做完 90 份 pilot 后，用实测解析失败率重新外推。视觉索引只覆盖**设上限**的表格/图表页子集（见 §4.2），不索引全部页面。

### 2.2 解析与切分

- 文本：`pymupdf`/`marker` 提取 + 表格用 `camelot`/`pdfplumber`；按标题层级切 200–400 词，chunk 前加"公司 | 年份 | 章节"上下文头（contextual chunk）。
- 视觉：每页渲染 150 dpi 图像，用 ColQwen2.5 / Qwen3-VL-Embedding 编码；页级 + 文本 chunk 级双索引，融合时页 → 其内 chunk 展开。
- 元数据：`{company, ticker, sector, year, page, section, has_table, has_chart}`。
- **预期会有 PDF 抽取噪声，并且可以容忍。** ACL 正式发表的 A3CG 文本里仍然带着 `"energy -efficient"`、`"Goals for the next 3 -5 years  (Medium - to long -term goals)"` 这类伪影。这直接说明我们自己 pipeline 里同等程度的噪声是可接受的——不要在归一化上过度投入。

### 2.3 评测集（≥ 1,000 条，IAA ≥ 80%）

- **`eval.xls`**：≥1,000 条 SGX 报告句子，含环境声明与对照句。标注 `has_aspect_action`、`aspect_span`，仅对 pair 样本标 `action ∈ {implemented, planning, indeterminate}`；可选 `specificity`。每条还必须记录：`{company, year, page}` 出处（证据条件化实验靠它检索上下文）；A3CG 的 aspect category（用于 seen/unseen 映射）；可选的 A3CG 失败模式标签（ellipsis / 歧义句法 / modality / 否定 / unattributed / future dependency，用于分桶分析）。A3CG 原数据约 **33.2% 无 aspect–action pair**（已核验：666/2,004），所以必须保留 no-pair 类，不能只强行平衡三种 action。
- **A3CG 论文全文没有报告任何 IAA 数值。** 它的流程是 5 名标注员 + 3 名 verifier，*全部为可持续性方向在读博士或博后*；试标到 ≥95% 正确率、每 3 天裁决分歧、verifier 每 3 天抽查 20%、错误率超 5% 则整批重标。这是一套标注**流程**，不构成"我们也能达到 ≥80% IAA"的证据。**满足课程 ≥80% 的要求完全是我们自己的事，也是本项目最大的进度风险。**
- **分阶段标注协议**（把一个难判断拆成三个容易判断）：
  - **第 A 轮** —— 句级 `has_aspect_action`（二分类）。快、一致性高，且约 33% 是负例，这本身就是一个合法的标注维度。
  - **第 B 轮** —— 对正例，给出由**微调后 A3CG 模型预抽取的候选 span**，标注员只做接受/拒绝/修改，而不是从零写 span。校验一致性远高于自由标注一致性，且作业明确允许"人工标注**或核验**"的记录。
  - **第 C 轮** —— 在已确认 span 上标 action（三分类）。
  - **按维度分别报告一致性**：二分类与 action 报 raw agreement + κ；span 用 token-level F1 / overlap（κ 对 span 无意义）。
  - 扩量前先做两轮 50 条试标 —— A3CG 自己也是这么做的。分歧几乎全部集中在 `implemented` vs `indeterminate`，把 A3CG 的 `indeterminate` 细则逐条抄进指南（有 hedging 但无兑现保证；只披露数字而未主张改善；只罗列职责而未明确关联可持续性改善）。
- **外部核查集（可选）**：只有核心 1,000 条完成且能稳定找到证据时，再增加 claim + evidence + `supports/refutes/NEI` 子集；不要把"选择大公司以保证 refutes"变成有偏抽样后再声称总体表现。
- **检索 qrels**：先做 ≥50 条查询 × pooled top-10 人工相关性；自然形成的表格/图表页子集单独报告，不人为规定 1/3 答案必须来自视觉页。

---

## 3. 基线水准

> 以下数值均为 2026-09-10 精读时从论文正文/表格中读出，非转述。

| 层面 | 现有水平 | 来源 |
|---|---|---|
| aspect–action 分类（A3CG） | 1,679 份 SGX 报告（2017–2022）、2,004 个 statements、2,723 个 aspect–action pair（implemented 1,459 / indeterminate 885 / planning 379）、10 个类别 + no-aspect。**AAA F1——全量 67.1–71.3（最佳 CONTRASTE 71.33）；seen 均值 61.96–67.47；unseen 均值 41.12–47.51（最佳 GRACE 47.51）。** 子任务 **AC（action）在任何设定下都比 ATE 更难**：AC 全量 59.5–65.7、seen 51.8–60.5、**unseen 仅 21.6–36.5**。LLM 明显落后（最佳 Claude 3.5 Sonnet+FS：unseen 42.03）。论文明确说它**不是**确定性漂绿检测 | [A3CG，ACL 2025](https://aclanthology.org/2025.acl-long.723/) Table 2 与 Table 14 |
| **A3CG 上的当前 SOTA** | **COGLM（LoRA + 对比 + 序数 + 门控 + MetaGradNorm）：72.40 全量 / 67.59 seen / 49.04 unseen。** 220M 的 T5 打败了他们试过的所有 7–8B LoRA 解码器，并在 unseen 上胜过 GPT-4o / Claude 3.5 / LLaMA-3-70B。增益非单调，且对超参极敏感。**纯模型侧——没有检索、没有文档上下文、没有时间维度** | [arXiv 2601.21722](https://arxiv.org/abs/2601.21722)（预印本，2026-01，与 A3CG 同组） |
| 漂绿 RAG 系统 | EmeraldMind：GreenClaims（51 条）上 EM-KGRAG 零样本准确率 93.55%、coverage 60.78%；620 条半合成 EmeraldData 上 EM-RAG coverage 62–77%。仅由 **37 份** ESG 报告构建；claim 由 LLM 生成并由 LLM 标注；无 aspect–action 粒度、无时间维度、无 SGX | [EmeraldMind，WWW 2026](https://arxiv.org/abs/2512.11506) |
| ESG PDF 问答难度 | 12 份报告 / 119 条 QA 上的 RAG 基线：**EM 21.0%、string F1 55.4%、数值准确率@±2% 45.3%、recall@5 70–80%** —— 数值与表格 grounding 是失败点 | [ESGBench，ICAIF 2025 workshop](https://arxiv.org/abs/2511.16438) |
| 环境声明检测 | 提供专家标注的二分类环境声明数据与 ClimateBERT 基线；删除未附表号的"F1≈0.8+" | [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) |
| 漂绿 NLP 全景 | *"目前不存在任何已验证的漂绿案例数据集。"* 建议用第三方判断替代主观标注，并采用**支持人工监督与可追溯推理的分解式 pipeline**——即它本身就为我们的架构背书 | [Calamai 等综述](https://arxiv.org/abs/2502.07541)（v2，2026-01） |
| 视觉文档检索 | 约 26k 页、3,099 条人工核验查询、6 语种；视觉检索优于文本，混合上下文改善生成，细粒度视觉 grounding 仍失败。公开记录未证明"ACL 2026 接收" | [ViDoRe V3，预印本](https://arxiv.org/abs/2601.08620) |
| RAG 事实核查 | 2025 冠军与效率数据应引用当年 overview/系统论文；2024 AIC-CTU 是前序系统，不是 2025 冠军论文 | [overview](https://aclanthology.org/2025.fever-1.15/)、[winner paper](https://aclanthology.org/2025.fever-1.22/)、[2024 predecessor](https://arxiv.org/abs/2410.11446) |
| 内部 v0 | 文本 BM25 + bge 稠密 + RRF + 重排；分类器 = A3CG 上微调的 encoder；核查 = LLM + top-5 外部证据 | 本项目 |

---

## 4. 方式方法

### 4.1 架构预览

```
(company, claim/aspect, year?) ─► 查询构造 (公司别名扩展, aspect 同义词)
   ─► 文本混合检索 (BM25 + bge-m3 + RRF) ─┐
   ─► 可选视觉页面检索 (ColQwen / Qwen3-VL-Emb) ┴► 跨模态融合 ─► 重排
   ─► 证据: 报告段落 + 可选页面截图/外部文章
   ─► 分类: aspect–action (A3CG 微调模型 / LLM+RAG)
        └─ 证据条件开关: 无 | 局部 | 同报告 | 跨年              ← 主消融
   ─► 可选外部核查: NLI/LLM → supports/refutes/NEI
   ─► 漂绿风险解释生成 (引用页码; 模糊措辞高亮; 目标/时间/数值缺失检查)
   ─► UI: 公司选择 + 声明输入 + 证据页缩略图 + 风险卡片
```

### 4.2 检索创新（Q3）

1. 混合检索 + 交叉编码重排（基本要求）。
2. **公司/年份元数据过滤 + 跨年份对比检索**（"2022 vs 2024 目标是否被悄悄改动"→ 时间线检索）。这是最站得住的新检索组件，且直接对应作业里的 "timeline and metadata search" 条目——**优先级提到视觉检索之前**。
3. **视觉页面检索（增强项）**：只在**设上限**的表格/图表子集上与文本检索融合。由于 pilot 中约 57% 的页面含表格，"自然表格/图表子集"会膨胀到半个语料，因此明确上限设为 **≤1,200 页**。预算：ColPali 类模型每页约 1,030 个 128 维向量，fp16 约 260 KB/页，1,200 页 ≈ 0.3 GB（全量 10k 页索引则约 2.7 GB、4090 级 GPU 上约 2–4 小时编码）。消融仅文本/仅视觉/融合，不把全页视觉索引设为最低交付。
4. **查询扩展**：aspect 同义词表（A3CG aspect 类别）+ HyDE 假设段落。
5. Contextual chunk header 与 late chunking 对照。

### 4.3 下游创新（Q5）

1. **证据条件化的 aspect–action 分类（主线）。** 同一分类器在 `纯单句 / +局部上下文 / +同报告检索 / +跨年检索` 四种条件下，在我们自建的带出处 SGX 集上对比（seen/unseen 按 A3CG fold 类别映射）。这是没人做过的实验，其余都是配套。
2. **跨年一致性核查。** 检索同一公司同一 aspect 的历年声明，报告标签迁移（`planning → implemented`？目标被弱化？声明消失？）。先做报告内；外部 AVeriTeC 式核查仅作第二阶段可选项。
3. **漂绿风险信号解释**：规则（无数字/无年份/模糊词典/`climate_specificity`）+ LLM 解释，claim-level citation。报告中需注明 SwissText 2025 已确立 specificity 与内部佐证信号，我们的增量是**按 aspect–action pair 施加并带页级出处**；始终称 risk signal，不输出公司级结论。
4. **跨类别泛化实验**：在 A3CG fold-k 的 seen 类别上训练，在我们 eval 集中属于 fold-k unseen 类别的样本上测试，检验 RAG 上下文是否改善 unseen 泛化；这是有价值的课程实验，但不预先承诺论文结果。可选加分项：在我们 2020–2022 年语料里精确匹配 A3CG 原句，为部分 A3CG 样本找回上下文。
5. **不要把对比 / 序数 / 门控目标写成创新** —— COGLM（arXiv 2601.21722，同一组，2026-01）已经在同一数据集上发表了完全相同的东西。把它复现成基线是有价值的；把它说成我们的贡献则不行。
6. 可选：SenticNet 概念级特征作为符号信号（与教授和博后他们组的工具方向对齐）。

### 4.4 评估

| 层 | 回答什么 | 指标 | 数据 |
|---|---|---|---|
| KB | 语料够不够、干不干净 | 报告数、chunk 数、词数、type 数、解析成功率 | 约 240 份 SGX 报告 |
| 检索 | RQ3 | P@5、R@10、MRR、nDCG@10；**wrong-company@10**（top-10 中别家公司段落的占比，自定义）；表格/图表页子集单列 | ≥50 条查询，分三类：指定公司查声明 / 跨年查同一 aspect / 通用；pooled top-10 人工相关性 |
| 分类（绝对值） | 系统本身能不能用 | has_pair F1、span token-F1、action macro-F1 + 各类 F1 + accuracy、联合 AAA F1 | 自建 `eval.xls` |
| **分类（主实验）** | **RQ1** | 四种证据条件相对纯单句的 **ΔF1**；**翻转分析**（加证据后改判的比例，及其中错→对与对→错的净差）；McNemar 检验或 bootstrap 95% CI | 同上，每条带出处 |
| 分桶分析 | 证据具体帮到哪类错误 | 按 A3CG 六类失败模式分别计算 Δ | eval 样本的失败模式标签 |
| 跨年轨迹 | RQ2 | 轨迹完全匹配率、transition F1 | 约 60 条 (公司, aspect) × ≥3 年的人工轨迹 |
| 生成 | 解释可不可信 | RAGAS faithfulness / answer relevance / context precision；**citation precision**（人工抽 50 条，看引用页是否真的支持）；可选人工 Likert | 系统输出 |
| 外部核查（可选） | — | 三分类 macro-F1；Ev2R 风格证据召回（LLM 评估） | 仅在实现时 |
| 系统 | 能不能用 | 各阶段 p50/p95 延迟、索引耗时、视觉索引显存/磁盘、5 条查询计时 | — |

- **必须精确写明指标口径**：AAA（联合 pair F1）还是 ATE 还是 AC，micro 还是 macro，给定 gold span 还是联合抽取。混着写是最快暴露"没看懂数字"的方式。
- **seen/unseen 的实现**：沿用 A3CG 三个 fold 的类别划分，在 fold-k 的 seen 类别上训练，在我们 eval 集中属于 fold-k unseen 类别的样本上测试。因此 `eval.xls` 需多标 aspect category（成本很低）。
- **主实验看 Δ，不看绝对 F1**：即使整体分数不高，只要 Δ 与置信区间报告得干净，结论依然成立。
- **分桶预测可以被证伪**：证据应该帮到 ellipsis / unattributed（缺上下文、缺归属），不应该帮到否定 / modality（信息就在句子里）。如果结果相反，本身也是有价值的发现。

---

## 5. 验收标准

**原分类指标高于已发表 SOTA，现已修正。** 旧版要求 action macro-F1 ≥0.70 seen / ≥0.55 unseen（期望 0.78 / 0.65）；而 A3CG 自己的 AC 分数是 seen 51.8–60.5、unseen 21.6–36.5，联合任务当前 SOTA 是 67.6 seen / 49.0 unseen。注意 A3CG 的 AC 本身就是"在正确识别 aspect 之后"再分类 action，已经接近"给定 gold span"，所以给定 span 并不会让任务明显变简单。**分类的绝对门槛以复现 A3CG 参照水平为准，主验收放在证据条件化的 Δ 上。** 分类口径在下面二选一，并在报告中写明；由于评测在我们自己的 SGX 集上进行，与 A3CG 数字的比较只是参照。

| 项目 | 最低门槛 | 期望 |
|---|---|---|
| KB | ≥10k chunk、≥100k 词 → **300 词/块时约需 240 份报告**（实测，见 §2.1） | 多行业、多年份；≤1,200 页的视觉子集 |
| 评测集 | `eval.xls` ≥1,000 条，含 no-pair；pair/action IAA ≥0.80，span agreement 单列；按 §2.3 分阶段协议执行 | 外部核查集与 qrels ≥50 仅在核心完成后增加 |
| 检索 | 混合检索的 nDCG@10 优于单独 BM25/稠密；加公司/年份过滤后 wrong-company@10 下降 | 视觉融合在受控表格/图表子集有正向提升 |
| **分类 —— 方案 (a)，与分阶段标注协议一致**：**给定 gold aspect span** 的 action 分类（三分类），同时报 accuracy | macro-F1 达到 A3CG T5 基线的 AC 水平：≥ 0.55（seen）、≥ 0.25（unseen） | 达到 A3CG 已发表最佳 AC：≥ 0.60 / ≥ 0.36 |
| **分类 —— 方案 (b)**：A3CG 的联合 **AAA F1**，可与文献直接比较 | ≥ 0.60（seen）、≥ 0.40（unseen） | ≥ 0.68 / ≥ 0.47（即逼近 COGLM 的 67.6 / 49.0） |
| **证据条件化消融（主线，主要验收项）** | 四种证据条件相对纯单句的 ΔF1 + 翻转分析，附 McNemar 检验或 bootstrap 95% CI；seen/unseen 分开；同时报告检索指标。负结果同样有效 | ellipsis / unattributed 分桶上 Δ 显著为正，否定 / modality 分桶上不显著（与预测一致） |
| 跨年轨迹 / 核查 | 约 60 条 (公司, aspect) × ≥3 年的轨迹集，报告轨迹完全匹配率与 transition F1 | 可选外部 supports/refutes/NEI macro-F1 ≥0.55 |
| 生成 | RAGAS faithfulness ≥ 0.75；所有风险提示可溯源到页码；人工抽查 50 条的 citation precision 单列 | ≥ 0.85 |
| 性能 | 端到端 ≤ 8 s（视觉检索较重；视觉重排单独计时） | ≤ 4 s |
| UI | 公司 + 声明输入、证据页缩略图、5 条查询计时 | — |

---

## 6. 论文校验与用途（[OneDrive 论文资料夹](Useful%20Paper.html)）

| 已核验来源 | 用途与边界 |
|---|---|
| [A3CG](https://aclanthology.org/2025.acl-long.723/)（ACL 2025） | **核心依据**：pair/no-pair、aspect span、action、seen/unseen 协议；原文明确不作确定性漂绿检测，提案必须保留这条边界。注意它**没有报告任何 IAA**。 |
| [COGLM / Robust greenwashing LM](https://arxiv.org/abs/2601.21722)（预印本，2026-01） | **同一组对 A3CG 的直接后续，也是当前 SOTA（72.4 / 67.6 / 49.0）。** 是需要复现并用检索超越的基线，*不是*可供我们主张的新颖点。 |
| **[EmeraldMind](https://arxiv.org/abs/2512.11506)（ACM Web Conference 2026）+ EmeraldApp demo** | **最接近的现有系统：知识图谱 + 向量 RAG 的漂绿检测，带证据理由与 abstain。** 必须引用并说明差异（§1.4）。它的弱点——仅 37 份报告、claim 由 LLM 生成并标注、无 aspect–action 粒度、无时间维度、无 SGX——正是我们的区分点。 |
| [ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/)（EMNLP 2025） | **"报告内证据核查"的直接先例**（PI / AE / CPEP / TV，证据限定同一文档，文本 + 图像 RAG 基线，κ 0.60–0.96）。相关工作中应优先于通用 AVeriTeC。 |
| [Corporate greenwashing survey](https://arxiv.org/abs/2502.07541)（Calamai 等，v2 2026-01） | 定义、数据与方法背景；其"**不存在已验证的漂绿数据集**"结论与"**分解式 + 人工监督 pipeline**"建议，是我们风险筛查框架最强的支撑。 |
| [SwissText 2025 ESG hints](https://aclanthology.org/2025.swisstext-1.3/) | 正式 proceedings 论文，150 份德国 DAX 报告；**已经确立**了 specificity + 内部佐证的风险提示，域与 SGX 不同。作为先行工作引用，不能写成我们的想法。 |
| [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) | 环境声明检测数据与基线，可用于候选句筛选。增补 `climate_specificity` 用于模糊度信号。全部 climatebert 数据集为 CC-BY-NC-SA-4.0。 |
| [ESGBench](https://arxiv.org/abs/2511.16438)（ICAIF 2025 workshop） | 规模很小（12 份报告 / 119 条 QA），但可作为"ESG PDF 数值与表格 grounding 有多难"的现成证据（EM 21%、数值 45%），用于设定合理的生成指标预期。 |
| [ViDoRe V3](https://arxiv.org/abs/2601.08620) / [ColPali](https://arxiv.org/abs/2407.01449) | 视觉页检索依据；ViDoRe V3 目前按预印本标注，不写"ACL 2026"。 |
| [Qwen3-VL Embedding](https://arxiv.org/abs/2601.04720) / [UniDoc-Bench](https://arxiv.org/abs/2510.03663)（预印本） | 视觉 embedding/reranking 与多模态评测候选；不应同时承诺实现所有模型。本行与上一行的四个 arXiv ID 已于 2026-09-10 重新核验。 |
| [AVeriTeC 2025 overview](https://aclanthology.org/2025.fever-1.15/) / [winner system](https://aclanthology.org/2025.fever-1.22/) | 外部事实核查的可选流程。旧 `2024_AIC-CTU` PDF 是 2024 前序方法，不是 2025 冠军论文。 |
| [Ev2R](https://arxiv.org/abs/2411.05375) | 证据召回评估参考；仅在实现外部核查时需要。 |
| [共用 OneDrive 论文资料夹](../Common%20Useful%20Paper.html) | 通用 RAG、评估与切分背景。 |

---

## 7. 挑战点

1. **标注与 IAA —— 最大的进度风险。** A3CG 用了 5 名可持续性方向博士/博后标注员 + 3 名 verifier，**仍然没有报告 κ**。≥80% 的要求只能靠我们自己；用 §2.3 的"预抽取 + 接受/拒绝"分阶段协议，并把两轮试标排进第 1–2 周。分歧会集中在 `implemented` vs `indeterminate`。
2. **PDF 工程量**：报告排版复杂（双栏、图表、跨页表），文本抽取噪声大——但 ACL 正式发表的 A3CG 文本同样带这些伪影，说明可以容忍而非致命。视觉检索能绕过 OCR 但索引重；§4.2 的 ≤1,200 页上限把它压在约 0.3 GB。
3. **语料抓取才是 KB 的真实成本**：240 份意味着要跨约 60–80 家公司 IR 站点 × 3–4 年，约 1–2 人周。没有已验证的单一批量来源；`sustainabilityreports.com` 宣称支持按国家/年份批量下载，值得先花一小时试，因为它可能直接省掉整个爬虫。
4. **外部证据稀疏**：多数中小公司没有稳定外部报道，核查集会偏向 NEI；综述也确认不存在已验证的漂绿数据集。**建议：砍掉外部事实核查，或保留为不设验收指标的拉伸目标**——它工作量最大而结论最难站住。
5. **算力不是瓶颈**：A3CG 自己的实验跑在*单张 RTX 4090* 上。只有视觉索引需要真实 GPU 时间（受控规模下约 0.3 GB、<1 小时）。无 GPU 时改用 `vidore/colSmol-500M` 或云端。
6. **与教授和博后他们组的工作接近**——现在还额外接近 EmeraldMind（WWW 2026）与 ML-Promise（EMNLP 2025）。对齐有好处，但也会被更严格审视；必须明确区分"复用 A3CG"与本项目新增的检索、证据条件化和跨年部分，并把这三个先行系统全部引用。
7. **法律/声誉**：即使只输出"漂绿风险信号"也属敏感判断；UI 与报告必须持续显示"辅助筛查，非结论"，不对具体公司作漂绿定性。

---

## 8. 其他注意事项

- **分工**：KB 大家一起做（PDF 抓取解析、页面渲染、元数据、声明抽取）；检索组 3 人（文本/视觉双索引、融合、重排、消融）；下游组 2 人（分类器、证据条件化消融、解释生成、RAGAS、UI）。
- **时间表**（截止 2026-11-07）：**W1 KB 组立即开始抓取**，不要等到 W3。W1–2 用约 30 家公司 × 3 年（约 90 份）做许可/下载/解析/规模 pilot 与试标，同时复现 GRACE 与 T5-base 基线；W3–4 扩到约 240 份门槛并完成文本 v0 + UI；W5–7 做元数据/跨年检索、证据条件化消融与分类，再按资源增加视觉检索；W8–9 评估；W10 报告。
- **第一周清单**：
  1. 用 HF checkpoint 跑 `keanepotato/a3cg_greenwash` 的 GRACE fold-1 seen/unseen，确认约 60.87 seen / 50.08 unseen。若能复现，下游一半风险一天内解除。
  2. 在 `full_train.json` 上微调一个 T5-base，目标约 70.5 全量 AAA F1，作为内部基线。
  3. 跑通约 90 份报告的端到端 pilot（下载 → 解析 → 切分 → 统计），报告解析失败率并重新外推 240 份目标。
  4. 花一小时试 `sustainabilityreports.com` 批量下载。
  5. 标注试标第 1 轮：50 条、3 名标注员、分阶段协议、分维度报一致性。
  6. 在动工前先定下分类指标口径（§5）。
- **后续研究可能性**：若许可允许发布数据、核心实验严谨且系统性检索确认新颖性，可再与教授和博后他们组讨论后续研究；课程提案阶段不承诺合作、Q1/Q2 发表或给予任何承诺。
- **降级方案**：若视觉检索算力不足，退回纯文本 + 表格结构化抽取，仍满足作业要求。

---

## 9. 参考链接

- **A3CG 代码 + 数据（用这个）**：https://github.com/keanepotato/a3cg_greenwash ；checkpoint：https://huggingface.co/keentomato （`a3cg_greenwash_grace_f1/f2/f3`）；无代码的镜像仓库：https://github.com/SenticNet/greenwashing-detection ；论文页：https://aclanthology.org/2025.acl-long.723/
- EmeraldMind（WWW 2026）：https://arxiv.org/abs/2512.11506 ；ML-Promise 数据：http://MLpromise.nlpfin.com/
- ClimateBERT 数据：https://huggingface.co/climatebert
- ViDoRe / ColPali 模型：https://huggingface.co/vidore ；Qwen3-VL-Embedding：https://huggingface.co/Qwen
- **SGXNet 直连 PDF 模式**：`https://links.sgx.com/1.0.0/corporate-announcements/<ANNOUNCEMENT_ID>/<file>.pdf`（无需认证；`api.sgx.com/announcements/...` 需认证）
- SustainabilityReports.com：https://www.sustainabilityreports.com/ ；SGX 可持续报告规则：https://www.sgx.com/regulation/sustainability-reporting
- NUS CGS × SGX 可持续报告审阅 2023：https://bschool.nus.edu.sg/cgs/wp-content/uploads/sites/7/2023/11/CGS-SGX-Sustainability-Reporting-Review-2023_Report.pdf
- AVeriTeC 2025 冠军代码：https://github.com/aic-factcheck/aic_averitec ；HerO：https://github.com/ssu-humane/HerO
- 工具：pymupdf/marker、pdfplumber、Pyserini、FAISS/Qdrant、colpali-engine、ir_measures、RAGAS、vLLM、Gradio
