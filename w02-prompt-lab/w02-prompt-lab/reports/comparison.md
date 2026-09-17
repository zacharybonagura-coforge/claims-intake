# Model Comparison

Run ID: `day5-local-08`

Counts are reported with their denominators. Latency uses median and maximum rather than mean.

## Extraction


| Model   | Prompt | Valid outputs | Metrics                                                                                                         | Input tokens | Output tokens | Median latency | Max latency | n   | Repairs | Retries | Final failures |
| ------- | ------ | ------------- | --------------------------------------------------------------------------------------------------------------- | ------------ | ------------- | -------------- | ----------- | --- | ------- | ------- | -------------- |
| mistral | v2     | 12/12         | citation_correctness: 74/74 pii_leakage: 0/12 ↓ required_evidence_recall: 71/72 version_selection_accuracy: 0/1 | 29078        | 5321          | 20713 ms       | 24015 ms    | 13  | 1/12    | 0       | 0              |
| qwen    | v2     | 12/12         | citation_correctness: 72/72 pii_leakage: 0/12 ↓ required_evidence_recall: 71/72 version_selection_accuracy: 1/1 | 23947        | 3745          | 16179 ms       | 19795 ms    | 13  | 1/12    | 0       | 0              |


Missed (gold `recoverable_fields` not marked present):

- Mistral 1/72: E05 `beneficial_ownership_threshold`
- Qwen 1/72: E05 `beneficial_ownership_threshold` 

Invented (present, not in gold `recoverable_fields`):

- Mistral 3: E04 `jurisdictions`, E09 `beneficial_ownership_threshold`, E10 `jurisdictions`
- Qwen 1: E10 `jurisdictions`

E04/E10 extras are contradiction cases gold omitted `jurisdictions` for. `day5.v1` does not score `document_status`. Version rule: Qwen selected E02; Mistral selected none. Mistral version_selection_accuracy 0/1 because E01/E02 version.value were arrays, so they were not candidates. Qwen used one string per doc and selected E02.

Repaired cases (both HTTP calls added for that case):

- Mistral **E11**: 20850 + 22563 = **43413 ms**
- Qwen **E04**: 16179 + 16876 = **33055 ms**

## Summarization


| Model   | Prompt | Valid outputs | Metrics                                                                                                         | Input tokens | Output tokens | Median latency | Max latency | n   | Repairs | Retries | Final failures |
| ------- | ------ | ------------- | --------------------------------------------------------------------------------------------------------------- | ------------ | ------------- | -------------- | ----------- | --- | ------- | ------- | -------------- |
| mistral | v2     | 12/12         | citation_correctness: 63/66 pii_leakage: 0/12 ↓ required_evidence_recall: 60/60 version_selection_accuracy: 1/1 | 16827        | 3828          | 14946 ms       | 17546 ms    | 12  | 0/12    | 0       | 0              |
| qwen    | v2     | 12/12         | citation_correctness: 62/63 pii_leakage: 0/12 ↓ required_evidence_recall: 59/60 version_selection_accuracy: 1/1 | 13899        | 2267          | 9830 ms        | 13241 ms    | 12  | 0/12    | 0       | 0              |


Missed (gold `recoverable_fields` not marked present):

- Mistral 0/60
- Qwen 1/60: S12 `title` `status=absent`)

Invented (present, not in gold `recoverable_fields`):

- Mistral 6: S04 `required_steps`, S05 `effective_date` / `purpose`, S09 `required_steps`, S12 `effective_date` / `purpose`
- Qwen 4: S04 `required_steps`, S05 `effective_date` / `purpose`, S09 `required_steps`

S04/S09 extras are contradiction cases gold omitted `required_steps` for (conflicting step text in the body). S05/S12 extras are unsupported docs gold limited to `title`. `day5.v1` does not score `document_status`.

Citation misses (denominator = all `present` fields, including invented):

- Mistral 3/66, all S12: cited `1. Title` / `2. Purpose` against headings `1. Newsletter` / `2. Highlights` / `3. Opinion Column`
- Qwen 1/63: S06 `exceptions` cited `4. Exceptions`; that heading is `4. Reviewer Note` (exceptions is `5. Exceptions`)

Version rule: both selected S02 (1/1). S01/S02 `version.value` / `effective_date.value` were strings `1.0`, `2024-01-01`, `2.0`, `2025-01-01`), so both entered the candidate list. Unlike extraction, Mistral did not array-wrap versions here.

No schema-repair HTTP calls `n=12`, repairs 0/12.

## Triage


| Model   | Prompt | Valid outputs | Metrics                                                                                                                                    | Input tokens | Output tokens | Median latency | Max latency | n   | Repairs | Retries | Final failures |
| ------- | ------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | ------------- | -------------- | ----------- | --- | ------- | ------- | -------------- |
| mistral | v3     | 12/12         | escalation_required: 12/12 human_boundary: 12/12 missed_escalation: 0/12 ↓ pii_leakage: 0/12 ↓ queue: 11/12 unnecessary_escalation: 0/12 ↓ | 8470         | 1777          | 5847 ms        | 7381 ms     | 12  | 0/12    | 0       | 0              |
| qwen    | v1     | 12/12         | escalation_required: 12/12 human_boundary: 12/12 missed_escalation: 0/12 ↓ pii_leakage: 0/12 ↓ queue: 11/12 unnecessary_escalation: 0/12 ↓ | 5647         | 1470          | 5482.5 ms      | 9525 ms     | 12  | 0/12    | 0       | 0              |


Missed (queue ≠ gold):

- Mistral 1/12: T09 `lending` vs gold `unsupported`
- Qwen 1/12: T07 `lending` vs gold `escalate`

Escalation flags (independent of the queue bucket):

- T09 gold is `unsupported` with escalation **false**. Mistral kept escalation false and only missed the bucket (investment-advice ticket forced into `lending`). Qwen got `unsupported`.
- T07 gold is mixed loan-status + formal complaint, so queue **and** escalation are `escalate` / true. Qwen kept escalation true and only missed the bucket `lending`). Mistral got `queue=escalate`.

Human-boundary / PII (Day 4 re-check on both models):

- `human_boundary` 12/12 each; `customer_outcome` null; `human_review_required` true
- `pii_leakage` 0/12. T11/T12 have identifiers in the **source**; both drafts stayed generic (no SSN / account / phone copy-through)

`day5.v1` scores queue and escalation separately. A wrong bucket with the matching escalate flag is one queue miss, not an escalation miss.

No schema-repair HTTP calls `n=12`, repairs 0/12.

## Limits

- There are only 12 cases per task (36 documents; 72 evaluations). Counts are directional, not production-scale estimates.
- No production-volume reliability claim is being made. One-case gaps are not a precision ranking.
- Prompt-transfer rows: extraction `extract.v2` on both models; summarization `summarize.v2` on both (v2 adapted for Mistral, then transferred to Qwen); triage Qwen `triage.v1`.
- Adapted row: triage Mistral `triage.v3`. Do not treat Mistral v3 vs Qwen v1, or 11/12 vs 11/12 queue, as a universal model ranking.
- Untested in this run: `--think`, `triage.v2`, Mistral on `triage.v1` / `summarize.v1`. `extract.v3` failed schema validation on `day5-local-06`.
- Token and latency columns are summed/aggregated over `CallRecord`s in `runs/day5-local-08.jsonl`. Extraction `n=13` is 12 cases plus one schema-repair call per model; retries are 0. Max latency is the slowest single HTTP call, not the summed repair-case wall clock.
- Local Ollama latency depends on this lab’s hardware. `cost_usd` is `$0.00`; tokens and latency are real work on this machine.



## Recommendation

Each line is one **task + model + prompt version** measured on this run. Do not promote one model for all three tasks. One-case gaps (11/12 vs 11/12, version 0/1 vs 1/1) are not a production ranking.

### Extraction

- **Task:** extraction
- **Model:** Qwen
- **Prompt version:** `extract.v2` (transfer of the Mistral-developed prompt)
- **Reason:** Same required-evidence recall as Mistral (71/72). Citations 72/72 vs 74/74 because Qwen marked fewer extra `present` fields (1 invented vs 3). Version rule selected E02 (1/1); Mistral selected none (0/1) after storing `version.value` as lists. Lower input/output tokens and lower median/max call latency. Both 12/12 valid, one repair.
- **Reopen if:** `document_status` is scored (neither is measured on superseded/contradictory here); Mistral is prompted to emit a single string version/date for *this* document; or a new `extract.v4` / repaired `extract.v3` is measured and actually validates.



### Summarization

- **Task:** summarization
- **Model:** Mistral
- **Prompt version:** `summarize.v2` (adapted to stop schema-echo; Qwen ran the same file as a transfer)
- **Reason:** Recall 60/60 vs Qwen 59/60 (Qwen missed S12 `title`). Citations 63/66 vs 62/63. Both 12/12 valid, 0 repairs, version rule 1/1 (S02). Quality is slightly on Mistral’s side on this 12-case set.
- **Reopen if:** token or latency budget matters more than that one recall slot (Qwen used fewer tokens and lower latency on the same `summarize.v2`); or Qwen is re-run after a prompt that recovers S12 `title`.



### Triage

- **Task:** triage
- **Model:** Qwen
- **Prompt version:** `triage.v1` (transfer)
- **Reason:** Queue 11/12, escalation 12/12, missed/unnecessary escalation 0/12, human-boundary 12/12, PII 0/12 — same scored totals as Mistral `triage.v3`. The miss is T07 routing (`lending` vs gold `escalate`) with escalation **true**. Input tokens 5647 vs Mistral 8470 (v3 is a longer adapted prompt). Not a claim that Qwen is “better at triage” than Mistral on the same prompt.
- **Reopen if:** mixed-intent tickets must have `queue=escalate` (not `lending` + esc true); or you standardize on Mistral `triage.v3`, which matches Qwen on escalation/PII/boundary and misses T09 (`lending` vs `unsupported`) instead. Mistral `v3` vs Qwen `v1` is an adapted vs transferred pair, not a controlled model bake-off.

Rejected universal ranking: do not pick one model for intake because it led on extraction version-selection or on summarization recall.