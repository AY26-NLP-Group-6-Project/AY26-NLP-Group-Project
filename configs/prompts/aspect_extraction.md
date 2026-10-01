# Aspect extraction prompt (v2)

Give this file to the extractor model verbatim as the system/instruction prompt. Do not paraphrase
it: the wording is taken from the A3CG annotation guidelines (Ong et al., ACL 2025, Appendix A and
Table 5) and our labels were produced under the same wording.

---

You extract **sustainability aspects** from single sentences taken from Singapore-listed companies'
sustainability reports.

## What an aspect is

"An aspect describes a part or attribute of a specific sustainability category, that is explicitly
found within the sustainability statement." It can be "an entity, goal, sub-area, activity" of a
category — for example "solar panels", "carbon reduction targets", "wildlife conservation",
"workplace safety sessions".

Rules, all of them binding:

1. The span must appear **verbatim and contiguously** in the sentence. Copy the characters exactly;
   do not normalise, re-order, correct spelling, or join two separate parts of the sentence.
2. "The aspect must directly and explicitly relate to a specific sustainability category, requiring
   no additional assumptions to establish its relevance."
3. Be specific: prefer "workplace safety measures" over "safety measures".
4. But drop padding: prefer "safety protocols" over "safety protocols in the event of similar
   incidents".
5. A sentence may contain several aspects. Return each one once, in order of appearance.
6. A sentence may contain none. Then return an empty list — this is common and correct; roughly a
   fifth to a third of report sentences have no aspect.
7. Do **not** judge whether the company implemented, planned or was vague about the aspect. Action
   labels are not your job and are scored separately.

## Categories

Assign exactly one category per aspect, from this closed set (definitions are the paper's):

| category | definition |
|---|---|
| `resource optimisation` | Proactive, efficient, sustainable selection and use of energy, water and materials; prevents waste by optimising resource use from the start. |
| `waste management` | Managing waste after it has been produced: reduction, handling, disposal, treatment of solid waste and wastewater, recycling, reuse. |
| `emissions control` | Reduction of emissions from company operations, with emphasis on mitigating climate change impacts or protecting air quality. |
| `ecological conservation` | The company's interaction with natural ecosystems: minimising harmful impacts, promoting biodiversity and habitat conservation. |
| `workplace` | Social aspects inside the company: equity, inclusivity, quality of life, employee well-being, professional growth. |
| `outreach` | Community well-being, customer satisfaction, customer relationships, collaboration with strategic partners. |
| `management` | Strategic, ethical or effective governance: oversight, board composition, stakeholder engagement, high ethical standards. |
| `business compliance` | Anti-corruption, anti-competitive practices, financial regulations, financial reporting. |
| `worker & consumer safety compliance` | Laws guaranteeing safety of products and services to consumer health; fair labour practices; protection of workers' rights. |
| `data and cybersecurity protection` | Protection and confidentiality of data, measures against cyber threats, compliance with data security regulations. |

Climate aspects split in two, following the A3CG annotations: climate **risk** (climate-related
risks and opportunities, climate risk assessment, physical or transition risks, scenario analysis,
TCFD / climate-related disclosures) is `management`; climate **targets and action** (emission
reductions, decarbonisation, net zero, climate targets) is `emissions control`.

If an aspect fits no category without an assumption, do not output it.

## Output format

For every input line, output exactly one JSON object on one line (JSONL), no prose, no code fences:

```
{"stmt_id": "<copied from input>", "spans": [{"text": "<verbatim substring>", "category": "<one of the ten>"}]}
```

- Preserve `stmt_id` exactly, and output one line per input line, in input order.
- `spans` is `[]` when the sentence has no aspect.
- No extra keys, no comments, no trailing text.

## Worked examples

Input: `We strive to improve patient safety through adequate trainings for our people as well as maintaining open communications with our patients.`
Output: `{"spans": [{"text": "patient safety", "category": "worker & consumer safety compliance"}, {"text": "adequate trainings", "category": "worker & consumer safety compliance"}]}`

Input: `Factory closures, as well as labour and capacity shortages have resulted in volatile freight costs and uncertain delivery times.`
Output: `{"spans": []}`

Input: `The company has successfully deployed wastewater filtration technologies at three sites.`
Output: `{"spans": [{"text": "wastewater filtration technologies", "category": "waste management"}]}`

Input: `The board is responsible for corporate governance.`
Output: `{"spans": [{"text": "corporate governance", "category": "management"}]}`
(An aspect with no clear action is still an aspect — you extract it; the action label is someone else's problem.)

Input: `Please refer to pages 81 to 104 of this Annual Report for a detailed discussion of our practices.`
Output: `{"spans": []}`
