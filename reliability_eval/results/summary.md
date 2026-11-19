# Tool-calling reliability results (test split)

Tasks: **72** (single_simple 22, single_args 14, multi_step 20, no_tool 16). Temperature 0. Cells show `% (k/n) [95% Wilson CI]`.

## 1. Main table

| Model | Mode | Tool selection acc. | Arg. correctness (given right tools) | Exact call match | Malformed call rate (per attempt) | Tasks with ≥1 malformed | End-to-end success | Mean s/task | Mean LLM calls |
|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 55.6% (40/72) [44–66] | 97.4% (37/38) [87–100] | 54.2% (39/72) [43–65] | 21.8% (17/78) [14–32] | 23.6% (17/72) [15–35] | — (no final answer in single-shot) | 0.3 | 1.0 |
| llama3.2:3b | react | 54.2% (39/72) [43–65] | 100.0% (38/38) [91–100] | 54.2% (39/72) [43–65] | 24.1% (20/83) [16–34] | 25.0% (18/72) [16–36] | 54.2% (39/72) [43–65] | 1.12 | 1.99 |
| llama3.2:3b | react_no_error_feedback | 54.2% (39/72) [43–65] | 100.0% (38/38) [91–100] | 54.2% (39/72) [43–65] | 21.0% (17/81) [14–31] | 23.6% (17/72) [15–35] | 54.2% (39/72) [43–65] | 0.95 | 1.82 |
| qwen2.5:7b | single_shot | 80.6% (58/72) [70–88] | 97.7% (42/43) [88–100] | 79.2% (57/72) [68–87] | 4.4% (3/68) [2–12] | 4.2% (3/72) [1–12] | — (no final answer in single-shot) | 0.8 | 1.0 |
| qwen2.5:7b | react | 94.4% (68/72) [87–98] | 96.2% (50/52) [87–99] | 91.7% (66/72) [83–96] | 0.0% (0/75) [0–5] | 0.0% (0/72) [0–5] | 91.7% (66/72) [83–96] | 1.39 | 1.85 |
| qwen2.5:7b | react_no_error_feedback | 94.4% (68/72) [87–98] | 96.2% (50/52) [87–99] | 91.7% (66/72) [83–96] | 0.0% (0/75) [0–5] | 0.0% (0/72) [0–5] | 91.7% (66/72) [83–96] | 1.49 | 1.85 |
| qwen2.5:3b | single_shot | 83.3% (60/72) [73–90] | 97.7% (43/44) [88–100] | 81.9% (59/72) [72–89] | 9.7% (7/72) [5–19] | 8.3% (6/72) [4–17] | — (no final answer in single-shot) | 0.48 | 1.0 |
| qwen2.5:3b | react | 87.5% (63/72) [78–93] | 97.9% (46/47) [89–100] | 86.1% (62/72) [76–92] | 20.2% (21/104) [14–29] | 9.7% (7/72) [5–19] | 83.3% (60/72) [73–90] | 1.15 | 2.01 |
| qwen2.5:3b | react_no_error_feedback | 84.7% (61/72) [75–91] | 97.8% (44/45) [88–100] | 83.3% (60/72) [73–90] | 10.5% (8/76) [5–19] | 9.7% (7/72) [5–19] | 80.6% (58/72) [70–88] | 0.82 | 1.71 |
| llama3.2:1b | single_shot | 2.8% (2/72) [1–10] | 100.0% (2/2) [34–100] | 2.8% (2/72) [1–10] | 90.8% (69/76) [82–95] | 90.3% (65/72) [81–95] | — (no final answer in single-shot) | 2.5 | 1.0 |
| llama3.2:1b | react | 9.7% (7/72) [5–19] | 83.3% (5/6) [44–97] | 8.3% (6/72) [4–17] | 90.7% (137/151) [85–94] | 86.1% (62/72) [76–92] | 8.3% (6/72) [4–17] | 2.65 | 2.46 |
| llama3.2:1b | react_no_error_feedback | 5.6% (4/72) [2–13] | 100.0% (3/3) [44–100] | 5.6% (4/72) [2–13] | 89.4% (76/85) [81–94] | 87.5% (63/72) [78–93] | 5.6% (4/72) [2–13] | 2.16 | 1.11 |

Definitions: selection = the set/sequence of successfully executed tool names equals the ground truth (for no_tool tasks: no call at all). Argument correctness is measured only on tasks where selection was right. Exact = both. Malformed = unknown tool, unknown/missing argument, uncoercible type/enum, or unparseable / text-only call. Success (loop modes) = exact match AND the run finished AND the final answer contains the expected value.

## 2. Exact call match by category

| Model | Mode | single_simple | single_args | multi_step | no_tool |
|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 95.5% (21/22) [78–99] | 92.9% (13/14) [69–99] | 15.0% (3/20) [5–36] | 12.5% (2/16) [3–36] |
| llama3.2:3b | react | 100.0% (22/22) [85–100] | 92.9% (13/14) [69–99] | 15.0% (3/20) [5–36] | 6.2% (1/16) [1–28] |
| llama3.2:3b | react_no_error_feedback | 100.0% (22/22) [85–100] | 92.9% (13/14) [69–99] | 15.0% (3/20) [5–36] | 6.2% (1/16) [1–28] |
| qwen2.5:7b | single_shot | 95.5% (21/22) [78–99] | 100.0% (14/14) [78–100] | 35.0% (7/20) [18–57] | 93.8% (15/16) [72–99] |
| qwen2.5:7b | react | 95.5% (21/22) [78–99] | 100.0% (14/14) [78–100] | 75.0% (15/20) [53–89] | 100.0% (16/16) [81–100] |
| qwen2.5:7b | react_no_error_feedback | 95.5% (21/22) [78–99] | 100.0% (14/14) [78–100] | 75.0% (15/20) [53–89] | 100.0% (16/16) [81–100] |
| qwen2.5:3b | single_shot | 100.0% (22/22) [85–100] | 92.9% (13/14) [69–99] | 40.0% (8/20) [22–61] | 100.0% (16/16) [81–100] |
| qwen2.5:3b | react | 100.0% (22/22) [85–100] | 100.0% (14/14) [78–100] | 50.0% (10/20) [30–70] | 100.0% (16/16) [81–100] |
| qwen2.5:3b | react_no_error_feedback | 100.0% (22/22) [85–100] | 100.0% (14/14) [78–100] | 40.0% (8/20) [22–61] | 100.0% (16/16) [81–100] |
| llama3.2:1b | single_shot | 9.1% (2/22) [3–28] | 0.0% (0/14) [0–22] | 0.0% (0/20) [0–16] | 0.0% (0/16) [0–19] |
| llama3.2:1b | react | 18.2% (4/22) [7–39] | 7.1% (1/14) [1–31] | 0.0% (0/20) [0–16] | 6.2% (1/16) [1–28] |
| llama3.2:1b | react_no_error_feedback | 13.6% (3/22) [5–33] | 0.0% (0/14) [0–22] | 0.0% (0/20) [0–16] | 6.2% (1/16) [1–28] |

## 3. Paired comparisons (same tasks)

`only A` / `only B` = tasks exactly one system got right; only these drive the exact McNemar p-value. A gap of g points on n tasks = g·n/100 tasks.

| Comparison | Metric | Subset | n | A right | B right | only A | only B | gap (pts) | p |
|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b: react (A) vs single_shot (B) | exact_match | all | 72 | 39 | 39 | 1 | 1 | +0.0 | 1.0 |
| llama3.2:3b: react (A) vs single_shot (B) | exact_match | excluding multi_step | 52 | 36 | 36 | 1 | 1 | +0.0 | 1.0 |
| llama3.2:3b: react (A) vs react_no_error_feedback (B) | success | all | 72 | 39 | 39 | 0 | 0 | +0.0 | 1.0 |
| llama3.2:3b: react (A) vs react_no_error_feedback (B) | success | excluding multi_step | 52 | 36 | 36 | 0 | 0 | +0.0 | 1.0 |
| qwen2.5:7b: react (A) vs single_shot (B) | exact_match | all | 72 | 66 | 57 | 9 | 0 | +12.5 | 0.0039 |
| qwen2.5:7b: react (A) vs single_shot (B) | exact_match | excluding multi_step | 52 | 51 | 50 | 1 | 0 | +1.9 | 1.0 |
| qwen2.5:7b: react (A) vs react_no_error_feedback (B) | success | all | 72 | 66 | 66 | 0 | 0 | +0.0 | 1.0 |
| qwen2.5:7b: react (A) vs react_no_error_feedback (B) | success | excluding multi_step | 52 | 51 | 51 | 0 | 0 | +0.0 | 1.0 |
| qwen2.5:3b: react (A) vs single_shot (B) | exact_match | all | 72 | 62 | 59 | 6 | 3 | +4.2 | 0.5078 |
| qwen2.5:3b: react (A) vs single_shot (B) | exact_match | excluding multi_step | 52 | 52 | 51 | 1 | 0 | +1.9 | 1.0 |
| qwen2.5:3b: react (A) vs react_no_error_feedback (B) | success | all | 72 | 60 | 58 | 2 | 0 | +2.8 | 0.5 |
| qwen2.5:3b: react (A) vs react_no_error_feedback (B) | success | excluding multi_step | 52 | 51 | 51 | 0 | 0 | +0.0 | 1.0 |
| llama3.2:1b: react (A) vs single_shot (B) | exact_match | all | 72 | 6 | 2 | 4 | 0 | +5.6 | 0.125 |
| llama3.2:1b: react (A) vs single_shot (B) | exact_match | excluding multi_step | 52 | 6 | 2 | 4 | 0 | +7.7 | 0.125 |
| llama3.2:1b: react (A) vs react_no_error_feedback (B) | success | all | 72 | 6 | 4 | 2 | 0 | +2.8 | 0.5 |
| llama3.2:1b: react (A) vs react_no_error_feedback (B) | success | excluding multi_step | 52 | 6 | 4 | 2 | 0 | +3.8 | 0.5 |
| single_shot: qwen2.5:7b (A) vs qwen2.5:3b (B) | exact_match | all | 72 | 57 | 59 | 5 | 7 | -2.8 | 0.7744 |
| single_shot: qwen2.5:7b (A) vs qwen2.5:3b (B) | exact_match | excluding multi_step | 52 | 50 | 51 | 1 | 2 | -1.9 | 1.0 |
| react: qwen2.5:7b (A) vs qwen2.5:3b (B) | success | all | 72 | 66 | 60 | 8 | 2 | +8.3 | 0.1094 |
| react: qwen2.5:7b (A) vs qwen2.5:3b (B) | success | excluding multi_step | 52 | 51 | 51 | 1 | 1 | +0.0 | 1.0 |
| react_no_error_feedback: qwen2.5:7b (A) vs qwen2.5:3b (B) | success | all | 72 | 66 | 58 | 10 | 2 | +11.1 | 0.0386 |
| react_no_error_feedback: qwen2.5:7b (A) vs qwen2.5:3b (B) | success | excluding multi_step | 52 | 51 | 51 | 1 | 1 | +0.0 | 1.0 |
| single_shot: llama3.2:3b (A) vs llama3.2:1b (B) | exact_match | all | 72 | 39 | 2 | 37 | 0 | +51.4 | 0.0 |
| single_shot: llama3.2:3b (A) vs llama3.2:1b (B) | exact_match | excluding multi_step | 52 | 36 | 2 | 34 | 0 | +65.4 | 0.0 |
| react: llama3.2:3b (A) vs llama3.2:1b (B) | success | all | 72 | 39 | 6 | 33 | 0 | +45.8 | 0.0 |
| react: llama3.2:3b (A) vs llama3.2:1b (B) | success | excluding multi_step | 52 | 36 | 6 | 30 | 0 | +57.7 | 0.0 |
| react_no_error_feedback: llama3.2:3b (A) vs llama3.2:1b (B) | success | all | 72 | 39 | 4 | 35 | 0 | +48.6 | 0.0 |
| react_no_error_feedback: llama3.2:3b (A) vs llama3.2:1b (B) | success | excluding multi_step | 52 | 36 | 4 | 32 | 0 | +61.5 | 0.0 |
| single_shot: qwen2.5:3b (A) vs llama3.2:3b (B) | exact_match | all | 72 | 59 | 39 | 21 | 1 | +27.8 | 0.0 |
| single_shot: qwen2.5:3b (A) vs llama3.2:3b (B) | exact_match | excluding multi_step | 52 | 51 | 36 | 16 | 1 | +28.8 | 0.0003 |
| react: qwen2.5:3b (A) vs llama3.2:3b (B) | success | all | 72 | 60 | 39 | 21 | 0 | +29.2 | 0.0 |
| react: qwen2.5:3b (A) vs llama3.2:3b (B) | success | excluding multi_step | 52 | 51 | 36 | 15 | 0 | +28.8 | 0.0001 |
| react_no_error_feedback: qwen2.5:3b (A) vs llama3.2:3b (B) | success | all | 72 | 58 | 39 | 19 | 0 | +26.4 | 0.0 |
| react_no_error_feedback: qwen2.5:3b (A) vs llama3.2:3b (B) | success | excluding multi_step | 52 | 51 | 36 | 15 | 0 | +28.8 | 0.0001 |
| single_shot: qwen2.5:7b (A) vs llama3.2:3b (B) | exact_match | all | 72 | 57 | 39 | 19 | 1 | +25.0 | 0.0 |
| single_shot: qwen2.5:7b (A) vs llama3.2:3b (B) | exact_match | excluding multi_step | 52 | 50 | 36 | 15 | 1 | +26.9 | 0.0005 |
| react: qwen2.5:7b (A) vs llama3.2:3b (B) | success | all | 72 | 66 | 39 | 28 | 1 | +37.5 | 0.0 |
| react: qwen2.5:7b (A) vs llama3.2:3b (B) | success | excluding multi_step | 52 | 51 | 36 | 16 | 1 | +28.8 | 0.0003 |
| react_no_error_feedback: qwen2.5:7b (A) vs llama3.2:3b (B) | success | all | 72 | 66 | 39 | 28 | 1 | +37.5 | 0.0 |
| react_no_error_feedback: qwen2.5:7b (A) vs llama3.2:3b (B) | success | excluding multi_step | 52 | 51 | 36 | 16 | 1 | +28.8 | 0.0003 |

## 4. Failure taxonomy (primary label per failed run)

| Model | Mode | failed runs | answer_wrong | argument_omission | cyclic_stagnation | incomplete_chain | invalid_type_or_enum | parse_failure | schema_hallucination | tool_skipped | unneeded_call | wrong_tool | wrong_value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 33 | 0 | 0 | 0 | 4 | 9 | 0 | 8 | 0 | 5 | 6 | 1 |
| llama3.2:3b | react | 33 | 0 | 1 | 0 | 5 | 6 | 6 | 5 | 0 | 5 | 5 | 0 |
| llama3.2:3b | react_no_error_feedback | 33 | 0 | 1 | 0 | 5 | 5 | 6 | 5 | 0 | 6 | 5 | 0 |
| qwen2.5:7b | single_shot | 15 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 1 | 7 | 1 |
| qwen2.5:7b | react | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| qwen2.5:7b | react_no_error_feedback | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| qwen2.5:3b | single_shot | 13 | 0 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 0 | 2 | 1 |
| qwen2.5:3b | react | 12 | 1 | 0 | 3 | 0 | 1 | 0 | 1 | 1 | 0 | 4 | 1 |
| qwen2.5:3b | react_no_error_feedback | 14 | 1 | 0 | 0 | 0 | 5 | 0 | 2 | 1 | 0 | 4 | 1 |
| llama3.2:1b | single_shot | 70 | 0 | 0 | 0 | 1 | 0 | 3 | 62 | 0 | 0 | 4 | 0 |
| llama3.2:1b | react | 66 | 0 | 0 | 3 | 1 | 0 | 5 | 52 | 0 | 1 | 4 | 0 |
| llama3.2:1b | react_no_error_feedback | 68 | 0 | 0 | 0 | 1 | 0 | 5 | 58 | 0 | 0 | 4 | 0 |

All runs pooled: schema_hallucination 193, wrong_tool 49, invalid_type_or_enum 35, incomplete_chain 28, parse_failure 25, unneeded_call 18, wrong_value 9, cyclic_stagnation 6, argument_omission 2, tool_skipped 2, answer_wrong 2

Multi-label counts grouped into the README's four classes (+ extra classes found):

- (extra) answer_wrong: 3
- (extra) incomplete_chain: 59
- (extra) invalid_value: 4
- (extra) stopped_on_error: 77
- (extra) tool_skipped: 2
- (extra) unneeded_call: 91
- (extra) wrong_tool: 52
- (extra) wrong_value: 10
- 1. Schema hallucination: 199
- 2. Type drift & parsing: 215
- 3. Argument omission: 3
- 4. Cyclic stagnation: 6

## 5. Recovery and 'answer looked right' (loop modes)

- llama3.2:3b | single_shot: recovered after an error = None; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 33; tool errors = 1; stop reasons = {'final_answer': 72}
- llama3.2:3b | react: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 3; type-drift attempts (coerced) = 36; tool errors = 1; stop reasons = {'final_answer': 72}
- llama3.2:3b | react_no_error_feedback: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 3; type-drift attempts (coerced) = 36; tool errors = 1; stop reasons = {'final_answer': 60, 'tool_error_no_feedback': 12}
- qwen2.5:7b | single_shot: recovered after an error = None; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 3; tool errors = 2; stop reasons = {'final_answer': 72}
- qwen2.5:7b | react: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 3; type-drift attempts (coerced) = 0; tool errors = 0; stop reasons = {'final_answer': 72}
- qwen2.5:7b | react_no_error_feedback: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 3; type-drift attempts (coerced) = 0; tool errors = 0; stop reasons = {'final_answer': 72}
- qwen2.5:3b | single_shot: recovered after an error = None; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 7; tool errors = 0; stop reasons = {'final_answer': 72}
- qwen2.5:3b | react: recovered after an error = 2; final answer contained the expected value but the tool call was wrong = 3; type-drift attempts (coerced) = 14; tool errors = 0; stop reasons = {'final_answer': 72}
- qwen2.5:3b | react_no_error_feedback: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 2; type-drift attempts (coerced) = 6; tool errors = 0; stop reasons = {'final_answer': 65, 'tool_error_no_feedback': 7}
- llama3.2:1b | single_shot: recovered after an error = None; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 0; tool errors = 0; stop reasons = {'final_answer': 72}
- llama3.2:1b | react: recovered after an error = 2; final answer contained the expected value but the tool call was wrong = 10; type-drift attempts (coerced) = 3; tool errors = 0; stop reasons = {'final_answer': 70, 'recursion_limit': 2}
- llama3.2:1b | react_no_error_feedback: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 0; tool errors = 0; stop reasons = {'tool_error_no_feedback': 58, 'final_answer': 14}

## 6. Run time

- llama3.2:3b | single_shot: 21.4 s model time over 72 tasks (mean 0.3 s/task)
- llama3.2:3b | react: 80.5 s model time over 72 tasks (mean 1.12 s/task)
- llama3.2:3b | react_no_error_feedback: 68.3 s model time over 72 tasks (mean 0.95 s/task)
- qwen2.5:7b | single_shot: 57.5 s model time over 72 tasks (mean 0.8 s/task)
- qwen2.5:7b | react: 100.3 s model time over 72 tasks (mean 1.39 s/task)
- qwen2.5:7b | react_no_error_feedback: 107.1 s model time over 72 tasks (mean 1.49 s/task)
- qwen2.5:3b | single_shot: 34.7 s model time over 72 tasks (mean 0.48 s/task)
- qwen2.5:3b | react: 82.5 s model time over 72 tasks (mean 1.15 s/task)
- qwen2.5:3b | react_no_error_feedback: 59.0 s model time over 72 tasks (mean 0.82 s/task)
- llama3.2:1b | single_shot: 179.8 s model time over 72 tasks (mean 2.5 s/task)
- llama3.2:1b | react: 191.0 s model time over 72 tasks (mean 2.65 s/task)
- llama3.2:1b | react_no_error_feedback: 155.6 s model time over 72 tasks (mean 2.16 s/task)

Environment: GPU Tesla T4, 15360 MiB, 580.178.04
Tesla T4, 15360 MiB, 580.178.04; Ollama 0.40.16; packages {'langgraph': '1.2.23', 'langchain-core': '1.8.3', 'langchain-ollama': '1.1.0', 'ollama': '0.6.3', 'pydantic': '2.14.1'}; models {"llama3.2:3b": {"digest": "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72", "size_bytes": 2019393189, "parameter_size": "3.2B", "quantization": "Q4_K_M", "family": "llama", "format": "gguf"}, "qwen2.5:7b": {"digest": "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e", "size_bytes": 4683087332, "parameter_size": "7.6B", "quantization": "Q4_K_M", "family": "qwen2", "format": "gguf"}, "qwen2.5:3b": {"digest": "357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b", "size_bytes": 1929912432, "parameter_size": "3.1B", "quantization": "Q4_K_M", "family": "qwen2", "format": "gguf"}, "llama3.2:1b": {"digest": "baf6a787fdffd633537aa2eb51cfd54cb93ff08e28040095462bb63daf552878", "size_bytes": 1321098329, "parameter_size": "1.2B", "quantization": "Q8_0", "family": "llama", "format": "gguf"}}
