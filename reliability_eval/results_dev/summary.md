# Tool-calling reliability results (dev split)

Tasks: **12** (single_simple 3, single_args 3, multi_step 3, no_tool 3). Temperature 0. Cells show `% (k/n) [95% Wilson CI]`.

## 1. Main table

| Model | Mode | Tool selection acc. | Arg. correctness (given right tools) | Exact call match | Malformed call rate (per attempt) | Tasks with ≥1 malformed | End-to-end success | Mean s/task | Mean LLM calls |
|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 58.3% (7/12) [32–81] | 100.0% (7/7) [65–100] | 58.3% (7/12) [32–81] | 28.6% (4/14) [12–55] | 33.3% (4/12) [14–61] | — (no final answer in single-shot) | 0.31 | 1.0 |
| llama3.2:3b | react | 58.3% (7/12) [32–81] | 100.0% (7/7) [65–100] | 58.3% (7/12) [32–81] | 23.1% (3/13) [8–50] | 25.0% (3/12) [9–53] | 58.3% (7/12) [32–81] | 0.99 | 2.0 |

Definitions: selection = the set/sequence of successfully executed tool names equals the ground truth (for no_tool tasks: no call at all). Argument correctness is measured only on tasks where selection was right. Exact = both. Malformed = unknown tool, unknown/missing argument, uncoercible type/enum, or unparseable / text-only call. Success (loop modes) = exact match AND the run finished AND the final answer contains the expected value.

## 2. Exact call match by category

| Model | Mode | single_simple | single_args | multi_step | no_tool |
|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 100.0% (3/3) [44–100] | 100.0% (3/3) [44–100] | 33.3% (1/3) [6–79] | 0.0% (0/3) [0–56] |
| llama3.2:3b | react | 100.0% (3/3) [44–100] | 100.0% (3/3) [44–100] | 33.3% (1/3) [6–79] | 0.0% (0/3) [0–56] |

## 3. Paired comparisons (same tasks)

`only A` / `only B` = tasks exactly one system got right; only these drive the exact McNemar p-value. A gap of g points on n tasks = g·n/100 tasks.

| Comparison | Metric | Subset | n | A right | B right | only A | only B | gap (pts) | p |
|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b: react (A) vs single_shot (B) | exact_match | all | 12 | 7 | 7 | 0 | 0 | +0.0 | 1.0 |
| llama3.2:3b: react (A) vs single_shot (B) | exact_match | excluding multi_step | 9 | 6 | 6 | 0 | 0 | +0.0 | 1.0 |

## 4. Failure taxonomy (primary label per failed run)

| Model | Mode | failed runs | argument_omission | invalid_type_or_enum | schema_hallucination | unneeded_call | wrong_tool |
|---|---|---|---|---|---|---|---|
| llama3.2:3b | single_shot | 5 | 1 | 1 | 2 | 1 | 0 |
| llama3.2:3b | react | 5 | 1 | 2 | 0 | 1 | 1 |

All runs pooled: invalid_type_or_enum 3, schema_hallucination 2, unneeded_call 2, argument_omission 2, wrong_tool 1

Multi-label counts grouped into the README's four classes (+ extra classes found):

- (extra) unneeded_call: 6
- (extra) wrong_tool: 1
- 1. Schema hallucination: 2
- 2. Type drift & parsing: 12
- 3. Argument omission: 2

## 5. Recovery and 'answer looked right' (loop modes)

- llama3.2:3b | single_shot: recovered after an error = None; final answer contained the expected value but the tool call was wrong = 0; type-drift attempts (coerced) = 4; tool errors = 0; stop reasons = {'final_answer': 12}
- llama3.2:3b | react: recovered after an error = 0; final answer contained the expected value but the tool call was wrong = 1; type-drift attempts (coerced) = 5; tool errors = 0; stop reasons = {'final_answer': 12}

## 6. Run time

- llama3.2:3b | single_shot: 3.7 s model time over 12 tasks (mean 0.31 s/task)
- llama3.2:3b | react: 11.9 s model time over 12 tasks (mean 0.99 s/task)

Environment: GPU Tesla T4, 15360 MiB, 580.178.04
Tesla T4, 15360 MiB, 580.178.04; Ollama 0.40.16; packages {'langgraph': '1.2.23', 'langchain-core': '1.8.3', 'langchain-ollama': '1.1.0', 'ollama': '0.6.3', 'pydantic': '2.14.1'}; models {"llama3.2:3b": {"digest": "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72", "size_bytes": 2019393189, "parameter_size": "3.2B", "quantization": "Q4_K_M", "family": "llama", "format": "gguf"}}
