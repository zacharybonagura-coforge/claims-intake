# Model Decision Record

Run ID: `day5-local-08`

Do not select one universal model solely because it leads on a different task.

## Decision constraints (fixed before results)

These were not edited to fit the winner:

- Local Ollama only; `cost_usd = 0.0`. Compare quality, input/output tokens, median/max latency, repairs, retries, and failures, not invented cloud price.
- 12 cases per task. Counts are directional. Do not treat 11/12 vs 10/12 as a production ranking.
- Recommend **per task**. A lead on extraction does not pick the triage model.
- Name the prompt version on every comparison. A transferred prompt is evidence about that prompt, not the model’s best adapted performance.
- Extraction quality: required-evidence recall, citations, missed vs invented presents, version-selection when grouped. `day5.v1` does not score `document_status`.
- Summarization quality: same evidence metrics plus version-selection on the card-dispute pair.
- Triage quality: queue, escalation_required, missed/unnecessary escalation, human-boundary, PII.



## Evaluated models

- mistral (`mistral:7b`)
- qwen (`qwen3:8b`) (thinking is off)



## Evaluated configurations

- `extraction` — mistral — `extract.v2` (developed with Mistral)
- `extraction` — qwen — `extract.v2` (prompt-transfer)
- `summarization` — mistral — `summarize.v2` (adapted: instance JSON, not schema echo)
- `summarization` — qwen — `summarize.v2` (prompt-transfer of that adaptation)
- `triage` — mistral — `triage.v3` (adapted: queue bound to escalation_required)
- `triage` — qwen — `triage.v1` (prompt-transfer / Day 4 standing prompt)

Not in this run: `--think`, `triage.v2`, Mistral `triage.v1` / `summarize.v1`, Qwen `extract.v3` (failed schema validation on `day5-local-06`).

## Extraction



### Evidence

- `extract.v2` / Mistral: valid 12/12; recall 71/72; citations 74/74; missed 1 (E05 `beneficial_ownership_threshold`); invented 3 (E04/E10 `jurisdictions`, E09 `beneficial_ownership_threshold`); version_selection 0/1 (`selected=none`; `version.value` lists); repairs 1/12 (E11); tokens 29078 / 5321; median 20713 ms; max call 24015 ms; n=13.
- `extract.v2` / Qwen (transfer): valid 12/12; recall 71/72; citations 72/72; missed 1 (E05 `beneficial_ownership_threshold`); invented 1 (E10 `jurisdictions`); version_selection 1/1 (E02); repairs 1/12 (E04); tokens 23947 / 3745; median 16179 ms; max call 19795 ms; n=13.



### Decision

Select **Qwen +** `extract.v2`. Same recall as Mistral on this prompt; fewer invented presents; version rule could run; lower tokens and latency.

### Rejected alternatives

- Mistral + `extract.v2`: same recall, but version 0/1 and more extra `present` fields. Not rejected as “worse at extraction” in general.
- Qwen + `extract.v3`: not a candidate here; that adapted prompt failed schema validation on an earlier run.



### Review triggers

- Score `document_status` (superseded / contradictory), or require a single string `version` / `effective_date` for this document only.
- Re-measure Mistral after a new prompt version that does not array-wrap version ids.
- A validating adapted Qwen prompt (`extract.v4` / fixed v3) beats transfer `extract.v2` on recall without extra presents.



## Summarization



### Evidence

- `summarize.v2` / Mistral: valid 12/12; recall 60/60; citations 63/66; missed 0; invented presents on S04/S05/S09/S12; version_selection 1/1 (S02); repairs 0/12; tokens 16827 / 3828; median 14946 ms; max 17546 ms; n=12.
- `summarize.v2` / Qwen (transfer): valid 12/12; recall 59/60 (missed S12 `title`); citations 62/63; invented presents on S04/S05/S09; version_selection 1/1 (S02); repairs 0/12; tokens 13899 / 2267; median 9830 ms; max 13241 ms; n=12.



### Decision

Select **Mistral +** `summarize.v2`. Higher recall on the same prompt version. Qwen’s cheaper tokens/latency and 2 less invented do not outweigh the S12 miss under the pre-set quality-first constraint for this task.

### Rejected alternatives

- Qwen + `summarize.v2` transfer: better operational cost, 59/60 recall. Rejected for the measured quality gap, not as “Qwen cannot summarize.”
- `summarize.v1`: untested in this run (known schema-echo / truncation on earlier Mistral runs).



### Review triggers

- Token or latency budget outranks one recall slot.
- Qwen + `summarize.v2` (or a later version) recovers S12 `title` at equal recall.



## Triage



### Evidence

- `triage.v3` / Mistral (adapted): valid 12/12; queue 11/12; escalation 12/12; missed/unnecessary escalation 0/12; human-boundary 12/12; PII 0/12; miss T09 queue `lending` vs gold `unsupported` (esc false matches); repairs 0/12; tokens 8470 / 1777; median 5847 ms; max 7381 ms; n=12.
- `triage.v1` / Qwen (transfer): valid 12/12; queue 11/12; escalation 12/12; missed/unnecessary escalation 0/12; human-boundary 12/12; PII 0/12; miss T07 queue `lending` vs gold `escalate` (esc true matches); repairs 0/12; tokens 5647 / 1470; median 5482.5 ms; max 9525 ms; n=12.



### Decision

Select **Qwen +** `triage.v1`. Same scored quality totals as Mistral `triage.v3` with fewer input tokens (standing v1 vs longer adapted v3). Escalation misses are none; the remaining miss is wrong queue routing only.

### Rejected alternatives

- Mistral + `triage.v3`: same 11/12 queue and 12/12 escalation, different miss (T09). Rejected as the default because this pair is adapted vs transfer, not a same-prompt bake-off, and v3 costs more prompt tokens. Not a claim that Mistral is worse at triage.
- Mistral + `triage.v1`: not re-run here. Earlier `-07` on that pair was queue 10/12 and escalation 9/12; v3 was the adaptation for that, not the selected production prompt for Qwen.



### Review triggers

- Mixed-intent cases must use `queue=escalate` (Qwen T07 is lending + esc true).
- Out-of-scope investment advice must be `unsupported` (Mistral T09).
- A same-prompt rerun (both models on `triage.v1` or both on `triage.v3`) contradicts this split.



## Universal ranking (rejected)

No single model is selected for all tasks. Qwen on `extract.v2` / `triage.v1` does not imply Qwen on `summarize.v2`. Mistral on `summarize.v2` does not imply Mistral on extraction or triage.