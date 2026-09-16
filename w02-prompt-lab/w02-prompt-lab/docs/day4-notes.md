Run `654f23a8-70a0-4539-80d0-5d8536a699c0`: Mistral (`mistral:7b`), temperature `0.0`, `max_output_tokens=256`. Both prompt versions used the same 12 triage cases. Provider/API cost = $0.00.

triage.v1
queue correct: 10/12
escalation correct: 9/12
missed escalations: 1
unnecessary escalations: 2
human-boundary passes: 12/12

triage.v2
queue correct: 9/12
escalation correct: 10/12
missed escalations: 1
unnecessary escalations: 1
human-boundary passes: 12/12

Changed-queue count: 1/12 (T09: unsupported → lending)

Output-token difference (v2 − v1): +378 total, +31.5 per case
Input-token difference (v2 − v1): +456 total, +38.0 per case

Latency: v1 median 7022 ms, max 10401 ms; v2 median 8877 ms, max 10314 ms
Observation count: 24 completions (12 per prompt version)

v1 failures: T05 unnecessary escalation; T07 missed escalation and wrong queue (`lending` instead of `escalate`); T08 wrong queue (`account_servicing` instead of `escalate`); T09 unnecessary escalation. v2 also had the v1 T05/T07/T08 errors, fixed T09's extra escalate, and introduced a T09 queue miss.

The analysis field did not earn its overhead. Queue was 1/12 worse and escalation was 1/12 better on the same case. That is not enough to justify +31.5 output tokens per case and ~1.9 s extra median latency. A one-case difference in a 12-case set is not proof that either prompt is generally better.

## Input tokens per case


| case      | v1       | v2       | delta    |
| --------- | -------- | -------- | -------- |
| T01       | 519      | 557      | +38      |
| T02       | 515      | 553      | +38      |
| T03       | 509      | 547      | +38      |
| T04       | 512      | 550      | +38      |
| T05       | 515      | 553      | +38      |
| T06       | 526      | 564      | +38      |
| T07       | 515      | 553      | +38      |
| T08       | 521      | 559      | +38      |
| T09       | 517      | 555      | +38      |
| T10       | 524      | 562      | +38      |
| T11       | 538      | 576      | +38      |
| T12       | 539      | 577      | +38      |
| **total** | **6250** | **6706** | **+456** |




## Output tokens per case


| case      | v1       | v2       | delta    |
| --------- | -------- | -------- | -------- |
| T01       | 147      | 188      | +41      |
| T02       | 135      | 164      | +29      |
| T03       | 143      | 192      | +49      |
| T04       | 153      | 172      | +19      |
| T05       | 179      | 210      | +31      |
| T06       | 182      | 192      | +10      |
| T07       | 158      | 199      | +41      |
| T08       | 165      | 185      | +20      |
| T09       | 140      | 157      | +17      |
| T10       | 169      | 226      | +57      |
| T11       | 148      | 196      | +48      |
| T12       | 143      | 159      | +16      |
| **total** | **1862** | **2240** | **+378** |


