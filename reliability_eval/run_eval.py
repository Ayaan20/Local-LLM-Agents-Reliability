"""Run the benchmark against models served by Ollama.

    python -m reliability_eval.run_eval --split test \
        --models llama3.2:3b qwen2.5:3b qwen2.5:7b llama3.2:1b \
        --modes single_shot react react_no_error_feedback --out results

Resumable: runs already in <out>/traces.jsonl are skipped.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .agents import MODES, Runner, make_llm
from .tasks import load_tasks


def _get(url: str, data: dict | None = None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def environment(base_url: str, models: list[str]) -> dict:
    env = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "python": sys.version.split()[0], "platform": platform.platform(), "packages": {}}
    for p in ("langgraph", "langchain-core", "langchain-ollama", "ollama", "pydantic"):
        try:
            env["packages"][p] = version(p)
        except PackageNotFoundError:
            env["packages"][p] = None
    try:
        env["ollama_version"] = _get(f"{base_url}/api/version").get("version")
    except Exception as e:
        env["ollama_version"] = f"unavailable: {e}"
    env["models"] = {}
    tags = {}
    try:
        tags = {m["name"]: m for m in _get(f"{base_url}/api/tags").get("models", [])}
    except Exception:
        pass
    for m in models:
        info = {"digest": tags.get(m, {}).get("digest"), "size_bytes": tags.get(m, {}).get("size")}
        try:
            d = _get(f"{base_url}/api/show", {"model": m}).get("details", {})
            info.update(parameter_size=d.get("parameter_size"), quantization=d.get("quantization_level"),
                        family=d.get("family"), format=d.get("format"))
        except Exception:
            pass
        env["models"][m] = info
    try:
        env["gpu"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        env["gpu"] = None
    return env


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["llama3.2:3b", "qwen2.5:7b"])
    ap.add_argument("--modes", nargs="+", default=list(MODES), choices=MODES)
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--tasks", nargs="*", help="only these task ids")
    ap.add_argument("--out", default="results")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--recursion-limit", type=int, default=25)  # same as repo config.py
    ap.add_argument("--num-ctx", type=int, default=4096)        # same as repo config.py
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(a.split)
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in set(a.tasks)]
    trace_path = out / "traces.jsonl"
    done = set()
    if trace_path.exists():
        for line in trace_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["model"], r["mode"], r["task_id"]))

    env = environment(a.base_url, a.models)
    env.update(split=a.split, n_tasks=len(tasks), modes=a.modes, recursion_limit=a.recursion_limit,
               num_ctx=a.num_ctx, seed=a.seed, temperature=0.0)
    (out / f"env_{int(time.time())}.json").write_text(json.dumps(env, indent=2))
    print(json.dumps(env, indent=2))

    t_all = time.perf_counter()
    with open(trace_path, "a") as f:
        for model in a.models:
            runner = Runner(make_llm(model, a.base_url, a.num_ctx, a.seed), a.recursion_limit)
            # warm-up so the first timed task does not include model loading
            t0 = time.perf_counter()
            runner.llm_tools.invoke("Say OK.")
            print(f"[{model}] loaded in {time.perf_counter() - t0:.1f}s", flush=True)
            for mode in a.modes:
                t_mode = time.perf_counter()
                for i, task in enumerate(tasks, 1):
                    if (model, mode, task["id"]) in done:
                        continue
                    try:
                        tr = runner.run(mode, task["prompt"])
                    except Exception as e:  # never lose the whole run to one task
                        tr = {"attempts": [], "turns": [], "final_text": "",
                              "stop_reason": f"exception: {type(e).__name__}: {e}", "messages": []}
                    tr.update(model=model, mode=mode, task_id=task["id"], split=task["split"])
                    f.write(json.dumps(tr, default=str) + "\n")
                    f.flush()
                    calls = [x["name"] for x in tr["attempts"]]
                    print(f"[{model}|{mode}] {i}/{len(tasks)} {task['id']:7s} "
                          f"{tr.get('wall_s', 0):6.2f}s stop={tr['stop_reason']} calls={calls}",
                          flush=True)
                print(f"[{model}|{mode}] done in {time.perf_counter() - t_mode:.0f}s", flush=True)
    print(f"ALL DONE in {time.perf_counter() - t_all:.0f}s")


if __name__ == "__main__":
    main()
