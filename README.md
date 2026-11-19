# Local LLM Agents: Tool-Calling Reliability

How reliably do small, locally served open-weight models call tools correctly inside an agent loop?

Most agent demos judge whether the final answer *looks* right. This project instead checks the
**tool call itself** against a ground truth: was the right tool called, with the right arguments,
in a valid format? It compares four local models (1B–7B) and three agent modes on a held-out task
suite, and sorts the failures it finds in the execution traces into a taxonomy.

> **Credit.** The LangGraph agent patterns, tutorials, tests and the `langgraph_ollama_local`
> package come from [AbhinaavRamesh/langgraph-ollama-tutorial](https://github.com/AbhinaavRamesh/langgraph-ollama-tutorial)
> (MIT licence, unchanged here). The reliability evaluation in [`reliability_eval/`](reliability_eval/)
> is the addition this repository makes.

---

## What was evaluated

**Task suite.** 84 tasks, each with a user prompt, the known-correct tool calls (name + arguments) and the
expected final answer: [`reliability_eval/tasks.py`](reliability_eval/tasks.py).

| Split | Tasks | Use |
|---|---|---|
| dev | 12 | smoke-testing the harness only |
| **test (held out)** | **72** | all reported numbers |

Test categories: `single_simple` 22 (one call, arguments stated plainly) · `single_args` 14 (one call, the
argument needs care: an enum value, "2 hours" → 120 minutes, number words, argument order) · `multi_step` 20
(2–3 calls, mostly dependent on earlier results) · `no_tool` 16 (general knowledge, where the correct
behaviour is *no* call).

**Tools.** 9 deterministic, offline mock tools (so the model is the only source of variation): `add`,
`subtract`, `multiply`, `divide`, `get_weather(city, unit∈{celsius,fahrenheit})`,
`convert_currency(amount, from_currency, to_currency)`, `find_employee(name)`, `get_employee(employee_id:int)`,
`create_reminder(text, minutes:int)`.

**Modes.**

| Mode | What happens |
|---|---|
| `single_shot` | One model reply; every needed call must be in it; the model never sees tool results. |
| `react` | LangGraph ReAct loop (agent → tools → agent …). The tool node validates every call against its schema and sends errors back to the model as tool messages so it can retry. |
| `react_no_error_feedback` | Same graph, but the first invalid call ends the run (ablation; mimics a tool node with no error handling). |

**Models** (Ollama, default quantisation): `llama3.2:1b` (Q8_0), `llama3.2:3b`, `qwen2.5:3b`, `qwen2.5:7b` (Q4_K_M).
Temperature 0, seed 42, context 4096 tokens, recursion limit 25.

**Metrics.**
- *Tool selection accuracy*: the successfully executed tool names equal the ground truth (for `no_tool`: no call at all).
- *Argument correctness*: on tasks where selection was right, every argument matches (numbers within 0.1 %, strings case-insensitive; `add`/`multiply` accept swapped operands; an argument the prompt didn't ask for must equal its default).
- *Exact call match*: both of the above.
- *Malformed call rate*: share of call attempts that are an unknown tool, unknown/missing argument, value that can't be coerced to the schema type/enum, or a call written as JSON text instead of a structured call.
- *End-to-end success* (loop modes): exact match, the run finished, and the final answer contains the expected value.

95 % Wilson intervals for every rate; exact McNemar tests for paired comparisons on the same tasks.

## Results (72 held-out tasks, Tesla T4, Ollama 0.40.16)

| Model | Mode | Tool selection | Arguments (given right tools) | Exact call match | Malformed call rate | Success |
|---|---|---|---|---|---|---|
| llama3.2:1b | single_shot | 2.8 % | 2/2 | 2.8 % (2/72) | 90.8 % | — |
| llama3.2:1b | react | 9.7 % | 5/6 | 8.3 % (6/72) | 90.7 % | 8.3 % |
| llama3.2:3b | single_shot | 55.6 % | 97.4 % | 54.2 % (39/72) | 21.8 % | — |
| llama3.2:3b | react | 54.2 % | 100 % | 54.2 % (39/72) | 24.1 % | 54.2 % |
| qwen2.5:3b | single_shot | 83.3 % | 97.7 % | 81.9 % (59/72) | 9.7 % | — |
| qwen2.5:3b | react | 87.5 % | 97.9 % | 86.1 % (62/72) | 20.2 % | 83.3 % |
| qwen2.5:7b | single_shot | 80.6 % | 97.7 % | 79.2 % (57/72) | 4.4 % | — |
| qwen2.5:7b | react | 94.4 % | 96.2 % | 91.7 % (66/72) | 0.0 % | 91.7 % |

With 72 tasks a single rate is uncertain by roughly ±10 points (e.g. 54.2 % → [43, 65] %); the
full table with intervals, the `react_no_error_feedback` rows, per-category results and all paired tests is in
[`reliability_eval/results/summary.md`](reliability_eval/results/summary.md).

### Findings

1. **Picking the tool is the hard part, not filling arguments.** Whenever a model chose the right tools, its
   arguments were right 96–100 % of the time.
2. **ReAct helps the strongest model, and only on multi-step tasks.** qwen2.5:7b: exact match 57 → 66 tasks
   (9 tasks better, 0 worse; McNemar p = 0.004). On the 20 multi-step tasks it went 35 % → 75 %; on the other
   52 tasks the gain is 1 task. qwen2.5:3b gained 3 tasks net (p = 0.51, not significant); llama3.2:3b gained
   nothing.
3. **Model family mattered more than size in this range.** At ~3B, Qwen beat Llama by ~21 tasks
   (p < 0.001). qwen2.5:7b vs qwen2.5:3b in ReAct: +6 tasks net (8 vs 2), p = 0.11, not significant, and all
   of it on multi-step tasks. llama3.2:1b was close to unusable.
4. **Error feedback was rarely used.** Feeding schema errors back recovered only 2 runs each for qwen2.5:3b
   and llama3.2:1b, and none for llama3.2:3b; qwen2.5:7b made no malformed calls in ReAct at all.

### Failure taxonomy (derived from the 864 traces)

Primary failure per failed run, all models and modes pooled:

| Failure | Runs | What it looks like in the traces |
|---|---|---|
| Schema hallucination | 193 | unknown argument keys; mostly llama3.2:1b pasting the tool's **JSON schema itself** as the arguments (45 of 56 tool tasks), e.g. `multiply({"type":"object","properties":{…}})` |
| Wrong tool | 49 | e.g. `subtract(120, -45)` for "add negative 45 and 120" |
| Invalid type / enum | 35 | `add(a="result of multiply", …)`, `get_employee(employee_id="result.employee_id")` |
| Incomplete chain | 28 | first step of a multi-step task done, then stopped |
| Parse failure | 25 | call written as JSON in the reply text instead of a structured call (llama3.2:3b in ReAct) |
| Unneeded call | 18 | `get_weather(city="Mars")` for "Which planet is the Red Planet?" |
| Wrong value | 9 | right tool, wrong argument (e.g. an unrequested `unit="fahrenheit"`) |
| Cyclic stagnation | 6 | the same broken call repeated; in one run qwen2.5:3b then guessed the wrong city and answered confidently |
| Argument omission / tool skipped / wrong answer | 2 / 2 / 2 | |

Separately, llama3.2:3b sent numbers as strings (`"12"`) in 33 single-shot calls; these were coerced and still counted as valid.

### Limitations

- One run per configuration at temperature 0: no estimate of run-to-run variance.
- 72 test tasks: differences under ~10 points are mostly not significant (see the paired tests).
- Synthetic mock tools and hand-written prompts; results may not transfer to real APIs or larger tool sets.
- Default Ollama quantisation (Q4_K_M; Q8_0 for the 1B model); full-precision models may behave differently.
- Scoring choices are strict in places (e.g. an unrequested non-default argument counts as wrong); the rules are in [`scoring.py`](reliability_eval/scoring.py). Relaxing that rule changes exact match by at most 1 task per configuration, so the findings do not depend on it.

## Reproduce

```bash
pip install "langgraph==1.2.23" "langchain-core==1.8.3" "langchain-ollama==1.1.0" "ollama==0.6.3" pytest
ollama pull llama3.2:3b && ollama pull qwen2.5:7b      # plus qwen2.5:3b, llama3.2:1b
python -m pytest reliability_eval/test_harness.py -q    # offline tests, no model needed
python -m reliability_eval.run_eval --split test --models llama3.2:3b qwen2.5:7b qwen2.5:3b llama3.2:1b --out results
python -m reliability_eval.report --out results
```

Or run [`reliability_eval/kaggle_tool_reliability.ipynb`](reliability_eval/kaggle_tool_reliability.ipynb) on Kaggle
(GPU T4, Internet on); the reported run took about 25 minutes end to end.

## Repository layout

```
reliability_eval/      tool-calling benchmark (tasks, tools, agents, scoring, stats, report, tests, results)
langgraph_ollama_local/, examples/, tests/, docs/, website/   upstream tutorial code (MIT, unchanged)
```
