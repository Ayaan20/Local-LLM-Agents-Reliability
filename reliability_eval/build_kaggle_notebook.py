"""Build a self-contained Kaggle notebook that embeds the harness source.

    python reliability_eval/build_kaggle_notebook.py  ->  reliability_eval/kaggle_tool_reliability.ipynb
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
FILES = ["__init__.py", "__main__.py", "tools.py", "tasks.py", "scoring.py", "agents.py",
         "stats.py", "run_eval.py", "report.py", "test_harness.py"]

MODELS = ["llama3.2:3b", "qwen2.5:7b", "qwen2.5:3b", "llama3.2:1b"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


cells = [md(f"""
# Local LLM agents: tool-calling reliability benchmark

Runs a held-out suite of **72 test tasks** (plus 12 dev tasks) with known-correct tool calls against
local open-weight models served by **Ollama**, in three modes:

* `single_shot`: one model reply; every needed tool call must be in it
* `react`: LangGraph ReAct loop; schema errors are fed back to the model
* `react_no_error_feedback`: same loop, but the first bad call ends the run (ablation)

Models: {", ".join(f"`{m}`" for m in MODELS)}. Temperature 0, seed 42, context 4096, recursion limit 25.

**How to run on Kaggle**
1. *Settings → Accelerator → GPU T4 x2* (or P100). *Settings → Internet → On* (needs a phone-verified account).
2. Click **Save Version → Save & Run All (Commit)**. It runs in the background; you can close the tab.
3. When it finishes, open the version → **Output** → download `results.zip`
   (`summary.md`, `scores.csv`, `traces.jsonl`, `examples.md`, `env_*.json`).

The run is resumable: if it stops, re-running skips tasks already in `traces.jsonl`.
"""),
    code("""
import os, sys, subprocess, time, json, urllib.request
from pathlib import Path
WORK = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path.cwd()
os.chdir(WORK)
MODELS = %s
MODELS_STR = " ".join(MODELS)
OUT = WORK / "results"
print("work dir:", WORK)
!nvidia-smi --query-gpu=name,memory.total --format=csv
""" % json.dumps(MODELS)),
    md("## 1. Install and start Ollama"),
    code("""
!apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y zstd pciutils lshw >/dev/null 2>&1
!curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -3
!ollama --version
"""),
    code("""
log = open(WORK / "ollama_server.log", "w")
server = subprocess.Popen(["ollama", "serve"], stdout=log, stderr=subprocess.STDOUT,
                          env={**os.environ, "OLLAMA_KEEP_ALIVE": "30m", "OLLAMA_HOST": "127.0.0.1:11434"})
for _ in range(60):
    try:
        print(urllib.request.urlopen("http://127.0.0.1:11434/api/version").read().decode()); break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("Ollama server did not start; see ollama_server.log")
"""),
    code("""
for m in MODELS:
    t0 = time.time()
    subprocess.run(["ollama", "pull", m], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"pulled {m} in {time.time()-t0:.0f}s")
!ollama list
"""),
    md("## 2. Python dependencies (pinned to the versions the harness was tested with)"),
    code("""
!pip install -q "langgraph==1.2.23" "langchain-core==1.8.3" "langchain-ollama==1.1.0" "ollama==0.6.3" pytest
"""),
    md("## 3. Write the harness source"),
]
for f in FILES:
    src = (HERE / f).read_text()
    cells.append(code(f"%%writefile reliability_eval/{f}\n" + src) if f != "__init__.py" else
                 code("!mkdir -p reliability_eval\n"))
    if f == "__init__.py":
        cells.append(code("%%writefile reliability_eval/__init__.py\n" + src))

cells += [
    md("## 4. Offline tests of the harness (scripted fake model, no LLM)"),
    code("!python -m pytest reliability_eval/test_harness.py -q -p no:cacheprovider\n"
         "!python -m reliability_eval.tasks"),
    md("## 5. Dev-split smoke test (12 tasks, first model only). Not used in reported numbers."),
    code("""
!python -m reliability_eval.run_eval --split dev --models {MODELS[0]} --modes single_shot react --out results_dev
!python -m reliability_eval.report --out results_dev --split dev > /dev/null && head -20 results_dev/summary.md
""".replace("{MODELS[0]}", MODELS[0])),
    md("## 6. Full held-out test run (72 tasks × 3 modes × all models)"),
    code("""
t0 = time.time()
!python -m reliability_eval.run_eval --split test --models {MODELS_STR} --out results
print(f"test run wall time: {(time.time()-t0)/60:.1f} min")
"""),
    md("## 7. Report"),
    code("""
!python -m reliability_eval.report --out results --split test > /dev/null
from IPython.display import Markdown, display
display(Markdown((OUT / "summary.md").read_text()))
"""),
    code("""
!cp reliability_eval/tasks.jsonl results/ 2>/dev/null; cp ollama_server.log results/ 2>/dev/null
!cd /kaggle/working 2>/dev/null; zip -qr results.zip results results_dev && ls -lh results.zip
"""),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                  "name": "python3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = HERE / "kaggle_tool_reliability.ipynb"
out.write_text(json.dumps(nb, indent=1))
print("wrote", out, len(cells), "cells")
