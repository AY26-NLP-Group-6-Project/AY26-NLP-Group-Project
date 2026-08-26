# Proposal 2 · Patch-Version-RAG: Version-Aware "Time-Travel" QA over Game Patch Notes

> Recommendation: safest primary (distinctive, clean evaluation, intuitive demo) ｜ 中文版：[README_CN.md](README_CN.md) ｜ [OneDrive paper folder](Useful%20Paper.html)
> One-liner: index every patch note plus champion / item pages of League of Legends (or Dota 2 / Minecraft) as a versioned knowledge base and answer "What was X's Q cooldown in patch 13.5?", "When was X last nerfed?", "What changed for X between 14.1 and 14.10?", "What is the current value?" — with patch-number citations and an explicit warning whenever retrieved evidence is outdated.

---

## 1. Problem definition

### 1.1 Formalisation

- **Input**: a natural-language question `q`, with explicit or implicit version / time information.
- **Knowledge base**: version-organised documents `D = {d_{e,v}}`, where `e` is an entity (champion / ability / item / map mechanic) and `v` a version (e.g. `14.10`); each version contributes patch-note passages plus an entity snapshot page for that version.
- **Output**: answer + citation (patch number / page version) + a "freshness status" (`current / outdated / changed-in-between`).
- **Four question types** (four balanced subsets of the eval set):
  1. **Point-in-time**: "In patch 13.5, what was Ahri's Q base damage?"
  2. **Change detection**: "In which patch was Ahri's Q last nerfed?" "How many times was Zhonya's changed in 2024?"
  3. **Interval diff**: "What changed for Yasuo from 14.1 to 14.10?"
  4. **Latest state**: "What is Kai'Sa's W cooldown now?" (the system must locate the latest version and state it)
  plus an adversarial subset: **stale-evidence traps** — no version in the question while the corpus holds several versions of the same value; the system must pick the latest and mention the history (ties in with the evidence-conflict research line).

### 1.2 Why this is worth doing

- [VersionRAG](https://arxiv.org/abs/2510.08109) (preprint, Oct 2025) reports 58% for naive RAG and 64% for GraphRAG on version-sensitive questions, while VersionQA has **100 questions over 34 documents**. A 1,000+ question benchmark is a clear increment, but publication value depends on release rights, natural questions and rigorous human verification.
- It hits two hot 2025–2026 lines at once: **temporal / version-aware RAG** (TG-RAG, ChronoQA, IA-RAG) and **evidence conflicts** (CONFLICTS, MAGIC, "Does RAG know when retrieval is wrong").
- Labels should be relatively controllable if the pilot confirms stable Wiki templates/modules: generate semi-automatically and verify every question by hand. **IAA above 90% is a target, not a guarantee.**
- Practically zero chance of topic overlap with classmates; the demo (timeline slider) is intuitive.

### 1.3 Mapping to the grading rubric

| Rubric item | This project |
|---|---|
| KB (20) | versioned corpus crawling & parsing, (entity, version, change) triple extraction, entity × version chunking |
| Retrieval (40) | hybrid retrieval + version filtering / routing + version-graph index + reranking; timeline / metadata search is an explicitly listed innovation |
| Downstream (40) | version-aware generation, stale-evidence warnings, change summaries, EM / F1 + RAGAS |

---

## 2. Data and knowledge base

### 2.1 Candidate corpora (pick one; LoL preferred)

| Game | Source | Size | Licence / notes |
|---|---|---|---|
| **League of Legends** | [official LoL Wiki](https://wiki.leagueoflegends.com) and [Riot patch notes](https://www.leagueoflegends.com/en-us/news/tags/patch-notes/) | historical patches and entity changes plausibly exceed 10k chunks; measure in the pilot | verify the current Wiki API, robots and text-reuse/attribution terms first; Riot content/assets remain subject to copyright and developer policies |
| Dota 2 | Valve changelog + Liquipedia / dota2.fandom | similar | Liquipedia CC BY-SA |
| Minecraft (Java) | Minecraft Wiki version-history pages | large | CC BY-NC-SA |
| Non-game fallback | PyTorch / Python / Kubernetes changelogs + per-version docs | large | more "serious", less fun |

### 2.2 Parsing and chunking

- In week 1, test the MediaWiki API, template coverage and reuse terms on 100 pages/patches. Only then scale `mwparserfromhell` extraction of `(entity, ability, field, old_value, new_value, patch)` triples.
- Document units: `patch_note_chunk` (all changes to one entity in one patch, 200–400 words) + `entity_snapshot_chunk` (the entity's value table at a given version, replayed from triples).
- Metadata: `{entity, entity_type, patch, patch_date, season, change_type ∈ {buff, nerf, adjust, rework, new, removed}}`; versions normalised to comparable tuples.
- Storage: JSONL + Pyserini index + FAISS; version graph (entity nodes —change edges→ version nodes) in NetworkX / SQLite.

### 2.3 Evaluation set (≥ 1,000 questions, IAA ≥ 80 %)

- Generate four question types from triples, then rewrite naturally and **verify every item by hand** for answer, gold evidence, naturalness and ambiguity. Independently double-code at least 20–30% and report answer agreement and question-acceptability IAA separately before adjudication.
- Total ≥1,000, roughly 250 per type; 100–200 are also tagged as stale-evidence traps within that total and reported separately.
- Format: JSONL `{"qid","question","type","entity","patch_ref","answer","evidence_ids"}` plus qrels (gold chunks per question).
- Extra: 50 free-form interval-diff questions with human reference summaries (ROUGE / BERTScore + RAGAS).

---

## 3. Baseline level

| Layer | Current level | Source |
|---|---|---|
| Version QA | Authors report naive RAG 58%, GraphRAG 64% and VersionRAG 90% on VersionQA; include the table reference when retaining exact values | [VersionRAG, preprint](https://arxiv.org/abs/2510.08109) |
| Temporal graph RAG | Supports temporal graphs, hierarchical summaries and incremental updates; old 0.599/0.405 and 6× claims are removed until table citations are supplied | [TG-RAG, preprint](https://arxiv.org/abs/2510.13590) |
| Time-sensitive QA datasets | 5,176 Chinese-news questions across absolute, aggregate and relative time, useful for typology design | [ChronoQA, preprint](https://arxiv.org/abs/2508.12282) |
| Conflict handling | Supports outdated/conflicting-context categories and generator-behaviour analysis; do not assume identical behaviour in the game domain | [CONFLICTS](https://arxiv.org/abs/2506.08500), [context compliance](https://arxiv.org/abs/2605.14473) (preprints) |
| Internal v0 | BM25 / bge dense / RRF / rerank (**no version filtering**) → expected 50–65 % accuracy on point-in-time & latest, lower on diff / change detection | this project |

---

## 4. Method

### 4.1 Architecture

```
q ─► intent classification (point / change / diff / latest) + entity / version extraction (rules + small model)
  ─► routing:
      point   → version-filtered hybrid retrieval (BM25 + dense + RRF) → rerank
      change  → traverse change edges of the entity in the version graph → relevant patch chunks
      diff    → all changes of the entity within the interval → aggregate
      latest  → max-version snapshot + last N changes
  ─► conflict / freshness check: several values for the same field → mark outdated / current
  ─► LLM generation (patch citations; change summaries; stale warnings)
  ─► UI: timeline slider + entity card + change table
```

### 4.2 Retrieval innovations (Q3, each ablatable)

1. Hybrid retrieval + cross-encoder reranking (course requirement).
2. **Version-aware filtering / weighting**: version constraints as hard filters or soft weights (closer to the target version = higher score); compare with no version constraint.
3. **Version-graph index + routing (enhancement)**: first establish a strong version-metadata filtering baseline, then implement a VersionRAG/TG-RAG-style graph if time permits.
4. **Chunking comparison**: patch-note chunks vs. entity snapshots vs. both; late chunking/contextual headers (see the [shared OneDrive paper folder](../Common%20Useful%20Paper.html)).
5. **Query rewriting**: canonicalise colloquial questions into "entity + field + version"; HyDE / G-RAG hypothetical-answer retrieval as a comparison.

### 4.3 Downstream innovations (Q5, ablation required)

1. **Stale-evidence warnings and conflict-aware generation**: list the timeline when several values exist and state "as of vX …", following CONFLICTS' outdated-type handling.
2. **Change-summary generation**: interval-diff questions answered from structured triples + LLM, evaluated with ROUGE / BERTScore.
3. **Self-check faithfulness**: every number in the answer must appear in the cited chunk (string / numeric match) or is highlighted.
4. **Iterative retrieval**: two-hop questions ("how did X's win rate move after its last nerf") through agentic follow-up retrieval (optional).
5. Optional: SFT a small model (Qwen3-1.7B / 4B) on generation questions and compare with a zero-shot 8B model.

### 4.4 Evaluation

- Retrieval: P@k, R@k, MRR, nDCG@10 (`ir_measures`), reported per question type; **version hit rate** (does top-k contain the target-version chunk?).
- Generation: EM / F1 (numeric questions), ROUGE-L / BERTScore (summary questions), RAGAS faithfulness / answer relevance / context precision; stale-trap subset reports the "warned about staleness" rate.
- System: latency, indexing time, token usage (vs. GraphRAG-style methods).

---

## 5. Acceptance criteria (loose for now)

| Item | Minimum | Target |
|---|---|---|
| KB | ≥ 10 k chunks, ≥ 100 k words, ≥ 100 patches covered | all patches + all champion snapshots |
| Eval set | ≥1,000 questions, four stratified types, every item verified; independently recoded subset has answer agreement and acceptability IAA ≥0.80 | ≥1,200, including ≥150 stale traps |
| Retrieval | version-aware hybrid retrieval beats v0 by ≥ 5 pt nDCG@10 | version hit rate@5 ≥ 0.85 |
| Generation | point / latest EM ≥ 0.70; change-type EM ≥ 0.55; diff ROUGE-L ≥ 0.35 | point ≥ 0.85; stale-warning rate ≥ 0.7 |
| RAGAS | faithfulness ≥ 0.8 | ≥ 0.9 |
| Performance | end-to-end ≤ 5 s | ≤ 2 s (graph paths are faster) |
| UI | timeline slider + clickable citations; 5 timed sample queries | — |

---

## 6. Citation audit and paper roles ([OneDrive paper folder](Useful%20Paper.html))

| Verified source | Use and boundary |
|---|---|
| [VersionRAG](https://arxiv.org/abs/2510.08109) (preprint) | **Direct template**: versioned QA, hierarchical version graph, intent routing and implicit change detection; 100 questions/34 documents is verified. |
| [TG-RAG](https://arxiv.org/abs/2510.13590) (preprint) | Temporal graph, hierarchical time-summary and incremental-update ideas; baseline status depends on code viability and implementation cost. |
| [ChronoQA](https://arxiv.org/abs/2508.12282) (preprint) | Absolute/aggregate/relative question construction directly informs the typology. |
| [IA-RAG](https://arxiv.org/abs/2606.06044) (preprint) | Optional interval-algebra enhancement, not a direct baseline for discrete patch versions. |
| [CONFLICTS](https://arxiv.org/abs/2506.08500) / [context compliance](https://arxiv.org/abs/2605.14473) (preprints) | Outdated/conflict taxonomy and generator-failure analysis; useful for warnings, not evidence of game-domain accuracy. |
| [Temporal robustness](https://arxiv.org/abs/2503.17073) (preprint) | Supports retrieval from time-qualified evidence instead of relying on parametric memory. |
| [HippoRAG 2](https://arxiv.org/abs/2502.14802) / [LightRAG](https://arxiv.org/abs/2410.05779) | Graph-retrieval comparisons; cite as experimental baselines only if actually implemented. |
| [When to use graphs in RAG](https://arxiv.org/abs/2506.05690) (preprint) | Helps justify when a version graph adds value over metadata filtering. |
| [Shared OneDrive paper folder](../Common%20Useful%20Paper.html) | Chunking, LiveRAG and general evaluation papers; cite individual methods only if implemented. |

---

## 7. Challenges

1. **Wikitext parsing**: patch-history templates evolved over the years; a robust parser plus sampled manual checks is the KB team's main workload.
2. **Snapshot replay**: one missed change corrupts later snapshots. Cross-check samples against [Data Dragon](https://developer.riotgames.com/docs/lol#data-dragon), but Riot notes that updates are manual, may not be immediate and versions may not match the client exactly; it is a validation source, not absolute truth.
3. **Question naturalness**: rewrite and human-polish template questions. Team members can independently restate real intents without importing Reddit questions and their extra data-access risk.
4. **Stale-trap design**: ensure the corpus really contains co-existing versions and that "latest" is well defined (write the data cut-off date in the report).
5. **Grader taste**: the professor and postdoc's group more often works on sentiment/opinion tasks; frame knowledge evolution and evidence conflict as a general NLP problem, with games as a clean test-bed and transfer to software/policy documents.
6. **Copyright and policy**: save a snapshot of current Wiki reuse terms during the pilot and attribute accordingly. Follow [Riot's developer policy](https://developer.riotgames.com/policies/general), include any required legal notice even for a school project, and do not redistribute copyrighted images/assets.

---

## 8. Other notes

- **Split**: KB team 2 (crawling, parsing, snapshot replay, QA generation scripts); retrieval team 2 (indexing, version graph, routing, ablations); downstream team 1–2 (generation, stale warnings, evaluation, UI). Everyone verifies questions.
- **Timeline**: W1–2 parser + triple extraction + v0; W3–4 QA generation & verification start + UI; W5–7 version graph / routing / conflict handling + ablations; W8–9 evaluation & failure analysis; W10 report.
- **Publication path**: resource + system paper ("PatchQA: a version-aware RAG benchmark over evolving game knowledge") → LREC-COLING / ECIR / CIKM short / SIGIR resource track; selling points: scale (> 1 k questions, hundreds of versions), four question types + stale traps, open-source parser.
- **Cheap domain switch**: if the game theme is a concern, the same pipeline runs on PyTorch / Kubernetes changelogs + versioned docs without changing the method.

---

## 9. Links

- LoL Wiki Patch History Project: https://wiki.leagueoflegends.com/en-us/League_of_Legends_Wiki_talk:Patch_History_Project
- LoL Wiki patch category: https://wiki.leagueoflegends.com/en-us/Category:Patch_notes ; Riot official patch notes: https://www.leagueoflegends.com/en-us/news/tags/patch-notes/
- Riot Data Dragon (per-version static data for validation): https://developer.riotgames.com/docs/lol#data-dragon
- TG-RAG code: https://github.com/hanjiale/Temporal-GraphRAG ; ECT-QA: https://huggingface.co/datasets/austinmyc/ECT-QA
- CONFLICTS: https://github.com/google-research-datasets/rag_conflicts
- HippoRAG: https://github.com/osu-nlp-group/hipporag ; LightRAG: https://github.com/HKUDS/LightRAG
- Tooling: mwparserfromhell, Pyserini, FAISS, NetworkX, ir_measures, RAGAS, vLLM / Ollama, Gradio
