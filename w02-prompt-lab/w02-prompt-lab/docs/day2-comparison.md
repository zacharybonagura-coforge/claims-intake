# Day 2 comparison

Provider is `ollama` for both models. Configured local charge is `$0.00`, so this report compares success counts, tokens, and latency only.

Run `d8a370f6-f592-4972-b0f4-c702323e9125`: 12 summarization cases (`S01`-`S12`) against Mistral and Qwen, same prompt, temperature `0.0`, and `max_output_tokens=512`.

## Tokens and latency


| Model        | Case      | Succeeded | Error        | Input tokens | Output tokens | Latency (ms)                    |
| ------------ | --------- | --------- | ------------ | ------------ | ------------- | ------------------------------- |
| `mistral:7b` | S01       | yes       |              | 266          | 169           | 9067                            |
| `mistral:7b` | S02       | yes       |              | 250          | 157           | 6510                            |
| `mistral:7b` | S03       | yes       |              | 227          | 143           | 5785                            |
| `mistral:7b` | S04       | yes       |              | 224          | 125           | 5058                            |
| `mistral:7b` | S05       | yes       |              | 192          | 85            | 3471                            |
| `mistral:7b` | S06       | yes       |              | 257          | 186           | 7596                            |
| `mistral:7b` | S07       | yes       |              | 214          | 166           | 6656                            |
| `mistral:7b` | S08       | yes       |              | 226          | 111           | 4526                            |
| `mistral:7b` | S09       | yes       |              | 212          | 107           | 4350                            |
| `mistral:7b` | S10       | yes       |              | 219          | 98            | 4023                            |
| `mistral:7b` | S11       | yes       |              | 199          | 177           | 7078                            |
| `mistral:7b` | S12       | yes       |              | 193          | 94            | 3840                            |
| `mistral:7b` | **total** | **12/12** | 12 successes | **2679**     | **1618**      | median **5421.5**, max **9067** |



| Model      | Case      | Succeeded | Error                  | Input tokens | Output tokens | Latency (ms)                    |
| ---------- | --------- | --------- | ---------------------- | ------------ | ------------- | ------------------------------- |
| `qwen3:8b` | S01       | no        | TruncatedResponseError | 238          | 512           | 26165                           |
| `qwen3:8b` | S02       | yes       |                        | 225          | 478           | 22229                           |
| `qwen3:8b` | S03       | yes       |                        | 208          | 454           | 20788                           |
| `qwen3:8b` | S04       | yes       |                        | 205          | 439           | 20336                           |
| `qwen3:8b` | S05       | yes       |                        | 178          | 376           | 17047                           |
| `qwen3:8b` | S06       | yes       |                        | 231          | 453           | 20767                           |
| `qwen3:8b` | S07       | yes       |                        | 191          | 446           | 27517                           |
| `qwen3:8b` | S08       | yes       |                        | 201          | 384           | 32586                           |
| `qwen3:8b` | S09       | yes       |                        | 193          | 362           | 31070                           |
| `qwen3:8b` | S10       | yes       |                        | 196          | 418           | 34359                           |
| `qwen3:8b` | S11       | yes       |                        | 177          | 405           | 33302                           |
| `qwen3:8b` | S12       | yes       |                        | 172          | 318           | 27449                           |
| `qwen3:8b` | **total** | **11/12** | 1 truncation           | **2415**     | **5045**      | median **26807**, max **34359** |




## Counts


| Model        | Cases | Successes | Failures                            |
| ------------ | ----- | --------- | ----------------------------------- |
| `mistral:7b` | 12    | 12        | 0                                   |
| `qwen3:8b`   | 12    | 11        | 1 (`S01`, `TruncatedResponseError`) |




## Tokens and latency


| Model        | Input tokens | Output tokens | Median latency (ms) | Max latency (ms) |
| ------------ | ------------ | ------------- | ------------------- | ---------------- |
| `mistral:7b` | 2679         | 1618          | 5421.5              | 9067             |
| `qwen3:8b`   | 2415         | 5045          | 26807               | 34359            |




## Observation

Mistral completed every case. Qwen truncated `S01` after 512 output tokens and still emitted about three times as many output tokens overall (5045 vs 1618). Median latency followed that gap, with Qwen 26.8 s vs Mistral 5.4 s. Qwen’s input total was slightly lower (2415 vs 2679). Workload and wait time here are driven by generation length, not by input length. Qwen went past 256 ouput ceiling on every case (318-512 output tokens), while Mistral stayed under it (85-186).

## Why `max_output_tokens=512`

A shared cap of 256 is not valid here because every Qwen case used 318–512 output tokens, so all twelve Qwen calls would have truncated during hidden thinking. You would then be comparing Mistral summaries to empty or cut-off Qwen outputs instead of measuring both models on the same task. 

This is a short summarization task, and the visible answer does not need a large generation budget. 512 is the right cap for this problem. A Mistral-sized cap at around 200 would be enough for the summary text, but would cut Qwen off during hidden thinking (every Qwen case used 318–512 output tokens). 512 lets 11 of 12 Qwen cases finish thinking and still produce an answer, while `S01` hitting 512 with empty `response_text` shows that a larger ceiling is not the fix. Extra max tokens would give more reasoning and latency, but not a longer summary.

We did not disable Qwen thinking. We should compare the configured models as they run, with one output cap, not a thinking flag.