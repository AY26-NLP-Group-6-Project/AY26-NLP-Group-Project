# AI6127 Group Project Group 6 · 选题提案总览

> 校验日期：2026-08-26 ｜ 截止：2026-11-07 23:59 SGT ｜ 作业说明：[Group Assignment Intro.pdf](../Group%20Assignment%20Intro.pdf) ｜ English: [README.md](README.md)
>
> 论文 PDF 已迁至 OneDrive （NTU给了我们一人3T, 不用白不用）：各选题通过自己的 `Useful Paper.html` 进入；通用论文通过 [Common Useful Paper.html](Common%20Useful%20Paper.html) 进入。下文另给 arXiv / ACL Anthology / 官方页面，便于独立核验元数据与原文主张。

## 结论与推荐顺序

| 目录 | 选题 | 当前建议 | 核心理由 |
|---|---|---|---|
| [Patch Version RAG](Patch%20Version%20RAG/README_CN.md) | 游戏补丁说明的版本感知 / 时间旅行问答 | **感觉最稳捏** | 数据与答案可追溯、1,000 题可人工逐条核验、版本过滤/路由可清楚消融；先做 API 与许可试采样即可锁定可行性。 |
| [Energy Opinion RAG](Energy%20Opinion%20RAG/README_CN.md) | 东南亚能源转型观点 RAG | **感觉也不错，但是数据gated** | 与课程兴趣高度契合，但 Reddit 研究访问现需审批，且“观点分布”不能被解释为总体民意；获批前不能把第三方 dump 当作低风险主数据源。 |
| [Greenwash RAG](Greenwash%20RAG/README_CN.md) | SGX 可持续报告的漂绿风险感知证据 RAG | **教授组估计喜欢，不过高上限伴随高风险** | A3CG 与本地场景很强，但标注、PDF/视觉检索及外部核查工作量最大；系统只能做风险筛查与证据辅助，不能作确定的漂绿判决。 |

## 作业硬约束速查

- KB ≥ 10,000 文档/段落且 ≥ 100,000 词；需自行清洗、切分并报告文档、chunk、词数与类型统计。
- 必须实现稀疏、稠密和混合检索（可再加重排）；不得用 SQL `LIKE`；需简单 UI、5 条示例查询与速度报告。
- 自建、留出的评测集 ≥ 1,000 条**人工标注/核验**记录（上学期ML作业100条都挺够呛的，这学期NLP大家都是加把劲骑士），去重、尽量均衡，IAA ≥ 80%；分类任务提交 `eval.xls`。半自动生成不等于免除逐条人工核验与独立重标子集。
- 检索报告 P@K、R@K、MRR、nDCG；下游报告任务指标，并做答案层面的 faithfulness、answer relevance、context relevance/precision（可用 RAGAS）及性能测量。
- 每个创新点都要有对应消融；与往届或同届项目重叠 >30% 将失去成绩。（我上学期的A-的LLM作业不能复用了555）
- 最终提交为以小组编号命名的单个 PDF (应该都会Latex吼，谁要是有vip的话请群里说，不然咱可能得代码库里放论文了)，并在报告中给出数据和代码的 OneDrive/GitHub 链接；不要把本仓库里的 HTML 跳转页误当作最终数据/代码交付物。

## 三个选题的可行性对比

| 维度 | Patch-Version | Energy-Opinion | Greenwash |
|---|---|---|---|
| 课程适配 | 高：QA + 版本元数据检索 + 生成 | 很高：观点/情感与课程兴趣直接相关 | 很高：延伸 A3CG 与 ESG 方向 |
| 数据风险 | **低–中**：先验证 Wiki API、复用条款及 Data Dragon 覆盖 | **中–高**：Reddit for Researchers 审批、伦理与不可再分发限制 | **中**：公开 PDF 多，但需记录许可、抓取条款与截止快照 |
| 1,000 条评测 | 最容易：四类 QA 逐条人工核验，另抽独立双标子集算 IAA | 中高：标签过多会压低 IAA；应缩为主观性/立场核心任务 | 最高：aspect span、action 与 no-aspect 都需要领域判断 |
| 最小可交付创新 | 版本元数据过滤/路由 + 过期证据警告 | 视角覆盖度重排 + 一项下游创新 | 证据条件化 aspect–action 消融（无/局部/同报告/跨年）+ 跨年检索；视觉只做 ≤1,200 页的受控子集消融 |
| 最大范围风险 | 一开始就做完整版本图和全量快照回放 | 同时做条件立场、frames、讽刺、冲突、Singlish | 同时做视觉索引、外部事实核查和公司级漂绿判断 |
| 推荐控制 | 图方法作为增强项；先用版本字段做强基线 | 未获数据授权则换合法开放语料；输出只代表采样平台话语 | 改称 risk-aware assistant；MVP 先做报告内证据与 action 分类 |

## 论文与引用校验结论

- 核心引用均能找到对应公开记录，但多篇 2025–2026 工作目前只是 arXiv 预印本；提案中已避免把预印本写成已同行评审或已被某会议接收。
- [VersionRAG](https://arxiv.org/abs/2510.08109) 的 100 题/34 文档及主要基线结果可作为 Patch-Version 的直接依据；[TG-RAG](https://arxiv.org/abs/2510.13590) 与 [ChronoQA](https://arxiv.org/abs/2508.12282) 支持时间检索动机，但精确表格数值应附表号/页码，否则只作定性引用。
- [O-RAG](https://arxiv.org/abs/2604.12138)、[BERDS](https://arxiv.org/abs/2409.18110) 与 [DIVERGE](https://arxiv.org/abs/2602.00238) 支持观点合成与视角覆盖问题；它们不能证明 Reddit 样本代表“新加坡人总体”。
- [A3CG](https://aclanthology.org/2025.acl-long.723/) 是 Greenwash 的最强依据，但原文明确说它**不是确定性漂绿检测系统**（因此提案统一改为"风险感知/证据辅助"），并且**全文没有报告任何 IAA 数值**。2026-09-10 更新：应使用论文本身引用的 [keanepotato/a3cg_greenwash](https://github.com/keanepotato/a3cg_greenwash)，它在数据之外还带 GRACE 实现、评测脚本与预测结果，checkpoint 在 HF `keentomato`；`SenticNet` 镜像仓库的 "code coming soon" 已过时。两个仓库都没有 LICENSE，论文脚注 2 承诺的公司/年份名录也不存在。
- Greenwash 原稿"未发现完全同构系统"的说法**撤回**：[EmeraldMind](https://arxiv.org/abs/2512.11506)（ACM Web Conference 2026）是带证据理由与 abstain 的知识图谱+向量 RAG 漂绿检测系统，[ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/)（EMNLP 2025）已经做了 ESG 承诺的报告内证据关联。两者都必须引用；仍然空着的口子见 [Greenwash README §1.4](Greenwash%20RAG/README_CN.md)。
- [ViDoRe V3](https://arxiv.org/abs/2601.08620) 支持视觉文档检索方向，但公开记录不足以把它写成“ACL 2026 已接收”；现标为预印本。
- AVeriTeC 2025 冠军结果应引用[官方 shared-task overview](https://aclanthology.org/2025.fever-1.15/)及[冠军系统论文](https://aclanthology.org/2025.fever-1.22/)。原来列出的 2024 AIC-CTU 论文不是 2025 冠军论文，只能作前序方法参考。

## 在线论文入口

| 资料夹 | 内容 |
|---|---|
| [Common Useful Paper](Common%20Useful%20Paper.html) | RAG、Agentic RAG、评估、LiveRAG、切分、图检索与冲突等通用论文 |
| [Energy Useful Paper](Energy%20Opinion%20RAG/Useful%20Paper.html) | 观点 RAG、多视角检索、Reddit/Singlish 与核能舆情 |
| [Patch Useful Paper](Patch%20Version%20RAG/Useful%20Paper.html) | VersionRAG、TG-RAG、ChronoQA、时间鲁棒性与冲突处理 |
| [Greenwash Useful Paper](Greenwash%20RAG/Useful%20Paper.html) | A3CG、环境声明、视觉文档检索与 AVeriTeC |

四个 HTML 的 meta-refresh 均能跳到预期 SharePoint 资料夹，但注意需要登录一个MS账号，否则自动请求会返回 HTTP 403 (NTU搞的强制认证)。

## 小建议

1. Patch-Version感觉不错：第一周完成 100 个页面/补丁的 API 与解析 pilot、许可记录、10k chunk 规模外推，以及 50 题独立双标试验；达到门槛再扩全量。
2. 或者大家对Energy感兴趣的话：我们得先申请 [Reddit for Researchers](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program)，取得学校伦理审查/豁免与数据使用许可后再锁题；否则切换到可合法复用的开放观点数据。
3. 如果组内有 ESG 领域经验、PDF 处理能力和可承受标注工时的情况下选 Greenwash；先做文本 MVP，视觉页面检索与外部核查作为逐级增强项。
4. 定题后把仓库根目录 README 的 `<Pending Proposal / Approval>` 替换为最终摘要，并把重叠检查、数据截止日期、许可与伦理处理写进报告。
