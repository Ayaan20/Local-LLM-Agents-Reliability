"""Score traces and write the report.

    python -m reliability_eval.report --out results [--split test]

Writes  scores.csv, summary.json, summary.md, examples.md  into --out.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .scoring import README_CLASS, score_run
from .stats import fmt_pct, mcnemar
from .tasks import load_tasks

MODE_ORDER = ["single_shot", "react", "react_no_error_feedback"]
CATS = ["single_simple", "single_args", "multi_step", "no_tool"]


def load(out: Path, split: str):
    tasks = {t["id"]: t for t in load_tasks("all")}
    runs = {}
    for line in (out / "traces.jsonl").read_text().splitlines():
        r = json.loads(line)
        if split != "all" and r.get("split") != split:
            continue
        runs[(r["model"], r["mode"], r["task_id"])] = r  # last write wins
    scores = [score_run(tasks[k[2]], r) for k, r in runs.items()]
    return tasks, runs, scores


def _k(rows, key, val=True):
    return sum(1 for r in rows if r[key] == val)


def aggregate(rows):
    n = len(rows)
    tool_rows = [r for r in rows if r["category"] != "no_tool"]
    sel_ok = [r for r in tool_rows if r["selection_ok"]]
    att = sum(r["n_attempts"] for r in rows)
    mal = sum(r["n_malformed"] for r in rows)
    loop = rows and rows[0]["mode"] != "single_shot"
    d = {
        "n_tasks": n,
        "selection": (_k(rows, "selection_ok"), n),
        "args_given_selection": (_k(sel_ok, "args_ok"), len(sel_ok)),
        "exact": (_k(rows, "exact_match"), n),
        "exact_tool_tasks": (_k(tool_rows, "exact_match"), len(tool_rows)),
        "malformed_attempts": (mal, att),
        "tasks_with_malformed": (_k(rows, "any_malformed"), n),
        "tool_errors": sum(r["n_tool_error"] for r in rows),
        "type_drift_attempts": sum(r["n_type_drift"] for r in rows),
        "success": (_k(rows, "success"), n) if loop else None,
        "recovered": _k(rows, "recovered") if loop else None,
        "answer_ok_but_call_wrong": _k(rows, "answer_ok_but_call_wrong"),
        "mean_latency_s": round(sum(r["latency_s"] for r in rows) / max(n, 1), 2),
        "total_latency_s": round(sum(r["latency_s"] for r in rows), 1),
        "mean_llm_calls": round(sum(r["llm_calls"] for r in rows) / max(n, 1), 2),
        "stop_reasons": dict(Counter(r["stop_reason"] for r in rows)),
    }
    return d


def paired(rows_a, rows_b, key):
    a = {r["task_id"]: bool(r[key]) for r in rows_a}
    b = {r["task_id"]: bool(r[key]) for r in rows_b}
    ids = sorted(set(a) & set(b))
    both = sum(a[i] and b[i] for i in ids)
    only_a = sum(a[i] and not b[i] for i in ids)
    only_b = sum(b[i] and not a[i] for i in ids)
    neither = len(ids) - both - only_a - only_b
    return {"n": len(ids), "a_right": both + only_a, "b_right": both + only_b, "both": both,
            "only_a": only_a, "only_b": only_b, "neither": neither,
            "p_mcnemar": round(mcnemar(only_a, only_b), 4)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--split", default="test")
    a = ap.parse_args(argv)
    out = Path(a.out)
    tasks, runs, scores = load(out, a.split)
    if not scores:
        raise SystemExit("no runs found for this split")

    with open(out / "scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(scores[0]))
        w.writeheader()
        for s in scores:
            w.writerow({**s, "labels": "|".join(s["labels"])})

    groups = defaultdict(list)
    for s in scores:
        groups[(s["model"], s["mode"])].append(s)
    models = list(dict.fromkeys(s["model"] for s in scores))
    keys = [(m, md) for m in models for md in MODE_ORDER if (m, md) in groups]
    agg = {f"{m}|{md}": aggregate(groups[(m, md)]) for m, md in keys}

    L = [f"# Tool-calling reliability results ({a.split} split)\n"]
    n_tasks = len({s['task_id'] for s in scores})
    cat_n = Counter(tasks[t]["category"] for t in {s['task_id'] for s in scores})
    L.append(f"Tasks: **{n_tasks}** ({', '.join(f'{c} {cat_n[c]}' for c in CATS)}). "
             "Temperature 0. Cells show `% (k/n) [95% Wilson CI]`.\n")

    L.append("## 1. Main table\n")
    L.append("| Model | Mode | Tool selection acc. | Arg. correctness (given right tools) | "
             "Exact call match | Malformed call rate (per attempt) | Tasks with ≥1 malformed | "
             "End-to-end success | Mean s/task | Mean LLM calls |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for m, md in keys:
        g = agg[f"{m}|{md}"]
        succ = fmt_pct(*g["success"]) if g["success"] else "— (no final answer in single-shot)"
        L.append(f"| {m} | {md} | {fmt_pct(*g['selection'])} | {fmt_pct(*g['args_given_selection'])} | "
                 f"{fmt_pct(*g['exact'])} | {fmt_pct(*g['malformed_attempts'])} | "
                 f"{fmt_pct(*g['tasks_with_malformed'])} | {succ} | {g['mean_latency_s']} | "
                 f"{g['mean_llm_calls']} |")
    L.append("\nDefinitions: selection = the set/sequence of successfully executed tool names equals "
             "the ground truth (for no_tool tasks: no call at all). Argument correctness is measured "
             "only on tasks where selection was right. Exact = both. Malformed = unknown tool, "
             "unknown/missing argument, uncoercible type/enum, or unparseable / text-only call. "
             "Success (loop modes) = exact match AND the run finished AND the final answer "
             "contains the expected value.\n")

    L.append("## 2. Exact call match by category\n")
    L.append("| Model | Mode | " + " | ".join(CATS) + " |")
    L.append("|---|---|" + "---|" * len(CATS))
    for m, md in keys:
        cells = []
        for c in CATS:
            rows = [r for r in groups[(m, md)] if r["category"] == c]
            cells.append(fmt_pct(_k(rows, "exact_match"), len(rows)))
        L.append(f"| {m} | {md} | " + " | ".join(cells) + " |")

    L.append("\n## 3. Paired comparisons (same tasks)\n")
    L.append("`only A` / `only B` = tasks exactly one system got right; only these drive the "
             "exact McNemar p-value. A gap of g points on n tasks = g·n/100 tasks.\n")
    L.append("| Comparison | Metric | Subset | n | A right | B right | only A | only B | gap (pts) | p |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    comps = []
    for m in models:
        for x, y, metric in [("react", "single_shot", "exact_match"),
                             ("react", "react_no_error_feedback", "success")]:
            if (m, x) in groups and (m, y) in groups:
                comps.append((f"{m}: {x} (A) vs {y} (B)", groups[(m, x)], groups[(m, y)], metric))
    for x, y in [("qwen2.5:7b", "qwen2.5:3b"), ("llama3.2:3b", "llama3.2:1b"),
                 ("qwen2.5:3b", "llama3.2:3b"), ("qwen2.5:7b", "llama3.2:3b")]:
        for md in MODE_ORDER:
            if (x, md) in groups and (y, md) in groups:
                comps.append((f"{md}: {x} (A) vs {y} (B)", groups[(x, md)], groups[(y, md)],
                              "success" if md != "single_shot" else "exact_match"))
    pair_json = []
    for name, ra, rb, metric in comps:
        for subset, f in [("all", lambda r: True),
                          ("excluding multi_step", lambda r: r["category"] != "multi_step")]:
            p = paired([r for r in ra if f(r)], [r for r in rb if f(r)], metric)
            gap = 100 * (p["a_right"] - p["b_right"]) / max(p["n"], 1)
            L.append(f"| {name} | {metric} | {subset} | {p['n']} | {p['a_right']} | {p['b_right']} | "
                     f"{p['only_a']} | {p['only_b']} | {gap:+.1f} | {p['p_mcnemar']} |")
            pair_json.append({"comparison": name, "metric": metric, "subset": subset, **p,
                              "gap_pts": round(gap, 1)})

    L.append("\n## 4. Failure taxonomy (primary label per failed run)\n")
    labels = sorted({s["primary_failure"] for s in scores if s["primary_failure"]})
    L.append("| Model | Mode | failed runs | " + " | ".join(labels) + " |")
    L.append("|---|---|---|" + "---|" * len(labels))
    tax = {}
    for m, md in keys:
        c = Counter(r["primary_failure"] for r in groups[(m, md)] if r["primary_failure"])
        tax[f"{m}|{md}"] = dict(c)
        L.append(f"| {m} | {md} | {sum(c.values())} | " + " | ".join(str(c.get(l, 0)) for l in labels) + " |")
    allc = Counter(s["primary_failure"] for s in scores if s["primary_failure"])
    L.append("\nAll runs pooled: " + ", ".join(f"{k} {v}" for k, v in allc.most_common()))
    readme = Counter()
    for s in scores:
        for lab in s["labels"]:
            readme[README_CLASS.get(lab, f"(extra) {lab}")] += 1
    L.append("\nMulti-label counts grouped into the README's four classes (+ extra classes found):\n")
    for k, v in sorted(readme.items()):
        L.append(f"- {k}: {v}")

    L.append("\n## 5. Recovery and 'answer looked right' (loop modes)\n")
    for m, md in keys:
        g = agg[f"{m}|{md}"]
        L.append(f"- {m} | {md}: recovered after an error = {g['recovered']}; final answer contained the "
                 f"expected value but the tool call was wrong = {g['answer_ok_but_call_wrong']}; "
                 f"type-drift attempts (coerced) = {g['type_drift_attempts']}; tool errors = {g['tool_errors']}; "
                 f"stop reasons = {g['stop_reasons']}")

    L.append("\n## 6. Run time\n")
    for m, md in keys:
        g = agg[f"{m}|{md}"]
        L.append(f"- {m} | {md}: {g['total_latency_s']} s model time over {g['n_tasks']} tasks "
                 f"(mean {g['mean_latency_s']} s/task)")
    envs = sorted(out.glob("env_*.json"))
    if envs:
        e = json.loads(envs[-1].read_text())
        L.append(f"\nEnvironment: GPU {e.get('gpu')}; Ollama {e.get('ollama_version')}; "
                 f"packages {e.get('packages')}; models {json.dumps(e.get('models'))}")

    (out / "summary.md").write_text("\n".join(L) + "\n")
    (out / "summary.json").write_text(json.dumps({"aggregate": agg, "paired": pair_json,
                                                  "taxonomy_primary": tax}, indent=2, default=str))

    # ---- examples for interview stories
    E = ["# Example failures (up to 2 per label)\n"]
    by_label = defaultdict(list)
    for s in scores:
        if s["primary_failure"]:
            by_label[s["primary_failure"]].append(s)
    for lab, rows in sorted(by_label.items()):
        E.append(f"## {lab} ({len(rows)} runs)\n")
        for s in rows[:2]:
            t = tasks[s["task_id"]]
            r = runs[(s["model"], s["mode"], s["task_id"])]
            E.append(f"**{s['model']} | {s['mode']} | {t['id']}**: {t['prompt']}")
            E.append(f"- expected: `{json.dumps(t['expected_calls'])}`")
            for at in r["attempts"]:
                E.append(f"- attempt: `{at.get('name')}({json.dumps(at.get('raw_args'), default=str)})` "
                         f"→ {at['status']}" + (f" ({at['error'][:120]})" if at.get("error") else ""))
            E.append(f"- final text: {r.get('final_text', '')[:200]!r}; stop: {r['stop_reason']}\n")
    (out / "examples.md").write_text("\n".join(E) + "\n")
    print((out / "summary.md").read_text())


if __name__ == "__main__":
    main()
